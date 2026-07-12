# apps/inventory/models/financial_models.py

from decimal import Decimal

from django.conf import settings
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
        ordering = ["name"]

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
        unique_together = ("asset", "period_year", "period_month")
        ordering = ["-period_year", "-period_month"]
        indexes = [
            models.Index(fields=["period_year", "period_month"]),
        ]

    def __str__(self):
        periodo = (
            f"{self.period_year}-{self.period_month:02d}"
            if self.period_month
            else str(self.period_year)
        )
        return f"{self.asset.inventory_number} · {periodo}"


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
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_export_type_display()} · {self.created_at:%Y-%m-%d}"