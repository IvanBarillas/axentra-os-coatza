# apps/inventory/models/financial_models.py

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.inventory.models.catalog_models import InventoryBaseModel


class DepreciationFrequency(models.TextChoices):
    MONTHLY = "MONTHLY", "Mensual"
    ANNUAL = "ANNUAL", "Anual"


class DepreciationMethod(models.TextChoices):
    STRAIGHT_LINE = "STRAIGHT_LINE", "Línea Recta"


class DepreciationPolicy(InventoryBaseModel):
    """
    Política de depreciación aplicada a una categoría/cuenta.

    Permite parametrizar vida útil, valor residual y método.
    """

    name = models.CharField(
        "Nombre de política",
        max_length=180,
        unique=True,
    )
    accounting_account = models.ForeignKey(
        "inventory.AccountingAccount",
        on_delete=models.PROTECT,
        related_name="depreciation_policies",
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

    class Meta:
        db_table = "inventory_depreciation_policies"
        verbose_name = "Política de depreciación"
        verbose_name_plural = "Políticas de depreciación"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["accounting_account"]),
            models.Index(fields=["method"]),
            models.Index(fields=["frequency"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def clean(self):
        if self.useful_life_months <= 0:
            raise ValidationError(
                {
                    "useful_life_months": "La vida útil debe ser mayor a cero."
                }
            )

        if self.residual_percentage < 0:
            raise ValidationError(
                {
                    "residual_percentage": "El porcentaje residual no puede ser negativo."
                }
            )

        if self.residual_percentage > 100:
            raise ValidationError(
                {
                    "residual_percentage": "El porcentaje residual no puede ser mayor a 100."
                }
            )

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class DepreciationRecord(InventoryBaseModel):
    """
    Registro de depreciación por periodo.

    El cálculo lo hará un service.
    Este modelo sólo conserva el resultado auditable.
    """

    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="depreciation_records",
    )
    policy = models.ForeignKey(
        DepreciationPolicy,
        on_delete=models.PROTECT,
        related_name="depreciation_records",
        null=True,
        blank=True,
    )

    period_year = models.PositiveIntegerField(
        "Año",
    )
    period_month = models.PositiveSmallIntegerField(
        "Mes",
        null=True,
        blank=True,
        help_text="1-12 si la depreciación es mensual.",
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
        null=True,
        blank=True,
    )
    calculated_at = models.DateTimeField(
        "Fecha de cálculo",
        auto_now_add=True,
    )

    class Meta:
        db_table = "inventory_depreciation_records"
        verbose_name = "Registro de depreciación"
        verbose_name_plural = "Registros de depreciación"
        unique_together = ("asset", "period_year", "period_month")
        ordering = ["-period_year", "-period_month"]
        indexes = [
            models.Index(fields=["asset"]),
            models.Index(fields=["policy"]),
            models.Index(fields=["period_year", "period_month"]),
            models.Index(fields=["calculated_by"]),
            models.Index(fields=["calculated_at"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def clean(self):
        if self.period_month is not None:
            if self.period_month < 1 or self.period_month > 12:
                raise ValidationError(
                    {
                        "period_month": "El mes debe estar entre 1 y 12."
                    }
                )

        money_fields = {
            "original_value": self.original_value,
            "residual_value": self.residual_value,
            "depreciation_amount": self.depreciation_amount,
            "accumulated_depreciation": self.accumulated_depreciation,
            "book_value": self.book_value,
        }

        for field_name, value in money_fields.items():
            if value < 0:
                raise ValidationError(
                    {
                        field_name: "El valor no puede ser negativo."
                    }
                )

        if self.residual_value > self.original_value:
            raise ValidationError(
                {
                    "residual_value": "El valor residual no puede ser mayor al valor original."
                }
            )

        if self.accumulated_depreciation > self.original_value:
            raise ValidationError(
                {
                    "accumulated_depreciation": "La depreciación acumulada no puede ser mayor al valor original."
                }
            )

    @property
    def period_label(self):
        if self.period_month:
            return f"{self.period_year}-{self.period_month:02d}"

        return str(self.period_year)

    def __str__(self):
        return f"{self.asset.display_inventory_number} · {self.period_label}"


class AccountingExportBatch(InventoryBaseModel):
    """
    Lote de exportación contable / SIGMAVER.

    Aquí agruparemos reportes A-G, CSV, Excel o pólizas.
    """

    class ExportType(models.TextChoices):
        REPORT_A = "REPORT_A", "Inciso A · Bienes Muebles"
        REPORT_B = "REPORT_B", "Inciso B · Altas Bienes Muebles"
        REPORT_C = "REPORT_C", "Inciso C · Bajas Bienes Muebles"
        REPORT_D = "REPORT_D", "Inciso D · Bienes Inmuebles"
        REPORT_E = "REPORT_E", "Inciso E · Altas Bienes Inmuebles"
        REPORT_F = "REPORT_F", "Inciso F · Bajas Bienes Inmuebles"
        REPORT_G = "REPORT_G", "Inciso G · Bienes Donados"
        DEPRECIATION = "DEPRECIATION", "Depreciación"
        ACCOUNTING_ENTRIES = "ACCOUNTING_ENTRIES", "Pólizas / Ajustes"

    export_type = models.CharField(
        "Tipo de exportación",
        max_length=40,
        choices=ExportType.choices,
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
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_exports_generated",
    )
    generated_file = models.FileField(
        "Archivo generado",
        upload_to="inventory/exports/%Y/%m/",
        null=True,
        blank=True,
    )
    metadata = models.JSONField(
        "Metadatos",
        default=dict,
        blank=True,
    )

    class Meta:
        db_table = "inventory_accounting_export_batches"
        verbose_name = "Lote de exportación contable"
        verbose_name_plural = "Lotes de exportación contable"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["export_type"]),
            models.Index(fields=["period_start"]),
            models.Index(fields=["period_end"]),
            models.Index(fields=["generated_by"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def clean(self):
        if self.period_start and self.period_end:
            if self.period_end < self.period_start:
                raise ValidationError(
                    {
                        "period_end": "La fecha final no puede ser anterior a la fecha inicial."
                    }
                )

    def __str__(self):
        return f"{self.get_export_type_display()} · {self.created_at:%Y-%m-%d}"
    
