# apps/inventory/models/movement_models.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.inventory.models.catalog_models import (
    DisposalReason,
    InventoryBaseModel,
    MovementType,
)


class InventoryMovement(InventoryBaseModel):
    """
    Bitácora administrativa de movimientos patrimoniales.

    Este modelo conserva el evento oficial:
    alta, asignación, reasignación, préstamo, devolución,
    cambio de ubicación, solicitud de baja, aprobación de baja,
    auditoría física o ajuste administrativo.

    No muta el Asset por sí solo.
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
        help_text="Folio de resguardo, baja, oficio, solicitud o expediente relacionado.",
    )

    payload = models.JSONField(
        "Payload de movimiento",
        default=dict,
        blank=True,
        help_text="Snapshot auditable del movimiento. No usar como fuente primaria de reglas.",
    )

    class Meta:
        db_table = "inventory_asset_movements"
        verbose_name = "Movimiento patrimonial"
        verbose_name_plural = "Movimientos patrimoniales"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["asset"]),
            models.Index(fields=["movement_type"]),
            models.Index(fields=["reference_folio"]),
            models.Index(fields=["from_dependencia"]),
            models.Index(fields=["to_dependencia"]),
            models.Index(fields=["from_area"]),
            models.Index(fields=["to_area"]),
            models.Index(fields=["from_sede"]),
            models.Index(fields=["to_sede"]),
            models.Index(fields=["from_user"]),
            models.Index(fields=["to_user"]),
            models.Index(fields=["performed_by"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def clean(self):
        if not self.reason or not self.reason.strip():
            raise ValidationError(
                {
                    "reason": "La justificación del movimiento es obligatoria."
                }
            )

        if self.movement_type in {
            MovementType.ASSIGNMENT,
            MovementType.REASSIGNMENT,
            MovementType.LOAN,
        }:
            if not self.to_user:
                raise ValidationError(
                    {
                        "to_user": "Este tipo de movimiento requiere usuario destino."
                    }
                )

        if self.movement_type == MovementType.RETURN:
            if not self.from_user:
                raise ValidationError(
                    {
                        "from_user": "Una devolución requiere usuario origen."
                    }
                )

    def save(self, *args, **kwargs):
        if self.reference_folio:
            self.reference_folio = self.reference_folio.strip().upper()

        self.reason = self.reason.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.asset.display_inventory_number} · "
            f"{self.get_movement_type_display()}"
        )


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

    Aquí vivirán los soportes:
    oficio, acta, dictamen, relación de bienes, fotos,
    denuncia, fundamento legal y ejecución de baja.

    La generación del dictamen puede vivir en otra app.
    Inventory conserva la baja patrimonial oficial.
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

    source_app = models.CharField(
        "App origen",
        max_length=80,
        blank=True,
        help_text="Ejemplo: innovation, workflows, helpdesk.",
    )
    source_model = models.CharField(
        "Modelo origen",
        max_length=120,
        blank=True,
        help_text="Ejemplo: TechnicalOpinion, DisposalWorkflow.",
    )
    source_object_id = models.CharField(
        "ID objeto origen",
        max_length=120,
        blank=True,
        help_text="UUID o identificador del registro origen.",
    )

    class Meta:
        db_table = "inventory_disposal_requests"
        verbose_name = "Expediente de baja"
        verbose_name_plural = "Expedientes de baja"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["folio"]),
            models.Index(fields=["asset"]),
            models.Index(fields=["status"]),
            models.Index(fields=["reason"]),
            models.Index(fields=["requested_by"]),
            models.Index(fields=["reviewed_by"]),
            models.Index(fields=["approved_by"]),
            models.Index(fields=["requested_at"]),
            models.Index(fields=["reviewed_at"]),
            models.Index(fields=["approved_at"]),
            models.Index(fields=["executed_at"]),
            models.Index(fields=["source_app", "source_model", "source_object_id"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def clean(self):
        if not self.description or not self.description.strip():
            raise ValidationError(
                {
                    "description": "La descripción o justificación de baja es obligatoria."
                }
            )

        if self.reviewed_at and self.reviewed_at < self.requested_at:
            raise ValidationError(
                {
                    "reviewed_at": "La fecha de revisión no puede ser anterior a la solicitud."
                }
            )

        if self.approved_at and self.approved_at < self.requested_at:
            raise ValidationError(
                {
                    "approved_at": "La fecha de aprobación no puede ser anterior a la solicitud."
                }
            )

        if self.executed_at and self.approved_at:
            if self.executed_at < self.approved_at:
                raise ValidationError(
                    {
                        "executed_at": "La fecha de ejecución no puede ser anterior a la aprobación."
                    }
                )

        if self.status == DisposalStatus.APPROVED and not self.approved_by:
            raise ValidationError(
                {
                    "approved_by": "Una baja aprobada debe indicar quién aprobó."
                }
            )

        if self.status == DisposalStatus.EXECUTED and not self.executed_at:
            raise ValidationError(
                {
                    "executed_at": "Una baja ejecutada debe tener fecha de ejecución."
                }
            )

    def save(self, *args, **kwargs):
        self.folio = self.folio.strip().upper()
        self.description = self.description.strip()

        if self.legal_reference:
            self.legal_reference = self.legal_reference.strip()

        if self.source_app:
            self.source_app = self.source_app.strip().lower()

        if self.source_model:
            self.source_model = self.source_model.strip()

        if self.source_object_id:
            self.source_object_id = self.source_object_id.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.folio} · {self.asset.display_inventory_number}"
    
