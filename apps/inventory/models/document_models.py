# apps/inventory/models/document_models.py

from django.conf import settings
from django.db import models

from apps.inventory.models.catalog_models import (
    DocumentType,
    InventoryBaseModel,
)


class AssetDocument(InventoryBaseModel):
    """
    Documento digital asociado a un activo,
    resguardo, baja o movimiento.
    """

    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="documents",
        null=True,
        blank=True,
    )
    custody_assignment = models.ForeignKey(
        "inventory.CustodyAssignment",
        on_delete=models.PROTECT,
        related_name="documents",
        null=True,
        blank=True,
    )
    disposal_request = models.ForeignKey(
        "inventory.DisposalRequest",
        on_delete=models.PROTECT,
        related_name="documents",
        null=True,
        blank=True,
    )
    movement = models.ForeignKey(
        "inventory.InventoryMovement",
        on_delete=models.PROTECT,
        related_name="documents",
        null=True,
        blank=True,
    )

    document_type = models.CharField(
        "Tipo de documento",
        max_length=50,
        choices=DocumentType.choices,
    )
    title = models.CharField(
        "Título",
        max_length=180,
    )
    file = models.FileField(
        "Archivo",
        upload_to="inventory/documents/%Y/%m/",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_documents_uploaded",
    )
    sha256_hash = models.CharField(
        "Hash SHA256",
        max_length=128,
        blank=True,
    )
    notes = models.TextField(
        "Notas",
        blank=True,
    )

    class Meta:
        db_table = "inventory_asset_documents"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["document_type"]),
        ]

    def save(self, *args, **kwargs):
        self.title = self.title.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_document_type_display()} · {self.title}"


class AssetPhoto(InventoryBaseModel):
    """
    Evidencia fotográfica del activo.

    Para alta y baja pediremos mínimo:
    - frente
    - serie / placa
    - estado general
    """

    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="photos",
    )
    photo_type = models.CharField(
        "Tipo de foto",
        max_length=50,
        choices=DocumentType.choices,
        default=DocumentType.PHOTO_FRONT,
    )
    image = models.ImageField(
        "Imagen",
        upload_to="inventory/photos/%Y/%m/",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_photos_uploaded",
    )
    caption = models.CharField(
        "Descripción",
        max_length=255,
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

    class Meta:
        db_table = "inventory_asset_photos"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.caption:
            self.caption = self.caption.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asset.inventory_number} · {self.get_photo_type_display()}"
    
