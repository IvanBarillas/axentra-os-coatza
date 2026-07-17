# apps/inventory/models/custody_models.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.inventory.models.catalog_models import (
    InventoryBaseModel,
    PhysicalCondition,
)


# =============================================================================
# CATÁLOGOS DEL FLUJO DE RESGUARDO
# =============================================================================


class CustodyStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    PENDING_AUTHORIZATION = (
        "PENDING_AUTHORIZATION",
        "Pendiente de autorización",
    )
    PENDING_ACCEPTANCE = (
        "PENDING_ACCEPTANCE",
        "Pendiente de aceptación y firma",
    )
    ACTIVE = "ACTIVE", "Resguardo activo"
    REJECTED = "REJECTED", "Rechazado"
    RETURN_PENDING = (
        "RETURN_PENDING",
        "Devolución en proceso",
    )
    RETURNED = "RETURNED", "Devuelto"
    CANCELLED = "CANCELLED", "Cancelado"


class CustodyAcceptanceMethod(models.TextChoices):
    HANDWRITTEN_SIGNATURE = (
        "HANDWRITTEN_SIGNATURE",
        "Firma autógrafa",
    )
    ELECTRONIC_ACCEPTANCE = (
        "ELECTRONIC_ACCEPTANCE",
        "Aceptación electrónica",
    )
    DIGITAL_SIGNATURE = (
        "DIGITAL_SIGNATURE",
        "Firma digital",
    )
    ADMINISTRATIVE_BYPASS = (
        "ADMINISTRATIVE_BYPASS",
        "Bypass administrativo",
    )


class CustodyEventType(models.TextChoices):
    CREATED = "CREATED", "Resguardo creado"
    SUBMITTED = "SUBMITTED", "Enviado a autorización"
    AUTHORIZED = "AUTHORIZED", "Autorizado"
    REJECTED = "REJECTED", "Rechazado"
    DELIVERED = "DELIVERED", "Bien entregado"
    ACCEPTED = "ACCEPTED", "Aceptado y firmado"
    ACTIVATED = "ACTIVATED", "Resguardo activado"
    RETURN_REQUESTED = (
        "RETURN_REQUESTED",
        "Devolución solicitada",
    )
    RETURNED = "RETURNED", "Bien devuelto"
    CANCELLED = "CANCELLED", "Resguardo cancelado"
    CORRECTED = "CORRECTED", "Corrección administrativa"
    BYPASS = "BYPASS", "Bypass administrativo"


# =============================================================================
# RESGUARDO OFICIAL
# =============================================================================


class CustodyAssignment(InventoryBaseModel):
    """
    Expediente de resguardo oficial de un activo.

    Un activo puede tener múltiples resguardos históricos, pero sólo un
    resguardo vigente o en proceso de formalización.

    Los cambios de estado deben realizarse mediante CustodyService. El modelo
    conserva el estado actual y CustodyAssignmentEvent conserva cada
    transición histórica.
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
    status = models.CharField(
        "Estado",
        max_length=40,
        choices=CustodyStatus.choices,
        default=CustodyStatus.DRAFT,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Resguardatario
    # -------------------------------------------------------------------------

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custody_assignments",
        verbose_name="Servidor público resguardatario",
    )
    assigned_to_name_snapshot = models.CharField(
        "Nombre del resguardatario",
        max_length=300,
    )
    assigned_to_email_snapshot = models.EmailField(
        "Correo del resguardatario",
    )
    assigned_to_position_snapshot = models.CharField(
        "Puesto del resguardatario",
        max_length=180,
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Ubicación y adscripción del resguardo
    # -------------------------------------------------------------------------

    dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_custodies",
        verbose_name="Dependencia",
    )
    area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_custodies",
        verbose_name="Área operativa",
        null=True,
        blank=True,
    )
    sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_custodies",
        verbose_name="Sede física",
        null=True,
        blank=True,
    )

    dependencia_id_snapshot = models.UUIDField(
        "UUID histórico de dependencia",
    )
    dependencia_name_snapshot = models.CharField(
        "Nombre histórico de dependencia",
        max_length=180,
    )
    dependencia_code_snapshot = models.CharField(
        "Código histórico de dependencia",
        max_length=20,
        blank=True,
    )

    area_id_snapshot = models.UUIDField(
        "UUID histórico de área",
        null=True,
        blank=True,
    )
    area_name_snapshot = models.CharField(
        "Nombre histórico de área",
        max_length=180,
        blank=True,
    )

    sede_id_snapshot = models.UUIDField(
        "UUID histórico de sede",
        null=True,
        blank=True,
    )
    sede_name_snapshot = models.CharField(
        "Nombre histórico de sede",
        max_length=180,
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Preparación, autorización y entrega
    # -------------------------------------------------------------------------

    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custodies_prepared",
        verbose_name="Elaborado por",
    )
    prepared_at = models.DateTimeField(
        "Fecha de elaboración",
        default=timezone.now,
    )

    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custodies_authorized",
        verbose_name="Autorizado por",
        null=True,
        blank=True,
    )
    authorized_at = models.DateTimeField(
        "Fecha de autorización",
        null=True,
        blank=True,
    )

    delivered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custodies_delivered",
        verbose_name="Entregado por",
        null=True,
        blank=True,
    )
    delivered_at = models.DateTimeField(
        "Fecha de entrega física",
        null=True,
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Aceptación del resguardatario
    # -------------------------------------------------------------------------

    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custodies_accepted",
        verbose_name="Aceptado por",
        null=True,
        blank=True,
    )
    accepted_at = models.DateTimeField(
        "Fecha de aceptación",
        null=True,
        blank=True,
    )
    acceptance_method = models.CharField(
        "Método de aceptación",
        max_length=40,
        choices=CustodyAcceptanceMethod.choices,
        blank=True,
    )
    acceptance_ip_address = models.GenericIPAddressField(
        "IP de aceptación",
        null=True,
        blank=True,
    )
    acceptance_user_agent = models.TextField(
        "Navegador de aceptación",
        blank=True,
    )
    digital_signature_hash = models.CharField(
        "Hash de firma o documento",
        max_length=255,
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Vigencia y condición de entrega
    # -------------------------------------------------------------------------

    assigned_at = models.DateTimeField(
        "Inicio efectivo del resguardo",
        null=True,
        blank=True,
    )
    expected_return_at = models.DateTimeField(
        "Fecha esperada de devolución",
        null=True,
        blank=True,
        help_text=(
            "Normalmente permanece vacío en resguardos permanentes."
        ),
    )
    delivery_condition = models.CharField(
        "Condición física al entregar",
        max_length=30,
        choices=PhysicalCondition.choices,
        default=PhysicalCondition.GOOD,
    )
    delivery_observations = models.TextField(
        "Observaciones de entrega",
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Rechazo
    # -------------------------------------------------------------------------

    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custodies_rejected",
        verbose_name="Rechazado por",
        null=True,
        blank=True,
    )
    rejected_at = models.DateTimeField(
        "Fecha de rechazo",
        null=True,
        blank=True,
    )
    rejection_reason = models.TextField(
        "Motivo del rechazo",
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Devolución
    # -------------------------------------------------------------------------

    return_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custody_returns_requested",
        verbose_name="Devolución solicitada por",
        null=True,
        blank=True,
    )
    return_requested_at = models.DateTimeField(
        "Fecha de solicitud de devolución",
        null=True,
        blank=True,
    )

    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custodies_returned",
        verbose_name="Devuelto por",
        null=True,
        blank=True,
    )
    received_return_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custody_returns_received",
        verbose_name="Devolución recibida por",
        null=True,
        blank=True,
    )
    returned_at = models.DateTimeField(
        "Fecha efectiva de devolución",
        null=True,
        blank=True,
    )
    return_condition = models.CharField(
        "Condición física al devolver",
        max_length=30,
        choices=PhysicalCondition.choices,
        blank=True,
    )
    return_observations = models.TextField(
        "Observaciones de devolución",
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Cancelación y bypass
    # -------------------------------------------------------------------------

    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custodies_cancelled",
        verbose_name="Cancelado por",
        null=True,
        blank=True,
    )
    cancelled_at = models.DateTimeField(
        "Fecha de cancelación",
        null=True,
        blank=True,
    )
    cancellation_reason = models.TextField(
        "Motivo de cancelación",
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

    notes = models.TextField(
        "Notas internas",
        blank=True,
    )

    class Meta:
        db_table = "inventory_custody_assignments"
        verbose_name = "Resguardo"
        verbose_name_plural = "Resguardos"
        ordering = ["-prepared_at"]
        indexes = [
            models.Index(fields=["asset", "status"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["dependencia", "status"]),
            models.Index(fields=["area", "status"]),
            models.Index(fields=["sede", "status"]),
            models.Index(fields=["prepared_by", "prepared_at"]),
            models.Index(fields=["authorized_by", "authorized_at"]),
            models.Index(fields=["accepted_by", "accepted_at"]),
            models.Index(fields=["assigned_at"]),
            models.Index(fields=["returned_at"]),
            models.Index(fields=["bypass_used"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["asset"],
                condition=(
                    Q(
                        status__in=[
                            CustodyStatus.PENDING_AUTHORIZATION,
                            CustodyStatus.PENDING_ACCEPTANCE,
                            CustodyStatus.ACTIVE,
                            CustodyStatus.RETURN_PENDING,
                        ]
                    )
                    & Q(is_deleted=False)
                ),
                name="uq_inv_open_custody_per_asset",
            ),
        ]

    def clean(self):
        errors = {}

        # ---------------------------------------------------------------------
        # Coherencia organizacional
        # ---------------------------------------------------------------------

        if self.area_id:
            if self.area.dependencia_id != self.dependencia_id:
                errors["area"] = (
                    "El área no pertenece a la dependencia seleccionada."
                )

            if (
                self.sede_id
                and self.area.sede_fisica_id != self.sede_id
            ):
                errors["sede"] = (
                    "La sede no coincide con la sede física del área."
                )

        if self.dependencia_id_snapshot != self.dependencia_id:
            errors["dependencia_id_snapshot"] = (
                "El UUID histórico debe corresponder a la dependencia "
                "seleccionada."
            )

        if self.area_id:
            if self.area_id_snapshot != self.area_id:
                errors["area_id_snapshot"] = (
                    "El UUID histórico debe corresponder al área."
                )
        elif self.area_id_snapshot:
            errors["area_id_snapshot"] = (
                "No debe existir un UUID histórico de área sin área."
            )

        if self.sede_id:
            if self.sede_id_snapshot != self.sede_id:
                errors["sede_id_snapshot"] = (
                    "El UUID histórico debe corresponder a la sede."
                )
        elif self.sede_id_snapshot:
            errors["sede_id_snapshot"] = (
                "No debe existir un UUID histórico de sede sin sede."
            )

        # ---------------------------------------------------------------------
        # Snapshots obligatorios
        # ---------------------------------------------------------------------

        if not self.assigned_to_name_snapshot.strip():
            errors["assigned_to_name_snapshot"] = (
                "Debe conservar el nombre del resguardatario."
            )

        if not self.assigned_to_email_snapshot.strip():
            errors["assigned_to_email_snapshot"] = (
                "Debe conservar el correo del resguardatario."
            )

        if not self.dependencia_name_snapshot.strip():
            errors["dependencia_name_snapshot"] = (
                "Debe conservar el nombre de la dependencia."
            )

        # ---------------------------------------------------------------------
        # Autorización
        # ---------------------------------------------------------------------

        authorization_required_statuses = {
            CustodyStatus.PENDING_ACCEPTANCE,
            CustodyStatus.ACTIVE,
            CustodyStatus.RETURN_PENDING,
            CustodyStatus.RETURNED,
        }

        if self.status in authorization_required_statuses:
            if not self.authorized_by_id:
                errors["authorized_by"] = (
                    "El resguardo debe estar autorizado."
                )

            if not self.authorized_at:
                errors["authorized_at"] = (
                    "Debe registrar la fecha de autorización."
                )

        if self.authorized_at and not self.authorized_by_id:
            errors["authorized_by"] = (
                "Debe indicar quién autorizó el resguardo."
            )

        # ---------------------------------------------------------------------
        # Entrega y aceptación
        # ---------------------------------------------------------------------

        active_statuses = {
            CustodyStatus.ACTIVE,
            CustodyStatus.RETURN_PENDING,
            CustodyStatus.RETURNED,
        }

        if self.status in active_statuses:
            if not self.delivered_by_id:
                errors["delivered_by"] = (
                    "Debe indicar quién entregó físicamente el bien."
                )

            if not self.delivered_at:
                errors["delivered_at"] = (
                    "Debe registrar la fecha de entrega física."
                )

            if not self.accepted_by_id:
                errors["accepted_by"] = (
                    "Debe indicar quién aceptó el resguardo."
                )

            if not self.accepted_at:
                errors["accepted_at"] = (
                    "Debe registrar la fecha de aceptación."
                )

            if not self.acceptance_method:
                errors["acceptance_method"] = (
                    "Debe indicar el método de aceptación."
                )

            if not self.assigned_at:
                errors["assigned_at"] = (
                    "Debe registrar el inicio efectivo del resguardo."
                )

        if (
            self.accepted_by_id
            and self.accepted_by_id != self.assigned_to_id
            and not self.bypass_used
        ):
            errors["accepted_by"] = (
                "El resguardo debe ser aceptado por el resguardatario. "
                "Una aceptación distinta requiere bypass."
            )

        if (
            self.acceptance_method
            == CustodyAcceptanceMethod.DIGITAL_SIGNATURE
            and not self.digital_signature_hash.strip()
        ):
            errors["digital_signature_hash"] = (
                "La firma digital requiere conservar su hash."
            )

        if (
            self.acceptance_method
            == CustodyAcceptanceMethod.ADMINISTRATIVE_BYPASS
            and not self.bypass_used
        ):
            errors["bypass_used"] = (
                "La aceptación administrativa requiere marcar bypass."
            )

        # ---------------------------------------------------------------------
        # Rechazo
        # ---------------------------------------------------------------------

        if self.status == CustodyStatus.REJECTED:
            if not self.rejected_by_id:
                errors["rejected_by"] = (
                    "Debe indicar quién rechazó el resguardo."
                )

            if not self.rejected_at:
                errors["rejected_at"] = (
                    "Debe registrar la fecha del rechazo."
                )

            if not self.rejection_reason.strip():
                errors["rejection_reason"] = (
                    "Debe indicar el motivo del rechazo."
                )

        # ---------------------------------------------------------------------
        # Devolución
        # ---------------------------------------------------------------------

        if self.status == CustodyStatus.RETURN_PENDING:
            if not self.return_requested_by_id:
                errors["return_requested_by"] = (
                    "Debe indicar quién solicitó la devolución."
                )

            if not self.return_requested_at:
                errors["return_requested_at"] = (
                    "Debe registrar la fecha de solicitud de devolución."
                )

        if self.status == CustodyStatus.RETURNED:
            if not self.returned_by_id:
                errors["returned_by"] = (
                    "Debe indicar quién devolvió el bien."
                )

            if not self.received_return_by_id:
                errors["received_return_by"] = (
                    "Debe indicar quién recibió la devolución."
                )

            if not self.returned_at:
                errors["returned_at"] = (
                    "Debe registrar la fecha efectiva de devolución."
                )

            if not self.return_condition:
                errors["return_condition"] = (
                    "Debe indicar la condición física de devolución."
                )

        if (
            self.status == CustodyStatus.ACTIVE
            and self.returned_at
        ):
            errors["status"] = (
                "Un resguardo activo no puede tener fecha de devolución."
            )

        # ---------------------------------------------------------------------
        # Cancelación
        # ---------------------------------------------------------------------

        if self.status == CustodyStatus.CANCELLED:
            if not self.cancelled_by_id:
                errors["cancelled_by"] = (
                    "Debe indicar quién canceló el resguardo."
                )

            if not self.cancelled_at:
                errors["cancelled_at"] = (
                    "Debe registrar la fecha de cancelación."
                )

            if not self.cancellation_reason.strip():
                errors["cancellation_reason"] = (
                    "Debe indicar el motivo de cancelación."
                )

        # ---------------------------------------------------------------------
        # Bypass
        # ---------------------------------------------------------------------

        if self.bypass_used and not self.bypass_reason.strip():
            errors["bypass_reason"] = (
                "Debe justificar el uso del bypass."
            )

        if not self.bypass_used and self.bypass_reason.strip():
            errors["bypass_reason"] = (
                "No debe registrar un motivo si no utilizó bypass."
            )

        # ---------------------------------------------------------------------
        # Orden cronológico
        # ---------------------------------------------------------------------

        chronology = [
            ("authorized_at", self.authorized_at, self.prepared_at),
            ("delivered_at", self.delivered_at, self.authorized_at),
            ("accepted_at", self.accepted_at, self.delivered_at),
            ("assigned_at", self.assigned_at, self.accepted_at),
            (
                "return_requested_at",
                self.return_requested_at,
                self.assigned_at,
            ),
            ("returned_at", self.returned_at, self.assigned_at),
        ]

        for field_name, current_date, previous_date in chronology:
            if (
                current_date
                and previous_date
                and current_date < previous_date
            ):
                errors[field_name] = (
                    "La fecha no puede ser anterior a la etapa previa."
                )

        if (
            self.expected_return_at
            and self.assigned_at
            and self.expected_return_at < self.assigned_at
        ):
            errors["expected_return_at"] = (
                "La devolución esperada no puede ser anterior al inicio "
                "del resguardo."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.folio = self.folio.strip().upper()

        self.assigned_to_name_snapshot = (
            self.assigned_to_name_snapshot.strip()
        )
        self.assigned_to_email_snapshot = (
            self.assigned_to_email_snapshot.strip().lower()
        )

        if self.assigned_to_position_snapshot:
            self.assigned_to_position_snapshot = (
                self.assigned_to_position_snapshot.strip().upper()
            )

        self.dependencia_name_snapshot = (
            self.dependencia_name_snapshot.strip().upper()
        )

        if self.dependencia_code_snapshot:
            self.dependencia_code_snapshot = (
                self.dependencia_code_snapshot.strip().upper()
            )

        if self.area_name_snapshot:
            self.area_name_snapshot = (
                self.area_name_snapshot.strip().upper()
            )

        if self.sede_name_snapshot:
            self.sede_name_snapshot = (
                self.sede_name_snapshot.strip().upper()
            )

        if self.digital_signature_hash:
            self.digital_signature_hash = (
                self.digital_signature_hash.strip()
            )

        text_fields = [
            "delivery_observations",
            "rejection_reason",
            "return_observations",
            "cancellation_reason",
            "bypass_reason",
            "notes",
        ]

        for field_name in text_fields:
            value = getattr(self, field_name, "")

            if value:
                setattr(self, field_name, value.strip())

        super().save(*args, **kwargs)

    @property
    def is_open(self):
        return self.status in {
            CustodyStatus.PENDING_AUTHORIZATION,
            CustodyStatus.PENDING_ACCEPTANCE,
            CustodyStatus.ACTIVE,
            CustodyStatus.RETURN_PENDING,
        }

    @property
    def is_current(self):
        return (
            self.status == CustodyStatus.ACTIVE
            and self.is_active
            and not self.is_deleted
        )

    def __str__(self):
        return (
            f"{self.folio} · "
            f"{self.asset.display_inventory_number} → "
            f"{self.assigned_to_name_snapshot}"
        )


# =============================================================================
# HISTORIAL INMUTABLE DE EVENTOS DE RESGUARDO
# =============================================================================


class CustodyAssignmentEvent(InventoryBaseModel):
    """
    Evento append-only de un resguardo.

    Conserva cada transición aunque cambien posteriormente el usuario,
    dependencia, área o sede. No debe editarse ni darse de baja desde
    interfaces ordinarias.
    """

    custody_assignment = models.ForeignKey(
        CustodyAssignment,
        on_delete=models.PROTECT,
        related_name="events",
    )
    event_type = models.CharField(
        "Tipo de evento",
        max_length=40,
        choices=CustodyEventType.choices,
        db_index=True,
    )
    previous_status = models.CharField(
        "Estado anterior",
        max_length=40,
        choices=CustodyStatus.choices,
        blank=True,
    )
    resulting_status = models.CharField(
        "Estado resultante",
        max_length=40,
        choices=CustodyStatus.choices,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_custody_events",
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
        "Snapshot adicional",
        default=dict,
        blank=True,
    )
    occurred_at = models.DateTimeField(
        "Fecha efectiva del evento",
        default=timezone.now,
        db_index=True,
    )

    class Meta:
        db_table = "inventory_custody_assignment_events"
        verbose_name = "Evento de resguardo"
        verbose_name_plural = "Eventos de resguardo"
        ordering = ["occurred_at", "created_at"]
        indexes = [
            models.Index(
                fields=["custody_assignment", "occurred_at"],
                name="idx_inv_custody_event_date",
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
            and self.event_type != CustodyEventType.CORRECTED
        ):
            errors["resulting_status"] = (
                "El evento debe producir una transición de estado."
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
            self.event_type == CustodyEventType.BYPASS
            and not self.bypass_used
        ):
            errors["bypass_used"] = (
                "Un evento BYPASS debe indicar que utilizó bypass."
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
            f"{self.custody_assignment.folio} · "
            f"{self.get_event_type_display()}"
        )
        
