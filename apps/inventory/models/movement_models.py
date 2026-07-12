# apps/inventory/models/movement_models.py

from django.conf import settings
from django.db import models

from apps.inventory.models.catalog_models import (
    DisposalReason,
    InventoryBaseModel,
    MovementType,
)


class InventoryMovement(InventoryBaseModel):
    """
    Bitácora administrativa de movimientos de activos.

    No muta el Asset por sí sola.
    Los services harán la operación atómica.
    """

    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(
        "Tipo de movimiento",
        max_length=40,
        choices=MovementType.choices,
    )

    from_dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_movements_from",
        null=True,
        blank=True,
    )
    to_dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_movements_to",
        null=True,
        blank=True,
    )
    from_area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_movements_from",
        null=True,
        blank=True,
    )
    to_area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_movements_to",
        null=True,
        blank=True,
    )
    from_sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_movements_from",
        null=True,
        blank=True,
    )
    to_sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_movements_to",
        null=True,
        blank=True,
    )

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_movements_from",
        null=True,
        blank=True,
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_movements_to",
        null=True,
        blank=True,
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_movements_performed",
    )
    reason = models.TextField(
        "Justificación",
    )
    reference_folio = models.CharField(
        "Folio de referencia",
        max_length=120,
        blank=True,
    )

    payload = models.JSONField(
        "Payload de movimiento",
        default=dict,
        blank=True,
    )

    class Meta:
        db_table = "inventory_asset_movements"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["movement_type"]),
            models.Index(fields=["reference_folio"]),
        ]

    def save(self, *args, **kwargs):
        if self.reference_folio:
            self.reference_folio = self.reference_folio.strip().upper()
        self.reason = self.reason.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asset.inventory_number} · {self.get_movement_type_display()}"


class DisposalStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    REQUESTED = "REQUESTED", "Solicitada"
    UNDER_REVIEW = "UNDER_REVIEW", "En Revisión"
    TECHNICAL_REPORT_REQUIRED = "TECHNICAL_REPORT_REQUIRED", "Requiere Dictamen"
    APPROVED = "APPROVED", "Aprobada"
    REJECTED = "REJECTED", "Rechazada"
    EXECUTED = "EXECUTED", "Ejecutada"
    CANCELLED = "CANCELLED", "Cancelada"


class DisposalRequest(InventoryBaseModel):
    """
    Expediente de baja patrimonial.

    Aquí vivirán los soportes: oficio, acta, dictamen,
    relación de bienes, fotos, denuncia, etc.
    """

    folio = models.CharField(
        "Folio de baja",
        max_length=80,
        unique=True,
    )
    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="disposal_requests",
    )
    reason = models.CharField(
        "Motivo de baja",
        max_length=50,
        choices=DisposalReason.choices,
    )
    status = models.CharField(
        "Estado del expediente",
        max_length=40,
        choices=DisposalStatus.choices,
        default=DisposalStatus.DRAFT,
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_disposals_requested",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_disposals_reviewed",
        null=True,
        blank=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_disposals_approved",
        null=True,
        blank=True,
    )

    requested_at = models.DateTimeField(
        "Fecha de solicitud",
        auto_now_add=True,
    )
    reviewed_at = models.DateTimeField(
        "Fecha de revisión",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(
        "Fecha de aprobación",
        null=True,
        blank=True,
    )
    executed_at = models.DateTimeField(
        "Fecha de ejecución",
        null=True,
        blank=True,
    )

    description = models.TextField(
        "Descripción / justificación",
    )
    legal_reference = models.TextField(
        "Fundamento / referencia legal",
        blank=True,
    )

    class Meta:
        db_table = "inventory_disposal_requests"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["folio"]),
            models.Index(fields=["status"]),
            models.Index(fields=["reason"]),
        ]

    def save(self, *args, **kwargs):
        self.folio = self.folio.strip().upper()
        self.description = self.description.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.folio} · {self.asset.inventory_number}"