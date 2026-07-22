# apps/inventory/models/asset_models.py

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from apps.inventory.models.catalog_models import (
    AccountingAccount,
    AcquisitionType,
    AssetCategory,
    AssetControlType,
    InventoryBaseModel,
    PhysicalCondition,
)


# =============================================================================
# SOLICITUD Y AUTORIZACIÓN DE ALTAS
# =============================================================================


class AssetIntakeStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    SUBMITTED = "SUBMITTED", "Enviada para aceptación"
    DEPARTMENT_APPROVED = (
        "DEPARTMENT_APPROVED",
        "Aceptada por la dependencia",
    )
    DEPARTMENT_REJECTED = (
        "DEPARTMENT_REJECTED",
        "Rechazada por la dependencia",
    )
    UNDER_PATRIMONY_REVIEW = (
        "UNDER_PATRIMONY_REVIEW",
        "En validación patrimonial",
    )
    OBSERVED = "OBSERVED", "Observada por Patrimonio"
    APPROVED = "APPROVED", "Aprobada para registro"
    REGISTERED = "REGISTERED", "Activo registrado"
    CANCELLED = "CANCELLED", "Cancelada"


class AssetIntakeDecisionType(models.TextChoices):
    SUBMIT = "SUBMIT", "Enviar solicitud"
    DEPARTMENT_APPROVE = (
        "DEPARTMENT_APPROVE",
        "Aceptar por la dependencia",
    )
    DEPARTMENT_REJECT = (
        "DEPARTMENT_REJECT",
        "Rechazar por la dependencia",
    )
    SEND_TO_PATRIMONY = (
        "SEND_TO_PATRIMONY",
        "Enviar a validación patrimonial",
    )
    PATRIMONY_OBSERVE = (
        "PATRIMONY_OBSERVE",
        "Emitir observación patrimonial",
    )
    PATRIMONY_APPROVE = (
        "PATRIMONY_APPROVE",
        "Aprobar registro patrimonial",
    )
    REGISTER_ASSET = (
        "REGISTER_ASSET",
        "Registrar activo oficial",
    )
    CANCEL = "CANCEL", "Cancelar solicitud"


class AssetIntakeRequest(InventoryBaseModel):
    """
    Solicitud previa al registro oficial de un activo.

    Una solicitud no es todavía un bien patrimonial. El activo oficial sólo
    debe crearse después de la aceptación departamental y la validación de
    Control Patrimonial.

    Las transiciones de estado deben ejecutarse mediante servicios. No deben
    realizarse directamente desde formularios, vistas o el administrador.
    """

    request_number = models.CharField(
        "Folio de solicitud",
        max_length=80,
        unique=True,
        help_text="Folio interno de seguimiento. Ejemplo: ALT-2026-000001.",
    )
    status = models.CharField(
        "Estado de la solicitud",
        max_length=40,
        choices=AssetIntakeStatus.choices,
        default=AssetIntakeStatus.DRAFT,
        db_index=True,
    )

    name = models.CharField(
        "Nombre / descripción corta",
        max_length=180,
    )
    description = models.TextField(
        "Descripción detallada",
        blank=True,
    )

    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.PROTECT,
        related_name="intake_requests",
        verbose_name="Categoría patrimonial propuesta",
    )
    expenditure_object = models.ForeignKey(
        "inventory.ExpenditureObject",
        on_delete=models.PROTECT,
        related_name="intake_requests",
        verbose_name="Clasificador por objeto del gasto",
        null=True,
        blank=True,
    )
    accounting_account = models.ForeignKey(
        AccountingAccount,
        on_delete=models.PROTECT,
        related_name="intake_requests",
        verbose_name="Cuenta contable propuesta",
        null=True,
        blank=True,
    )

    acquisition_type = models.CharField(
        "Tipo de adquisición",
        max_length=40,
        choices=AcquisitionType.choices,
        default=AcquisitionType.PURCHASE,
    )
    acquisition_date = models.DateField(
        "Fecha de adquisición",
        null=True,
        blank=True,
    )
    reception_date = models.DateField(
        "Fecha de recepción física",
        null=True,
        blank=True,
    )
    acquisition_cost = models.DecimalField(
        "Costo de adquisición",
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    residual_value = models.DecimalField(
        "Valor residual propuesto",
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    manufacturer = models.ForeignKey(
        "inventory.Manufacturer",
        on_delete=models.PROTECT,
        related_name="intake_requests",
        null=True,
        blank=True,
    )
    model = models.ForeignKey(
        "inventory.AssetModel",
        on_delete=models.PROTECT,
        related_name="intake_requests",
        null=True,
        blank=True,
    )
    serial_number = models.CharField(
        "Número de serie / service tag",
        max_length=120,
        null=True,
        blank=True,
    )

    supplier = models.ForeignKey(
        "inventory.Supplier",
        on_delete=models.PROTECT,
        related_name="intake_requests",
        null=True,
        blank=True,
    )
    contract = models.ForeignKey(
        "inventory.Contract",
        on_delete=models.PROTECT,
        related_name="intake_requests",
        null=True,
        blank=True,
    )

    requested_sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_intake_requests",
        verbose_name="Sede receptora propuesta",
        null=True,
        blank=True,
    )
    requested_dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_intake_requests",
        verbose_name="Dependencia receptora",
    )
    requested_area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_intake_requests",
        verbose_name="Área receptora propuesta",
        null=True,
        blank=True,
    )
    proposed_custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_intake_custody_proposals",
        verbose_name="Resguardatario propuesto",
        null=True,
        blank=True,
    )
    location_detail = models.CharField(
        "Detalle de ubicación física",
        max_length=255,
        blank=True,
        help_text="Ejemplo: rack del cuarto piso, oficina 204 o almacén norte.",
    )

    captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_intake_requests_captured",
        verbose_name="Capturado por",
        null=True,
        blank=True,
    )
    captured_at = models.DateTimeField(
        "Fecha de captura",
        null=True,
        blank=True,
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_intake_requests_submitted",
        verbose_name="Enviado por",
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(
        "Fecha de envío",
        null=True,
        blank=True,
    )

    # Referencia desacoplada a Compras, Donaciones u otro módulo productor.
    source_app = models.CharField(
        "Aplicación de origen",
        max_length=80,
        blank=True,
    )
    source_model = models.CharField(
        "Modelo de origen",
        max_length=120,
        blank=True,
    )
    source_object_id = models.UUIDField(
        "UUID del registro de origen",
        null=True,
        blank=True,
        db_index=True,
    )
    source_folio = models.CharField(
        "Folio del registro de origen",
        max_length=120,
        blank=True,
        db_index=True,
    )

    department_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_intakes_department_approved",
        verbose_name="Director o encargado que aceptó",
        null=True,
        blank=True,
    )
    department_approved_at = models.DateTimeField(
        "Fecha de aceptación departamental",
        null=True,
        blank=True,
    )
    department_rejection_reason = models.TextField(
        "Motivo de rechazo departamental",
        blank=True,
    )

    patrimony_validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_intakes_patrimony_validated",
        verbose_name="Validador patrimonial",
        null=True,
        blank=True,
    )
    patrimony_validated_at = models.DateTimeField(
        "Fecha de validación patrimonial",
        null=True,
        blank=True,
    )
    patrimony_observation = models.TextField(
        "Observación patrimonial",
        blank=True,
    )

    bypass_used = models.BooleanField(
        "Se utilizó bypass administrativo",
        default=False,
        db_index=True,
    )
    bypass_reason = models.TextField(
        "Motivo del bypass",
        blank=True,
        help_text=(
            "Obligatorio cuando manager/root sustituye una aprobación "
            "departamental o patrimonial."
        ),
    )

    notes = models.TextField(
        "Notas internas",
        blank=True,
    )
    extra_attributes = models.JSONField(
        "Atributos extendidos",
        default=dict,
        blank=True,
        help_text="No utilizar para reglas críticas del flujo.",
    )

    class Meta:
        db_table = "inventory_asset_intake_requests"
        verbose_name = "Solicitud de alta de activo"
        verbose_name_plural = "Solicitudes de alta de activos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["request_number"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["requested_dependencia", "status"]),
            models.Index(fields=["requested_area", "status"]),
            models.Index(fields=["submitted_by", "status"]),
            models.Index(
                fields=["captured_by", "status"],
                name="idx_inv_intake_capture_st",
            ),
            models.Index(
                fields=["source_app", "source_object_id"],
                name="idx_inv_intake_source_ref",
            ),
            models.Index(fields=["acquisition_date"]),
            models.Index(fields=["serial_number"]),
            models.Index(fields=["bypass_used"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(acquisition_cost__gte=0),
                name="ck_inv_intake_acquisition_cost_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(residual_value__gte=0),
                name="ck_inv_intake_residual_value_gte_zero",
            ),
        ]

    def clean(self):
        errors = {}

        if self.acquisition_cost < 0:
            errors["acquisition_cost"] = (
                "El costo de adquisición no puede ser negativo."
            )

        if self.residual_value < 0:
            errors["residual_value"] = (
                "El valor residual no puede ser negativo."
            )

        if self.residual_value > self.acquisition_cost:
            errors["residual_value"] = (
                "El valor residual no puede ser mayor al costo de adquisición."
            )

        if (
            self.reception_date
            and self.acquisition_date
            and self.reception_date < self.acquisition_date
        ):
            errors["reception_date"] = (
                "La fecha de recepción no puede ser anterior "
                "a la fecha de adquisición."
            )

        if self.requested_area_id:
            if (
                self.requested_area.dependencia_id
                != self.requested_dependencia_id
            ):
                errors["requested_area"] = (
                    "El área seleccionada no pertenece a la dependencia "
                    "receptora."
                )

            if (
                self.requested_sede_id
                and self.requested_area.sede_fisica_id
                != self.requested_sede_id
            ):
                errors["requested_sede"] = (
                    "La sede seleccionada no coincide con la sede física "
                    "del área receptora."
                )

        if self.bypass_used and not self.bypass_reason.strip():
            errors["bypass_reason"] = (
                "Debe indicar el motivo por el cual se utilizó el bypass."
            )

        if not self.bypass_used and self.bypass_reason.strip():
            errors["bypass_reason"] = (
                "No debe registrar un motivo si no se utilizó bypass."
            )

        if self.status not in {
            AssetIntakeStatus.DRAFT,
            AssetIntakeStatus.CANCELLED,
        }:
            if not self.submitted_by_id:
                errors["submitted_by"] = (
                    "Una solicitud enviada debe indicar quién la remitió."
                )
            if not self.submitted_at:
                errors["submitted_at"] = (
                    "Una solicitud enviada debe conservar la fecha de envío."
                )

        source_values = (
            self.source_app.strip(),
            self.source_model.strip(),
            self.source_object_id,
        )
        if any(source_values) and not all(source_values):
            errors["source_object_id"] = (
                "La referencia externa requiere aplicación, modelo y UUID."
            )

        if (
            self.status in {
                AssetIntakeStatus.DEPARTMENT_APPROVED,
                AssetIntakeStatus.UNDER_PATRIMONY_REVIEW,
            }
            and not self.department_approved_by_id
        ):
            errors["department_approved_by"] = (
                "Una solicitud aceptada debe indicar quién la aprobó."
            )

        if (
            self.status == AssetIntakeStatus.DEPARTMENT_REJECTED
            and not self.department_rejection_reason.strip()
        ):
            errors["department_rejection_reason"] = (
                "Debe indicar el motivo del rechazo departamental."
            )

        if (
            self.status
            in {
                AssetIntakeStatus.APPROVED,
                AssetIntakeStatus.REGISTERED,
            }
            and not self.patrimony_validated_by_id
        ):
            errors["patrimony_validated_by"] = (
                "La solicitud debe contar con validación patrimonial."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.request_number = self.request_number.strip().upper()
        self.name = self.name.strip().upper()

        if self.description:
            self.description = self.description.strip()

        if self.serial_number:
            self.serial_number = self.serial_number.strip().upper()

        if self.department_rejection_reason:
            self.department_rejection_reason = (
                self.department_rejection_reason.strip()
            )

        if self.patrimony_observation:
            self.patrimony_observation = (
                self.patrimony_observation.strip()
            )

        if self.bypass_reason:
            self.bypass_reason = self.bypass_reason.strip()

        if self.source_app:
            self.source_app = self.source_app.strip().lower()

        if self.source_model:
            self.source_model = self.source_model.strip()

        if self.source_folio:
            self.source_folio = self.source_folio.strip().upper()

        if self.location_detail:
            self.location_detail = self.location_detail.strip()

        if self.notes:
            self.notes = self.notes.strip()

        super().save(*args, **kwargs)

    @property
    def resulting_asset(self):
        return getattr(self, "registered_asset", None)

    @property
    def is_editable(self):
        return self.status in {
            AssetIntakeStatus.DRAFT,
            AssetIntakeStatus.DEPARTMENT_REJECTED,
            AssetIntakeStatus.OBSERVED,
        }

    @property
    def is_waiting_department_approval(self):
        return self.status == AssetIntakeStatus.SUBMITTED

    @property
    def is_ready_for_registration(self):
        return self.status == AssetIntakeStatus.APPROVED

    def __str__(self):
        return f"{self.request_number} · {self.name}"


class AssetIntakeDecision(InventoryBaseModel):
    """
    Evento inmutable del flujo de aprobación de una solicitud de alta.

    Aunque una solicitud contiene campos de proyección para consultar rápidamente
    su situación actual, este modelo conserva cada decisión y sus snapshots.

    No debe editarse ni eliminarse desde interfaces ordinarias.
    """

    intake_request = models.ForeignKey(
        AssetIntakeRequest,
        on_delete=models.PROTECT,
        related_name="decisions",
    )
    decision_type = models.CharField(
        "Tipo de decisión",
        max_length=40,
        choices=AssetIntakeDecisionType.choices,
        db_index=True,
    )
    previous_status = models.CharField(
        "Estado anterior",
        max_length=40,
        choices=AssetIntakeStatus.choices,
    )
    resulting_status = models.CharField(
        "Estado resultante",
        max_length=40,
        choices=AssetIntakeStatus.choices,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_intake_decisions",
        verbose_name="Operador",
    )
    actor_name_snapshot = models.CharField(
        "Nombre del operador",
        max_length=300,
    )
    actor_email_snapshot = models.EmailField(
        "Correo del operador",
    )

    dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_intake_decisions",
        null=True,
        blank=True,
    )
    dependencia_name_snapshot = models.CharField(
        "Nombre de dependencia",
        max_length=180,
        blank=True,
    )
    dependencia_code_snapshot = models.CharField(
        "Código presupuestal de dependencia",
        max_length=20,
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
        "Fecha efectiva de la decisión",
        default=timezone.now,
        db_index=True,
    )

    class Meta:
        db_table = "inventory_asset_intake_decisions"
        verbose_name = "Decisión de solicitud de alta"
        verbose_name_plural = "Decisiones de solicitudes de alta"
        ordering = ["occurred_at", "created_at"]
        indexes = [
            models.Index(fields=["intake_request", "occurred_at"]),
            models.Index(fields=["decision_type", "occurred_at"]),
            models.Index(fields=["actor", "occurred_at"]),
            models.Index(fields=["dependencia", "occurred_at"]),
            models.Index(fields=["bypass_used", "occurred_at"]),
        ]

    def clean(self):
        errors = {}

        if self.previous_status == self.resulting_status:
            errors["resulting_status"] = (
                "Una decisión debe producir una transición de estado."
            )

        if self.bypass_used and not self.bypass_reason.strip():
            errors["bypass_reason"] = (
                "El motivo del bypass es obligatorio."
            )

        if not self.actor_name_snapshot.strip():
            errors["actor_name_snapshot"] = (
                "Debe conservar el nombre del operador."
            )

        if not self.actor_email_snapshot.strip():
            errors["actor_email_snapshot"] = (
                "Debe conservar el correo del operador."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.actor_name_snapshot = self.actor_name_snapshot.strip()
        self.actor_email_snapshot = (
            self.actor_email_snapshot.strip().lower()
        )

        if self.dependencia_name_snapshot:
            self.dependencia_name_snapshot = (
                self.dependencia_name_snapshot.strip().upper()
            )

        if self.dependencia_code_snapshot:
            self.dependencia_code_snapshot = (
                self.dependencia_code_snapshot.strip().upper()
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
            f"{self.intake_request.request_number} · "
            f"{self.get_decision_type_display()}"
        )


# =============================================================================
# CONFIGURACIÓN Y SECUENCIAS DE FOLIOS
# =============================================================================


class InventoryFolioPolicy(InventoryBaseModel):
    """
    Política institucional para construir folios oficiales.

    Permite que Inventory funcione en distintos municipios o empresas sin
    codificar la clave 039 directamente en servicios o modelos.
    """

    name = models.CharField(
        "Nombre de política",
        max_length=180,
    )
    municipality_code = models.CharField(
        "Clave de municipio / entidad",
        max_length=10,
        help_text="Ejemplo: 039.",
    )
    municipality_name = models.CharField(
        "Nombre del municipio / entidad",
        max_length=180,
    )
    format_template = models.CharField(
        "Plantilla del folio",
        max_length=255,
        default=(
            "{municipality}-{year_short}-{conac}-"
            "{dependency}-{asset_type}-{progressive}"
        ),
        help_text=(
            "Variables disponibles: municipality, fiscal_year, year_short, "
            "conac, dependency, asset_type y progressive."
        ),
    )
    progressive_length = models.PositiveSmallIntegerField(
        "Longitud del progresivo",
        default=4,
    )
    effective_from = models.DateField(
        "Vigente desde",
    )
    effective_until = models.DateField(
        "Vigente hasta",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "inventory_folio_policies"
        verbose_name = "Política de folios"
        verbose_name_plural = "Políticas de folios"
        ordering = ["-effective_from", "name"]
        indexes = [
            models.Index(fields=["municipality_code"]),
            models.Index(fields=["effective_from", "effective_until"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(progressive_length__gte=1),
                name="ck_inv_folio_progressive_length_gte_1",
            ),
        ]

    def clean(self):
        errors = {}

        if self.progressive_length < 1:
            errors["progressive_length"] = (
                "La longitud del progresivo debe ser mayor a cero."
            )

        if self.progressive_length > 12:
            errors["progressive_length"] = (
                "La longitud del progresivo no puede ser mayor a 12."
            )

        if (
            self.effective_until
            and self.effective_until < self.effective_from
        ):
            errors["effective_until"] = (
                "La fecha final no puede ser anterior a la fecha inicial."
            )

        required_tokens = {
            "{municipality}",
            "{year_short}",
            "{conac}",
            "{dependency}",
            "{asset_type}",
            "{progressive}",
        }

        missing_tokens = [
            token
            for token in required_tokens
            if token not in self.format_template
        ]

        if missing_tokens:
            errors["format_template"] = (
                "La plantilla debe incluir: "
                + ", ".join(sorted(missing_tokens))
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        self.municipality_code = (
            self.municipality_code.strip().upper()
        )
        self.municipality_name = (
            self.municipality_name.strip().upper()
        )
        self.format_template = self.format_template.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.municipality_code} · {self.name} "
            f"({self.effective_from:%Y-%m-%d})"
        )


class InventoryFolioSequence(InventoryBaseModel):
    """
    Secuencia transaccional para folios oficiales.

    El valor de current_number debe incrementarse exclusivamente desde
    InventoryFolioService utilizando transaction.atomic() y select_for_update().
    """

    policy = models.ForeignKey(
        InventoryFolioPolicy,
        on_delete=models.PROTECT,
        related_name="sequences",
    )
    fiscal_year = models.PositiveSmallIntegerField(
        "Ejercicio fiscal",
        help_text="Año completo. Ejemplo: 2026.",
    )
    conac_code = models.CharField(
        "Código CONAC / COG",
        max_length=10,
    )
    dependency_code = models.CharField(
        "Código de dependencia de origen",
        max_length=20,
    )
    asset_type_code = models.CharField(
        "Tipo de bien",
        max_length=2,
        help_text="Ejemplo: BM, BI o BP.",
    )
    current_number = models.PositiveIntegerField(
        "Consecutivo actual",
        default=0,
    )

    class Meta:
        db_table = "inventory_folio_sequences"
        verbose_name = "Secuencia de folio"
        verbose_name_plural = "Secuencias de folios"
        ordering = [
            "policy",
            "fiscal_year",
            "conac_code",
            "dependency_code",
            "asset_type_code",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "policy",
                    "fiscal_year",
                    "conac_code",
                    "dependency_code",
                    "asset_type_code",
                ],
                name="uq_inv_folio_sequence_scope",
            ),
            models.CheckConstraint(
                condition=Q(fiscal_year__gte=2000),
                name="ck_inv_folio_fiscal_year_gte_2000",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "policy",
                    "fiscal_year",
                    "conac_code",
                    "dependency_code",
                    "asset_type_code",
                ],
                name="idx_inv_folio_sequence_scope",
            ),
        ]

    def clean(self):
        errors = {}

        if self.fiscal_year < 2000:
            errors["fiscal_year"] = (
                "El ejercicio fiscal debe utilizar cuatro dígitos."
            )

        if len(self.asset_type_code.strip()) != 2:
            errors["asset_type_code"] = (
                "El tipo de bien debe contener exactamente dos caracteres."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.conac_code = self.conac_code.strip().upper()
        self.dependency_code = (
            self.dependency_code.strip().upper().zfill(3)
        )
        self.asset_type_code = (
            self.asset_type_code.strip().upper()
        )

        super().save(*args, **kwargs)

    @property
    def year_short(self):
        return str(self.fiscal_year)[-2:]

    @property
    def next_number_preview(self):
        return self.current_number + 1

    def __str__(self):
        return (
            f"{self.policy.municipality_code}-{self.year_short}-"
            f"{self.conac_code}-{self.dependency_code}-"
            f"{self.asset_type_code} · {self.current_number}"
        )


# =============================================================================
# ACTIVO PATRIMONIAL OFICIAL
# =============================================================================


class AssetPatrimonialStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Activo"
    PENDING_DISPOSAL = (
        "PENDING_DISPOSAL",
        "En proceso de baja",
    )
    DISPOSED = "DISPOSED", "Dado de baja"
    ARCHIVED = "ARCHIVED", "Archivado"


class AssetOperationalStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Disponible"
    ASSIGNED = "ASSIGNED", "Asignado"
    LOANED = "LOANED", "Prestado"
    IN_DIAGNOSIS = "IN_DIAGNOSIS", "En diagnóstico"
    IN_REPAIR = "IN_REPAIR", "En reparación"
    OUT_OF_SERVICE = "OUT_OF_SERVICE", "Fuera de servicio"
    NOT_LOCATED = "NOT_LOCATED", "No localizado"


class Asset(InventoryBaseModel):
    """
    Expediente patrimonial oficial.

    Este modelo sólo representa bienes que terminaron el flujo de alta. Una
    captura inicial debe vivir en AssetIntakeRequest.

    Los campos current_* son una proyección del estado vigente para consultas
    rápidas. Los movimientos y resguardos conservan el historial.
    """

    source_intake_request = models.OneToOneField(
        AssetIntakeRequest,
        on_delete=models.PROTECT,
        related_name="registered_asset",
        verbose_name="Solicitud de alta origen",
        null=True,
        blank=True,
    )

    official_inventory_number = models.CharField(
        "Folio oficial patrimonial",
        max_length=80,
        unique=True,
        help_text=(
            "Folio oficial inmutable generado por el sistema. "
            "Ejemplo: 039-26-5151-012-BM-0005."
        ),
    )
    internal_inventory_number = models.CharField(
        "Folio interno Axentra",
        max_length=80,
        unique=True,
        help_text="Folio técnico interno. Ejemplo: AXN-INV-2026-000001.",
    )
    legacy_inventory_number = models.CharField(
        "Número de inventario anterior",
        max_length=80,
        blank=True,
        db_index=True,
    )

    name = models.CharField(
        "Nombre / descripción corta",
        max_length=180,
    )
    description = models.TextField(
        "Descripción detallada",
        blank=True,
    )

    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.PROTECT,
        related_name="assets",
    )
    expenditure_object = models.ForeignKey(
        "inventory.ExpenditureObject",
        on_delete=models.PROTECT,
        related_name="assets",
        verbose_name="Clasificador por objeto del gasto",
        null=True,
        blank=True,
    )
    accounting_account = models.ForeignKey(
        AccountingAccount,
        on_delete=models.PROTECT,
        related_name="assets",
        null=True,
        blank=True,
    )

    control_type = models.CharField(
        "Tipo de control",
        max_length=30,
        choices=AssetControlType.choices,
        default=AssetControlType.INTERNAL_CONTROL,
    )
    patrimonial_status = models.CharField(
        "Estado patrimonial",
        max_length=30,
        choices=AssetPatrimonialStatus.choices,
        default=AssetPatrimonialStatus.ACTIVE,
        db_index=True,
    )
    operational_status = models.CharField(
        "Estado operativo",
        max_length=30,
        choices=AssetOperationalStatus.choices,
        default=AssetOperationalStatus.AVAILABLE,
        db_index=True,
    )
    physical_condition = models.CharField(
        "Condición física",
        max_length=30,
        choices=PhysicalCondition.choices,
        default=PhysicalCondition.GOOD,
    )

    acquisition_type = models.CharField(
        "Tipo de adquisición",
        max_length=40,
        choices=AcquisitionType.choices,
        default=AcquisitionType.PURCHASE,
    )
    acquisition_date = models.DateField(
        "Fecha de adquisición",
    )
    reception_date = models.DateField(
        "Fecha de recepción física",
        null=True,
        blank=True,
    )
    registration_date = models.DateField(
        "Fecha de incorporación al inventario",
        default=timezone.localdate,
    )
    registered_at = models.DateTimeField(
        "Fecha y hora de registro oficial",
        default=timezone.now,
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_assets_registered",
        verbose_name="Registrado por",
    )

    acquisition_cost = models.DecimalField(
        "Costo de adquisición",
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    residual_value = models.DecimalField(
        "Valor residual / desecho",
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    useful_life_months = models.PositiveIntegerField(
        "Vida útil en meses",
        null=True,
        blank=True,
    )

    is_capitalizable = models.BooleanField(
        "Capitalizable contablemente",
        default=False,
        db_index=True,
    )
    uma_value = models.ForeignKey(
        "inventory.UmaValue",
        on_delete=models.PROTECT,
        related_name="assets",
        verbose_name="UMA utilizada",
        null=True,
        blank=True,
    )
    uma_value_applied = models.DecimalField(
        "Valor UMA aplicado",
        max_digits=16,
        decimal_places=4,
        null=True,
        blank=True,
    )
    uma_multiplier_applied = models.DecimalField(
        "Multiplicador UMA aplicado",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    capitalization_threshold_amount = models.DecimalField(
        "Umbral de capitalización aplicado",
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
    )
    capitalization_rule_snapshot = models.JSONField(
        "Snapshot de regla de capitalización",
        default=dict,
        blank=True,
    )

    manufacturer = models.ForeignKey(
        "inventory.Manufacturer",
        on_delete=models.PROTECT,
        related_name="assets",
        null=True,
        blank=True,
    )
    model = models.ForeignKey(
        "inventory.AssetModel",
        on_delete=models.PROTECT,
        related_name="assets",
        null=True,
        blank=True,
    )
    serial_number = models.CharField(
        "Número de serie / service tag",
        max_length=120,
        null=True,
        blank=True,
    )

    supplier = models.ForeignKey(
        "inventory.Supplier",
        on_delete=models.PROTECT,
        related_name="assets",
        null=True,
        blank=True,
    )
    contract = models.ForeignKey(
        "inventory.Contract",
        on_delete=models.PROTECT,
        related_name="assets",
        null=True,
        blank=True,
    )

    origin_sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_assets_origin",
        verbose_name="Sede de alta original",
        null=True,
        blank=True,
    )
    origin_dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_assets_origin",
        verbose_name="Dependencia de alta original",
    )
    origin_area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_assets_origin",
        verbose_name="Área de alta original",
        null=True,
        blank=True,
    )

    origin_dependencia_code_snapshot = models.CharField(
        "Código original de dependencia",
        max_length=20,
        help_text=(
            "Código utilizado al generar el folio. Es inmutable aunque "
            "el bien sea transferido."
        ),
    )
    origin_dependencia_name_snapshot = models.CharField(
        "Nombre original de dependencia",
        max_length=180,
    )

    current_sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_assets_current",
        verbose_name="Sede actual",
        null=True,
        blank=True,
    )
    current_dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_assets_current",
        verbose_name="Dependencia responsable actual",
        null=True,
        blank=True,
    )
    current_area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_assets_current",
        verbose_name="Área operativa actual",
        null=True,
        blank=True,
    )
    current_custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_assets_in_custody",
        verbose_name="Resguardatario actual",
        null=True,
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

    location_detail = models.CharField(
        "Detalle de ubicación física",
        max_length=255,
        blank=True,
        help_text="Referencia precisa dentro de la sede: piso, oficina, rack o almacén.",
    )

    notes = models.TextField(
        "Notas",
        blank=True,
    )
    extra_attributes = models.JSONField(
        "Atributos extendidos",
        default=dict,
        blank=True,
        help_text="No utilizar para reglas críticas.",
    )

    class Meta:
        db_table = "inventory_assets"
        verbose_name = "Activo patrimonial"
        verbose_name_plural = "Activos patrimoniales"
        ordering = ["-registered_at"]
        indexes = [
            models.Index(fields=["legacy_inventory_number"]),
            models.Index(fields=["serial_number"]),
            models.Index(fields=["patrimonial_status"]),
            models.Index(fields=["operational_status"]),
            models.Index(fields=["control_type"]),
            models.Index(fields=["is_capitalizable"]),
            models.Index(
                fields=["current_dependencia", "patrimonial_status"],
                name="idx_inv_asset_dep_patrimonial",
            ),
            models.Index(
                fields=["current_sede", "operational_status"],
                name="idx_inv_asset_sede_operational",
            ),
            models.Index(
                fields=["acquisition_date", "registration_date"],
                name="idx_inv_asset_legal_dates",
            ),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.UniqueConstraint(
                Lower("serial_number"),
                condition=Q(
                    serial_number__isnull=False,
                    is_deleted=False,
                )
                & ~Q(serial_number=""),
                name="uq_inv_asset_serial_lower",
            ),
            models.CheckConstraint(
                condition=Q(acquisition_cost__gte=0),
                name="ck_inv_asset_acquisition_cost_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(residual_value__gte=0),
                name="ck_inv_asset_residual_value_gte_zero",
            ),
        ]

    def clean(self):
        errors = {}

        if self.acquisition_cost < 0:
            errors["acquisition_cost"] = (
                "El costo de adquisición no puede ser negativo."
            )

        if self.residual_value < 0:
            errors["residual_value"] = (
                "El valor residual no puede ser negativo."
            )

        if self.residual_value > self.acquisition_cost:
            errors["residual_value"] = (
                "El valor residual no puede ser mayor al costo de adquisición."
            )

        if self.registration_date < self.acquisition_date:
            errors["registration_date"] = (
                "La fecha de registro no puede ser anterior "
                "a la fecha de adquisición."
            )

        if (
            self.reception_date
            and self.reception_date < self.acquisition_date
        ):
            errors["reception_date"] = (
                "La fecha de recepción no puede ser anterior "
                "a la fecha de adquisición."
            )

        if self.origin_area_id:
            if (
                self.origin_area.dependencia_id
                != self.origin_dependencia_id
            ):
                errors["origin_area"] = (
                    "El área original no pertenece a la dependencia original."
                )

            if (
                self.origin_sede_id
                and self.origin_area.sede_fisica_id
                != self.origin_sede_id
            ):
                errors["origin_sede"] = (
                    "La sede original no coincide con la sede del área."
                )

        if self.current_area_id:
            if (
                self.current_dependencia_id
                and self.current_area.dependencia_id
                != self.current_dependencia_id
            ):
                errors["current_area"] = (
                    "El área actual no pertenece a la dependencia actual."
                )

            if (
                self.current_sede_id
                and self.current_area.sede_fisica_id
                != self.current_sede_id
            ):
                errors["current_sede"] = (
                    "La sede actual no coincide con la sede del área."
                )

        if self.is_capitalizable:
            required_capitalization_fields = {
                "uma_value_applied": self.uma_value_applied,
                "uma_multiplier_applied": self.uma_multiplier_applied,
                "capitalization_threshold_amount": (
                    self.capitalization_threshold_amount
                ),
            }

            for field_name, value in required_capitalization_fields.items():
                if value is None:
                    errors[field_name] = (
                        "Debe conservar el valor utilizado por la regla "
                        "de capitalización."
                    )

        if (
            self.patrimonial_status
            == AssetPatrimonialStatus.DISPOSED
            and self.is_active
        ):
            errors["is_active"] = (
                "Un activo dado de baja no puede permanecer activo."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.official_inventory_number = (
            self.official_inventory_number.strip().upper()
        )
        self.internal_inventory_number = (
            self.internal_inventory_number.strip().upper()
        )

        if self.legacy_inventory_number:
            self.legacy_inventory_number = (
                self.legacy_inventory_number.strip().upper()
            )

        if self.serial_number:
            self.serial_number = self.serial_number.strip().upper()

        self.name = self.name.strip().upper()
        self.origin_dependencia_code_snapshot = (
            self.origin_dependencia_code_snapshot.strip().upper()
        )
        self.origin_dependencia_name_snapshot = (
            self.origin_dependencia_name_snapshot.strip().upper()
        )

        if self.description:
            self.description = self.description.strip()

        if self.location_detail:
            self.location_detail = self.location_detail.strip()

        if self.notes:
            self.notes = self.notes.strip()

        super().save(*args, **kwargs)

    @property
    def display_inventory_number(self):
        return (
            self.official_inventory_number
            or self.internal_inventory_number
            or self.legacy_inventory_number
            or "SIN-FOLIO"
        )

    @property
    def depreciable_base(self):
        return max(
            self.acquisition_cost - self.residual_value,
            Decimal("0.00"),
        )

    @property
    def is_disposed(self):
        return (
            self.patrimonial_status
            == AssetPatrimonialStatus.DISPOSED
        )

    @property
    def is_available_for_assignment(self):
        return (
            self.patrimonial_status
            == AssetPatrimonialStatus.ACTIVE
            and self.operational_status
            == AssetOperationalStatus.AVAILABLE
            and self.is_active
            and not self.is_deleted
        )

    def __str__(self):
        return f"{self.display_inventory_number} · {self.name}"


# =============================================================================
# DETALLE DE BIENES INMUEBLES
# =============================================================================


class ImmovableAssetDetail(InventoryBaseModel):
    """
    Información jurídica y catastral exclusiva de bienes inmuebles.
    """

    asset = models.OneToOneField(
        Asset,
        on_delete=models.CASCADE,
        related_name="immovable_detail",
    )
    cadastral_key = models.CharField(
        "Clave catastral",
        max_length=120,
        blank=True,
    )
    public_registry_record = models.CharField(
        "Registro Público / inscripción",
        max_length=180,
        blank=True,
    )
    deed_number = models.CharField(
        "Número de escritura / título",
        max_length=120,
        blank=True,
    )
    surface_m2 = models.DecimalField(
        "Superficie m²",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    legal_status = models.CharField(
        "Estado jurídico",
        max_length=180,
        blank=True,
    )

    class Meta:
        db_table = "inventory_immovable_asset_details"
        verbose_name = "Detalle de inmueble"
        verbose_name_plural = "Detalles de inmuebles"
        indexes = [
            models.Index(fields=["cadastral_key"]),
            models.Index(fields=["public_registry_record"]),
            models.Index(fields=["deed_number"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(surface_m2__isnull=True) | Q(surface_m2__gte=0),
                name="ck_inv_immovable_surface_gte_zero",
            ),
        ]

    def clean(self):
        if self.surface_m2 is not None and self.surface_m2 < 0:
            raise ValidationError(
                {
                    "surface_m2": (
                        "La superficie no puede ser negativa."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if self.cadastral_key:
            self.cadastral_key = self.cadastral_key.strip().upper()

        if self.public_registry_record:
            self.public_registry_record = (
                self.public_registry_record.strip().upper()
            )

        if self.deed_number:
            self.deed_number = self.deed_number.strip().upper()

        if self.legal_status:
            self.legal_status = self.legal_status.strip().upper()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Inmueble · {self.asset.display_inventory_number}"
    
    
