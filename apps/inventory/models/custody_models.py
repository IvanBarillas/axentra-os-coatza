# apps/inventory/models/custody_models.py

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.inventory.models.catalog_models import InventoryBaseModel


class CustodyStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    PENDING_SIGNATURE = "PENDING_SIGNATURE", "Pendiente de Firma"
    ACTIVE = "ACTIVE", "Activo"
    REJECTED = "REJECTED", "Rechazado"
    RETURNED = "RETURNED", "Devuelto"
    CANCELLED = "CANCELLED", "Cancelado"


class CustodyAssignment(InventoryBaseModel):
    """
    Vale de resguardo oficial.

    Un activo puede tener varios resguardos históricos,
    pero sólo uno activo.
    """

    folio = models.CharField(
        "Folio de resguardo",
        max_length=80,
        unique=True,
    )
    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="custody_assignments",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custody_assignments",
        verbose_name="Servidor público resguardatario",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custody_created",
        verbose_name="Entrega / genera resguardo",
    )

    dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_custodies",
        null=True,
        blank=True,
    )
    area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_custodies",
        null=True,
        blank=True,
    )
    sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_custodies",
        null=True,
        blank=True,
    )

    status = models.CharField(
        "Estado del resguardo",
        max_length=30,
        choices=CustodyStatus.choices,
        default=CustodyStatus.PENDING_SIGNATURE,
    )

    assigned_at = models.DateTimeField(
        "Fecha de asignación",
        default=timezone.now,
    )
    signed_at = models.DateTimeField(
        "Fecha de firma",
        null=True,
        blank=True,
    )
    returned_at = models.DateTimeField(
        "Fecha de devolución",
        null=True,
        blank=True,
    )

    digital_signature_hash = models.CharField(
        "Hash de firma digital",
        max_length=255,
        blank=True,
    )
    notes = models.TextField(
        "Notas",
        blank=True,
    )

    class Meta:
        db_table = "inventory_custody_assignments"
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["folio"]),
            models.Index(fields=["status"]),
            models.Index(fields=["assigned_to"]),
        ]

    def save(self, *args, **kwargs):
        self.folio = self.folio.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.folio} · {self.asset.inventory_number} → {self.assigned_to}"