# apps/inventory/models/custody_models.py

from django.conf import settings
from django.core.exceptions import ValidationError
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
    pero sólo uno activo a la vez.

    La lógica para activar, devolver o cancelar resguardos
    no debe vivir aquí; debe vivir en services/.
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
        verbose_name = "Resguardo"
        verbose_name_plural = "Resguardos"
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["folio"]),
            models.Index(fields=["asset"]),
            models.Index(fields=["status"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["assigned_by"]),
            models.Index(fields=["dependencia"]),
            models.Index(fields=["area"]),
            models.Index(fields=["sede"]),
            models.Index(fields=["assigned_at"]),
            models.Index(fields=["signed_at"]),
            models.Index(fields=["returned_at"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def clean(self):
        if self.signed_at and self.assigned_at:
            if self.signed_at < self.assigned_at:
                raise ValidationError(
                    {
                        "signed_at": "La fecha de firma no puede ser anterior a la fecha de asignación."
                    }
                )

        if self.returned_at and self.assigned_at:
            if self.returned_at < self.assigned_at:
                raise ValidationError(
                    {
                        "returned_at": "La fecha de devolución no puede ser anterior a la fecha de asignación."
                    }
                )

        if self.status == CustodyStatus.RETURNED and not self.returned_at:
            raise ValidationError(
                {
                    "returned_at": "Un resguardo devuelto debe tener fecha de devolución."
                }
            )

        if self.status == CustodyStatus.ACTIVE and self.returned_at:
            raise ValidationError(
                {
                    "status": "Un resguardo activo no puede tener fecha de devolución."
                }
            )

    def save(self, *args, **kwargs):
        self.folio = self.folio.strip().upper()

        if self.digital_signature_hash:
            self.digital_signature_hash = self.digital_signature_hash.strip()

        if self.notes:
            self.notes = self.notes.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.folio} · "
            f"{self.asset.display_inventory_number} → "
            f"{self.assigned_to}"
        )
        
