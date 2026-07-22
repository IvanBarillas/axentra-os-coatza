"""Diagnóstico de preparación funcional de Inventory sin modificar datos."""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

from apps.inventory.models import Asset, AssetDocument, DepreciationPolicy
from apps.inventory.models.document_models import DocumentValidationStatus
from apps.inventory.selectors import FinancialSelectors


class Command(BaseCommand):
    help = "Revisa migraciones, configuración financiera y expedientes pendientes de Inventory."

    def add_arguments(self, parser):
        parser.add_argument("--strict", action="store_true", help="Devuelve error cuando encuentra bloqueadores.")

    def handle(self, *args, **options):
        blockers = []; warnings = []
        applied = {name for app, name in MigrationRecorder(connection).applied_migrations() if app == "inventory"}
        latest = max(applied) if applied else "ninguna"
        self.stdout.write(self.style.MIGRATE_HEADING("Diagnóstico de Inventory"))
        self.stdout.write(f"Migración más reciente aplicada: {latest}")
        if "0008_document_movement_request_owner" not in applied:
            blockers.append("La migración 0008 de Inventory no está aplicada.")

        official_assets = Asset.objects.filter(is_deleted=False).count()
        capitalizable_assets = Asset.objects.filter(is_deleted=False, is_capitalizable=True).count()
        uncovered = FinancialSelectors.assets_without_policy()
        policy_count = DepreciationPolicy.objects.filter(is_deleted=False, is_active=True).count()
        pending_documents = AssetDocument.objects.filter(is_deleted=False, validation_status=DocumentValidationStatus.PENDING).count()

        self.stdout.write(f"Bienes oficiales: {official_assets}")
        self.stdout.write(f"Bienes capitalizables: {capitalizable_assets}")
        self.stdout.write(f"Políticas financieras activas: {policy_count}")
        self.stdout.write(f"Documentos pendientes de validación: {pending_documents}")
        self.stdout.write(f"Bienes sin política aplicable: {len(uncovered)}")

        if capitalizable_assets and not policy_count:
            blockers.append("Existen bienes capitalizables, pero no hay políticas de depreciación.")
        if uncovered:
            blockers.append(f"{len(uncovered)} bienes capitalizables no tienen política vigente.")
        if pending_documents:
            warnings.append(f"Hay {pending_documents} documentos pendientes de validación.")

        for message in warnings:
            self.stdout.write(self.style.WARNING(f"ADVERTENCIA: {message}"))
        for message in blockers:
            self.stdout.write(self.style.ERROR(f"BLOQUEADOR: {message}"))
        if blockers and options["strict"]:
            raise CommandError("Inventory no está listo: corrija los bloqueadores indicados.")
        if blockers:
            self.stdout.write(self.style.WARNING("Diagnóstico terminado con bloqueadores."))
        else:
            self.stdout.write(self.style.SUCCESS("Inventory superó las comprobaciones de preparación."))
