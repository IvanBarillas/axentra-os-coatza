# apps/inventory/models/document_models.py

import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.inventory.models.catalog_models import (
    DisposalReason,
    DocumentType,
    InventoryBaseModel,
)
from apps.inventory.models.movement_models import DisposalApprovalStage


# =============================================================================
# FUNCIONES DE ALMACENAMIENTO
# =============================================================================


def inventory_document_upload_path(instance, filename):
    """
    Genera una ruta estable sin depender del folio o nombre del propietario.

    Los folios y nombres pueden cambiar. El UUID del documento permanece
    estable durante toda su vida.
    """
    today = timezone.localdate()
    safe_filename = Path(filename).name

    return (
        f"inventory/documents/"
        f"{today:%Y/%m}/"
        f"{instance.id}/"
        f"{safe_filename}"
    )


def inventory_photo_upload_path(instance, filename):
    today = timezone.localdate()
    safe_filename = Path(filename).name

    return (
        f"inventory/photos/"
        f"{today:%Y/%m}/"
        f"{instance.id}/"
        f"{safe_filename}"
    )


# =============================================================================
# CATÁLOGOS DOCUMENTALES
# =============================================================================


class InventoryDocumentOwnerType(models.TextChoices):
    INTAKE_REQUEST = (
        "INTAKE_REQUEST",
        "Solicitud de alta",
    )
    ASSET = "ASSET", "Activo patrimonial"
    CUSTODY_ASSIGNMENT = (
        "CUSTODY_ASSIGNMENT",
        "Resguardo",
    )
    MOVEMENT = "MOVEMENT", "Movimiento patrimonial"
    LOAN = "LOAN", "Préstamo"
    DISPOSAL_REQUEST = (
        "DISPOSAL_REQUEST",
        "Expediente de baja",
    )
    DISPOSAL_APPROVAL = (
        "DISPOSAL_APPROVAL",
        "Etapa de aprobación de baja",
    )
    PHYSICAL_AUDIT_SESSION = (
        "PHYSICAL_AUDIT_SESSION",
        "Auditoría física",
    )
    PHYSICAL_AUDIT_ITEM = (
        "PHYSICAL_AUDIT_ITEM",
        "Partida de auditoría física",
    )
    SERVICE_ORDER = (
        "SERVICE_ORDER",
        "Orden de servicio",
    )
    TECHNICAL_DIAGNOSIS = (
        "TECHNICAL_DIAGNOSIS",
        "Diagnóstico técnico",
    )
    TECHNICAL_REPORT = (
        "TECHNICAL_REPORT",
        "Dictamen técnico",
    )
    COMPONENT = "COMPONENT", "Componente o refacción"
    OTHER = "OTHER", "Otro expediente"


class DocumentValidationStatus(models.TextChoices):
    PENDING = "PENDING", "Pendiente de validación"
    VALIDATED = "VALIDATED", "Validado"
    REJECTED = "REJECTED", "Rechazado"
    EXPIRED = "EXPIRED", "Vencido"
    SUPERSEDED = "SUPERSEDED", "Sustituido"
    CANCELLED = "CANCELLED", "Cancelado"


class DocumentAccessLevel(models.TextChoices):
    PUBLIC = "PUBLIC", "Público"
    INTERNAL = "INTERNAL", "Uso interno"
    CONFIDENTIAL = "CONFIDENTIAL", "Confidencial"
    RESTRICTED = "RESTRICTED", "Acceso restringido"


class DocumentValidationEventType(models.TextChoices):
    UPLOADED = "UPLOADED", "Documento cargado"
    SUBMITTED = "SUBMITTED", "Enviado a validación"
    VALIDATED = "VALIDATED", "Documento validado"
    REJECTED = "REJECTED", "Documento rechazado"
    SUPERSEDED = "SUPERSEDED", "Documento sustituido"
    CANCELLED = "CANCELLED", "Documento cancelado"
    DOWNLOADED = "DOWNLOADED", "Documento descargado"
    BYPASS = "BYPASS", "Validación mediante bypass"


class InventoryPhotoType(models.TextChoices):
    FRONT = "FRONT", "Vista frontal"
    BACK = "BACK", "Vista posterior"
    LEFT_SIDE = "LEFT_SIDE", "Costado izquierdo"
    RIGHT_SIDE = "RIGHT_SIDE", "Costado derecho"
    SERIAL = "SERIAL", "Serie / placa"
    INVENTORY_LABEL = (
        "INVENTORY_LABEL",
        "Etiqueta de inventario",
    )
    GENERAL_CONDITION = (
        "GENERAL_CONDITION",
        "Condición general",
    )
    LOCATION = "LOCATION", "Ubicación física"
    DAMAGE = "DAMAGE", "Daño"
    REPAIR_BEFORE = (
        "REPAIR_BEFORE",
        "Antes de reparación",
    )
    REPAIR_AFTER = (
        "REPAIR_AFTER",
        "Después de reparación",
    )
    DELIVERY = "DELIVERY", "Entrega"
    RETURN = "RETURN", "Devolución"
    PHYSICAL_AUDIT = (
        "PHYSICAL_AUDIT",
        "Auditoría física",
    )
    DISPOSAL = "DISPOSAL", "Evidencia de baja"
    OTHER = "OTHER", "Otra fotografía"


class DocumentRequirementLevel(models.TextChoices):
    REQUIRED = "REQUIRED", "Obligatorio"
    OPTIONAL = "OPTIONAL", "Opcional"


class DisposalStageDocumentRequirement(InventoryBaseModel):
    """Documento esperado para una etapa y, opcionalmente, un motivo de baja."""

    stage = models.CharField(
        "Etapa de baja",
        max_length=40,
        choices=DisposalApprovalStage.choices,
    )
    disposal_reason = models.CharField(
        "Motivo específico",
        max_length=50,
        choices=DisposalReason.choices,
        blank=True,
        help_text="Vacío significa que aplica a todos los motivos.",
    )
    document_type = models.CharField(
        "Tipo de documento",
        max_length=60,
        choices=DocumentType.choices,
    )
    requirement_level = models.CharField(
        "Nivel de requisito",
        max_length=20,
        choices=DocumentRequirementLevel.choices,
        default=DocumentRequirementLevel.REQUIRED,
    )
    instructions = models.TextField("Indicaciones", blank=True)

    class Meta:
        db_table = "inventory_disposal_stage_document_requirements"
        verbose_name = "Requisito documental de baja"
        verbose_name_plural = "Requisitos documentales de bajas"
        ordering = ["stage", "disposal_reason", "document_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["stage", "disposal_reason", "document_type"],
                name="uq_inv_disp_doc_requirement",
            )
        ]

    def __str__(self):
        return f"{self.get_stage_display()} · {self.get_document_type_display()}"


# =============================================================================
# DOCUMENTO DIGITAL
# =============================================================================


class AssetDocument(InventoryBaseModel):
    """
    Documento digital de Inventory.

    Se conserva el nombre AssetDocument por compatibilidad conceptual, pero
    puede pertenecer a cualquier expediente del módulo mediante:

        owner_type + owner_id

    Esto permite cargar documentos durante una solicitud de alta, antes de
    que exista el activo oficial, y evita acoplar este modelo con cada nuevo
    expediente de Inventory.

    La existencia del propietario debe validarse desde InventoryDocumentService.
    """

    owner_type = models.CharField(
        "Tipo de expediente propietario",
        max_length=40,
        choices=InventoryDocumentOwnerType.choices,
        db_index=True,
    )
    owner_id = models.UUIDField(
        "UUID del expediente propietario",
        db_index=True,
    )

    document_type = models.CharField(
        "Tipo de documento",
        max_length=60,
        choices=DocumentType.choices,
        db_index=True,
    )
    title = models.CharField(
        "Título",
        max_length=180,
    )
    description = models.TextField(
        "Descripción",
        blank=True,
    )

    file = models.FileField(
        "Archivo",
        upload_to=inventory_document_upload_path,
    )
    original_filename = models.CharField(
        "Nombre original",
        max_length=255,
    )
    content_type = models.CharField(
        "Tipo MIME",
        max_length=120,
        blank=True,
    )
    file_size = models.PositiveBigIntegerField(
        "Tamaño en bytes",
        null=True,
        blank=True,
    )
    sha256_hash = models.CharField(
        "Hash SHA-256",
        max_length=64,
        blank=True,
        db_index=True,
        help_text=(
            "Debe calcularse desde el servicio de carga después de recibir "
            "el archivo."
        ),
    )

    validation_status = models.CharField(
        "Estado de validación",
        max_length=30,
        choices=DocumentValidationStatus.choices,
        default=DocumentValidationStatus.PENDING,
        db_index=True,
    )
    access_level = models.CharField(
        "Nivel de acceso",
        max_length=30,
        choices=DocumentAccessLevel.choices,
        default=DocumentAccessLevel.INTERNAL,
        db_index=True,
    )
    is_required_evidence = models.BooleanField(
        "Evidencia obligatoria",
        default=False,
        db_index=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_documents_uploaded",
        verbose_name="Cargado por",
    )
    uploaded_by_name_snapshot = models.CharField(
        "Nombre de quien cargó",
        max_length=300,
    )
    uploaded_by_email_snapshot = models.EmailField(
        "Correo de quien cargó",
    )
    uploaded_at = models.DateTimeField(
        "Fecha de carga",
        default=timezone.now,
        db_index=True,
    )

    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_documents_validated",
        verbose_name="Validado por",
        null=True,
        blank=True,
    )
    validated_at = models.DateTimeField(
        "Fecha de validación",
        null=True,
        blank=True,
    )
    validation_notes = models.TextField(
        "Notas de validación",
        blank=True,
    )
    rejection_reason = models.TextField(
        "Motivo de rechazo",
        blank=True,
    )

    document_date = models.DateField(
        "Fecha del documento",
        null=True,
        blank=True,
    )
    expires_at = models.DateField(
        "Fecha de vencimiento",
        null=True,
        blank=True,
    )
    external_reference = models.CharField(
        "Referencia externa",
        max_length=180,
        blank=True,
        help_text=(
            "Folio de factura, contrato, oficio, acta o documento externo."
        ),
    )

    document_group_id = models.UUIDField(
        "Grupo de versiones",
        default=uuid.uuid4,
        db_index=True,
        help_text=(
            "Las versiones del mismo documento comparten este UUID."
        ),
    )
    version_number = models.PositiveSmallIntegerField(
        "Versión",
        default=1,
    )
    is_current_version = models.BooleanField(
        "Versión vigente",
        default=True,
        db_index=True,
    )
    replaces_document = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="replacement_versions",
        verbose_name="Documento sustituido",
        null=True,
        blank=True,
    )

    contains_personal_data = models.BooleanField(
        "Contiene datos personales",
        default=False,
    )
    contains_sensitive_data = models.BooleanField(
        "Contiene datos sensibles",
        default=False,
    )

    bypass_used = models.BooleanField(
        "Validado mediante bypass",
        default=False,
        db_index=True,
    )
    bypass_reason = models.TextField(
        "Motivo del bypass",
        blank=True,
    )

    metadata = models.JSONField(
        "Metadatos",
        default=dict,
        blank=True,
        help_text="No utilizar como fuente primaria de reglas críticas.",
    )
    notes = models.TextField(
        "Notas internas",
        blank=True,
    )

    class Meta:
        db_table = "inventory_asset_documents"
        verbose_name = "Documento de inventario"
        verbose_name_plural = "Documentos de inventario"
        ordering = ["-uploaded_at", "-created_at"]
        indexes = [
            models.Index(
                fields=["owner_type", "owner_id"],
                name="idx_inv_document_owner",
            ),
            models.Index(
                fields=[
                    "owner_type",
                    "owner_id",
                    "document_type",
                ],
                name="idx_inv_document_owner_type",
            ),
            models.Index(
                fields=["validation_status", "uploaded_at"],
            ),
            models.Index(
                fields=["access_level", "uploaded_at"],
            ),
            models.Index(
                fields=["document_group_id", "version_number"],
            ),
            models.Index(
                fields=["is_required_evidence", "validation_status"],
                name="idx_inv_doc_req_status",
            ),
            models.Index(fields=["uploaded_by", "uploaded_at"]),
            models.Index(fields=["validated_by", "validated_at"]),
            models.Index(fields=["external_reference"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["document_group_id", "version_number"],
                name="uq_inv_document_group_version",
            ),
            models.UniqueConstraint(
                fields=["document_group_id"],
                condition=Q(
                    is_current_version=True,
                    is_deleted=False,
                ),
                name="uq_inv_doc_current_ver",
            ),
            models.CheckConstraint(
                condition=Q(version_number__gte=1),
                name="ck_inv_document_version_gte_1",
            ),
        ]

    def clean(self):
        errors = {}

        if not self.title.strip():
            errors["title"] = (
                "El título del documento es obligatorio."
            )

        if not self.original_filename.strip():
            errors["original_filename"] = (
                "Debe conservar el nombre original del archivo."
            )

        if not self.uploaded_by_name_snapshot.strip():
            errors["uploaded_by_name_snapshot"] = (
                "Debe conservar el nombre de quien cargó el documento."
            )

        if not self.uploaded_by_email_snapshot.strip():
            errors["uploaded_by_email_snapshot"] = (
                "Debe conservar el correo de quien cargó el documento."
            )

        if self.version_number < 1:
            errors["version_number"] = (
                "La versión debe ser mayor o igual a uno."
            )

        if (
            self.expires_at
            and self.document_date
            and self.expires_at < self.document_date
        ):
            errors["expires_at"] = (
                "La fecha de vencimiento no puede ser anterior "
                "a la fecha del documento."
            )

        if self.validation_status == DocumentValidationStatus.VALIDATED:
            if not self.validated_by_id:
                errors["validated_by"] = (
                    "Un documento validado debe indicar quién lo validó."
                )

            if not self.validated_at:
                errors["validated_at"] = (
                    "Un documento validado debe registrar la fecha."
                )

        if self.validation_status == DocumentValidationStatus.REJECTED:
            if not self.validated_by_id:
                errors["validated_by"] = (
                    "Debe indicar quién rechazó el documento."
                )

            if not self.validated_at:
                errors["validated_at"] = (
                    "Debe registrar la fecha del rechazo."
                )

            if not self.rejection_reason.strip():
                errors["rejection_reason"] = (
                    "Debe indicar el motivo del rechazo."
                )

        if self.validated_at and self.validated_at < self.uploaded_at:
            errors["validated_at"] = (
                "La validación no puede ser anterior a la carga."
            )

        if self.replaces_document_id:
            if self.replaces_document_id == self.id:
                errors["replaces_document"] = (
                    "Un documento no puede sustituirse a sí mismo."
                )

            if (
                self.replaces_document.owner_type != self.owner_type
                or self.replaces_document.owner_id != self.owner_id
            ):
                errors["replaces_document"] = (
                    "El documento sustituido debe pertenecer al mismo "
                    "expediente."
                )

            if (
                self.replaces_document.document_group_id
                != self.document_group_id
            ):
                errors["document_group_id"] = (
                    "La nueva versión debe conservar el grupo documental."
                )

            if (
                self.version_number
                <= self.replaces_document.version_number
            ):
                errors["version_number"] = (
                    "La versión debe ser mayor a la versión sustituida."
                )

        if self.bypass_used and not self.bypass_reason.strip():
            errors["bypass_reason"] = (
                "Debe justificar el uso del bypass."
            )

        if (
            self.bypass_used
            and self.validation_status
            != DocumentValidationStatus.VALIDATED
        ):
            errors["validation_status"] = (
                "El bypass documental sólo puede utilizarse para validar."
            )

        if (
            self.contains_sensitive_data
            and self.access_level
            not in {
                DocumentAccessLevel.CONFIDENTIAL,
                DocumentAccessLevel.RESTRICTED,
            }
        ):
            errors["access_level"] = (
                "Un documento con datos sensibles debe ser confidencial "
                "o restringido."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.title = self.title.strip().upper()
        self.original_filename = (
            Path(self.original_filename).name.strip()
        )

        if self.description:
            self.description = self.description.strip()

        if self.content_type:
            self.content_type = self.content_type.strip().lower()

        if self.sha256_hash:
            self.sha256_hash = self.sha256_hash.strip().lower()

        self.uploaded_by_name_snapshot = (
            self.uploaded_by_name_snapshot.strip()
        )
        self.uploaded_by_email_snapshot = (
            self.uploaded_by_email_snapshot.strip().lower()
        )

        if self.validation_notes:
            self.validation_notes = self.validation_notes.strip()

        if self.rejection_reason:
            self.rejection_reason = self.rejection_reason.strip()

        if self.external_reference:
            self.external_reference = (
                self.external_reference.strip().upper()
            )

        if self.bypass_reason:
            self.bypass_reason = self.bypass_reason.strip()

        if self.notes:
            self.notes = self.notes.strip()

        super().save(*args, **kwargs)

    @property
    def owner_reference(self):
        return f"{self.owner_type}:{self.owner_id}"

    @property
    def is_validated(self):
        return (
            self.validation_status
            == DocumentValidationStatus.VALIDATED
        )

    @property
    def is_expired(self):
        return bool(
            self.expires_at
            and self.expires_at < timezone.localdate()
        )

    def __str__(self):
        return (
            f"{self.get_document_type_display()} · "
            f"{self.title} · V{self.version_number}"
        )


# =============================================================================
# HISTORIAL DE VALIDACIÓN DOCUMENTAL
# =============================================================================


class DocumentValidationEvent(InventoryBaseModel):
    """
    Evento append-only del expediente documental.

    Conserva cargas, validaciones, rechazos, sustituciones, descargas y bypass.
    """

    document = models.ForeignKey(
        AssetDocument,
        on_delete=models.PROTECT,
        related_name="validation_events",
    )
    event_type = models.CharField(
        "Tipo de evento",
        max_length=30,
        choices=DocumentValidationEventType.choices,
        db_index=True,
    )
    previous_status = models.CharField(
        "Estado anterior",
        max_length=30,
        choices=DocumentValidationStatus.choices,
        blank=True,
    )
    resulting_status = models.CharField(
        "Estado resultante",
        max_length=30,
        choices=DocumentValidationStatus.choices,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_document_events",
        verbose_name="Operador",
    )
    actor_name_snapshot = models.CharField(
        "Nombre del operador",
        max_length=300,
    )
    actor_email_snapshot = models.EmailField(
        "Correo del operador",
    )

    comment = models.TextField(
        "Comentario / justificación",
        blank=True,
    )
    bypass_used = models.BooleanField(
        "Se utilizó bypass",
        default=False,
        db_index=True,
    )
    bypass_reason = models.TextField(
        "Motivo del bypass",
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        "Dirección IP",
        null=True,
        blank=True,
    )
    user_agent = models.TextField(
        "Navegador / dispositivo",
        blank=True,
    )
    payload = models.JSONField(
        "Datos adicionales",
        default=dict,
        blank=True,
    )
    occurred_at = models.DateTimeField(
        "Fecha efectiva del evento",
        default=timezone.now,
        db_index=True,
    )

    class Meta:
        db_table = "inventory_document_validation_events"
        verbose_name = "Evento de documento"
        verbose_name_plural = "Eventos de documentos"
        ordering = ["occurred_at", "created_at"]
        indexes = [
            models.Index(
                fields=["document", "occurred_at"],
                name="idx_inv_document_event_date",
            ),
            models.Index(fields=["event_type", "occurred_at"]),
            models.Index(fields=["actor", "occurred_at"]),
            models.Index(fields=["bypass_used", "occurred_at"]),
        ]

    def clean(self):
        errors = {}

        if (
            self.previous_status
            and self.previous_status == self.resulting_status
            and self.event_type
            not in {
                DocumentValidationEventType.DOWNLOADED,
                DocumentValidationEventType.UPLOADED,
            }
        ):
            errors["resulting_status"] = (
                "El evento debe producir un cambio de estado."
            )

        if not self.actor_name_snapshot.strip():
            errors["actor_name_snapshot"] = (
                "Debe conservar el nombre del operador."
            )

        if not self.actor_email_snapshot.strip():
            errors["actor_email_snapshot"] = (
                "Debe conservar el correo del operador."
            )

        if self.bypass_used and not self.bypass_reason.strip():
            errors["bypass_reason"] = (
                "Debe justificar el uso del bypass."
            )

        if (
            self.event_type == DocumentValidationEventType.BYPASS
            and not self.bypass_used
        ):
            errors["bypass_used"] = (
                "Un evento BYPASS debe indicar el uso del bypass."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.actor_name_snapshot = (
            self.actor_name_snapshot.strip()
        )
        self.actor_email_snapshot = (
            self.actor_email_snapshot.strip().lower()
        )

        if self.comment:
            self.comment = self.comment.strip()

        if self.bypass_reason:
            self.bypass_reason = self.bypass_reason.strip()

        if self.user_agent:
            self.user_agent = self.user_agent.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.document.title} · "
            f"{self.get_event_type_display()}"
        )


# =============================================================================
# EVIDENCIA FOTOGRÁFICA
# =============================================================================


class AssetPhoto(InventoryBaseModel):
    """
    Evidencia fotográfica desacoplada.

    Una fotografía puede cargarse desde la solicitud de alta, auditoría física,
    resguardo, préstamo, devolución, reparación o baja, incluso antes de que
    exista un Asset oficial.
    """

    owner_type = models.CharField(
        "Tipo de expediente propietario",
        max_length=40,
        choices=InventoryDocumentOwnerType.choices,
        db_index=True,
    )
    owner_id = models.UUIDField(
        "UUID del expediente propietario",
        db_index=True,
    )

    photo_type = models.CharField(
        "Tipo de fotografía",
        max_length=40,
        choices=InventoryPhotoType.choices,
        default=InventoryPhotoType.FRONT,
        db_index=True,
    )
    image = models.ImageField(
        "Imagen",
        upload_to=inventory_photo_upload_path,
    )
    original_filename = models.CharField(
        "Nombre original",
        max_length=255,
    )
    content_type = models.CharField(
        "Tipo MIME",
        max_length=120,
        blank=True,
    )
    file_size = models.PositiveBigIntegerField(
        "Tamaño en bytes",
        null=True,
        blank=True,
    )
    sha256_hash = models.CharField(
        "Hash SHA-256",
        max_length=64,
        blank=True,
        db_index=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_photos_uploaded",
        verbose_name="Cargada por",
    )
    uploaded_by_name_snapshot = models.CharField(
        "Nombre de quien cargó",
        max_length=300,
    )
    uploaded_by_email_snapshot = models.EmailField(
        "Correo de quien cargó",
    )
    uploaded_at = models.DateTimeField(
        "Fecha de carga",
        default=timezone.now,
        db_index=True,
    )
    captured_at = models.DateTimeField(
        "Fecha de captura",
        null=True,
        blank=True,
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

    is_required_evidence = models.BooleanField(
        "Evidencia obligatoria",
        default=False,
        db_index=True,
    )
    is_validated = models.BooleanField(
        "Fotografía validada",
        default=False,
        db_index=True,
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_photos_validated",
        null=True,
        blank=True,
    )
    validated_at = models.DateTimeField(
        "Fecha de validación",
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        "Metadatos",
        default=dict,
        blank=True,
    )
    notes = models.TextField(
        "Notas internas",
        blank=True,
    )

    class Meta:
        db_table = "inventory_asset_photos"
        verbose_name = "Evidencia fotográfica"
        verbose_name_plural = "Evidencias fotográficas"
        ordering = ["-captured_at", "-uploaded_at"]
        indexes = [
            models.Index(
                fields=["owner_type", "owner_id"],
                name="idx_inv_photo_owner",
            ),
            models.Index(
                fields=["owner_type", "owner_id", "photo_type"],
                name="idx_inv_photo_owner_type",
            ),
            models.Index(fields=["uploaded_by", "uploaded_at"]),
            models.Index(fields=["captured_at"]),
            models.Index(
                fields=["is_required_evidence", "is_validated"],
                name="idx_inv_photo_required_valid",
            ),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def clean(self):
        errors = {}

        if not self.original_filename.strip():
            errors["original_filename"] = (
                "Debe conservar el nombre original de la imagen."
            )

        if not self.uploaded_by_name_snapshot.strip():
            errors["uploaded_by_name_snapshot"] = (
                "Debe conservar el nombre de quien cargó la imagen."
            )

        if not self.uploaded_by_email_snapshot.strip():
            errors["uploaded_by_email_snapshot"] = (
                "Debe conservar el correo de quien cargó la imagen."
            )

        if self.is_validated:
            if not self.validated_by_id:
                errors["validated_by"] = (
                    "Debe indicar quién validó la fotografía."
                )

            if not self.validated_at:
                errors["validated_at"] = (
                    "Debe registrar la fecha de validación."
                )

        if self.validated_at and self.validated_at < self.uploaded_at:
            errors["validated_at"] = (
                "La validación no puede ser anterior a la carga."
            )

        if (
            self.captured_at
            and self.captured_at > timezone.now()
        ):
            errors["captured_at"] = (
                "La fecha de captura no puede estar en el futuro."
            )

        if (
            self.latitude is None
            and self.longitude is not None
        ):
            errors["latitude"] = (
                "Debe proporcionar latitud y longitud juntas."
            )

        if (
            self.longitude is None
            and self.latitude is not None
        ):
            errors["longitude"] = (
                "Debe proporcionar latitud y longitud juntas."
            )

        if self.latitude is not None:
            if self.latitude < -90 or self.latitude > 90:
                errors["latitude"] = (
                    "La latitud debe encontrarse entre -90 y 90."
                )

        if self.longitude is not None:
            if self.longitude < -180 or self.longitude > 180:
                errors["longitude"] = (
                    "La longitud debe encontrarse entre -180 y 180."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.original_filename = (
            Path(self.original_filename).name.strip()
        )

        if self.content_type:
            self.content_type = self.content_type.strip().lower()

        if self.sha256_hash:
            self.sha256_hash = self.sha256_hash.strip().lower()

        self.uploaded_by_name_snapshot = (
            self.uploaded_by_name_snapshot.strip()
        )
        self.uploaded_by_email_snapshot = (
            self.uploaded_by_email_snapshot.strip().lower()
        )

        if self.caption:
            self.caption = self.caption.strip()

        if self.notes:
            self.notes = self.notes.strip()

        super().save(*args, **kwargs)

    @property
    def owner_reference(self):
        return f"{self.owner_type}:{self.owner_id}"

    def __str__(self):
        return (
            f"{self.get_owner_type_display()} · "
            f"{self.get_photo_type_display()}"
        )
        
