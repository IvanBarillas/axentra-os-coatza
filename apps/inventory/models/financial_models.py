# apps/inventory/models/financial_models.py

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.inventory.models.catalog_models import InventoryBaseModel


# =============================================================================
# RUTAS DE ALMACENAMIENTO
# =============================================================================


def accounting_export_upload_path(instance, filename):
    today = timezone.localdate()
    safe_filename = Path(filename).name

    return (
        f"inventory/financial/exports/"
        f"{today:%Y/%m}/"
        f"{instance.id}/"
        f"{safe_filename}"
    )


def reconciliation_source_upload_path(instance, filename):
    today = timezone.localdate()
    safe_filename = Path(filename).name

    return (
        f"inventory/financial/reconciliation/"
        f"{today:%Y/%m}/"
        f"{instance.id}/"
        f"{safe_filename}"
    )


def reconciliation_result_upload_path(instance, filename):
    today = timezone.localdate()
    safe_filename = Path(filename).name

    return (
        f"inventory/financial/reconciliation-results/"
        f"{today:%Y/%m}/"
        f"{instance.id}/"
        f"{safe_filename}"
    )


# =============================================================================
# CATÁLOGOS FINANCIEROS
# =============================================================================


class DepreciationFrequency(models.TextChoices):
    MONTHLY = "MONTHLY", "Mensual"
    ANNUAL = "ANNUAL", "Anual"


class DepreciationMethod(models.TextChoices):
    STRAIGHT_LINE = "STRAIGHT_LINE", "Línea recta"


class DepreciationRunStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    PROCESSING = "PROCESSING", "Procesando"
    COMPLETED = "COMPLETED", "Calculado"
    POSTED = "POSTED", "Aplicado / contabilizado"
    FAILED = "FAILED", "Fallido"
    CANCELLED = "CANCELLED", "Cancelado"


class AccountingExportStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Solicitado"
    PROCESSING = "PROCESSING", "Procesando"
    COMPLETED = "COMPLETED", "Generado"
    FAILED = "FAILED", "Fallido"
    CANCELLED = "CANCELLED", "Cancelado"


class AccountingExportFormat(models.TextChoices):
    XLSX = "XLSX", "Microsoft Excel"
    CSV = "CSV", "Archivo CSV"
    PDF = "PDF", "Documento PDF"
    JSON = "JSON", "Archivo JSON"
    TXT = "TXT", "Archivo de texto"


class ReconciliationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    FILE_UPLOADED = "FILE_UPLOADED", "Archivo cargado"
    PROCESSING = "PROCESSING", "Procesando"
    WITH_DIFFERENCES = (
        "WITH_DIFFERENCES",
        "Conciliación con diferencias",
    )
    RECONCILED = "RECONCILED", "Conciliado"
    UNDER_REVIEW = "UNDER_REVIEW", "En revisión"
    CLOSED = "CLOSED", "Cerrado"
    FAILED = "FAILED", "Fallido"
    CANCELLED = "CANCELLED", "Cancelado"


class ReconciliationItemResult(models.TextChoices):
    MATCHED = "MATCHED", "Conciliado"
    DIFFERENCE = "DIFFERENCE", "Con diferencia"
    INVENTORY_ONLY = (
        "INVENTORY_ONLY",
        "Sólo existe en Inventory",
    )
    ACCOUNTING_ONLY = (
        "ACCOUNTING_ONLY",
        "Sólo existe en contabilidad",
    )
    NOT_EVALUATED = (
        "NOT_EVALUATED",
        "No evaluado",
    )


# =============================================================================
# POLÍTICAS DE DEPRECIACIÓN
# =============================================================================


class DepreciationPolicy(InventoryBaseModel):
    """
    Política versionada de depreciación.

    Una política establece el método, frecuencia, vida útil y valor residual
    aplicables durante un periodo determinado. Los registros calculados deben
    conservar snapshots, de manera que una modificación futura de la política
    no cambie resultados históricos.
    """

    policy_code = models.CharField(
        "Código de política",
        max_length=50,
    )
    version_number = models.PositiveSmallIntegerField(
        "Versión",
        default=1,
    )
    name = models.CharField(
        "Nombre",
        max_length=180,
    )

    accounting_account = models.ForeignKey(
        "inventory.AccountingAccount",
        on_delete=models.PROTECT,
        related_name="depreciation_policies",
        verbose_name="Cuenta contable",
    )
    category = models.ForeignKey(
        "inventory.AssetCategory",
        on_delete=models.PROTECT,
        related_name="depreciation_policies",
        verbose_name="Categoría patrimonial",
        null=True,
        blank=True,
    )

    method = models.CharField(
        "Método",
        max_length=30,
        choices=DepreciationMethod.choices,
        default=DepreciationMethod.STRAIGHT_LINE,
    )
    frequency = models.CharField(
        "Frecuencia",
        max_length=20,
        choices=DepreciationFrequency.choices,
        default=DepreciationFrequency.MONTHLY,
    )
    useful_life_months = models.PositiveIntegerField(
        "Vida útil en meses",
    )
    residual_percentage = models.DecimalField(
        "Porcentaje residual",
        max_digits=6,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Ejemplo: 10.000 para 10%.",
    )

    effective_from = models.DateField(
        "Vigente desde",
    )
    effective_until = models.DateField(
        "Vigente hasta",
        null=True,
        blank=True,
    )

    source_reference = models.CharField(
        "Referencia normativa o técnica",
        max_length=255,
        blank=True,
    )
    calculation_settings = models.JSONField(
        "Configuración adicional",
        default=dict,
        blank=True,
        help_text="No utilizar para sustituir los campos principales.",
    )

    class Meta:
        db_table = "inventory_depreciation_policies"
        verbose_name = "Política de depreciación"
        verbose_name_plural = "Políticas de depreciación"
        ordering = [
            "policy_code",
            "-version_number",
        ]
        indexes = [
            models.Index(
                fields=["accounting_account", "effective_from"],
            ),
            models.Index(
                fields=["category", "effective_from"],
            ),
            models.Index(fields=["method", "frequency"]),
            models.Index(fields=["effective_from", "effective_until"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["policy_code", "version_number"],
                name="uq_inv_depr_pol_ver",
            ),
            models.CheckConstraint(
                condition=Q(version_number__gte=1),
                name="ck_inv_depr_pol_ver_gte1",
            ),
            models.CheckConstraint(
                condition=Q(useful_life_months__gt=0),
                name="ck_inv_depr_pol_life_gt0",
            ),
            models.CheckConstraint(
                condition=(
                    Q(residual_percentage__gte=0)
                    & Q(residual_percentage__lte=100)
                ),
                name="ck_inv_depr_pol_res_range",
            ),
        ]

    def clean(self):
        errors = {}

        if not self.policy_code.strip():
            errors["policy_code"] = (
                "El código de política es obligatorio."
            )

        if not self.name.strip():
            errors["name"] = (
                "El nombre de la política es obligatorio."
            )

        if self.version_number < 1:
            errors["version_number"] = (
                "La versión debe ser mayor o igual a uno."
            )

        if self.useful_life_months <= 0:
            errors["useful_life_months"] = (
                "La vida útil debe ser mayor a cero."
            )

        if self.residual_percentage < 0:
            errors["residual_percentage"] = (
                "El porcentaje residual no puede ser negativo."
            )

        if self.residual_percentage > 100:
            errors["residual_percentage"] = (
                "El porcentaje residual no puede superar 100%."
            )

        if (
            self.effective_until
            and self.effective_until < self.effective_from
        ):
            errors["effective_until"] = (
                "La fecha final no puede ser anterior a la fecha inicial."
            )

        if (
            self.category_id
            and self.accounting_account.category_id
            and self.accounting_account.category_id != self.category_id
        ):
            errors["accounting_account"] = (
                "La cuenta contable pertenece a una categoría diferente."
            )

        if not self.accounting_account.is_depreciable:
            errors["accounting_account"] = (
                "La cuenta seleccionada está marcada como no depreciable."
            )

        overlapping = (
            DepreciationPolicy.objects
            .filter(
                policy_code__iexact=self.policy_code.strip(),
                effective_from__lte=(
                    self.effective_until or self.effective_from
                ),
                is_deleted=False,
            )
            .filter(
                Q(effective_until__isnull=True)
                | Q(effective_until__gte=self.effective_from)
            )
            .exclude(pk=self.pk)
            .exists()
        )

        if overlapping:
            errors["effective_from"] = (
                "La vigencia se traslapa con otra versión de la política."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.policy_code = self.policy_code.strip().upper()
        self.name = self.name.strip().upper()

        if self.source_reference:
            self.source_reference = self.source_reference.strip()

        super().save(*args, **kwargs)

    @property
    def residual_factor(self):
        return (
            self.residual_percentage / Decimal("100.00")
        )

    def __str__(self):
        return (
            f"{self.policy_code} V{self.version_number} · "
            f"{self.name}"
        )


# =============================================================================
# EJECUCIÓN DE DEPRECIACIÓN
# =============================================================================


class DepreciationRun(InventoryBaseModel):
    """
    Lote transaccional de cálculo de depreciación.

    Una ejecución agrupa todos los resultados calculados para un periodo. Esto
    permite conocer quién ejecutó el proceso, cuándo ocurrió, qué activos se
    incluyeron y cuáles fueron los totales.

    Los resultados deben generarse desde DepreciationService.
    """

    folio = models.CharField(
        "Folio de ejecución",
        max_length=80,
        unique=True,
    )
    status = models.CharField(
        "Estado",
        max_length=30,
        choices=DepreciationRunStatus.choices,
        default=DepreciationRunStatus.DRAFT,
        db_index=True,
    )
    frequency = models.CharField(
        "Frecuencia",
        max_length=20,
        choices=DepreciationFrequency.choices,
    )

    period_year = models.PositiveSmallIntegerField(
        "Año",
        db_index=True,
    )
    period_month = models.PositiveSmallIntegerField(
        "Mes",
        null=True,
        blank=True,
    )
    period_start = models.DateField(
        "Inicio del periodo",
    )
    period_end = models.DateField(
        "Fin del periodo",
    )
    cutoff_at = models.DateTimeField(
        "Fecha de corte",
        default=timezone.now,
    )

    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_depreciation_runs_started",
        verbose_name="Iniciada por",
    )
    initiated_by_name_snapshot = models.CharField(
        "Nombre de quien inició",
        max_length=300,
    )
    initiated_by_email_snapshot = models.EmailField(
        "Correo de quien inició",
    )
    initiated_at = models.DateTimeField(
        "Fecha de inicio",
        default=timezone.now,
    )

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_depreciation_runs_completed",
        verbose_name="Finalizada por",
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(
        "Fecha de finalización",
        null=True,
        blank=True,
    )

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_depreciation_runs_posted",
        verbose_name="Aplicada por",
        null=True,
        blank=True,
    )
    posted_at = models.DateTimeField(
        "Fecha de aplicación",
        null=True,
        blank=True,
    )

    asset_count = models.PositiveIntegerField(
        "Activos procesados",
        default=0,
    )
    original_value_total = models.DecimalField(
        "Valor original total",
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    period_depreciation_total = models.DecimalField(
        "Depreciación del periodo",
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    accumulated_depreciation_total = models.DecimalField(
        "Depreciación acumulada",
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    book_value_total = models.DecimalField(
        "Valor neto en libros",
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    error_message = models.TextField(
        "Detalle de error",
        blank=True,
    )
    calculation_metadata = models.JSONField(
        "Metadatos de cálculo",
        default=dict,
        blank=True,
    )
    notes = models.TextField(
        "Notas",
        blank=True,
    )

    class Meta:
        db_table = "inventory_depreciation_runs"
        verbose_name = "Ejecución de depreciación"
        verbose_name_plural = "Ejecuciones de depreciación"
        ordering = [
            "-period_year",
            "-period_month",
            "-created_at",
        ]
        indexes = [
            models.Index(
                fields=["status", "period_year", "period_month"],
                name="idx_inv_depr_run_status_period",
            ),
            models.Index(fields=["frequency", "period_year"]),
            models.Index(fields=["initiated_by", "initiated_at"]),
            models.Index(fields=["completed_at"]),
            models.Index(fields=["posted_at"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(period_year__gte=2000),
                name="ck_inv_depr_run_year_gte_2000",
            ),
            models.CheckConstraint(
                condition=(
                    Q(period_month__isnull=True)
                    | (
                        Q(period_month__gte=1)
                        & Q(period_month__lte=12)
                    )
                ),
                name="ck_inv_depr_run_month_range",
            ),
            models.CheckConstraint(
                condition=Q(asset_count__gte=0),
                name="ck_inv_depr_run_count_gte0",
            ),
        ]

    def clean(self):
        errors = {}

        if self.period_year < 2000:
            errors["period_year"] = (
                "El año debe utilizar cuatro dígitos."
            )

        if self.frequency == DepreciationFrequency.MONTHLY:
            if self.period_month is None:
                errors["period_month"] = (
                    "Una ejecución mensual requiere indicar el mes."
                )
            elif self.period_month < 1 or self.period_month > 12:
                errors["period_month"] = (
                    "El mes debe encontrarse entre 1 y 12."
                )

        if (
            self.frequency == DepreciationFrequency.ANNUAL
            and self.period_month is not None
        ):
            errors["period_month"] = (
                "Una ejecución anual no debe indicar un mes."
            )

        if self.period_end < self.period_start:
            errors["period_end"] = (
                "La fecha final no puede ser anterior a la inicial."
            )

        if self.period_start.year != self.period_year:
            errors["period_start"] = (
                "La fecha inicial no pertenece al ejercicio indicado."
            )

        if self.period_end.year != self.period_year:
            errors["period_end"] = (
                "La fecha final no pertenece al ejercicio indicado."
            )

        if self.status in {
            DepreciationRunStatus.COMPLETED,
            DepreciationRunStatus.POSTED,
        }:
            if not self.completed_by_id:
                errors["completed_by"] = (
                    "Debe indicar quién finalizó el cálculo."
                )

            if not self.completed_at:
                errors["completed_at"] = (
                    "Debe registrar la fecha de finalización."
                )

        if self.status == DepreciationRunStatus.POSTED:
            if not self.posted_by_id:
                errors["posted_by"] = (
                    "Debe indicar quién aplicó la depreciación."
                )

            if not self.posted_at:
                errors["posted_at"] = (
                    "Debe registrar la fecha de aplicación."
                )

        if (
            self.completed_at
            and self.completed_at < self.initiated_at
        ):
            errors["completed_at"] = (
                "La finalización no puede ser anterior al inicio."
            )

        if (
            self.posted_at
            and self.completed_at
            and self.posted_at < self.completed_at
        ):
            errors["posted_at"] = (
                "La aplicación no puede ser anterior al cálculo."
            )

        money_fields = {
            "original_value_total": self.original_value_total,
            "period_depreciation_total": (
                self.period_depreciation_total
            ),
            "accumulated_depreciation_total": (
                self.accumulated_depreciation_total
            ),
            "book_value_total": self.book_value_total,
        }

        for field_name, value in money_fields.items():
            if value < 0:
                errors[field_name] = (
                    "El importe no puede ser negativo."
                )

        if (
            self.status == DepreciationRunStatus.FAILED
            and not self.error_message.strip()
        ):
            errors["error_message"] = (
                "Una ejecución fallida debe conservar el error."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.folio = self.folio.strip().upper()
        self.initiated_by_name_snapshot = (
            self.initiated_by_name_snapshot.strip()
        )
        self.initiated_by_email_snapshot = (
            self.initiated_by_email_snapshot.strip().lower()
        )

        if self.error_message:
            self.error_message = self.error_message.strip()

        if self.notes:
            self.notes = self.notes.strip()

        super().save(*args, **kwargs)

    @property
    def period_label(self):
        if self.period_month:
            return f"{self.period_year}-{self.period_month:02d}"

        return str(self.period_year)

    def __str__(self):
        return f"{self.folio} · {self.period_label}"


# =============================================================================
# RESULTADOS DE DEPRECIACIÓN
# =============================================================================


class DepreciationRecord(InventoryBaseModel):
    """
    Resultado inmutable de depreciación de un activo dentro de una ejecución.

    Conserva snapshots de la política y de los valores utilizados. Una
    corrección posterior debe realizarse mediante una nueva ejecución o un
    proceso de reversión, nunca modificando silenciosamente el registro.
    """

    run = models.ForeignKey(
        DepreciationRun,
        on_delete=models.PROTECT,
        related_name="records",
    )
    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="depreciation_records",
    )
    policy = models.ForeignKey(
        DepreciationPolicy,
        on_delete=models.PROTECT,
        related_name="depreciation_records",
    )

    asset_folio_snapshot = models.CharField(
        "Folio del activo",
        max_length=100,
    )
    asset_name_snapshot = models.CharField(
        "Nombre del activo",
        max_length=180,
    )
    accounting_account_code_snapshot = models.CharField(
        "Cuenta contable aplicada",
        max_length=50,
    )
    policy_code_snapshot = models.CharField(
        "Código de política",
        max_length=50,
    )
    policy_version_snapshot = models.PositiveSmallIntegerField(
        "Versión de política",
    )
    method_snapshot = models.CharField(
        "Método aplicado",
        max_length=30,
        choices=DepreciationMethod.choices,
    )
    useful_life_months_snapshot = models.PositiveIntegerField(
        "Vida útil aplicada",
    )
    residual_percentage_snapshot = models.DecimalField(
        "Porcentaje residual aplicado",
        max_digits=6,
        decimal_places=3,
    )

    period_year = models.PositiveSmallIntegerField(
        "Año",
    )
    period_month = models.PositiveSmallIntegerField(
        "Mes",
        null=True,
        blank=True,
    )
    period_start = models.DateField(
        "Inicio del periodo",
    )
    period_end = models.DateField(
        "Fin del periodo",
    )

    original_value = models.DecimalField(
        "Valor original",
        max_digits=16,
        decimal_places=2,
    )
    residual_value = models.DecimalField(
        "Valor residual",
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    depreciable_base = models.DecimalField(
        "Base depreciable",
        max_digits=16,
        decimal_places=2,
    )
    previous_accumulated_depreciation = models.DecimalField(
        "Depreciación acumulada anterior",
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    depreciation_amount = models.DecimalField(
        "Depreciación del periodo",
        max_digits=16,
        decimal_places=2,
    )
    accumulated_depreciation = models.DecimalField(
        "Depreciación acumulada",
        max_digits=16,
        decimal_places=2,
    )
    book_value = models.DecimalField(
        "Valor neto en libros",
        max_digits=16,
        decimal_places=2,
    )

    calculated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_depreciations_calculated",
        verbose_name="Calculado por",
    )
    calculated_by_name_snapshot = models.CharField(
        "Nombre de quien calculó",
        max_length=300,
    )
    calculated_by_email_snapshot = models.EmailField(
        "Correo de quien calculó",
    )
    calculated_at = models.DateTimeField(
        "Fecha de cálculo",
        default=timezone.now,
        db_index=True,
    )

    calculation_payload = models.JSONField(
        "Detalle del cálculo",
        default=dict,
        blank=True,
    )
    notes = models.TextField(
        "Notas",
        blank=True,
    )

    class Meta:
        db_table = "inventory_depreciation_records"
        verbose_name = "Registro de depreciación"
        verbose_name_plural = "Registros de depreciación"
        ordering = [
            "-period_year",
            "-period_month",
            "asset_folio_snapshot",
        ]
        indexes = [
            models.Index(fields=["asset", "period_year", "period_month"]),
            models.Index(fields=["policy", "period_year"]),
            models.Index(fields=["run", "asset"]),
            models.Index(fields=["accounting_account_code_snapshot"]),
            models.Index(fields=["calculated_by", "calculated_at"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "asset"],
                name="uq_inv_depr_record_run_asset",
            ),
            models.CheckConstraint(
                condition=Q(period_year__gte=2000),
                name="ck_inv_depr_rec_year_gte2000",
            ),
            models.CheckConstraint(
                condition=(
                    Q(period_month__isnull=True)
                    | (
                        Q(period_month__gte=1)
                        & Q(period_month__lte=12)
                    )
                ),
                name="ck_inv_depr_record_month_range",
            ),
            models.CheckConstraint(
                condition=Q(original_value__gte=0),
                name="ck_inv_depr_orig_val_gte0",
            ),
            models.CheckConstraint(
                condition=Q(residual_value__gte=0),
                name="ck_inv_depr_res_val_gte0",
            ),
            models.CheckConstraint(
                condition=Q(depreciable_base__gte=0),
                name="ck_inv_depr_base_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(depreciation_amount__gte=0),
                name="ck_inv_depr_amount_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(accumulated_depreciation__gte=0),
                name="ck_inv_depr_accumulated_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(book_value__gte=0),
                name="ck_inv_depr_book_value_gte_0",
            ),
        ]

    def clean(self):
        errors = {}

        if self.period_year < 2000:
            errors["period_year"] = (
                "El año debe utilizar cuatro dígitos."
            )

        if self.run_id:
            if self.period_year != self.run.period_year:
                errors["period_year"] = (
                    "El año no coincide con la ejecución."
                )

            if self.period_month != self.run.period_month:
                errors["period_month"] = (
                    "El mes no coincide con la ejecución."
                )

            if self.period_start != self.run.period_start:
                errors["period_start"] = (
                    "La fecha inicial no coincide con la ejecución."
                )

            if self.period_end != self.run.period_end:
                errors["period_end"] = (
                    "La fecha final no coincide con la ejecución."
                )

        money_fields = {
            "original_value": self.original_value,
            "residual_value": self.residual_value,
            "depreciable_base": self.depreciable_base,
            "previous_accumulated_depreciation": (
                self.previous_accumulated_depreciation
            ),
            "depreciation_amount": self.depreciation_amount,
            "accumulated_depreciation": (
                self.accumulated_depreciation
            ),
            "book_value": self.book_value,
        }

        for field_name, value in money_fields.items():
            if value < 0:
                errors[field_name] = (
                    "El valor no puede ser negativo."
                )

        expected_base = max(
            self.original_value - self.residual_value,
            Decimal("0.00"),
        )

        if self.depreciable_base != expected_base:
            errors["depreciable_base"] = (
                "La base depreciable debe ser igual al valor original "
                "menos el valor residual."
            )

        expected_accumulated = (
            self.previous_accumulated_depreciation
            + self.depreciation_amount
        )

        if self.accumulated_depreciation != expected_accumulated:
            errors["accumulated_depreciation"] = (
                "La depreciación acumulada no coincide con el saldo "
                "anterior más la depreciación del periodo."
            )

        if self.accumulated_depreciation > self.depreciable_base:
            errors["accumulated_depreciation"] = (
                "La depreciación acumulada no puede superar la base "
                "depreciable."
            )

        expected_book_value = (
            self.original_value
            - self.accumulated_depreciation
        )

        if self.book_value != expected_book_value:
            errors["book_value"] = (
                "El valor en libros debe ser igual al valor original "
                "menos la depreciación acumulada."
            )

        if self.book_value < self.residual_value:
            errors["book_value"] = (
                "El valor en libros no puede ser menor al valor residual."
            )

        if self.residual_percentage_snapshot < 0:
            errors["residual_percentage_snapshot"] = (
                "El porcentaje residual no puede ser negativo."
            )

        if self.residual_percentage_snapshot > 100:
            errors["residual_percentage_snapshot"] = (
                "El porcentaje residual no puede superar 100%."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.asset_folio_snapshot = (
            self.asset_folio_snapshot.strip().upper()
        )
        self.asset_name_snapshot = (
            self.asset_name_snapshot.strip().upper()
        )
        self.accounting_account_code_snapshot = (
            self.accounting_account_code_snapshot.strip()
        )
        self.policy_code_snapshot = (
            self.policy_code_snapshot.strip().upper()
        )
        self.calculated_by_name_snapshot = (
            self.calculated_by_name_snapshot.strip()
        )
        self.calculated_by_email_snapshot = (
            self.calculated_by_email_snapshot.strip().lower()
        )

        if self.notes:
            self.notes = self.notes.strip()

        super().save(*args, **kwargs)

    @property
    def period_label(self):
        if self.period_month:
            return f"{self.period_year}-{self.period_month:02d}"

        return str(self.period_year)

    def __str__(self):
        return (
            f"{self.asset_folio_snapshot} · "
            f"{self.period_label}"
        )


# =============================================================================
# EXPORTACIONES CONTABLES Y DE TRANSPARENCIA
# =============================================================================


class AccountingExportBatch(InventoryBaseModel):
    """
    Lote auditable de exportación.

    Permite generar reportes contables, patrimoniales, de transparencia,
    depreciación o integraciones con sistemas externos.
    """

    class ExportType(models.TextChoices):
        REPORT_A = (
            "REPORT_A",
            "Inciso A · Bienes muebles",
        )
        REPORT_B = (
            "REPORT_B",
            "Inciso B · Altas de bienes muebles",
        )
        REPORT_C = (
            "REPORT_C",
            "Inciso C · Bajas de bienes muebles",
        )
        REPORT_D = (
            "REPORT_D",
            "Inciso D · Bienes inmuebles",
        )
        REPORT_E = (
            "REPORT_E",
            "Inciso E · Altas de bienes inmuebles",
        )
        REPORT_F = (
            "REPORT_F",
            "Inciso F · Bajas de bienes inmuebles",
        )
        REPORT_G = (
            "REPORT_G",
            "Inciso G · Bienes donados",
        )
        DEPRECIATION = (
            "DEPRECIATION",
            "Depreciación",
        )
        ACCOUNTING_ENTRIES = (
            "ACCOUNTING_ENTRIES",
            "Pólizas / ajustes",
        )
        ACCOUNT_BALANCES = (
            "ACCOUNT_BALANCES",
            "Saldos por cuenta",
        )
        TRANSPARENCY_MOVABLE = (
            "TRANSPARENCY_MOVABLE",
            "Transparencia · Bienes muebles",
        )
        TRANSPARENCY_IMMOVABLE = (
            "TRANSPARENCY_IMMOVABLE",
            "Transparencia · Bienes inmuebles",
        )
        TRANSPARENCY_ADDITIONS = (
            "TRANSPARENCY_ADDITIONS",
            "Transparencia · Altas",
        )
        TRANSPARENCY_DISPOSALS = (
            "TRANSPARENCY_DISPOSALS",
            "Transparencia · Bajas",
        )
        TRANSPARENCY_DONATIONS = (
            "TRANSPARENCY_DONATIONS",
            "Transparencia · Donaciones",
        )
        CUSTOM = "CUSTOM", "Reporte personalizado"

    folio = models.CharField(
        "Folio de exportación",
        max_length=80,
        unique=True,
    )
    export_type = models.CharField(
        "Tipo de exportación",
        max_length=40,
        choices=ExportType.choices,
        db_index=True,
    )
    status = models.CharField(
        "Estado",
        max_length=30,
        choices=AccountingExportStatus.choices,
        default=AccountingExportStatus.REQUESTED,
        db_index=True,
    )
    file_format = models.CharField(
        "Formato",
        max_length=20,
        choices=AccountingExportFormat.choices,
        default=AccountingExportFormat.XLSX,
    )
    destination_system = models.CharField(
        "Sistema destino",
        max_length=100,
        blank=True,
        help_text="Ejemplo: SIGMAVER, PNT, portal institucional.",
    )

    period_start = models.DateField(
        "Inicio del periodo",
        null=True,
        blank=True,
    )
    period_end = models.DateField(
        "Fin del periodo",
        null=True,
        blank=True,
    )
    cutoff_at = models.DateTimeField(
        "Fecha de corte",
        default=timezone.now,
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_exports_requested",
        verbose_name="Solicitado por",
    )
    requested_by_name_snapshot = models.CharField(
        "Nombre del solicitante",
        max_length=300,
    )
    requested_by_email_snapshot = models.EmailField(
        "Correo del solicitante",
    )
    requested_at = models.DateTimeField(
        "Fecha de solicitud",
        default=timezone.now,
    )

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_exports_completed",
        verbose_name="Finalizado por",
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(
        "Fecha de finalización",
        null=True,
        blank=True,
    )

    generated_file = models.FileField(
        "Archivo generado",
        upload_to=accounting_export_upload_path,
        null=True,
        blank=True,
    )
    generated_filename = models.CharField(
        "Nombre del archivo",
        max_length=255,
        blank=True,
    )
    generated_file_hash = models.CharField(
        "Hash SHA-256",
        max_length=64,
        blank=True,
    )
    generated_file_size = models.PositiveBigIntegerField(
        "Tamaño en bytes",
        null=True,
        blank=True,
    )

    record_count = models.PositiveIntegerField(
        "Registros exportados",
        default=0,
    )
    total_amount = models.DecimalField(
        "Importe total",
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    filters_snapshot = models.JSONField(
        "Filtros aplicados",
        default=dict,
        blank=True,
    )
    metadata = models.JSONField(
        "Metadatos",
        default=dict,
        blank=True,
    )
    error_message = models.TextField(
        "Detalle de error",
        blank=True,
    )

    class Meta:
        db_table = "inventory_accounting_export_batches"
        verbose_name = "Lote de exportación"
        verbose_name_plural = "Lotes de exportación"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["export_type", "status"]),
            models.Index(fields=["destination_system", "status"]),
            models.Index(fields=["period_start", "period_end"]),
            models.Index(fields=["requested_by", "requested_at"]),
            models.Index(fields=["completed_at"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(record_count__gte=0),
                name="ck_inv_exp_rec_count_gte0",
            ),
            models.CheckConstraint(
                condition=Q(total_amount__gte=0),
                name="ck_inv_export_total_gte_0",
            ),
        ]

    def clean(self):
        errors = {}

        if (
            self.period_start
            and self.period_end
            and self.period_end < self.period_start
        ):
            errors["period_end"] = (
                "La fecha final no puede ser anterior a la inicial."
            )

        if self.status == AccountingExportStatus.COMPLETED:
            if not self.generated_file:
                errors["generated_file"] = (
                    "Una exportación completada debe tener archivo."
                )

            if not self.completed_by_id:
                errors["completed_by"] = (
                    "Debe indicar quién finalizó la exportación."
                )

            if not self.completed_at:
                errors["completed_at"] = (
                    "Debe registrar la fecha de finalización."
                )

        if (
            self.status == AccountingExportStatus.FAILED
            and not self.error_message.strip()
        ):
            errors["error_message"] = (
                "Una exportación fallida debe conservar el error."
            )

        if (
            self.completed_at
            and self.completed_at < self.requested_at
        ):
            errors["completed_at"] = (
                "La finalización no puede ser anterior a la solicitud."
            )

        if self.total_amount < 0:
            errors["total_amount"] = (
                "El importe total no puede ser negativo."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.folio = self.folio.strip().upper()
        self.requested_by_name_snapshot = (
            self.requested_by_name_snapshot.strip()
        )
        self.requested_by_email_snapshot = (
            self.requested_by_email_snapshot.strip().lower()
        )

        if self.destination_system:
            self.destination_system = (
                self.destination_system.strip().upper()
            )

        if self.generated_filename:
            self.generated_filename = (
                Path(self.generated_filename).name.strip()
            )

        if self.generated_file_hash:
            self.generated_file_hash = (
                self.generated_file_hash.strip().lower()
            )

        if self.error_message:
            self.error_message = self.error_message.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.folio} · "
            f"{self.get_export_type_display()}"
        )


# =============================================================================
# CONCILIACIÓN FÍSICO-CONTABLE
# =============================================================================


class AccountingReconciliation(InventoryBaseModel):
    """
    Sesión mensual o extraordinaria de conciliación.

    Compara los valores registrados en Inventory contra una balanza o archivo
    generado por SIGMAVER u otro sistema contable.
    """

    folio = models.CharField(
        "Folio de conciliación",
        max_length=80,
        unique=True,
    )
    status = models.CharField(
        "Estado",
        max_length=30,
        choices=ReconciliationStatus.choices,
        default=ReconciliationStatus.DRAFT,
        db_index=True,
    )
    source_system = models.CharField(
        "Sistema contable origen",
        max_length=100,
        default="SIGMAVER",
    )

    period_start = models.DateField(
        "Inicio del periodo",
    )
    period_end = models.DateField(
        "Fin del periodo",
    )
    cutoff_at = models.DateTimeField(
        "Fecha de corte de Inventory",
        default=timezone.now,
    )

    source_file = models.FileField(
        "Balanza o archivo fuente",
        upload_to=reconciliation_source_upload_path,
        null=True,
        blank=True,
    )
    source_filename = models.CharField(
        "Nombre original",
        max_length=255,
        blank=True,
    )
    source_file_hash = models.CharField(
        "Hash SHA-256 del archivo fuente",
        max_length=64,
        blank=True,
    )
    source_file_size = models.PositiveBigIntegerField(
        "Tamaño en bytes",
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_reconciliations_created",
        verbose_name="Creada por",
    )
    created_by_name_snapshot = models.CharField(
        "Nombre de quien creó",
        max_length=300,
    )
    created_by_email_snapshot = models.EmailField(
        "Correo de quien creó",
    )

    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_reconciliations_processed",
        verbose_name="Procesada por",
        null=True,
        blank=True,
    )
    processed_at = models.DateTimeField(
        "Fecha de procesamiento",
        null=True,
        blank=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_reconciliations_reviewed",
        verbose_name="Revisada por",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(
        "Fecha de revisión",
        null=True,
        blank=True,
    )

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_reconciliations_closed",
        verbose_name="Cerrada por",
        null=True,
        blank=True,
    )
    closed_at = models.DateTimeField(
        "Fecha de cierre",
        null=True,
        blank=True,
    )

    inventory_total = models.DecimalField(
        "Total según Inventory",
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    accounting_total = models.DecimalField(
        "Total según contabilidad",
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    difference_total = models.DecimalField(
        "Diferencia total",
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    matched_account_count = models.PositiveIntegerField(
        "Cuentas conciliadas",
        default=0,
    )
    different_account_count = models.PositiveIntegerField(
        "Cuentas con diferencia",
        default=0,
    )

    result_file = models.FileField(
        "Resultado de conciliación",
        upload_to=reconciliation_result_upload_path,
        null=True,
        blank=True,
    )
    result_file_hash = models.CharField(
        "Hash del archivo resultado",
        max_length=64,
        blank=True,
    )

    closing_notes = models.TextField(
        "Conclusiones",
        blank=True,
    )
    error_message = models.TextField(
        "Detalle de error",
        blank=True,
    )
    import_metadata = models.JSONField(
        "Metadatos de importación",
        default=dict,
        blank=True,
    )

    class Meta:
        db_table = "inventory_accounting_reconciliations"
        verbose_name = "Conciliación físico-contable"
        verbose_name_plural = "Conciliaciones físico-contables"
        ordering = ["-period_end", "-created_at"]
        indexes = [
            models.Index(fields=["status", "period_end"]),
            models.Index(fields=["source_system", "period_end"]),
            models.Index(fields=["period_start", "period_end"]),
            models.Index(fields=["created_by", "created_at"]),
            models.Index(fields=["processed_at"]),
            models.Index(fields=["closed_at"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def clean(self):
        errors = {}

        if self.period_end < self.period_start:
            errors["period_end"] = (
                "La fecha final no puede ser anterior a la inicial."
            )

        money_fields = {
            "inventory_total": self.inventory_total,
            "accounting_total": self.accounting_total,
        }

        for field_name, value in money_fields.items():
            if value < 0:
                errors[field_name] = (
                    "El importe no puede ser negativo."
                )

        expected_difference = (
            self.inventory_total - self.accounting_total
        )

        if self.difference_total != expected_difference:
            errors["difference_total"] = (
                "La diferencia debe ser igual al total de Inventory "
                "menos el total contable."
            )

        process_statuses = {
            ReconciliationStatus.WITH_DIFFERENCES,
            ReconciliationStatus.RECONCILED,
            ReconciliationStatus.UNDER_REVIEW,
            ReconciliationStatus.CLOSED,
        }

        if self.status in process_statuses:
            if not self.source_file:
                errors["source_file"] = (
                    "La conciliación requiere el archivo contable fuente."
                )

            if not self.processed_by_id:
                errors["processed_by"] = (
                    "Debe indicar quién procesó la conciliación."
                )

            if not self.processed_at:
                errors["processed_at"] = (
                    "Debe registrar la fecha de procesamiento."
                )

        if self.status == ReconciliationStatus.CLOSED:
            if not self.reviewed_by_id:
                errors["reviewed_by"] = (
                    "Una conciliación cerrada debe estar revisada."
                )

            if not self.reviewed_at:
                errors["reviewed_at"] = (
                    "Debe registrar la fecha de revisión."
                )

            if not self.closed_by_id:
                errors["closed_by"] = (
                    "Debe indicar quién cerró la conciliación."
                )

            if not self.closed_at:
                errors["closed_at"] = (
                    "Debe registrar la fecha de cierre."
                )

            if not self.closing_notes.strip():
                errors["closing_notes"] = (
                    "Debe registrar las conclusiones."
                )

        if (
            self.status == ReconciliationStatus.FAILED
            and not self.error_message.strip()
        ):
            errors["error_message"] = (
                "Una conciliación fallida debe conservar el error."
            )

        if (
            self.reviewed_at
            and self.processed_at
            and self.reviewed_at < self.processed_at
        ):
            errors["reviewed_at"] = (
                "La revisión no puede ser anterior al procesamiento."
            )

        if (
            self.closed_at
            and self.reviewed_at
            and self.closed_at < self.reviewed_at
        ):
            errors["closed_at"] = (
                "El cierre no puede ser anterior a la revisión."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.folio = self.folio.strip().upper()
        self.source_system = self.source_system.strip().upper()
        self.created_by_name_snapshot = (
            self.created_by_name_snapshot.strip()
        )
        self.created_by_email_snapshot = (
            self.created_by_email_snapshot.strip().lower()
        )

        if self.source_filename:
            self.source_filename = (
                Path(self.source_filename).name.strip()
            )

        if self.source_file_hash:
            self.source_file_hash = (
                self.source_file_hash.strip().lower()
            )

        if self.result_file_hash:
            self.result_file_hash = (
                self.result_file_hash.strip().lower()
            )

        if self.closing_notes:
            self.closing_notes = self.closing_notes.strip()

        if self.error_message:
            self.error_message = self.error_message.strip()

        super().save(*args, **kwargs)

    @property
    def is_balanced(self):
        return self.difference_total == Decimal("0.00")

    def __str__(self):
        return (
            f"{self.folio} · "
            f"{self.period_start:%Y-%m-%d} / "
            f"{self.period_end:%Y-%m-%d}"
        )


class AccountingReconciliationItem(InventoryBaseModel):
    """
    Resultado por cuenta contable dentro de una conciliación.

    Conserva los códigos y nombres como snapshots para que el resultado
    histórico no cambie si posteriormente se actualiza el catálogo.
    """

    reconciliation = models.ForeignKey(
        AccountingReconciliation,
        on_delete=models.CASCADE,
        related_name="items",
    )
    accounting_account = models.ForeignKey(
        "inventory.AccountingAccount",
        on_delete=models.PROTECT,
        related_name="reconciliation_items",
        null=True,
        blank=True,
    )

    account_code_snapshot = models.CharField(
        "Código de cuenta",
        max_length=50,
    )
    account_name_snapshot = models.CharField(
        "Nombre de cuenta",
        max_length=255,
        blank=True,
    )

    inventory_amount = models.DecimalField(
        "Saldo según Inventory",
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    accounting_amount = models.DecimalField(
        "Saldo según contabilidad",
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    difference_amount = models.DecimalField(
        "Diferencia",
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    result = models.CharField(
        "Resultado",
        max_length=30,
        choices=ReconciliationItemResult.choices,
        default=ReconciliationItemResult.NOT_EVALUATED,
        db_index=True,
    )

    inventory_asset_count = models.PositiveIntegerField(
        "Activos en Inventory",
        default=0,
    )
    source_row_count = models.PositiveIntegerField(
        "Registros contables fuente",
        default=0,
    )

    review_notes = models.TextField(
        "Notas de revisión",
        blank=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_reconciliation_items_reviewed",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(
        "Fecha de revisión",
        null=True,
        blank=True,
    )
    source_payload = models.JSONField(
        "Datos fuente",
        default=dict,
        blank=True,
    )

    class Meta:
        db_table = "inventory_accounting_reconciliation_items"
        verbose_name = "Partida de conciliación"
        verbose_name_plural = "Partidas de conciliación"
        ordering = ["account_code_snapshot"]
        indexes = [
            models.Index(
                fields=["reconciliation", "result"],
                name="idx_inv_recon_item_result",
            ),
            models.Index(fields=["accounting_account"]),
            models.Index(fields=["account_code_snapshot"]),
            models.Index(fields=["reviewed_by", "reviewed_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["reconciliation", "account_code_snapshot"],
                name="uq_inv_recon_account_code",
            ),
            models.CheckConstraint(
                condition=Q(inventory_amount__gte=0),
                name="ck_inv_rec_inv_amt_gte0",
            ),
            models.CheckConstraint(
                condition=Q(accounting_amount__gte=0),
                name="ck_inv_rec_acc_amt_gte0",
            ),
        ]

    def clean(self):
        errors = {}

        expected_difference = (
            self.inventory_amount - self.accounting_amount
        )

        if self.difference_amount != expected_difference:
            errors["difference_amount"] = (
                "La diferencia debe ser igual al saldo de Inventory "
                "menos el saldo contable."
            )

        if self.inventory_amount < 0:
            errors["inventory_amount"] = (
                "El saldo de Inventory no puede ser negativo."
            )

        if self.accounting_amount < 0:
            errors["accounting_amount"] = (
                "El saldo contable no puede ser negativo."
            )

        if (
            self.result == ReconciliationItemResult.MATCHED
            and self.difference_amount != Decimal("0.00")
        ):
            errors["result"] = (
                "Una partida conciliada no puede tener diferencia."
            )

        if (
            self.result == ReconciliationItemResult.DIFFERENCE
            and self.difference_amount == Decimal("0.00")
        ):
            errors["result"] = (
                "Una partida sin diferencia debe marcarse conciliada."
            )

        if self.reviewed_at and not self.reviewed_by_id:
            errors["reviewed_by"] = (
                "Debe indicar quién revisó la partida."
            )

        if self.reviewed_by_id and not self.reviewed_at:
            errors["reviewed_at"] = (
                "Debe registrar la fecha de revisión."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.account_code_snapshot = (
            self.account_code_snapshot.strip()
        )

        if self.account_name_snapshot:
            self.account_name_snapshot = (
                self.account_name_snapshot.strip().upper()
            )

        if self.review_notes:
            self.review_notes = self.review_notes.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.reconciliation.folio} · "
            f"{self.account_code_snapshot} · "
            f"{self.difference_amount}"
        )
        
