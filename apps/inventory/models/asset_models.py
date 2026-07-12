# apps/inventory/models/asset_models.py

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.inventory.models.catalog_models import (
    AccountingAccount,
    AcquisitionType,
    AssetCategory,
    AssetControlType,
    AssetLifecycleStatus,
    InventoryBaseModel,
    PhysicalCondition,
)


class Asset(InventoryBaseModel):
    """
    Bien patrimonial principal.

    Este modelo no intenta ser sólo GLPI.
    Es el expediente patrimonial del bien.
    """

    official_inventory_number = models.CharField(
        "Folio oficial patrimonial",
        max_length=80,
        unique=True,
        null=True,
        blank=True,
        help_text="Folio estructurado para ORFIS / SIGMAVER. Ej: 039-26-5151-012-BM-0005.",
    )

    internal_inventory_number = models.CharField(
        "Folio interno Axentra",
        max_length=80,
        unique=True,
        null=True,
        blank=True,
        help_text="Folio operativo interno. Ej: AXN-INV-2026-000001.",
    )

    legacy_inventory_number = models.CharField(
        "Número de inventario anterior",
        max_length=80,
        blank=True,
        help_text="Folio previo o heredado durante una migración.",
    )

    name = models.CharField(
        "Nombre / descripción corta",
        max_length=180,
    )
    description = models.TextField(
        "Descripción detallada",
        blank=True,
    )

    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.PROTECT,
        related_name="assets",
    )
    accounting_account = models.ForeignKey(
        AccountingAccount,
        on_delete=models.PROTECT,
        related_name="assets",
        null=True,
        blank=True,
    )

    control_type = models.CharField(
        "Tipo de control",
        max_length=30,
        choices=AssetControlType.choices,
        default=AssetControlType.INTERNAL_CONTROL,
    )
    lifecycle_status = models.CharField(
        "Estado patrimonial",
        max_length=30,
        choices=AssetLifecycleStatus.choices,
        default=AssetLifecycleStatus.REGISTERED,
    )
    physical_condition = models.CharField(
        "Estado físico",
        max_length=30,
        choices=PhysicalCondition.choices,
        default=PhysicalCondition.GOOD,
    )

    acquisition_type = models.CharField(
        "Tipo de adquisición",
        max_length=40,
        choices=AcquisitionType.choices,
        default=AcquisitionType.PURCHASE,
    )
    acquisition_date = models.DateField(
        "Fecha de adquisición",
        null=True,
        blank=True,
    )
    registration_date = models.DateField(
        "Fecha de registro en inventario",
        null=True,
        blank=True,
    )

    acquisition_cost = models.DecimalField(
        "Costo de adquisición",
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    residual_value = models.DecimalField(
        "Valor residual / desecho",
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    useful_life_months = models.PositiveIntegerField(
        "Vida útil en meses",
        null=True,
        blank=True,
    )

    is_capitalizable = models.BooleanField(
        "Capitalizable contablemente",
        default=False,
    )
    capitalization_threshold_amount = models.DecimalField(
        "Umbral de capitalización aplicado",
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
    )

    manufacturer = models.ForeignKey(
        "inventory.Manufacturer",
        on_delete=models.PROTECT,
        related_name="assets",
        null=True,
        blank=True,
    )
    model = models.ForeignKey(
        "inventory.AssetModel",
        on_delete=models.PROTECT,
        related_name="assets",
        null=True,
        blank=True,
    )
    serial_number = models.CharField(
        "Número de serie / service tag",
        max_length=120,
        null=True,
        blank=True,
    )

    supplier = models.ForeignKey(
        "inventory.Supplier",
        on_delete=models.PROTECT,
        related_name="assets",
        null=True,
        blank=True,
    )
    contract = models.ForeignKey(
        "inventory.Contract",
        on_delete=models.PROTECT,
        related_name="assets",
        null=True,
        blank=True,
    )

    sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_assets",
        verbose_name="Sede física",
        null=True,
        blank=True,
    )
    dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_assets",
        verbose_name="Dependencia responsable",
        null=True,
        blank=True,
    )
    area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_assets",
        verbose_name="Área operativa",
        null=True,
        blank=True,
    )
    current_custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_assets_in_custody",
        verbose_name="Resguardatario actual",
        null=True,
        blank=True,
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

    notes = models.TextField(
        "Notas",
        blank=True,
    )
    extra_attributes = models.JSONField(
        "Atributos extendidos",
        default=dict,
        blank=True,
        help_text="Datos flexibles no normalizados. No usar para reglas críticas.",
    )

    class Meta:
        db_table = "inventory_assets"
        verbose_name = "Activo patrimonial"
        verbose_name_plural = "Activos patrimoniales"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["official_inventory_number"]),
            models.Index(fields=["internal_inventory_number"]),
            models.Index(fields=["legacy_inventory_number"]),
            models.Index(fields=["serial_number"]),
            models.Index(fields=["lifecycle_status"]),
            models.Index(fields=["control_type"]),
            models.Index(fields=["is_capitalizable"]),
        ]

    def clean(self):
        if self.serial_number:
            duplicated = (
                Asset.objects.filter(
                    serial_number__iexact=self.serial_number.strip(),
                    is_deleted=False,
                )
                .exclude(pk=self.pk)
                .exists()
            )

            if duplicated:
                raise ValidationError(
                    {
                        "serial_number": "Ya existe un activo con este número de serie."
                    }
                )

        if self.acquisition_cost < 0:
            raise ValidationError(
                {
                    "acquisition_cost": "El costo de adquisición no puede ser negativo."
                }
            )

        if self.residual_value < 0:
            raise ValidationError(
                {
                    "residual_value": "El valor residual no puede ser negativo."
                }
            )

        if self.residual_value > self.acquisition_cost:
            raise ValidationError(
                {
                    "residual_value": "El valor residual no puede ser mayor al costo de adquisición."
                }
            )

    def save(self, *args, **kwargs):
        if self.official_inventory_number:
            self.official_inventory_number = self.official_inventory_number.strip().upper()

        if self.internal_inventory_number:
            self.internal_inventory_number = self.internal_inventory_number.strip().upper()

        if self.legacy_inventory_number:
            self.legacy_inventory_number = self.legacy_inventory_number.strip().upper()

        if self.serial_number:
            self.serial_number = self.serial_number.strip().upper()

        self.name = self.name.strip().upper()

        super().save(*args, **kwargs)

    @property
    def display_inventory_number(self):
        return (
            self.official_inventory_number
            or self.internal_inventory_number
            or self.legacy_inventory_number
            or "SIN-FOLIO"
        )

    @property
    def depreciable_base(self):
        return max(self.acquisition_cost - self.residual_value, Decimal("0.00"))

    def __str__(self):
        return f"{self.display_inventory_number} · {self.name}"


class InventoryFolioSequence(InventoryBaseModel):
    """
    Secuencia transaccional para folios oficiales de inventario.

    Ejemplo de scope:
    039-26-5151-012-BM-0005

    El consecutivo vive agrupado por:
    municipio + año + CONAC + dependencia + tipo de activo.
    """

    municipality_code = models.CharField(
        "Clave municipal",
        max_length=3,
    )
    year = models.PositiveSmallIntegerField(
        "Año corto",
        help_text="Ejemplo: 26 para 2026.",
    )
    conac_code = models.CharField(
        "Código CONAC / COG",
        max_length=10,
    )
    dependency_code = models.CharField(
        "Código presupuestal de dependencia",
        max_length=10,
    )
    asset_type_code = models.CharField(
        "Tipo de bien",
        max_length=2,
        help_text="BM, BI, BP, etc.",
    )
    current_number = models.PositiveIntegerField(
        "Consecutivo actual",
        default=0,
    )

    class Meta:
        db_table = "inventory_folio_sequences"
        verbose_name = "Secuencia de folio"
        verbose_name_plural = "Secuencias de folios"
        ordering = [
            "municipality_code",
            "year",
            "conac_code",
            "dependency_code",
            "asset_type_code",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "municipality_code",
                    "year",
                    "conac_code",
                    "dependency_code",
                    "asset_type_code",
                ],
                name="uq_inventory_folio_sequence_scope",
            )
        ]
        indexes = [
            models.Index(
                fields=[
                    "municipality_code",
                    "year",
                    "conac_code",
                    "dependency_code",
                    "asset_type_code",
                ]
            ),
        ]

    def save(self, *args, **kwargs):
        self.municipality_code = self.municipality_code.strip().zfill(3)
        self.conac_code = self.conac_code.strip().upper()
        self.dependency_code = self.dependency_code.strip().upper().zfill(3)
        self.asset_type_code = self.asset_type_code.strip().upper()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.municipality_code}-{self.year:02d}-"
            f"{self.conac_code}-{self.dependency_code}-"
            f"{self.asset_type_code} · {self.current_number:04d}"
        )


class ImmovableAssetDetail(InventoryBaseModel):
    """
    Detalle especial para bienes inmuebles:
    terrenos, edificios, bodegas, oficinas, instalaciones.
    """

    asset = models.OneToOneField(
        Asset,
        on_delete=models.CASCADE,
        related_name="immovable_detail",
    )
    cadastral_key = models.CharField(
        "Clave catastral",
        max_length=120,
        blank=True,
    )
    public_registry_record = models.CharField(
        "Registro Público / inscripción",
        max_length=180,
        blank=True,
    )
    deed_number = models.CharField(
        "Número de escritura / título",
        max_length=120,
        blank=True,
    )
    surface_m2 = models.DecimalField(
        "Superficie m²",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    legal_status = models.CharField(
        "Estado jurídico",
        max_length=180,
        blank=True,
    )

    class Meta:
        db_table = "inventory_immovable_asset_details"
        verbose_name = "Detalle de inmueble"
        verbose_name_plural = "Detalles de inmuebles"

    def save(self, *args, **kwargs):
        if self.cadastral_key:
            self.cadastral_key = self.cadastral_key.strip().upper()
        if self.public_registry_record:
            self.public_registry_record = self.public_registry_record.strip().upper()
        if self.deed_number:
            self.deed_number = self.deed_number.strip().upper()
        if self.legal_status:
            self.legal_status = self.legal_status.strip().upper()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Inmueble · {self.asset.display_inventory_number}"
    
