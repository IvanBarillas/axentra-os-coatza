# apps/inventory/models/technical_models.py

from django.db import models

from apps.inventory.models.catalog_models import (
    InventoryBaseModel,
    RelationType,
)


class TechnicalAssetType(models.TextChoices):
    COMPUTER = "COMPUTER", "Computadora"
    SERVER = "SERVER", "Servidor"
    MONITOR = "MONITOR", "Monitor"
    PRINTER = "PRINTER", "Impresora / Multifuncional"
    NETWORK_DEVICE = "NETWORK_DEVICE", "Equipo de Red"
    ACCESS_POINT = "ACCESS_POINT", "Access Point"
    TELEPHONY_DEVICE = "TELEPHONY_DEVICE", "Teléfono IP / Analógico"
    TELEPHONY_LINE = "TELEPHONY_LINE", "Línea Telefónica / SIP"
    PBX = "PBX", "PBX / Conmutador"
    UPS = "UPS", "UPS / No Break"
    CAMERA = "CAMERA", "Cámara / CCTV"
    SOFTWARE_LICENSE = "SOFTWARE_LICENSE", "Licencia de Software"
    PERIPHERAL = "PERIPHERAL", "Periférico"
    OTHER = "OTHER", "Otro"


class TechnicalAssetProfile(InventoryBaseModel):
    """
    Ficha técnica tipo GLPI.

    Sólo se crea para activos tecnológicos.
    El activo patrimonial sigue siendo Asset.
    """

    asset = models.OneToOneField(
        "inventory.Asset",
        on_delete=models.CASCADE,
        related_name="technical_profile",
    )
    technical_type = models.CharField(
        "Tipo técnico",
        max_length=40,
        choices=TechnicalAssetType.choices,
        default=TechnicalAssetType.OTHER,
    )

    hostname = models.CharField(
        "Hostname",
        max_length=120,
        blank=True,
    )
    ip_address = models.GenericIPAddressField(
        "Dirección IP",
        null=True,
        blank=True,
    )
    mac_address = models.CharField(
        "Dirección MAC",
        max_length=40,
        blank=True,
    )

    operating_system = models.CharField(
        "Sistema operativo",
        max_length=160,
        blank=True,
    )
    processor = models.CharField(
        "Procesador",
        max_length=160,
        blank=True,
    )
    ram_gb = models.DecimalField(
        "RAM GB",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    storage_description = models.CharField(
        "Almacenamiento",
        max_length=200,
        blank=True,
    )

    vlan = models.CharField(
        "VLAN",
        max_length=50,
        blank=True,
    )
    ssid = models.CharField(
        "SSID",
        max_length=120,
        blank=True,
    )
    extension_number = models.CharField(
        "Extensión telefónica",
        max_length=50,
        blank=True,
    )
    phone_number = models.CharField(
        "Número telefónico / troncal",
        max_length=50,
        blank=True,
    )

    warranty_end_date = models.DateField(
        "Fin de garantía",
        null=True,
        blank=True,
    )
    technical_notes = models.TextField(
        "Notas técnicas",
        blank=True,
    )
    specs = models.JSONField(
        "Especificaciones técnicas extendidas",
        default=dict,
        blank=True,
    )

    class Meta:
        db_table = "inventory_technical_asset_profiles"
        ordering = ["asset__inventory_number"]
        indexes = [
            models.Index(fields=["technical_type"]),
            models.Index(fields=["hostname"]),
            models.Index(fields=["ip_address"]),
            models.Index(fields=["mac_address"]),
        ]

    def save(self, *args, **kwargs):
        if self.hostname:
            self.hostname = self.hostname.strip().upper()
        if self.mac_address:
            self.mac_address = self.mac_address.strip().upper()
        if self.operating_system:
            self.operating_system = self.operating_system.strip().upper()
        if self.processor:
            self.processor = self.processor.strip().upper()
        if self.storage_description:
            self.storage_description = self.storage_description.strip().upper()
        if self.ssid:
            self.ssid = self.ssid.strip()
        if self.extension_number:
            self.extension_number = self.extension_number.strip()
        if self.phone_number:
            self.phone_number = self.phone_number.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asset.inventory_number} · {self.get_technical_type_display()}"


class AssetRelation(InventoryBaseModel):
    """
    Relación tipo CMDB.

    Ejemplos:
    - Computadora incluye monitor
    - Switch conectado a access point
    - PBX usa línea SIP
    - Laptop asignada con cargador
    """

    parent_asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="child_relations",
    )
    child_asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="parent_relations",
    )
    relation_type = models.CharField(
        "Tipo de relación",
        max_length=40,
        choices=RelationType.choices,
    )
    notes = models.TextField(
        "Notas",
        blank=True,
    )

    class Meta:
        db_table = "inventory_asset_relations"
        unique_together = ("parent_asset", "child_asset", "relation_type")
        ordering = ["parent_asset__inventory_number"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.parent_asset_id and self.child_asset_id:
            if self.parent_asset_id == self.child_asset_id:
                raise ValidationError(
                    "Un activo no puede relacionarse consigo mismo."
                )

    def __str__(self):
        return (
            f"{self.parent_asset.inventory_number} "
            f"{self.get_relation_type_display()} "
            f"{self.child_asset.inventory_number}"
        )