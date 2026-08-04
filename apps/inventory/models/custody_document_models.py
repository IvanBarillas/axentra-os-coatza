"""Documentos agrupadores e históricos inmutables de resguardo."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.inventory.models.catalog_models import InventoryBaseModel


class CustodyDocumentStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    IN_PROCESS = "IN_PROCESS", "En proceso"
    ACTIVE = "ACTIVE", "Vigente"
    CLOSED = "CLOSED", "Finalizado"
    REPLACED = "REPLACED", "Sustituido por cambio de titular"
    CANCELLED = "CANCELLED", "Cancelado"


class CustodyDocumentType(models.TextChoices):
    ASSIGNMENT = "ASSIGNMENT", "Resguardo de entrega"
    RELEASE = "RELEASE", "Constancia de entrega y liberación"


class CustodyDocument(InventoryBaseModel):
    """Cabecera de un documento que agrupa uno o varios resguardos."""

    folio = models.CharField(
        "Folio del documento",
        max_length=80,
        unique=True,
    )
    document_type = models.CharField(
        "Tipo de documento",
        max_length=20,
        choices=CustodyDocumentType.choices,
        default=CustodyDocumentType.ASSIGNMENT,
        db_index=True,
    )
    status = models.CharField(
        "Estado",
        max_length=20,
        choices=CustodyDocumentStatus.choices,
        default=CustodyDocumentStatus.DRAFT,
        db_index=True,
    )
    department_id = models.UUIDField(
        "UUID de la dependencia",
        db_index=True,
    )
    department_name_snapshot = models.CharField(
        "Dependencia",
        max_length=220,
    )
    department_code_snapshot = models.CharField(
        "Código de dependencia",
        max_length=40,
        blank=True,
    )
    assignee_mode = models.CharField(
        "Tipo de responsable",
        max_length=30,
    )
    assigned_to_id_snapshot = models.UUIDField(
        "UUID del responsable",
    )
    assigned_to_name_snapshot = models.CharField(
        "Responsable",
        max_length=300,
    )
    assigned_to_email_snapshot = models.EmailField(
        "Correo del responsable",
        blank=True,
    )
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custody_documents_prepared",
        verbose_name="Elaborado por",
    )
    prepared_at = models.DateTimeField(
        "Fecha de elaboración",
        default=timezone.now,
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custody_documents_closed",
        verbose_name="Finalizado por",
        null=True,
        blank=True,
    )
    closed_at = models.DateTimeField(
        "Fecha de finalización",
        null=True,
        blank=True,
    )
    closure_reason = models.TextField(
        "Motivo de finalización",
        blank=True,
    )
    replacement_of = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        related_name="replacement_document",
        verbose_name="Documento sustituido",
        null=True,
        blank=True,
    )
    source_document = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="release_documents",
        verbose_name="Resguardo que se libera",
        null=True,
        blank=True,
    )
    received_by_id_snapshot = models.UUIDField(
        "UUID de quien recibe",
        null=True,
        blank=True,
    )
    received_by_name_snapshot = models.CharField(
        "Recibido por",
        max_length=300,
        blank=True,
    )
    received_by_email_snapshot = models.EmailField(
        "Correo de quien recibe",
        blank=True,
    )
    notes = models.TextField("Notas", blank=True)

    class Meta:
        db_table = "inventory_custody_documents"
        verbose_name = "Documento de resguardo"
        verbose_name_plural = "Documentos de resguardo"
        ordering = ["-prepared_at"]
        indexes = [
            models.Index(
                fields=["department_id", "status"],
                name="inv_cust_doc_dept_status",
            ),
            models.Index(
                fields=["assigned_to_id_snapshot", "status"],
                name="inv_cust_doc_assignee",
            ),
            models.Index(
                fields=["prepared_at"],
                name="inv_cust_doc_prepared",
            ),
        ]

    @property
    def is_historical(self):
        return self.status in {
            CustodyDocumentStatus.CLOSED,
            CustodyDocumentStatus.REPLACED,
            CustodyDocumentStatus.CANCELLED,
        }

    def clean(self):
        errors = {}
        if self.document_type == CustodyDocumentType.RELEASE:
            if not self.source_document_id:
                errors["source_document"] = (
                    "La constancia debe indicar el resguardo que libera."
                )
            if not self.received_by_id_snapshot:
                errors["received_by_id_snapshot"] = (
                    "La constancia debe indicar quién recibe los bienes."
                )
        if self.is_historical:
            if not self.closed_at:
                errors["closed_at"] = "El histórico requiere fecha de cierre."
            if not self.closure_reason.strip():
                errors["closure_reason"] = "Indique el motivo del cierre."
        if self.replacement_of_id == self.id:
            errors["replacement_of"] = "Un documento no puede sustituirse a sí mismo."
        if errors:
            raise ValidationError(errors)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Los documentos de resguardo forman parte del histórico "
            "institucional y no pueden eliminarse."
        )

    def save(self, *args, **kwargs):
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).only(
                "status"
            ).first()
            if previous and previous.is_historical:
                raise ValidationError(
                    "El documento pertenece al histórico inmutable y "
                    "ya no admite modificaciones."
                )
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.folio} · {self.assigned_to_name_snapshot}"


class CustodyDocumentItem(InventoryBaseModel):
    """Renglón histórico que relaciona el documento con un resguardo."""

    document = models.ForeignKey(
        CustodyDocument,
        on_delete=models.PROTECT,
        related_name="items",
        verbose_name="Documento",
    )
    custody_assignment = models.ForeignKey(
        "inventory.CustodyAssignment",
        on_delete=models.PROTECT,
        related_name="document_items",
        verbose_name="Resguardo individual",
    )
    asset_id_snapshot = models.UUIDField("UUID histórico del bien")
    inventory_number_snapshot = models.CharField(
        "Folio patrimonial histórico",
        max_length=120,
    )
    asset_name_snapshot = models.CharField(
        "Nombre histórico del bien",
        max_length=220,
    )
    serial_number_snapshot = models.CharField(
        "Número de serie histórico",
        max_length=160,
        blank=True,
    )

    class Meta:
        db_table = "inventory_custody_document_items"
        verbose_name = "Bien en documento de resguardo"
        verbose_name_plural = "Bienes en documentos de resguardo"
        ordering = ["inventory_number_snapshot"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "asset_id_snapshot"],
                name="uq_inv_custody_document_asset",
            ),
        ]

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Los renglones históricos de un resguardo no pueden eliminarse."
        )

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(
                "Los renglones históricos de un resguardo son inmutables."
            )
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.inventory_number_snapshot} · {self.asset_name_snapshot}"


__all__ = [
    "CustodyDocument",
    "CustodyDocumentItem",
    "CustodyDocumentStatus",
    "CustodyDocumentType",
]
