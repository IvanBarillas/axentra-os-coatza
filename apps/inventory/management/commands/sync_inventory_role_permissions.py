"""Sincroniza snapshots de permisos de un rol de Inventory bajo demanda."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.inventory.permissions import InventoryPermissions
from apps.security.models import UserAppRole


class Command(BaseCommand):
    help = (
        "Actualiza permissions_list de las membresías de un rol de Inventory "
        "conforme al manifiesto vigente. Sin --apply sólo muestra los cambios."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--role",
            required=True,
            help="Rol funcional que se desea sincronizar, por ejemplo director.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Confirma la escritura de los nuevos permisos.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        role = str(options["role"] or "").strip().lower()
        expected = InventoryPermissions.ROLE_MAPPING.get(role)
        if expected is None:
            available = ", ".join(sorted(InventoryPermissions.ROLE_MAPPING))
            raise CommandError(
                f"El rol [{role}] no existe. Roles disponibles: {available}."
            )

        memberships = UserAppRole.objects.filter(
            app__slug=str(InventoryPermissions.APP_CODE),
            role__iexact=role,
            is_active=True,
            is_deleted=False,
        ).select_related("user", "app")

        changed = 0
        for membership in memberships:
            current = list(membership.permissions_list or [])
            if current == list(expected):
                self.stdout.write(
                    self.style.SUCCESS(f"Sin cambios: {membership.user}")
                )
                continue
            changed += 1
            removed = sorted(set(current) - set(expected))
            added = sorted(set(expected) - set(current))
            self.stdout.write(f"Usuario: {membership.user}")
            if removed:
                self.stdout.write(f"  Se retirarán: {', '.join(removed)}")
            if added:
                self.stdout.write(f"  Se agregarán: {', '.join(added)}")
            if options["apply"]:
                membership.permissions_list = list(expected)
                membership.save(update_fields=["permissions_list", "updated_at"])

        if not options["apply"]:
            transaction.set_rollback(True)
            self.stdout.write(
                self.style.WARNING(
                    f"Vista previa terminada: {changed} membresía(s) cambiarían. "
                    "Ejecute nuevamente con --apply para confirmar."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sincronización terminada: {changed} membresía(s) actualizadas."
                )
            )
