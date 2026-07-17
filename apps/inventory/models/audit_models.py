# apps/inventory/models/audit_models.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.inventory.models.catalog_models import (
    InventoryBaseModel,
    PhysicalCondition,
)


# =============================================================================
# AUDITORÍA FÍSICA
# =============================================================================


class PhysicalAuditScope(models.TextChoices):
    ANNUAL = "ANNUAL", "Inventario anual"
    PARTIAL = "PARTIAL", "Revisión parcial"
    DEPARTMENT = "DEPARTMENT", "Revisión por dependencia"
    LOCATION = "LOCATION", "Revisión por sede"
    SPECIAL = "SPECIAL", "Auditoría especial"


class PhysicalAuditStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    PREPARING = "PREPARING", "Preparando inventario"
    FROZEN = "FROZEN", "Inventario congelado"
    IN_PROGRESS = "IN_PROGRESS", "En levantamiento"
    RECONCILIATION = "RECONCILIATION", "En conciliación"
    CLOSED = "CLOSED", "Cerrada"
    CANCELLED = "CANCELLED", "Cancelada"


class PhysicalAuditResult(models.TextChoices):
    PENDING = "PENDING", "Pendiente de revisión"
    FOUND = "FOUND", "Encontrado y conciliado"
    NOT_FOUND = "NOT_FOUND", "No localizado"
    FOUND_DIFFERENT_LOCATION = (
        "FOUND_DIFFERENT_LOCATION",
        "Encontrado en ubicación diferente",
    )
    FOUND_DIFFERENT_CUSTODIAN = (
        "FOUND_DIFFERENT_CUSTODIAN",
        "Encontrado con resguardatario diferente",
    )
    FOUND_DIFFERENT_LOCATION_AND_CUSTODIAN = (
        "FOUND_DIFFERENT_LOCATION_AND_CUSTODIAN",
        "Ubicación y resguardatario diferentes",
    )
    DAMAGED = "DAMAGED", "Encontrado con daño"
    UNREGISTERED = "UNREGISTERED", "Sobrante no registrado"
    EXCLUDED = "EXCLUDED", "Excluido con justificación"


class PhysicalAuditSession(InventoryBaseModel):
    """
    Periodo formal de levantamiento físico.

    Al congelar la sesión se debe generar un PhysicalAuditItem por cada activo
    esperado. Esos registros conservan un snapshot de la ubicación, dependencia,
    área, resguardatario, folio y condición física existentes en ese momento.

    El proceso para preparar, congelar, iniciar, conciliar y cerrar una sesión
    debe vivir en servicios transaccionales.
    """

    folio = models.CharField(
        "Folio de auditoría física",
        max_length=80,
        unique=True,
    )
    name = models.CharField(
        "Nombre de auditoría",
        max_length=180,
    )
    fiscal_year = models.PositiveSmallIntegerField(
        "Ejercicio fiscal",
        db_index=True,
    )
    scope = models.CharField(
        "Alcance",
        max_length=30,
        choices=PhysicalAuditScope.choices,
        default=PhysicalAuditScope.ANNUAL,
        db_index=True,
    )
    status = models.CharField(
        "Estado",
        max_length=30,
        choices=PhysicalAuditStatus.choices,
        default=PhysicalAuditStatus.DRAFT,
        db_index=True,
    )

    sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_audit_sessions",
        null=True,
        blank=True,
        verbose_name="Sede incluida",
    )
    dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_audit_sessions",
        null=True,
        blank=True,
        verbose_name="Dependencia incluida",
    )
    area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_audit_sessions",
        null=True,
        blank=True,
        verbose_name="Área incluida",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audits_created",
        verbose_name="Creada por",
    )
    frozen_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audits_frozen",
        verbose_name="Congelada por",
        null=True,
        blank=True,
    )
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audits_started",
        verbose_name="Iniciada por",
        null=True,
        blank=True,
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audits_closed",
        verbose_name="Cerrada por",
        null=True,
        blank=True,
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audits_cancelled",
        verbose_name="Cancelada por",
        null=True,
        blank=True,
    )

    snapshot_at = models.DateTimeField(
        "Fecha de corte del inventario",
        null=True,
        blank=True,
        help_text=(
            "Momento exacto utilizado para congelar la población esperada."
        ),
    )
    frozen_at = models.DateTimeField(
        "Fecha de congelamiento",
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(
        "Inicio del levantamiento",
        null=True,
        blank=True,
    )
    closed_at = models.DateTimeField(
        "Cierre",
        null=True,
        blank=True,
    )
    cancelled_at = models.DateTimeField(
        "Fecha de cancelación",
        null=True,
        blank=True,
    )

    expected_assets_count = models.PositiveIntegerField(
        "Activos esperados al congelar",
        default=0,
    )
    found_assets_count = models.PositiveIntegerField(
        "Activos encontrados",
        default=0,
    )
    discrepancy_assets_count = models.PositiveIntegerField(
        "Activos con discrepancia",
        default=0,
    )
    not_found_assets_count = models.PositiveIntegerField(
        "Activos no localizados",
        default=0,
    )
    unregistered_assets_count = models.PositiveIntegerField(
        "Bienes sobrantes no registrados",
        default=0,
    )

    closing_summary = models.TextField(
        "Conclusiones del levantamiento",
        blank=True,
    )
    cancellation_reason = models.TextField(
        "Motivo de cancelación",
        blank=True,
    )
    notes = models.TextField(
        "Notas",
        blank=True,
    )

    class Meta:
        db_table = "inventory_physical_audit_sessions"
        verbose_name = "Auditoría física"
        verbose_name_plural = "Auditorías físicas"
        ordering = ["-fiscal_year", "-created_at"]
        indexes = [
            models.Index(fields=["status", "fiscal_year"]),
            models.Index(fields=["scope", "fiscal_year"]),
            models.Index(fields=["sede", "status"]),
            models.Index(fields=["dependencia", "status"]),
            models.Index(fields=["area", "status"]),
            models.Index(fields=["snapshot_at"]),
            models.Index(fields=["started_at"]),
            models.Index(fields=["closed_at"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(fiscal_year__gte=2000),
                name="ck_inv_audit_fiscal_year_gte_2000",
            ),
        ]

    def clean(self):
        errors = {}

        if self.fiscal_year < 2000:
            errors["fiscal_year"] = (
                "El ejercicio fiscal debe utilizar cuatro dígitos."
            )

        if self.area_id:
            if (
                self.dependencia_id
                and self.area.dependencia_id != self.dependencia_id
            ):
                errors["area"] = (
                    "El área no pertenece a la dependencia seleccionada."
                )

            if (
                self.sede_id
                and self.area.sede_fisica_id != self.sede_id
            ):
                errors["sede"] = (
                    "La sede no coincide con la sede física del área."
                )

        if self.scope == PhysicalAuditScope.DEPARTMENT:
            if not self.dependencia_id:
                errors["dependencia"] = (
                    "Una auditoría por dependencia requiere una dependencia."
                )

        if self.scope == PhysicalAuditScope.LOCATION:
            if not self.sede_id:
                errors["sede"] = (
                    "Una auditoría por ubicación requiere una sede."
                )

        if self.status in {
            PhysicalAuditStatus.FROZEN,
            PhysicalAuditStatus.IN_PROGRESS,
            PhysicalAuditStatus.RECONCILIATION,
            PhysicalAuditStatus.CLOSED,
        }:
            if not self.snapshot_at:
                errors["snapshot_at"] = (
                    "Una auditoría congelada debe tener fecha de corte."
                )

            if not self.frozen_at:
                errors["frozen_at"] = (
                    "Una auditoría congelada debe registrar la fecha "
                    "de congelamiento."
                )

            if not self.frozen_by_id:
                errors["frozen_by"] = (
                    "Debe indicar quién congeló el inventario."
                )

        if self.status in {
            PhysicalAuditStatus.IN_PROGRESS,
            PhysicalAuditStatus.RECONCILIATION,
            PhysicalAuditStatus.CLOSED,
        }:
            if not self.started_at:
                errors["started_at"] = (
                    "Debe registrar la fecha de inicio del levantamiento."
                )

            if not self.started_by_id:
                errors["started_by"] = (
                    "Debe indicar quién inició el levantamiento."
                )

        if self.status == PhysicalAuditStatus.CLOSED:
            if not self.closed_at:
                errors["closed_at"] = (
                    "Una auditoría cerrada debe tener fecha de cierre."
                )

            if not self.closed_by_id:
                errors["closed_by"] = (
                    "Una auditoría cerrada debe indicar quién la cerró."
                )

            if not self.closing_summary.strip():
                errors["closing_summary"] = (
                    "Debe registrar las conclusiones del levantamiento."
                )

        if self.status == PhysicalAuditStatus.CANCELLED:
            if not self.cancelled_at:
                errors["cancelled_at"] = (
                    "Una auditoría cancelada debe tener fecha."
                )

            if not self.cancelled_by_id:
                errors["cancelled_by"] = (
                    "Debe indicar quién canceló la auditoría."
                )

            if not self.cancellation_reason.strip():
                errors["cancellation_reason"] = (
                    "Debe indicar el motivo de cancelación."
                )

        if (
            self.frozen_at
            and self.started_at
            and self.started_at < self.frozen_at
        ):
            errors["started_at"] = (
                "El levantamiento no puede iniciar antes de congelar "
                "el inventario."
            )

        if (
            self.started_at
            and self.closed_at
            and self.closed_at < self.started_at
        ):
            errors["closed_at"] = (
                "El cierre no puede ser anterior al inicio."
            )

        counters = {
            "expected_assets_count": self.expected_assets_count,
            "found_assets_count": self.found_assets_count,
            "discrepancy_assets_count": (
                self.discrepancy_assets_count
            ),
            "not_found_assets_count": self.not_found_assets_count,
            "unregistered_assets_count": (
                self.unregistered_assets_count
            ),
        }

        for field_name, value in counters.items():
            if value < 0:
                errors[field_name] = (
                    "El contador no puede ser negativo."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.folio = self.folio.strip().upper()
        self.name = self.name.strip().upper()

        if self.closing_summary:
            self.closing_summary = self.closing_summary.strip()

        if self.cancellation_reason:
            self.cancellation_reason = (
                self.cancellation_reason.strip()
            )

        if self.notes:
            self.notes = self.notes.strip()

        super().save(*args, **kwargs)

    @property
    def is_frozen(self):
        return self.status in {
            PhysicalAuditStatus.FROZEN,
            PhysicalAuditStatus.IN_PROGRESS,
            PhysicalAuditStatus.RECONCILIATION,
            PhysicalAuditStatus.CLOSED,
        }

    @property
    def progress_percentage(self):
        if self.expected_assets_count <= 0:
            return 0

        processed = (
            self.found_assets_count
            + self.discrepancy_assets_count
            + self.not_found_assets_count
        )

        return min(
            round(
                processed * 100 / self.expected_assets_count,
                2,
            ),
            100,
        )

    def __str__(self):
        return f"{self.folio} · {self.name}"


class PhysicalAuditItem(InventoryBaseModel):
    """
    Activo esperado o sobrante detectado dentro de una auditoría.

    Para activos registrados conserva dos grupos de información:

    1. Snapshot esperado:
       Datos existentes cuando se congeló la auditoría.

    2. Datos encontrados:
       Ubicación, resguardatario y condición detectados durante el escaneo.

    Los snapshots no deben actualizarse si posteriormente cambia el Asset.
    """

    session = models.ForeignKey(
        PhysicalAuditSession,
        on_delete=models.CASCADE,
        related_name="items",
    )
    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="physical_audit_items",
        null=True,
        blank=True,
    )
    was_expected = models.BooleanField(
        "Formaba parte del inventario esperado",
        default=True,
        db_index=True,
    )

    inventory_number_snapshot = models.CharField(
        "Folio esperado",
        max_length=100,
        blank=True,
    )
    internal_number_snapshot = models.CharField(
        "Folio interno esperado",
        max_length=100,
        blank=True,
    )
    serial_number_snapshot = models.CharField(
        "Número de serie esperado",
        max_length=120,
        blank=True,
    )
    asset_name_snapshot = models.CharField(
        "Nombre del activo esperado",
        max_length=180,
        blank=True,
    )

    expected_sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_audit_items_expected",
        null=True,
        blank=True,
    )
    expected_dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_audit_items_expected",
        null=True,
        blank=True,
    )
    expected_area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_audit_items_expected",
        null=True,
        blank=True,
    )
    expected_custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audit_items_expected",
        null=True,
        blank=True,
    )

    expected_sede_name_snapshot = models.CharField(
        "Nombre esperado de sede",
        max_length=180,
        blank=True,
    )
    expected_dependencia_name_snapshot = models.CharField(
        "Nombre esperado de dependencia",
        max_length=180,
        blank=True,
    )
    expected_area_name_snapshot = models.CharField(
        "Nombre esperado de área",
        max_length=180,
        blank=True,
    )
    expected_custodian_name_snapshot = models.CharField(
        "Nombre esperado del resguardatario",
        max_length=300,
        blank=True,
    )
    expected_custodian_email_snapshot = models.EmailField(
        "Correo esperado del resguardatario",
        blank=True,
    )
    expected_condition = models.CharField(
        "Condición física esperada",
        max_length=30,
        choices=PhysicalCondition.choices,
        blank=True,
    )

    scanned_inventory_number = models.CharField(
        "Número escaneado",
        max_length=100,
        blank=True,
        help_text=(
            "Puede ser folio oficial, folio interno, folio anterior, "
            "QR o código de barras."
        ),
    )
    result = models.CharField(
        "Resultado",
        max_length=60,
        choices=PhysicalAuditResult.choices,
        default=PhysicalAuditResult.PENDING,
        db_index=True,
    )

    observed_sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_audit_items_observed",
        null=True,
        blank=True,
    )
    observed_dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_audit_items_observed",
        null=True,
        blank=True,
    )
    observed_area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_audit_items_observed",
        null=True,
        blank=True,
    )
    observed_custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audit_items_observed",
        null=True,
        blank=True,
    )
    observed_condition = models.CharField(
        "Condición física encontrada",
        max_length=30,
        choices=PhysicalCondition.choices,
        blank=True,
    )

    observed_sede_name_snapshot = models.CharField(
        "Nombre encontrado de sede",
        max_length=180,
        blank=True,
    )
    observed_dependencia_name_snapshot = models.CharField(
        "Nombre encontrado de dependencia",
        max_length=180,
        blank=True,
    )
    observed_area_name_snapshot = models.CharField(
        "Nombre encontrado de área",
        max_length=180,
        blank=True,
    )
    observed_custodian_name_snapshot = models.CharField(
        "Nombre encontrado del resguardatario",
        max_length=300,
        blank=True,
    )
    observed_custodian_email_snapshot = models.EmailField(
        "Correo encontrado del resguardatario",
        blank=True,
    )

    scanned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audit_items_scanned",
        null=True,
        blank=True,
    )
    scanned_at = models.DateTimeField(
        "Fecha de lectura",
        null=True,
        blank=True,
        db_index=True,
    )

    latitude = models.DecimalField(
        "Latitud",
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        "Longitud",
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    discrepancy_reason = models.TextField(
        "Descripción de discrepancia",
        blank=True,
    )
    reconciliation_notes = models.TextField(
        "Notas de conciliación",
        blank=True,
    )
    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audit_items_reconciled",
        null=True,
        blank=True,
    )
    reconciled_at = models.DateTimeField(
        "Fecha de conciliación",
        null=True,
        blank=True,
    )

    evidence = models.JSONField(
        "Evidencias adicionales",
        default=dict,
        blank=True,
        help_text=(
            "Metadatos de fotografías o documentos. Los archivos deben "
            "almacenarse en el módulo documental correspondiente."
        ),
    )
    notes = models.TextField(
        "Notas",
        blank=True,
    )

    class Meta:
        db_table = "inventory_physical_audit_items"
        verbose_name = "Partida de auditoría física"
        verbose_name_plural = "Partidas de auditoría física"
        ordering = [
            "session",
            "inventory_number_snapshot",
            "created_at",
        ]
        indexes = [
            models.Index(fields=["session", "result"]),
            models.Index(fields=["session", "was_expected"]),
            models.Index(fields=["asset"]),
            models.Index(fields=["inventory_number_snapshot"]),
            models.Index(fields=["scanned_inventory_number"]),
            models.Index(fields=["serial_number_snapshot"]),
            models.Index(fields=["expected_sede", "result"]),
            models.Index(fields=["expected_dependencia", "result"]),
            models.Index(fields=["observed_sede", "result"]),
            models.Index(fields=["observed_dependencia", "result"]),
            models.Index(fields=["scanned_by", "scanned_at"]),
            models.Index(fields=["reconciled_by", "reconciled_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "asset"],
                condition=Q(asset__isnull=False),
                name="uq_inv_audit_session_asset",
            ),
            models.CheckConstraint(
                condition=(
                    Q(asset__isnull=False)
                    | ~Q(scanned_inventory_number="")
                ),
                name="ck_inv_audit_item_has_identity",
            ),
        ]

    def clean(self):
        errors = {}

        if self.was_expected and not self.asset_id:
            errors["asset"] = (
                "Una partida esperada debe estar vinculada a un activo."
            )

        if (
            not self.was_expected
            and self.result != PhysicalAuditResult.UNREGISTERED
        ):
            errors["result"] = (
                "Un bien no esperado debe clasificarse como sobrante "
                "no registrado."
            )

        if (
            self.result == PhysicalAuditResult.UNREGISTERED
            and not self.scanned_inventory_number.strip()
        ):
            errors["scanned_inventory_number"] = (
                "Un sobrante no registrado debe conservar el código "
                "o folio escaneado."
            )

        if (
            self.result != PhysicalAuditResult.PENDING
            and self.result != PhysicalAuditResult.NOT_FOUND
        ):
            if not self.scanned_by_id:
                errors["scanned_by"] = (
                    "Debe indicar quién realizó la lectura."
                )

            if not self.scanned_at:
                errors["scanned_at"] = (
                    "Debe registrar la fecha de lectura."
                )

        if self.result == PhysicalAuditResult.NOT_FOUND:
            if self.scanned_at:
                errors["scanned_at"] = (
                    "Un activo no localizado no debe tener una lectura física."
                )

        discrepancy_results = {
            PhysicalAuditResult.FOUND_DIFFERENT_LOCATION,
            PhysicalAuditResult.FOUND_DIFFERENT_CUSTODIAN,
            (
                PhysicalAuditResult
                .FOUND_DIFFERENT_LOCATION_AND_CUSTODIAN
            ),
            PhysicalAuditResult.DAMAGED,
        }

        if (
            self.result in discrepancy_results
            and not self.discrepancy_reason.strip()
        ):
            errors["discrepancy_reason"] = (
                "Debe describir la discrepancia encontrada."
            )

        if self.observed_area_id:
            if (
                self.observed_dependencia_id
                and self.observed_area.dependencia_id
                != self.observed_dependencia_id
            ):
                errors["observed_area"] = (
                    "El área encontrada no pertenece a la dependencia "
                    "encontrada."
                )

            if (
                self.observed_sede_id
                and self.observed_area.sede_fisica_id
                != self.observed_sede_id
            ):
                errors["observed_sede"] = (
                    "La sede encontrada no coincide con la sede del área."
                )

        if self.reconciled_at and not self.reconciled_by_id:
            errors["reconciled_by"] = (
                "Debe indicar quién realizó la conciliación."
            )

        if self.reconciled_by_id and not self.reconciled_at:
            errors["reconciled_at"] = (
                "Debe registrar la fecha de conciliación."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        uppercase_fields = [
            "inventory_number_snapshot",
            "internal_number_snapshot",
            "serial_number_snapshot",
            "asset_name_snapshot",
            "scanned_inventory_number",
            "expected_sede_name_snapshot",
            "expected_dependencia_name_snapshot",
            "expected_area_name_snapshot",
            "observed_sede_name_snapshot",
            "observed_dependencia_name_snapshot",
            "observed_area_name_snapshot",
        ]

        for field_name in uppercase_fields:
            value = getattr(self, field_name, "")

            if value:
                setattr(
                    self,
                    field_name,
                    value.strip().upper(),
                )

        if self.expected_custodian_name_snapshot:
            self.expected_custodian_name_snapshot = (
                self.expected_custodian_name_snapshot.strip()
            )

        if self.expected_custodian_email_snapshot:
            self.expected_custodian_email_snapshot = (
                self.expected_custodian_email_snapshot
                .strip()
                .lower()
            )

        if self.observed_custodian_name_snapshot:
            self.observed_custodian_name_snapshot = (
                self.observed_custodian_name_snapshot.strip()
            )

        if self.observed_custodian_email_snapshot:
            self.observed_custodian_email_snapshot = (
                self.observed_custodian_email_snapshot
                .strip()
                .lower()
            )

        if self.discrepancy_reason:
            self.discrepancy_reason = (
                self.discrepancy_reason.strip()
            )

        if self.reconciliation_notes:
            self.reconciliation_notes = (
                self.reconciliation_notes.strip()
            )

        if self.notes:
            self.notes = self.notes.strip()

        super().save(*args, **kwargs)

    @property
    def has_discrepancy(self):
        return self.result in {
            PhysicalAuditResult.FOUND_DIFFERENT_LOCATION,
            PhysicalAuditResult.FOUND_DIFFERENT_CUSTODIAN,
            (
                PhysicalAuditResult
                .FOUND_DIFFERENT_LOCATION_AND_CUSTODIAN
            ),
            PhysicalAuditResult.DAMAGED,
            PhysicalAuditResult.NOT_FOUND,
            PhysicalAuditResult.UNREGISTERED,
        }

    @property
    def target_display(self):
        if self.inventory_number_snapshot:
            return self.inventory_number_snapshot

        if self.asset_id:
            return self.asset.display_inventory_number

        return self.scanned_inventory_number or "SIN IDENTIFICADOR"

    def __str__(self):
        return (
            f"{self.session.folio} · "
            f"{self.target_display} · "
            f"{self.get_result_display()}"
        )


# =============================================================================
# BITÁCORA INTERNA DEL MÓDULO
# =============================================================================


class InventoryAuditLevel(models.TextChoices):
    INFO = "INFO", "Informativo"
    SUCCESS = "SUCCESS", "Operación exitosa"
    WARNING = "WARNING", "Advertencia"
    CRITICAL = "CRITICAL", "Operación crítica"


class InventoryAuditAction(models.TextChoices):
    CREATE = "CREATE", "Creación"
    UPDATE = "UPDATE", "Modificación"
    DELETE = "DELETE", "Baja lógica"
    RESTORE = "RESTORE", "Restauración"
    SUBMIT = "SUBMIT", "Envío"
    APPROVE = "APPROVE", "Aprobación"
    REJECT = "REJECT", "Rechazo"
    ASSIGN = "ASSIGN", "Asignación"
    TRANSFER = "TRANSFER", "Transferencia"
    LOAN = "LOAN", "Préstamo"
    RETURN = "RETURN", "Devolución"
    REGISTER = "REGISTER", "Registro oficial"
    DISPOSAL = "DISPOSAL", "Baja patrimonial"
    UPLOAD = "UPLOAD", "Carga documental"
    DOWNLOAD = "DOWNLOAD", "Descarga"
    EXPORT = "EXPORT", "Exportación"
    AUDIT = "AUDIT", "Auditoría física"
    BYPASS = "BYPASS", "Bypass administrativo"
    ACCESS = "ACCESS", "Acceso"
    QUERY = "QUERY", "Consulta"


class InventoryAuditLog(InventoryBaseModel):
    """
    Bitácora append-only del módulo Inventory.

    Conserva mutaciones y operaciones sensibles dentro de Inventory. Puede
    complementarse con SecurityAuditLog del Core, pero no depende de él.

    Los eventos no deben modificarse ni darse de baja desde interfaces
    ordinarias. Una corrección debe generar un evento adicional.
    """

    action_type = models.CharField(
        "Acción",
        max_length=40,
        choices=InventoryAuditAction.choices,
        db_index=True,
    )
    level = models.CharField(
        "Nivel",
        max_length=20,
        choices=InventoryAuditLevel.choices,
        default=InventoryAuditLevel.INFO,
        db_index=True,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audit_logs",
        null=True,
        blank=True,
        verbose_name="Operador",
    )
    actor_name_snapshot = models.CharField(
        "Nombre del operador",
        max_length=300,
        blank=True,
    )
    actor_email_snapshot = models.EmailField(
        "Correo del operador",
        blank=True,
    )

    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    intake_request = models.ForeignKey(
        "inventory.AssetIntakeRequest",
        on_delete=models.PROTECT,
        related_name="audit_logs",
        null=True,
        blank=True,
    )

    target_model = models.CharField(
        "Modelo objetivo",
        max_length=120,
        blank=True,
    )
    target_id = models.UUIDField(
        "UUID objetivo",
        null=True,
        blank=True,
        db_index=True,
    )

    summary = models.CharField(
        "Resumen",
        max_length=255,
    )
    reason = models.TextField(
        "Justificación",
        blank=True,
    )
    old_value = models.JSONField(
        "Valor anterior",
        default=dict,
        blank=True,
    )
    new_value = models.JSONField(
        "Valor nuevo",
        default=dict,
        blank=True,
    )
    payload = models.JSONField(
        "Datos adicionales",
        default=dict,
        blank=True,
    )

    request_id = models.UUIDField(
        "Identificador de correlación",
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Permite relacionar eventos generados dentro de una misma "
            "operación transaccional."
        ),
    )

    bypass_used = models.BooleanField(
        "Se utilizó bypass",
        default=False,
        db_index=True,
    )
    bypass_reason = models.TextField(
        "Motivo del bypass",
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        "Dirección IP",
        null=True,
        blank=True,
    )
    user_agent = models.TextField(
        "Navegador / dispositivo",
        blank=True,
    )
    occurred_at = models.DateTimeField(
        "Fecha efectiva del evento",
        default=timezone.now,
        db_index=True,
    )

    class Meta:
        db_table = "inventory_audit_logs"
        verbose_name = "Evento de auditoría de inventario"
        verbose_name_plural = "Eventos de auditoría de inventario"
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["action_type", "occurred_at"]),
            models.Index(fields=["level", "occurred_at"]),
            models.Index(fields=["asset", "occurred_at"]),
            models.Index(fields=["intake_request", "occurred_at"]),
            models.Index(fields=["actor", "occurred_at"]),
            models.Index(
                fields=["target_model", "target_id"],
                name="idx_inv_audit_target",
            ),
            models.Index(fields=["request_id", "occurred_at"]),
            models.Index(fields=["bypass_used", "occurred_at"]),
        ]

    def clean(self):
        errors = {}

        if not self.summary.strip():
            errors["summary"] = (
                "El resumen del evento es obligatorio."
            )

        if self.actor_id:
            if not self.actor_name_snapshot.strip():
                errors["actor_name_snapshot"] = (
                    "Debe conservar el nombre del operador."
                )

            if not self.actor_email_snapshot.strip():
                errors["actor_email_snapshot"] = (
                    "Debe conservar el correo del operador."
                )

        if self.bypass_used and not self.bypass_reason.strip():
            errors["bypass_reason"] = (
                "El motivo del bypass es obligatorio."
            )

        if (
            self.action_type == InventoryAuditAction.BYPASS
            and not self.bypass_used
        ):
            errors["bypass_used"] = (
                "Un evento BYPASS debe indicar que utilizó bypass."
            )

        if self.target_id and not self.target_model.strip():
            errors["target_model"] = (
                "Debe indicar el modelo correspondiente al UUID objetivo."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.summary = self.summary.strip()

        if self.reason:
            self.reason = self.reason.strip()

        if self.actor_name_snapshot:
            self.actor_name_snapshot = (
                self.actor_name_snapshot.strip()
            )

        if self.actor_email_snapshot:
            self.actor_email_snapshot = (
                self.actor_email_snapshot.strip().lower()
            )

        if self.target_model:
            self.target_model = self.target_model.strip()

        if self.bypass_reason:
            self.bypass_reason = self.bypass_reason.strip()

        if self.user_agent:
            self.user_agent = self.user_agent.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.get_action_type_display()} · "
            f"{self.summary}"
        )
        
