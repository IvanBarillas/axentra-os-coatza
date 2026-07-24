"""Crea identidades de prueba para todos los roles funcionales de Inventory."""

from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.inventory.permissions import InventoryPermissions
from apps.security.models.accounts import UserProfile
from apps.security.models.infrastructure import AppModule, UserAppRole
from apps.security.models.organigrama import AreaOperativa, Dependencia


@dataclass(frozen=True, slots=True)
class InventoryRoleFixture:
    role: str
    email: str
    first_name: str
    last_name: str
    puesto: str
    dependencia: str
    area: str
    sede: str = "TESORERIA MUNICIPAL"


ROLE_FIXTURES = (
    InventoryRoleFixture(
        "owner",
        "inventory.owner@axentra.com.mx",
        "Olivia",
        "Owner Inventory",
        "Responsable general de pruebas",
        "PATRIMONIO MUNICIPAL",
        "CAPTURISTA",
    ),
    InventoryRoleFixture(
        "admin",
        "inventory.admin@axentra.com.mx",
        "Adriana",
        "Administradora Inventory",
        "Administradora de Inventario",
        "PATRIMONIO MUNICIPAL",
        "CAPTURISTA",
    ),
    InventoryRoleFixture(
        "admin_patrimonio",
        "inventory.patrimonio@axentra.com.mx",
        "Patricia",
        "Patrimonio Municipal",
        "Administradora de Patrimonio",
        "PATRIMONIO MUNICIPAL",
        "CAPTURISTA",
    ),
    InventoryRoleFixture(
        "adquisiciones",
        "inventory.adquisiciones@axentra.com.mx",
        "Andrea",
        "Adquisiciones",
        "Operadora de Adquisiciones",
        "DIRECCION DE EGRESOS",
        "PROVEEDORES",
    ),
    InventoryRoleFixture(
        "almacenista",
        "inventory.almacenista@axentra.com.mx",
        "Alberto",
        "Almacenista",
        "Responsable de Almacén Patrimonial",
        "PATRIMONIO MUNICIPAL",
        "PARQUE VEHICULAR",
    ),
    InventoryRoleFixture(
        "auditor",
        "inventory.auditor@axentra.com.mx",
        "Aurora",
        "Auditora",
        "Auditora Patrimonial",
        "RECURSOS HUMANOS",
        "CAPACITACION",
    ),
    InventoryRoleFixture(
        "editor",
        "inventory.editor@axentra.com.mx",
        "Esteban",
        "Editor",
        "Operador de Inventario",
        "INNOVACION GUBERNAMENTAL",
        "SOPORTE TECNICO",
    ),
    InventoryRoleFixture(
        "reviewer",
        "inventory.reviewer@axentra.com.mx",
        "Rebeca",
        "Revisora",
        "Revisora Patrimonial",
        "RECURSOS HUMANOS",
        "CAPACITACION",
    ),
    InventoryRoleFixture(
        "director",
        "inventory.director@axentra.com.mx",
        "Daniel",
        "Director de Egresos",
        "Director de la Dependencia",
        "DIRECCION DE EGRESOS",
        "PAGOS",
    ),
    InventoryRoleFixture(
        "resguardatario",
        "inventory.resguardatario@axentra.com.mx",
        "Rafael",
        "Resguardatario",
        "Servidor Público Resguardatario",
        "DIRECCION DE EGRESOS",
        "PAGOS",
    ),
    InventoryRoleFixture(
        "viewer",
        "inventory.viewer@axentra.com.mx",
        "Valeria",
        "Consulta",
        "Usuario de Consulta",
        "DIRECCION DE EGRESOS",
        "PAGOS",
    ),
)


class Command(BaseCommand):
    help = (
        "Crea usuarios, perfiles y membresías para probar todos los roles "
        "de Inventory. Uso exclusivo de desarrollo y QA."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="Inventory2026@Test",
            help="Contraseña inicial para usuarios nuevos.",
        )
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="También reemplaza la contraseña de usuarios existentes.",
        )
        parser.add_argument(
            "--allow-non-debug",
            action="store_true",
            help=(
                "Permite la ejecución con DEBUG=False. Debe usarse solamente "
                "en un ambiente aislado de QA."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options["allow_non_debug"]:
            raise CommandError(
                "Este comando crea cuentas de prueba y está bloqueado cuando "
                "DEBUG=False. Para un QA aislado use --allow-non-debug."
            )

        password = str(options["password"] or "").strip()
        if len(password) < 12:
            raise CommandError(
                "La contraseña de prueba debe contener al menos 12 caracteres."
            )

        declared_roles = set(InventoryPermissions.ROLE_MAPPING)
        fixture_roles = {fixture.role for fixture in ROLE_FIXTURES}
        if fixture_roles != declared_roles:
            missing = sorted(declared_roles - fixture_roles)
            unknown = sorted(fixture_roles - declared_roles)
            raise CommandError(
                "Las cuentas de prueba no coinciden con ROLE_MAPPING. "
                f"Faltantes={missing}; desconocidos={unknown}."
            )

        try:
            inventory_app = AppModule.objects.get(
                slug="inventory",
                is_deleted=False,
            )
        except AppModule.DoesNotExist as exc:
            raise CommandError(
                "Inventory no está registrado en AppModule. Ejecute primero "
                "`python manage.py migrate` y "
                "`python manage.py check_axentra_modules --persist`."
            ) from exc
        if not inventory_app.is_active:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️ Inventory está desactivado. Las cuentas se crearán, "
                    "pero no podrán entrar hasta activar el módulo."
                )
            )

        User = get_user_model()
        created_users = 0
        updated_users = 0
        created_roles = 0
        updated_roles = 0
        users_by_role = {}

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n🧪 === USUARIOS FUNCIONALES DE INVENTORY ==="
            )
        )

        for fixture in ROLE_FIXTURES:
            area = self._resolve_area(fixture)
            self._migrate_legacy_test_email(User, fixture.email)
            user, created = User.objects.get_or_create(
                email=fixture.email,
                defaults={
                    "first_name": fixture.first_name,
                    "last_name": fixture.last_name,
                    "is_staff": False,
                    "is_superuser": False,
                    "is_active": True,
                },
            )

            user.first_name = fixture.first_name
            user.last_name = fixture.last_name
            user.is_staff = False
            user.is_superuser = False
            user.is_active = True
            self._set_if_present(user, "is_deleted", False)
            self._set_if_present(user, "deleted_at", None)
            self._set_if_present(user, "is_email_verified", True)
            self._set_if_present(user, "must_change_password", False)
            self._set_if_present(user, "is_manager", False)

            if created or options["reset_passwords"]:
                user.set_password(password)
            user.save()

            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "area": area,
                    "puesto": fixture.puesto,
                    "is_active": True,
                    "is_deleted": False,
                    "deleted_at": None,
                },
            )

            membership, role_created = UserAppRole.objects.update_or_create(
                user=user,
                app=inventory_app,
                defaults={
                    "role": fixture.role,
                    "permissions_list": list(
                        InventoryPermissions.ROLE_MAPPING[fixture.role]
                    ),
                    "is_active": True,
                    "is_deleted": False,
                    "deleted_at": None,
                },
            )

            users_by_role[fixture.role] = user
            created_users += int(created)
            updated_users += int(not created)
            created_roles += int(role_created)
            updated_roles += int(not role_created)

            action = "CREADO" if created else "VERIFICADO"
            self.stdout.write(
                f"   [{action:<10}] {fixture.role:<18} "
                f"{fixture.email:<42} "
                f"{area.dependencia.nombre} / {area.nombre}"
            )

        self._assign_department_manager(users_by_role["director"])

        self.stdout.write(
            self.style.SUCCESS(
                "\n✅ Usuarios: "
                f"{created_users} creados, {updated_users} verificados. "
                "Membresías: "
                f"{created_roles} creadas, {updated_roles} sincronizadas."
            )
        )
        if created_users or options["reset_passwords"]:
            self.stdout.write(
                self.style.WARNING(
                    f"🔑 Contraseña de pruebas configurada: {password}"
                )
            )
        else:
            self.stdout.write(
                "🔐 Las contraseñas existentes fueron conservadas. "
                "Use --reset-passwords para reemplazarlas."
            )

    @staticmethod
    def _set_if_present(instance, field_name, value):
        if hasattr(instance, field_name):
            setattr(instance, field_name, value)

    @staticmethod
    def _migrate_legacy_test_email(User, valid_email):
        """Conserva UUID y relaciones de cuentas creadas con el dominio .test."""

        legacy_email = valid_email.replace(
            "@axentra.com.mx",
            "@axentra.test",
        )
        legacy_user = User.objects.filter(email=legacy_email).first()
        if legacy_user is None:
            return

        if not User.objects.filter(email=valid_email).exists():
            legacy_user.email = valid_email
            update_fields = ["email"]
            if hasattr(legacy_user, "updated_at"):
                update_fields.append("updated_at")
            legacy_user.save(update_fields=update_fields)
            return

        # Si ambas cuentas existen, se conserva la dirección válida y la
        # identidad antigua queda fuera de cualquier listado operativo.
        legacy_user.is_active = False
        if hasattr(legacy_user, "is_deleted"):
            legacy_user.is_deleted = True
        if hasattr(legacy_user, "deleted_at"):
            from django.utils import timezone

            legacy_user.deleted_at = timezone.now()
        legacy_user.save()

    @staticmethod
    def _resolve_area(fixture):
        try:
            return AreaOperativa.objects.select_related(
                "dependencia",
                "sede_fisica",
            ).get(
                nombre=fixture.area,
                dependencia__nombre=fixture.dependencia,
                sede_fisica__nombre=fixture.sede,
                is_active=True,
                is_deleted=False,
            )
        except AreaOperativa.DoesNotExist as exc:
            raise CommandError(
                "No existe el área requerida para el rol "
                f"[{fixture.role}]: {fixture.area}@{fixture.sede}, "
                f"dependencia {fixture.dependencia}. "
                "Ejecute primero `python manage.py seed_core_data`."
            ) from exc
        except AreaOperativa.MultipleObjectsReturned as exc:
            raise CommandError(
                "El organigrama contiene más de un área activa para "
                f"{fixture.area}@{fixture.sede} dentro de "
                f"{fixture.dependencia}."
            ) from exc

    @staticmethod
    def _assign_department_manager(director):
        dependencia = Dependencia.objects.get(
            nombre="DIRECCION DE EGRESOS",
            is_deleted=False,
        )
        if dependencia.encargado_departamento_id != director.id:
            dependencia.encargado_departamento = director
            dependencia.save(
                update_fields=[
                    "encargado_departamento",
                    "updated_at",
                ]
            )


__all__ = ["InventoryRoleFixture", "ROLE_FIXTURES"]
