# apps/inventory/models/movement_models.py

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.inventory.models.catalog_models import (
    DisposalReason,
    InventoryBaseModel,
    MovementType,
    PhysicalCondition,
)


# =============================================================================
# MOVIMIENTOS PATRIMONIALES
# =============================================================================


class MovementReferenceType(models.TextChoices):
    INTAKE_REQUEST = "INTAKE_REQUEST", "Solicitud de alta"
    CUSTODY_ASSIGNMENT = "CUSTODY_ASSIGNMENT", "Resguardo"
    LOAN = "LOAN", "Préstamo"
    DISPOSAL_REQUEST = "DISPOSAL_REQUEST", "Expediente de baja"
    SERVICE_ORDER = "SERVICE_ORDER", "Orden de servicio"
    PHYSICAL_AUDIT = "PHYSICAL_AUDIT", "Auditoría física"
    ADMINISTRATIVE_ORDER = (
        "ADMINISTRATIVE_ORDER",
        "Oficio administrativo",
    )
    OTHER = "OTHER", "Otro expediente"


class AssetMovementRequestStatus(models.TextChoices):
    PENDING_ORIGIN_APPROVAL = "PENDING_ORIGIN_APPROVAL", "Pendiente de autorización de origen"
    PENDING_DESTINATION_ACCEPTANCE = "PENDING_DESTINATION_ACCEPTANCE", "Pendiente de aceptación de destino"
    PENDING_PATRIMONY_EXECUTION = "PENDING_PATRIMONY_EXECUTION", "Pendiente de ejecución por Patrimonio"
    REJECTED = "REJECTED", "Rechazada"
    EXECUTED = "EXECUTED", "Ejecutada"
    CANCELLED = "CANCELLED", "Cancelada"


class AssetMovementRequest(InventoryBaseModel):
    """Expediente previo; el movimiento append-only nace sólo al ejecutarlo."""

    folio = models.CharField("Folio de solicitud", max_length=80, unique=True)
    asset = models.ForeignKey("inventory.Asset", on_delete=models.PROTECT, related_name="movement_requests")
    movement_type = models.CharField("Tipo de movimiento", max_length=40, choices=MovementType.choices)
    status = models.CharField("Estado", max_length=40, choices=AssetMovementRequestStatus.choices, default=AssetMovementRequestStatus.PENDING_ORIGIN_APPROVAL, db_index=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inventory_movement_requests")
    requested_at = models.DateTimeField("Fecha de solicitud", default=timezone.now)
    reason = models.TextField("Justificación")
    occurred_at = models.DateTimeField("Fecha efectiva propuesta", null=True, blank=True)

    origin_dependencia = models.ForeignKey("security.Dependencia", on_delete=models.PROTECT, related_name="inventory_movement_requests_origin", null=True, blank=True)
    origin_area = models.ForeignKey("security.AreaOperativa", on_delete=models.PROTECT, related_name="inventory_movement_requests_origin", null=True, blank=True)
    origin_sede = models.ForeignKey("security.Sede", on_delete=models.PROTECT, related_name="inventory_movement_requests_origin", null=True, blank=True)
    origin_custodian = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inventory_movement_requests_origin", null=True, blank=True)
    destination_dependencia = models.ForeignKey("security.Dependencia", on_delete=models.PROTECT, related_name="inventory_movement_requests_destination", null=True, blank=True)
    destination_area = models.ForeignKey("security.AreaOperativa", on_delete=models.PROTECT, related_name="inventory_movement_requests_destination", null=True, blank=True)
    destination_sede = models.ForeignKey("security.Sede", on_delete=models.PROTECT, related_name="inventory_movement_requests_destination", null=True, blank=True)
    destination_custodian = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inventory_movement_requests_destination", null=True, blank=True)

    origin_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inventory_movement_origin_approvals", null=True, blank=True)
    origin_approved_at = models.DateTimeField(null=True, blank=True)
    destination_accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inventory_movement_destination_acceptances", null=True, blank=True)
    destination_accepted_at = models.DateTimeField(null=True, blank=True)
    executed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inventory_movement_executions", null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    resulting_movement = models.OneToOneField("inventory.InventoryMovement", on_delete=models.PROTECT, related_name="source_request", null=True, blank=True)
    rejection_reason = models.TextField("Motivo de rechazo", blank=True)
    bypass_used = models.BooleanField(default=False)
    bypass_reason = models.TextField(blank=True)

    class Meta:
        db_table = "inventory_asset_movement_requests"
        ordering = ["-requested_at"]
        indexes = [models.Index(fields=["status", "requested_at"], name="inv_mov_req_status_idx"), models.Index(fields=["asset", "requested_at"], name="inv_mov_req_asset_idx")]

    def __str__(self):
        return f"{self.folio} · {self.asset.display_inventory_number}"


class InventoryMovement(InventoryBaseModel):
    """
    Evento patrimonial append-only.

    Conserva altas, asignaciones, transferencias, préstamos, devoluciones,
    cambios de ubicación, salidas a servicio, bajas y correcciones.

    No debe editarse ni eliminarse desde interfaces ordinarias. Si un movimiento
    contiene un error se debe crear un movimiento CORRECTION relacionado con el
    evento original.

    Los campos from_* y to_* conservan tanto FK al Core como snapshots
    históricos.
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
        db_index=True,
    )
    correlation_id = models.UUIDField(
        "Identificador de correlación",
        default=uuid.uuid4,
        db_index=True,
        help_text=(
            "Agrupa movimientos y eventos de una misma operación "
            "transaccional."
        ),
    )

    # -------------------------------------------------------------------------
    # Origen
    # -------------------------------------------------------------------------

    from_dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_movements_from",
        null=True,
        blank=True,
    )
    from_dependencia_id_snapshot = models.UUIDField(
        "UUID de dependencia origen",
        null=True,
        blank=True,
    )
    from_dependencia_name_snapshot = models.CharField(
        "Nombre de dependencia origen",
        max_length=180,
        blank=True,
    )
    from_dependencia_code_snapshot = models.CharField(
        "Código de dependencia origen",
        max_length=20,
        blank=True,
    )

    from_area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_movements_from",
        null=True,
        blank=True,
    )
    from_area_id_snapshot = models.UUIDField(
        "UUID de área origen",
        null=True,
        blank=True,
    )
    from_area_name_snapshot = models.CharField(
        "Nombre de área origen",
        max_length=180,
        blank=True,
    )

    from_sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_movements_from",
        null=True,
        blank=True,
    )
    from_sede_id_snapshot = models.UUIDField(
        "UUID de sede origen",
        null=True,
        blank=True,
    )
    from_sede_name_snapshot = models.CharField(
        "Nombre de sede origen",
        max_length=180,
        blank=True,
    )

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_movements_from",
        null=True,
        blank=True,
    )
    from_user_id_snapshot = models.UUIDField(
        "UUID de usuario origen",
        null=True,
        blank=True,
    )
    from_user_name_snapshot = models.CharField(
        "Nombre de usuario origen",
        max_length=300,
        blank=True,
    )
    from_user_email_snapshot = models.EmailField(
        "Correo de usuario origen",
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Destino
    # -------------------------------------------------------------------------

    to_dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_movements_to",
        null=True,
        blank=True,
    )
    to_dependencia_id_snapshot = models.UUIDField(
        "UUID de dependencia destino",
        null=True,
        blank=True,
    )
    to_dependencia_name_snapshot = models.CharField(
        "Nombre de dependencia destino",
        max_length=180,
        blank=True,
    )
    to_dependencia_code_snapshot = models.CharField(
        "Código de dependencia destino",
        max_length=20,
        blank=True,
    )

    to_area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_movements_to",
        null=True,
        blank=True,
    )
    to_area_id_snapshot = models.UUIDField(
        "UUID de área destino",
        null=True,
        blank=True,
    )
    to_area_name_snapshot = models.CharField(
        "Nombre de área destino",
        max_length=180,
        blank=True,
    )

    to_sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_movements_to",
        null=True,
        blank=True,
    )
    to_sede_id_snapshot = models.UUIDField(
        "UUID de sede destino",
        null=True,
        blank=True,
    )
    to_sede_name_snapshot = models.CharField(
        "Nombre de sede destino",
        max_length=180,
        blank=True,
    )

    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_movements_to",
        null=True,
        blank=True,
    )
    to_user_id_snapshot = models.UUIDField(
        "UUID de usuario destino",
        null=True,
        blank=True,
    )
    to_user_name_snapshot = models.CharField(
        "Nombre de usuario destino",
        max_length=300,
        blank=True,
    )
    to_user_email_snapshot = models.EmailField(
        "Correo de usuario destino",
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Condición física
    # -------------------------------------------------------------------------

    condition_before = models.CharField(
        "Condición anterior",
        max_length=30,
        choices=PhysicalCondition.choices,
        blank=True,
    )
    condition_after = models.CharField(
        "Condición posterior",
        max_length=30,
        choices=PhysicalCondition.choices,
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Operador y fechas
    # -------------------------------------------------------------------------

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_movements_performed",
    )
    performed_by_name_snapshot = models.CharField(
        "Nombre del operador",
        max_length=300,
    )
    performed_by_email_snapshot = models.EmailField(
        "Correo del operador",
    )
    occurred_at = models.DateTimeField(
        "Fecha efectiva del movimiento",
        default=timezone.now,
        db_index=True,
    )
    recorded_at = models.DateTimeField(
        "Fecha de registro",
        default=timezone.now,
        db_index=True,
    )

    reason = models.TextField(
        "Justificación",
    )
    reference_folio = models.CharField(
        "Folio de referencia",
        max_length=120,
        blank=True,
    )
    reference_type = models.CharField(
        "Tipo de expediente relacionado",
        max_length=40,
        choices=MovementReferenceType.choices,
        blank=True,
    )
    reference_id = models.UUIDField(
        "UUID de expediente relacionado",
        null=True,
        blank=True,
    )

    corrects_movement = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="correction_movements",
        null=True,
        blank=True,
        verbose_name="Movimiento corregido",
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
    payload = models.JSONField(
        "Snapshot adicional",
        default=dict,
        blank=True,
        help_text="No utilizar como fuente primaria de reglas.",
    )

    class Meta:
        db_table = "inventory_asset_movements"
        verbose_name = "Movimiento patrimonial"
        verbose_name_plural = "Movimientos patrimoniales"
        ordering = ["-occurred_at", "-recorded_at"]
        indexes = [
            models.Index(fields=["asset", "occurred_at"]),
            models.Index(fields=["movement_type", "occurred_at"]),
            models.Index(fields=["correlation_id"]),
            models.Index(fields=["reference_type", "reference_id"]),
            models.Index(fields=["reference_folio"]),
            models.Index(fields=["from_dependencia", "occurred_at"]),
            models.Index(fields=["to_dependencia", "occurred_at"]),
            models.Index(fields=["from_sede", "occurred_at"]),
            models.Index(fields=["to_sede", "occurred_at"]),
            models.Index(fields=["from_user", "occurred_at"]),
            models.Index(fields=["to_user", "occurred_at"]),
            models.Index(fields=["performed_by", "occurred_at"]),
            models.Index(fields=["bypass_used", "occurred_at"]),
        ]

    def clean(self):
        errors = {}

        if not self.reason.strip():
            errors["reason"] = (
                "La justificación del movimiento es obligatoria."
            )

        if self.reference_type and not self.reference_id:
            errors["reference_id"] = (
                "Debe indicar el UUID del expediente relacionado."
            )

        if self.reference_id and not self.reference_type:
            errors["reference_type"] = (
                "Debe indicar el tipo de expediente relacionado."
            )

        if (
            self.movement_type
            in {
                MovementType.ASSIGNMENT,
                MovementType.REASSIGNMENT,
                MovementType.CUSTODY_CHANGE,
                MovementType.LOAN,
            }
            and not self.to_user_id
            and not (
                self.movement_type == MovementType.LOAN
                and (
                    self.payload.get("external_borrower")
                    or self.to_area_id
                )
            )
        ):
            errors["to_user"] = (
                "Este movimiento requiere un usuario destino."
            )

        if (
            self.movement_type == MovementType.RETURN
            and not self.from_user_id
            and not (
                self.payload.get("external_borrower")
                or self.from_area_id
            )
        ):
            errors["from_user"] = (
                "Una devolución requiere un usuario origen."
            )

        destination_required = {
            MovementType.ASSIGNMENT,
            MovementType.REASSIGNMENT,
            MovementType.TRANSFER,
            MovementType.LOCATION_CHANGE,
            MovementType.LOAN,
            MovementType.RETURN,
        }

        if self.movement_type in destination_required:
            has_destination = any(
                [
                    self.to_dependencia_id,
                    self.to_area_id,
                    self.to_sede_id,
                    self.to_user_id,
                ]
            )

            if not has_destination and not self.payload.get(
                "external_destination"
            ):
                errors["to_dependencia"] = (
                    "Este movimiento requiere algún destino."
                )

        if self.to_area_id:
            if (
                self.to_dependencia_id
                and self.to_area.dependencia_id
                != self.to_dependencia_id
            ):
                errors["to_area"] = (
                    "El área destino no pertenece a la dependencia destino."
                )

            if (
                self.to_sede_id
                and self.to_area.sede_fisica_id != self.to_sede_id
            ):
                errors["to_sede"] = (
                    "La sede destino no coincide con la sede del área."
                )

        if self.from_area_id:
            if (
                self.from_dependencia_id
                and self.from_area.dependencia_id
                != self.from_dependencia_id
            ):
                errors["from_area"] = (
                    "El área origen no pertenece a la dependencia origen."
                )

            if (
                self.from_sede_id
                and self.from_area.sede_fisica_id
                != self.from_sede_id
            ):
                errors["from_sede"] = (
                    "La sede origen no coincide con la sede del área."
                )

        snapshot_pairs = [
            (
                "from_dependencia_id_snapshot",
                self.from_dependencia_id_snapshot,
                self.from_dependencia_id,
            ),
            (
                "from_area_id_snapshot",
                self.from_area_id_snapshot,
                self.from_area_id,
            ),
            (
                "from_sede_id_snapshot",
                self.from_sede_id_snapshot,
                self.from_sede_id,
            ),
            (
                "from_user_id_snapshot",
                self.from_user_id_snapshot,
                self.from_user_id,
            ),
            (
                "to_dependencia_id_snapshot",
                self.to_dependencia_id_snapshot,
                self.to_dependencia_id,
            ),
            (
                "to_area_id_snapshot",
                self.to_area_id_snapshot,
                self.to_area_id,
            ),
            (
                "to_sede_id_snapshot",
                self.to_sede_id_snapshot,
                self.to_sede_id,
            ),
            (
                "to_user_id_snapshot",
                self.to_user_id_snapshot,
                self.to_user_id,
            ),
        ]

        for field_name, snapshot_id, current_id in snapshot_pairs:
            if current_id and snapshot_id != current_id:
                errors[field_name] = (
                    "El UUID histórico debe coincidir con la referencia."
                )

            if not current_id and snapshot_id:
                errors[field_name] = (
                    "No debe existir UUID histórico sin referencia."
                )

        if (
            self.movement_type == MovementType.CORRECTION
            and not self.corrects_movement_id
        ):
            errors["corrects_movement"] = (
                "Una corrección debe indicar el movimiento corregido."
            )

        if (
            self.corrects_movement_id
            and self.corrects_movement.asset_id != self.asset_id
        ):
            errors["corrects_movement"] = (
                "Sólo puede corregir movimientos del mismo activo."
            )

        if (
            self.corrects_movement_id
            and self.corrects_movement_id == self.id
        ):
            errors["corrects_movement"] = (
                "Un movimiento no puede corregirse a sí mismo."
            )

        if self.occurred_at > self.recorded_at:
            errors["occurred_at"] = (
                "La fecha efectiva no puede ser posterior al registro."
            )

        if self.bypass_used and not self.bypass_reason.strip():
            errors["bypass_reason"] = (
                "Debe justificar el uso del bypass."
            )

        if not self.performed_by_name_snapshot.strip():
            errors["performed_by_name_snapshot"] = (
                "Debe conservar el nombre del operador."
            )

        if not self.performed_by_email_snapshot.strip():
            errors["performed_by_email_snapshot"] = (
                "Debe conservar el correo del operador."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.reference_folio:
            self.reference_folio = (
                self.reference_folio.strip().upper()
            )

        self.reason = self.reason.strip()
        self.performed_by_name_snapshot = (
            self.performed_by_name_snapshot.strip()
        )
        self.performed_by_email_snapshot = (
            self.performed_by_email_snapshot.strip().lower()
        )

        uppercase_fields = [
            "from_dependencia_name_snapshot",
            "from_dependencia_code_snapshot",
            "from_area_name_snapshot",
            "from_sede_name_snapshot",
            "to_dependencia_name_snapshot",
            "to_dependencia_code_snapshot",
            "to_area_name_snapshot",
            "to_sede_name_snapshot",
        ]

        for field_name in uppercase_fields:
            value = getattr(self, field_name, "")

            if value:
                setattr(
                    self,
                    field_name,
                    value.strip().upper(),
                )

        user_name_fields = [
            "from_user_name_snapshot",
            "to_user_name_snapshot",
        ]

        for field_name in user_name_fields:
            value = getattr(self, field_name, "")

            if value:
                setattr(self, field_name, value.strip())

        email_fields = [
            "from_user_email_snapshot",
            "to_user_email_snapshot",
        ]

        for field_name in email_fields:
            value = getattr(self, field_name, "")

            if value:
                setattr(
                    self,
                    field_name,
                    value.strip().lower(),
                )

        if self.bypass_reason:
            self.bypass_reason = self.bypass_reason.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.asset.display_inventory_number} · "
            f"{self.get_movement_type_display()} · "
            f"{self.occurred_at:%Y-%m-%d %H:%M}"
        )


# =============================================================================
# PRÉSTAMOS TEMPORALES
# =============================================================================


class AssetLoanStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    REQUESTED = "REQUESTED", "Solicitado"
    DEPARTMENT_APPROVED = (
        "DEPARTMENT_APPROVED",
        "Aceptado por la dependencia",
    )
    AUTHORIZED = "AUTHORIZED", "Autorizado"
    REJECTED = "REJECTED", "Rechazado"
    DELIVERED = "DELIVERED", "Entregado"
    OVERDUE = "OVERDUE", "Vencido"
    RETURN_PENDING = (
        "RETURN_PENDING",
        "Devolución en proceso",
    )
    RETURNED = "RETURNED", "Devuelto"
    CANCELLED = "CANCELLED", "Cancelado"


class AssetLoan(InventoryBaseModel):
    """
    Expediente de préstamo temporal.

    El préstamo no cambia la adscripción patrimonial permanente ni sustituye
    el resguardo oficial. Sólo modifica temporalmente la custodia y ubicación
    operativa del bien.
    """

    folio = models.CharField(
        "Folio de préstamo",
        max_length=80,
        unique=True,
    )
    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="loans",
    )
    status = models.CharField(
        "Estado",
        max_length=40,
        choices=AssetLoanStatus.choices,
        default=AssetLoanStatus.DRAFT,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Solicitante y receptor
    # -------------------------------------------------------------------------

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_loans_requested",
        verbose_name="Solicitado por",
    )
    requested_at = models.DateTimeField(
        "Fecha de solicitud",
        default=timezone.now,
    )

    borrower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_loans_received",
        verbose_name="Receptor interno",
        null=True,
        blank=True,
    )
    borrower_id_snapshot = models.UUIDField(
        "UUID histórico del receptor",
        null=True,
        blank=True,
    )
    borrower_name_snapshot = models.CharField(
        "Nombre del receptor",
        max_length=300,
        blank=True,
    )
    borrower_email_snapshot = models.EmailField(
        "Correo del receptor",
        blank=True,
    )
    borrower_position_snapshot = models.CharField(
        "Puesto del receptor",
        max_length=180,
        blank=True,
    )

    external_borrower = models.BooleanField(
        "Receptor externo",
        default=False,
    )
    external_organization = models.CharField(
        "Institución externa",
        max_length=255,
        blank=True,
    )
    external_identification = models.CharField(
        "Identificación del receptor externo",
        max_length=120,
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Ubicación de origen y destino
    # -------------------------------------------------------------------------

    origin_dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_loans_origin",
    )
    origin_area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_loans_origin",
        null=True,
        blank=True,
    )
    origin_sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_loans_origin",
        null=True,
        blank=True,
    )

    destination_dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_loans_destination",
        null=True,
        blank=True,
    )
    destination_area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_loans_destination",
        null=True,
        blank=True,
    )
    destination_sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_loans_destination",
        null=True,
        blank=True,
    )
    external_destination = models.CharField(
        "Ubicación externa",
        max_length=255,
        blank=True,
    )

    origin_snapshot = models.JSONField(
        "Snapshot de origen",
        default=dict,
    )
    destination_snapshot = models.JSONField(
        "Snapshot de destino",
        default=dict,
    )

    # -------------------------------------------------------------------------
    # Aprobación departamental y autorización patrimonial
    # -------------------------------------------------------------------------

    department_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_loans_department_approved",
        null=True,
        blank=True,
    )
    department_approved_at = models.DateTimeField(
        "Fecha de aceptación departamental",
        null=True,
        blank=True,
    )

    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_loans_authorized",
        null=True,
        blank=True,
    )
    authorized_at = models.DateTimeField(
        "Fecha de autorización",
        null=True,
        blank=True,
    )

    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_loans_rejected",
        null=True,
        blank=True,
    )
    rejected_at = models.DateTimeField(
        "Fecha de rechazo",
        null=True,
        blank=True,
    )
    rejection_reason = models.TextField(
        "Motivo de rechazo",
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Entrega y devolución
    # -------------------------------------------------------------------------

    delivered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_loans_delivered",
        null=True,
        blank=True,
    )
    delivered_at = models.DateTimeField(
        "Fecha de entrega",
        null=True,
        blank=True,
    )
    due_at = models.DateTimeField(
        "Fecha límite de devolución",
    )
    delivery_condition = models.CharField(
        "Condición al entregar",
        max_length=30,
        choices=PhysicalCondition.choices,
        default=PhysicalCondition.GOOD,
    )
    delivery_notes = models.TextField(
        "Observaciones de entrega",
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
        related_name="inventory_loans_returned",
        null=True,
        blank=True,
    )
    received_return_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_loan_returns_received",
        null=True,
        blank=True,
    )
    returned_at = models.DateTimeField(
        "Fecha efectiva de devolución",
        null=True,
        blank=True,
    )
    return_condition = models.CharField(
        "Condición al devolver",
        max_length=30,
        choices=PhysicalCondition.choices,
        blank=True,
    )
    return_notes = models.TextField(
        "Observaciones de devolución",
        blank=True,
    )

    purpose = models.TextField(
        "Objeto del préstamo",
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

    class Meta:
        db_table = "inventory_asset_loans"
        verbose_name = "Préstamo de activo"
        verbose_name_plural = "Préstamos de activos"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["asset", "status"]),
            models.Index(fields=["borrower", "status"]),
            models.Index(fields=["requested_by", "requested_at"]),
            models.Index(fields=["origin_dependencia", "status"]),
            models.Index(fields=["destination_dependencia", "status"]),
            models.Index(fields=["due_at", "status"]),
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
                            AssetLoanStatus.REQUESTED,
                            AssetLoanStatus.DEPARTMENT_APPROVED,
                            AssetLoanStatus.AUTHORIZED,
                            AssetLoanStatus.DELIVERED,
                            AssetLoanStatus.OVERDUE,
                            AssetLoanStatus.RETURN_PENDING,
                        ]
                    )
                    & Q(is_deleted=False)
                ),
                name="uq_inv_open_loan_per_asset",
            ),
        ]

    def clean(self):
        errors = {}

        if not self.purpose.strip():
            errors["purpose"] = (
                "Debe indicar el objeto del préstamo."
            )

        if self.external_borrower:
            if self.borrower_id:
                errors["borrower"] = (
                    "Un receptor externo no debe vincularse a un usuario."
                )

            if not self.borrower_name_snapshot.strip():
                errors["borrower_name_snapshot"] = (
                    "Debe indicar el nombre del receptor externo."
                )

            if not self.external_organization.strip():
                errors["external_organization"] = (
                    "Debe indicar la institución externa."
                )

            if not self.external_identification.strip():
                errors["external_identification"] = (
                    "Debe indicar la identificación del receptor."
                )
        else:
            if self.borrower_id and self.borrower_id_snapshot != self.borrower_id:
                errors["borrower_id_snapshot"] = (
                    "El UUID histórico debe coincidir con el receptor."
                )

            if not self.borrower_id and self.borrower_id_snapshot:
                errors["borrower_id_snapshot"] = (
                    "No debe existir UUID histórico sin receptor."
                )

        if self.origin_area_id:
            if (
                self.origin_area.dependencia_id
                != self.origin_dependencia_id
            ):
                errors["origin_area"] = (
                    "El área origen no pertenece a la dependencia."
                )

            if (
                self.origin_sede_id
                and self.origin_area.sede_fisica_id
                != self.origin_sede_id
            ):
                errors["origin_sede"] = (
                    "La sede origen no coincide con la sede del área."
                )

        if self.destination_area_id:
            if (
                self.destination_dependencia_id
                and self.destination_area.dependencia_id
                != self.destination_dependencia_id
            ):
                errors["destination_area"] = (
                    "El área destino no pertenece a la dependencia."
                )

            if (
                self.destination_sede_id
                and self.destination_area.sede_fisica_id
                != self.destination_sede_id
            ):
                errors["destination_sede"] = (
                    "La sede destino no coincide con la sede del área."
                )

        if self.external_borrower:
            if not self.external_destination.strip():
                errors["external_destination"] = (
                    "Debe indicar la ubicación externa."
                )
        else:
            has_destination = any(
                [
                    self.destination_dependencia_id,
                    self.destination_area_id,
                    self.destination_sede_id,
                ]
            )

            if not has_destination:
                errors["destination_dependencia"] = (
                    "Debe indicar el destino del préstamo."
                )

            assignment_statuses = {
                AssetLoanStatus.DEPARTMENT_APPROVED,
                AssetLoanStatus.AUTHORIZED,
                AssetLoanStatus.DELIVERED,
                AssetLoanStatus.OVERDUE,
                AssetLoanStatus.RETURN_PENDING,
                AssetLoanStatus.RETURNED,
            }
            if self.status in assignment_statuses and not self.destination_area_id:
                errors["destination_area"] = (
                    "La dependencia receptora debe asignar un área antes de aceptar."
                )

        authorization_statuses = {
            AssetLoanStatus.AUTHORIZED,
            AssetLoanStatus.DELIVERED,
            AssetLoanStatus.OVERDUE,
            AssetLoanStatus.RETURN_PENDING,
            AssetLoanStatus.RETURNED,
        }

        # Los préstamos internos quedan autorizados por la aceptación de la
        # dependencia receptora y la confirmación bilateral del acuse. La
        # autorización patrimonial se conserva sólo para préstamos externos.
        if self.external_borrower and self.status in authorization_statuses:
            if not self.authorized_by_id:
                errors["authorized_by"] = (
                    "El préstamo debe estar autorizado."
                )

            if not self.authorized_at:
                errors["authorized_at"] = (
                    "Debe registrar la fecha de autorización."
                )

        delivery_statuses = {
            AssetLoanStatus.DELIVERED,
            AssetLoanStatus.OVERDUE,
            AssetLoanStatus.RETURN_PENDING,
            AssetLoanStatus.RETURNED,
        }

        if self.status in delivery_statuses:
            if not self.delivered_by_id:
                errors["delivered_by"] = (
                    "Debe indicar quién entregó el bien."
                )

            if not self.delivered_at:
                errors["delivered_at"] = (
                    "Debe registrar la fecha de entrega."
                )

        if self.status == AssetLoanStatus.REJECTED:
            if not self.rejected_by_id:
                errors["rejected_by"] = (
                    "Debe indicar quién rechazó el préstamo."
                )

            if not self.rejected_at:
                errors["rejected_at"] = (
                    "Debe registrar la fecha del rechazo."
                )

            if not self.rejection_reason.strip():
                errors["rejection_reason"] = (
                    "Debe indicar el motivo del rechazo."
                )

        if self.status == AssetLoanStatus.RETURNED:
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
                    "Debe registrar la fecha de devolución."
                )

            if not self.return_condition:
                errors["return_condition"] = (
                    "Debe indicar la condición de devolución."
                )

        if self.due_at <= self.requested_at:
            errors["due_at"] = (
                "La fecha límite debe ser posterior a la solicitud."
            )

        if (
            self.delivered_at
            and self.delivered_at < self.requested_at
        ):
            errors["delivered_at"] = (
                "La entrega no puede ser anterior a la solicitud."
            )

        if (
            self.returned_at
            and self.delivered_at
            and self.returned_at < self.delivered_at
        ):
            errors["returned_at"] = (
                "La devolución no puede ser anterior a la entrega."
            )

        if self.bypass_used and not self.bypass_reason.strip():
            errors["bypass_reason"] = (
                "Debe justificar el uso del bypass."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.folio = self.folio.strip().upper()
        self.borrower_name_snapshot = (
            self.borrower_name_snapshot.strip()
        )

        if self.borrower_email_snapshot:
            self.borrower_email_snapshot = (
                self.borrower_email_snapshot.strip().lower()
            )

        if self.borrower_position_snapshot:
            self.borrower_position_snapshot = (
                self.borrower_position_snapshot.strip().upper()
            )

        if self.external_organization:
            self.external_organization = (
                self.external_organization.strip().upper()
            )

        if self.external_identification:
            self.external_identification = (
                self.external_identification.strip().upper()
            )

        if self.external_destination:
            self.external_destination = (
                self.external_destination.strip().upper()
            )

        self.purpose = self.purpose.strip()

        text_fields = [
            "rejection_reason",
            "delivery_notes",
            "return_notes",
            "bypass_reason",
        ]

        for field_name in text_fields:
            value = getattr(self, field_name, "")

            if value:
                setattr(self, field_name, value.strip())

        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return (
            self.status
            in {
                AssetLoanStatus.DELIVERED,
                AssetLoanStatus.OVERDUE,
                AssetLoanStatus.RETURN_PENDING,
            }
            and self.due_at < timezone.now()
            and not self.returned_at
        )

    def __str__(self):
        return (
            f"{self.folio} · "
            f"{self.asset.display_inventory_number} → "
            f"{self.borrower_name_snapshot}"
        )


# =============================================================================
# BAJAS PATRIMONIALES
# =============================================================================


class DisposalStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    SUBMITTED = "SUBMITTED", "Solicitada"
    EVIDENCE_PENDING = (
        "EVIDENCE_PENDING",
        "Evidencia pendiente",
    )
    TECHNICAL_REVIEW = (
        "TECHNICAL_REVIEW",
        "En dictamen técnico",
    )
    ADMINISTRATIVE_REVIEW = (
        "ADMINISTRATIVE_REVIEW",
        "En revisión administrativa",
    )
    AUTHORIZATION_PENDING = (
        "AUTHORIZATION_PENDING",
        "Pendiente de confirmación contable",
    )
    APPROVED = "APPROVED", "Aprobada"
    REJECTED = "REJECTED", "Rechazada"
    EXECUTED = "EXECUTED", "Ejecutada"
    CANCELLED = "CANCELLED", "Cancelada"


class DisposalApprovalStage(models.TextChoices):
    DEPARTMENT = "DEPARTMENT", "Dependencia responsable"
    TECHNICAL = "TECHNICAL", "Dictamen técnico"
    PATRIMONY = "PATRIMONY", "Control Patrimonial"
    LEGAL = "LEGAL", "Área Jurídica"
    INTERNAL_CONTROL = (
        "INTERNAL_CONTROL",
        "Órgano Interno de Control",
    )
    COUNCIL = "COUNCIL", "Cabildo"
    FINAL_AUTHORIZATION = (
        "FINAL_AUTHORIZATION",
        "Confirmación de baja contable",
    )


class DisposalApprovalDecision(models.TextChoices):
    PENDING = "PENDING", "Pendiente"
    APPROVED = "APPROVED", "Aprobada"
    REJECTED = "REJECTED", "Rechazada"
    OBSERVED = "OBSERVED", "Observada"
    NOT_REQUIRED = "NOT_REQUIRED", "No requerida"


class DisposalRequest(InventoryBaseModel):
    """
    Expediente de baja patrimonial.

    La baja no se ejecuta al crear este registro. Primero deben reunirse las
    evidencias y aprobaciones aplicables. DisposalService será responsable de
    validar documentos, autorizaciones y estado del activo antes de ejecutar.
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
        "Motivo",
        max_length=50,
        choices=DisposalReason.choices,
        db_index=True,
    )
    status = models.CharField(
        "Estado",
        max_length=40,
        choices=DisposalStatus.choices,
        default=DisposalStatus.DRAFT,
        db_index=True,
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_disposals_requested",
    )
    requested_by_name_snapshot = models.CharField(
        "Nombre del solicitante",
        max_length=300,
    )
    requested_by_email_snapshot = models.EmailField(
        "Correo del solicitante",
    )
    requested_at = models.DateTimeField(
        "Fecha de solicitud",
        default=timezone.now,
    )

    description = models.TextField(
        "Descripción / justificación",
    )
    legal_reference = models.TextField(
        "Fundamento / referencia legal",
        blank=True,
    )
    technical_report_required = models.BooleanField(
        "Requiere dictamen técnico",
        default=False,
    )
    required_document_types_snapshot = models.JSONField(
        "Documentos obligatorios",
        default=list,
        blank=True,
        help_text=(
            "Snapshot de tipos documentales exigidos para esta baja."
        ),
    )

    source_app = models.CharField(
        "Aplicación origen",
        max_length=80,
        blank=True,
    )
    source_model = models.CharField(
        "Modelo origen",
        max_length=120,
        blank=True,
    )
    source_object_id = models.UUIDField(
        "UUID del registro origen",
        null=True,
        blank=True,
    )

    final_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_disposals_final_approved",
        null=True,
        blank=True,
    )
    final_approved_at = models.DateTimeField(
        "Fecha de aprobación final",
        null=True,
        blank=True,
    )
    accounting_disposal_number = models.CharField(
        "Número de baja contable",
        max_length=120,
        blank=True,
        db_index=True,
    )
    accounting_disposal_date = models.DateField(
        "Fecha efectiva de baja contable",
        null=True,
        blank=True,
    )

    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_disposals_executed",
        null=True,
        blank=True,
    )
    executed_at = models.DateTimeField(
        "Fecha de ejecución",
        null=True,
        blank=True,
    )
    execution_notes = models.TextField(
        "Notas de ejecución",
        blank=True,
    )

    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_disposals_rejected",
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

    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_disposals_cancelled",
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

    class Meta:
        db_table = "inventory_disposal_requests"
        verbose_name = "Expediente de baja"
        verbose_name_plural = "Expedientes de baja"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["asset", "status"]),
            models.Index(fields=["reason", "status"]),
            models.Index(fields=["requested_by", "requested_at"]),
            models.Index(fields=["final_approved_at"]),
            models.Index(fields=["executed_at"]),
            models.Index(
                fields=["source_app", "source_model", "source_object_id"],
                name="idx_inv_disposal_source",
            ),
            models.Index(fields=["bypass_used"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["asset"],
                condition=(
                    Q(
                        status__in=[
                            DisposalStatus.SUBMITTED,
                            DisposalStatus.EVIDENCE_PENDING,
                            DisposalStatus.TECHNICAL_REVIEW,
                            DisposalStatus.ADMINISTRATIVE_REVIEW,
                            DisposalStatus.AUTHORIZATION_PENDING,
                            DisposalStatus.APPROVED,
                        ]
                    )
                    & Q(is_deleted=False)
                ),
                name="uq_inv_open_disposal_per_asset",
            ),
        ]

    def clean(self):
        errors = {}

        if not self.description.strip():
            errors["description"] = (
                "La justificación de la baja es obligatoria."
            )

        if self.source_object_id:
            if not self.source_app.strip():
                errors["source_app"] = (
                    "Debe indicar la aplicación origen."
                )

            if not self.source_model.strip():
                errors["source_model"] = (
                    "Debe indicar el modelo origen."
                )

        if self.status in {
            DisposalStatus.APPROVED,
            DisposalStatus.EXECUTED,
        }:
            if not self.final_approved_by_id:
                errors["final_approved_by"] = (
                    "Debe indicar quién aprobó finalmente la baja."
                )

            if not self.final_approved_at:
                errors["final_approved_at"] = (
                    "Debe registrar la fecha de aprobación."
                )

        if self.status == DisposalStatus.EXECUTED:
            if not self.executed_by_id:
                errors["executed_by"] = (
                    "Debe indicar quién ejecutó la baja."
                )

            if not self.executed_at:
                errors["executed_at"] = (
                    "Debe registrar la fecha de ejecución."
                )

            if not self.execution_notes.strip():
                errors["execution_notes"] = (
                    "Debe registrar las notas de ejecución."
                )

        if self.status == DisposalStatus.REJECTED:
            if not self.rejected_by_id:
                errors["rejected_by"] = (
                    "Debe indicar quién rechazó la baja."
                )

            if not self.rejected_at:
                errors["rejected_at"] = (
                    "Debe registrar la fecha de rechazo."
                )

            if not self.rejection_reason.strip():
                errors["rejection_reason"] = (
                    "Debe indicar el motivo del rechazo."
                )

        if self.status == DisposalStatus.CANCELLED:
            if not self.cancelled_by_id:
                errors["cancelled_by"] = (
                    "Debe indicar quién canceló la solicitud."
                )

            if not self.cancelled_at:
                errors["cancelled_at"] = (
                    "Debe registrar la fecha de cancelación."
                )

            if not self.cancellation_reason.strip():
                errors["cancellation_reason"] = (
                    "Debe indicar el motivo de cancelación."
                )

        chronology = [
            (
                "final_approved_at",
                self.final_approved_at,
                self.requested_at,
            ),
            (
                "executed_at",
                self.executed_at,
                self.final_approved_at,
            ),
            (
                "rejected_at",
                self.rejected_at,
                self.requested_at,
            ),
            (
                "cancelled_at",
                self.cancelled_at,
                self.requested_at,
            ),
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

        if self.bypass_used and not self.bypass_reason.strip():
            errors["bypass_reason"] = (
                "Debe justificar el uso del bypass."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.folio = self.folio.strip().upper()
        self.requested_by_name_snapshot = (
            self.requested_by_name_snapshot.strip()
        )
        self.requested_by_email_snapshot = (
            self.requested_by_email_snapshot.strip().lower()
        )
        self.description = self.description.strip()

        if self.legal_reference:
            self.legal_reference = self.legal_reference.strip()

        if self.source_app:
            self.source_app = self.source_app.strip().lower()

        if self.source_model:
            self.source_model = self.source_model.strip()

        text_fields = [
            "execution_notes",
            "rejection_reason",
            "cancellation_reason",
            "bypass_reason",
        ]

        for field_name in text_fields:
            value = getattr(self, field_name, "")

            if value:
                setattr(self, field_name, value.strip())

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.folio} · "
            f"{self.asset.display_inventory_number}"
        )


class DisposalApproval(InventoryBaseModel):
    """
    Resolución append-only de una etapa de autorización de baja.

    Cada municipio o empresa podrá decidir qué etapas son obligatorias según
    el motivo, valor y naturaleza del activo.
    """

    disposal_request = models.ForeignKey(
        DisposalRequest,
        on_delete=models.PROTECT,
        related_name="approvals",
    )
    stage = models.CharField(
        "Etapa",
        max_length=40,
        choices=DisposalApprovalStage.choices,
    )
    decision = models.CharField(
        "Decisión",
        max_length=30,
        choices=DisposalApprovalDecision.choices,
        default=DisposalApprovalDecision.PENDING,
        db_index=True,
    )

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_disposal_approvals",
        null=True,
        blank=True,
    )
    decided_by_name_snapshot = models.CharField(
        "Nombre del responsable",
        max_length=300,
        blank=True,
    )
    decided_by_email_snapshot = models.EmailField(
        "Correo del responsable",
        blank=True,
    )
    decided_at = models.DateTimeField(
        "Fecha de resolución",
        null=True,
        blank=True,
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
    payload = models.JSONField(
        "Snapshot adicional",
        default=dict,
        blank=True,
    )

    class Meta:
        db_table = "inventory_disposal_approvals"
        verbose_name = "Aprobación de baja"
        verbose_name_plural = "Aprobaciones de bajas"
        ordering = ["disposal_request", "created_at"]
        indexes = [
            models.Index(
                fields=["disposal_request", "stage"],
                name="idx_inv_disp_appr_stage",
            ),
            models.Index(fields=["decision", "decided_at"]),
            models.Index(fields=["decided_by", "decided_at"]),
            models.Index(fields=["bypass_used"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["disposal_request", "stage"],
                name="uq_inv_disposal_approval_stage",
            ),
        ]

    def clean(self):
        errors = {}

        resolved_decisions = {
            DisposalApprovalDecision.APPROVED,
            DisposalApprovalDecision.REJECTED,
            DisposalApprovalDecision.OBSERVED,
            DisposalApprovalDecision.NOT_REQUIRED,
        }

        if self.decision in resolved_decisions:
            if not self.decided_by_id:
                errors["decided_by"] = (
                    "Debe indicar quién resolvió la etapa."
                )

            if not self.decided_at:
                errors["decided_at"] = (
                    "Debe registrar la fecha de resolución."
                )

            if not self.comment.strip():
                errors["comment"] = (
                    "Debe registrar una justificación."
                )

        if self.decided_by_id:
            if not self.decided_by_name_snapshot.strip():
                errors["decided_by_name_snapshot"] = (
                    "Debe conservar el nombre del responsable."
                )

            if not self.decided_by_email_snapshot.strip():
                errors["decided_by_email_snapshot"] = (
                    "Debe conservar el correo del responsable."
                )

        if (
            self.decided_at
            and self.decided_at
            < self.disposal_request.requested_at
        ):
            errors["decided_at"] = (
                "La resolución no puede ser anterior a la solicitud."
            )

        if self.bypass_used and not self.bypass_reason.strip():
            errors["bypass_reason"] = (
                "Debe justificar el uso del bypass."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.decided_by_name_snapshot:
            self.decided_by_name_snapshot = (
                self.decided_by_name_snapshot.strip()
            )

        if self.decided_by_email_snapshot:
            self.decided_by_email_snapshot = (
                self.decided_by_email_snapshot.strip().lower()
            )

        if self.comment:
            self.comment = self.comment.strip()

        if self.bypass_reason:
            self.bypass_reason = self.bypass_reason.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.disposal_request.folio} · "
            f"{self.get_stage_display()} · "
            f"{self.get_decision_display()}"
        )
        
