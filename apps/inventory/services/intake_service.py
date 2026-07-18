# apps/inventory/services/intake_service.py

"""Flujo transaccional de solicitudes de alta patrimonial."""

from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from apps.inventory.integrations.core_directory import (
    CoreDirectoryError,
    get_area_context,
    get_department,
    get_module_role,
    get_site,
    get_user_identity,
    get_user_organizational_context,
    user_can_approve_department,
    validate_organizational_context,
)
from apps.inventory.models import (
    AccountingAccount,
    AcquisitionType,
    Asset,
    AssetCategory,
    AssetControlType,
    AssetIntakeDecision,
    AssetIntakeDecisionType,
    AssetIntakeRequest,
    AssetIntakeStatus,
    AssetOperationalStatus,
    AssetPatrimonialStatus,
    CapitalizationRule,
    ExpenditureObject,
    InventoryAssetTypeCode,
    InventoryAuditAction,
    InventoryAuditLevel,
    InventoryMovement,
    Manufacturer,
    MovementReferenceType,
    MovementType,
    PhysicalCondition,
    Supplier,
    UmaValue,
)
from apps.inventory.models import AssetModel, Contract
from apps.inventory.services.audit_service import (
    AuditRequestContext,
    build_audit_request_context,
    log_inventory_event,
    model_snapshot,
)
from apps.inventory.dtos import (
    AssetRegistrationResultDTO,
    CapitalizationResultDTO,
    CreateAssetIntakeDTO,
    IntakeTransitionResultDTO,
    PatrimonyApprovalDTO,
)
from apps.inventory.services.exceptions import (
    InventoryAuthorizationError,
    InventoryBypassReasonRequired,
    InventoryConfigurationError,
    InventoryConflictError,
    InventoryNotFoundError,
    InventoryStateError,
    InventoryValidationError,
)
from apps.inventory.services.folio_service import (
    generate_inventory_folio,
)


PERMISSION_CREATE = "can_create_asset"
PERMISSION_CREATE_ANY_DEPARTMENT = (
    "can_create_intake_for_any_department"
)
PERMISSION_SUBMIT = "can_submit_asset_intake"
PERMISSION_DEPARTMENT_APPROVE = "can_approve_department_intake"
PERMISSION_PATRIMONY_VALIDATE = "can_validate_patrimony_intake"
PERMISSION_REGISTER_ASSET = "can_register_asset"


def _money(value, *, field_name: str) -> Decimal:
    try:
        normalized = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise InventoryValidationError(
            f"{field_name} debe ser un importe válido."
        ) from exc

    if normalized < 0:
        raise InventoryValidationError(
            f"{field_name} no puede ser negativo."
        )
    return normalized


def _require_text(value, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise InventoryValidationError(
            f"{field_name} es obligatorio."
        )
    return normalized


def _get_active(model, object_id, *, label: str, required=True):
    if object_id is None:
        if required:
            raise InventoryValidationError(f"{label} es obligatorio.")
        return None

    try:
        return model.objects.get(
            pk=object_id,
            is_active=True,
            is_deleted=False,
        )
    except (
        model.DoesNotExist,
        DjangoValidationError,
        ValueError,
        TypeError,
    ) as exc:
        raise InventoryValidationError(
            f"{label} no existe o no está disponible."
        ) from exc


def _get_actor_role(actor_id):
    """Resuelve identidad y rol activo de Inventory una sola vez."""

    try:
        actor = get_user_identity(actor_id)
        role = get_module_role(actor.id)
    except CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc

    if not actor.has_global_bypass and not role:
        raise InventoryAuthorizationError(
            "El usuario no tiene acceso activo a Inventory."
        )

    return actor, role


def _has_permission(actor, role, permission: str) -> bool:
    return bool(
        actor.has_global_bypass
        or (role and role.has_permission(permission))
    )


def _require_any_module_permission(actor_id, *permissions):
    actor, role = _get_actor_role(actor_id)

    if any(
        _has_permission(actor, role, permission)
        for permission in permissions
    ):
        return actor, role

    expected = ", ".join(f"[{value}]" for value in permissions)
    raise InventoryAuthorizationError(
        f"La operación requiere alguno de estos permisos: {expected}."
    )


def _require_patrimony_validator(actor_id):
    try:
        actor = get_user_identity(actor_id)
        role = get_module_role(actor.id)
    except CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc

    if role and role.has_permission(PERMISSION_PATRIMONY_VALIDATE):
        return actor, False

    if actor.has_global_bypass:
        return actor, True

    raise InventoryAuthorizationError(
        f"La operación requiere el permiso "
        f"[{PERMISSION_PATRIMONY_VALIDATE}]."
    )


def _require_asset_registrar(actor_id):
    """Exige el permiso independiente para crear el activo oficial."""

    try:
        actor = get_user_identity(actor_id)
        role = get_module_role(actor.id)
    except CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc

    if role and role.has_permission(PERMISSION_REGISTER_ASSET):
        return actor, False

    if actor.has_global_bypass:
        return actor, True

    raise InventoryAuthorizationError(
        f"La operación requiere el permiso "
        f"[{PERMISSION_REGISTER_ASSET}]."
    )


def _can_operate_intake_for_department(
    *,
    actor,
    role,
    actor_department_id,
    target_department_id,
) -> bool:
    """Comprueba alcance local o permiso de captura transversal."""

    if actor.has_global_bypass:
        return True

    if actor_department_id == target_department_id:
        return True

    return bool(
        role
        and role.has_permission(PERMISSION_CREATE_ANY_DEPARTMENT)
    )


def _context(request_context=None, request=None):
    return request_context or build_audit_request_context(request)


def _request_number(instance_id, created_on=None):
    year = (created_on or timezone.localdate()).year
    return f"ALT-{year}-{instance_id.hex[:12].upper()}"


def _validate_instance(instance):
    try:
        instance.full_clean()
    except DjangoValidationError as exc:
        errors = getattr(exc, "message_dict", {"__all__": exc.messages})
        raise InventoryValidationError(
            "Los datos no superaron la validación del dominio.",
            details={"errors": errors},
        ) from exc


def _lock_intake(intake_request_id):
    try:
        return (
            AssetIntakeRequest.objects
            .select_for_update()
            .select_related(
                "category",
                "expenditure_object",
                "accounting_account",
                "manufacturer",
                "model",
                "supplier",
                "contract",
                "requested_sede",
                "requested_dependencia",
                "requested_area",
                "proposed_custodian",
                "captured_by",
                "capture_dependencia",
                "submitted_by",
            )
            .get(pk=intake_request_id, is_deleted=False)
        )
    except (AssetIntakeRequest.DoesNotExist, ValueError, TypeError) as exc:
        raise InventoryNotFoundError(
            "La solicitud de alta no existe."
        ) from exc


def _create_decision(
    *,
    intake,
    decision_type,
    previous_status,
    resulting_status,
    actor_id,
    context,
    comment="",
    bypass_used=False,
    bypass_reason="",
    payload=None,
):
    actor = get_user_identity(actor_id, include_unavailable=True)
    department = get_department(
        intake.requested_dependencia_id,
        include_unavailable=True,
    )

    decision = AssetIntakeDecision(
        intake_request=intake,
        decision_type=decision_type,
        previous_status=previous_status,
        resulting_status=resulting_status,
        actor_id=actor.id,
        actor_name_snapshot=actor.display_name,
        actor_email_snapshot=actor.normalized_email,
        dependencia_id=department.id,
        dependencia_name_snapshot=department.name,
        dependencia_code_snapshot=department.normalized_code,
        comment=str(comment or "").strip(),
        bypass_used=bypass_used,
        bypass_reason=str(bypass_reason or "").strip(),
        ip_address=context.ip_address,
        user_agent=context.user_agent,
        payload=payload or {},
        occurred_at=timezone.now(),
    )
    _validate_instance(decision)
    decision.save(force_insert=True)
    return decision


def _transition_result(intake, previous_status, decision, context):
    return IntakeTransitionResultDTO(
        intake_request_id=intake.id,
        request_number=intake.request_number,
        previous_status=previous_status,
        current_status=intake.status,
        decision_id=decision.id,
        request_id=context.request_id,
        bypass_used=decision.bypass_used,
    )


@transaction.atomic
def create_intake_draft(
    *,
    data: CreateAssetIntakeDTO,
    actor_id,
    request_context: AuditRequestContext | None = None,
    request=None,
) -> AssetIntakeRequest:
    actor, role = _require_any_module_permission(
        actor_id,
        PERMISSION_CREATE,
    )
    context = _context(request_context, request)

    try:
        org_context = get_user_organizational_context(
            actor.id,
            require_profile=not actor.has_global_bypass,
        )
        department = get_department(data.requested_department_id)
        validate_organizational_context(
            department_id=department.id,
            area_id=data.requested_area_id,
            site_id=data.requested_site_id,
        )
    except CoreDirectoryError as exc:
        raise InventoryValidationError(str(exc)) from exc

    actor_department = org_context.department
    actor_department_id = org_context.department_id
    cross_department = bool(
        actor_department_id
        and actor_department_id != department.id
    )

    if not _can_operate_intake_for_department(
        actor=actor,
        role=role,
        actor_department_id=actor_department_id,
        target_department_id=department.id,
    ):
        raise InventoryAuthorizationError(
            "La solicitud está destinada a otra dependencia y el usuario "
            f"no cuenta con el permiso "
            f"[{PERMISSION_CREATE_ANY_DEPARTMENT}]."
        )

    category = _get_active(
        AssetCategory, data.category_id, label="La categoría"
    )
    expenditure = _get_active(
        ExpenditureObject,
        data.expenditure_object_id,
        label="El objeto del gasto",
        required=False,
    )
    account = _get_active(
        AccountingAccount,
        data.accounting_account_id,
        label="La cuenta contable",
        required=False,
    )

    if expenditure:
        if expenditure.category_id != category.id:
            raise InventoryValidationError(
                "El objeto del gasto pertenece a otra categoría."
            )
        if account is None:
            account = expenditure.accounting_account

    if account and account.category_id not in {None, category.id}:
        raise InventoryValidationError(
            "La cuenta contable pertenece a otra categoría."
        )

    acquisition_cost = _money(
        data.acquisition_cost, field_name="acquisition_cost"
    )
    residual_value = _money(
        data.residual_value, field_name="residual_value"
    )
    if residual_value > acquisition_cost:
        raise InventoryValidationError(
            "El valor residual no puede superar el costo."
        )

    valid_acquisition_types = {v for v, _ in AcquisitionType.choices}
    if data.acquisition_type not in valid_acquisition_types:
        raise InventoryValidationError("Tipo de adquisición inválido.")

    intake_id = uuid4()
    captured_at = timezone.now()
    intake = AssetIntakeRequest(
        id=intake_id,
        request_number=_request_number(intake_id),
        status=AssetIntakeStatus.DRAFT,
        name=_require_text(data.name, field_name="name"),
        description=str(data.description or "").strip(),
        category=category,
        expenditure_object=expenditure,
        accounting_account=account,
        acquisition_type=data.acquisition_type,
        acquisition_date=data.acquisition_date,
        reception_date=data.reception_date,
        acquisition_cost=acquisition_cost,
        residual_value=residual_value,
        manufacturer=_get_active(Manufacturer, data.manufacturer_id, label="El fabricante", required=False),
        model=_get_active(AssetModel, data.model_id, label="El modelo", required=False),
        serial_number=data.serial_number,
        supplier=_get_active(Supplier, data.supplier_id, label="El proveedor", required=False),
        contract=_get_active(Contract, data.contract_id, label="El contrato", required=False),
        requested_sede_id=data.requested_site_id,
        requested_dependencia_id=department.id,
        requested_area_id=data.requested_area_id,
        proposed_custodian_id=data.proposed_custodian_id,
        captured_by_id=actor.id,
        captured_by_id_snapshot=actor.id,
        captured_by_name_snapshot=actor.display_name,
        captured_by_email_snapshot=actor.normalized_email,
        captured_at=captured_at,
        capture_dependencia_id=actor_department_id,
        capture_dependencia_id_snapshot=actor_department_id,
        capture_dependencia_name_snapshot=(
            actor_department.name if actor_department else ""
        ),
        capture_dependencia_code_snapshot=(
            actor_department.normalized_code
            if actor_department else ""
        ),
        requested_dependencia_id_snapshot=department.id,
        requested_dependencia_name_snapshot=department.name,
        requested_dependencia_code_snapshot=department.normalized_code,
        is_cross_department_capture=cross_department,
        submitted_by_id=actor.id,
        notes=str(data.notes or "").strip(),
        extra_attributes=dict(data.extra_attributes or {}),
    )

    if intake.model_id and intake.manufacturer_id:
        if intake.model.manufacturer_id != intake.manufacturer_id:
            raise InventoryValidationError(
                "El modelo no pertenece al fabricante seleccionado."
            )

    if intake.contract_id and intake.supplier_id:
        if intake.contract.supplier_id != intake.supplier_id:
            raise InventoryValidationError(
                "El contrato no pertenece al proveedor seleccionado."
            )

    if data.proposed_custodian_id:
        proposed = get_user_identity(data.proposed_custodian_id)
        proposed_context = get_user_organizational_context(
            proposed.id, require_profile=True
        )
        if proposed_context.department_id != department.id:
            raise InventoryValidationError(
                "El resguardatario propuesto pertenece a otra dependencia."
            )

    _validate_instance(intake)
    intake.save(force_insert=True)

    log_inventory_event(
        action=InventoryAuditAction.CREATE,
        level=InventoryAuditLevel.SUCCESS,
        summary="Solicitud de alta creada en borrador",
        actor_id=actor.id,
        intake_request_id=intake.id,
        target=intake,
        new_value=model_snapshot(intake),
        payload={
            "source_department_id": (
                str(actor_department_id)
                if actor_department_id else None
            ),
            "source_department_name": (
                actor_department.name if actor_department else ""
            ),
            "source_department_code": (
                actor_department.normalized_code
                if actor_department else ""
            ),
            "target_department_id": str(department.id),
            "target_department_name": department.name,
            "target_department_code": department.normalized_code,
            "cross_department_capture": cross_department,
            "captured_at": captured_at.isoformat(),
        },
        request_context=context,
    )
    return intake


@transaction.atomic
def submit_intake(
    *, intake_request_id, actor_id,
    request_context=None, request=None,
):
    actor, role = _require_any_module_permission(
        actor_id,
        PERMISSION_SUBMIT,
    )
    context = _context(request_context, request)
    intake = _lock_intake(intake_request_id)

    if intake.status not in {
        AssetIntakeStatus.DRAFT,
        AssetIntakeStatus.DEPARTMENT_REJECTED,
        AssetIntakeStatus.OBSERVED,
    }:
        raise InventoryStateError(
            "La solicitud no puede enviarse desde su estado actual."
        )

    actor_context = get_user_organizational_context(
        actor.id, require_profile=not actor.has_global_bypass
    )
    is_original_capturer = intake.submitted_by_id == actor.id
    can_operate_target = _can_operate_intake_for_department(
        actor=actor,
        role=role,
        actor_department_id=actor_context.department_id,
        target_department_id=intake.requested_dependencia_id,
    )

    if not is_original_capturer and not can_operate_target:
        raise InventoryAuthorizationError(
            "No puede enviar una solicitud capturada por otro usuario para "
            "una dependencia fuera de su alcance."
        )

    if not intake.acquisition_date or not intake.expenditure_object_id:
        raise InventoryValidationError(
            "Para enviar se requiere fecha de adquisición y objeto del gasto."
        )

    previous = intake.status
    intake.status = AssetIntakeStatus.SUBMITTED
    intake.submitted_by_id = actor.id
    intake.submitted_at = timezone.now()
    intake.department_rejection_reason = ""
    intake.patrimony_observation = ""
    _validate_instance(intake)
    intake.save()

    decision = _create_decision(
        intake=intake,
        decision_type=AssetIntakeDecisionType.SUBMIT,
        previous_status=previous,
        resulting_status=intake.status,
        actor_id=actor.id,
        context=context,
    )
    log_inventory_event(
        action=InventoryAuditAction.SUBMIT,
        summary="Solicitud enviada a aceptación departamental",
        actor_id=actor.id,
        intake_request_id=intake.id,
        target=intake,
        payload={
            "decision_id": decision.id,
            "target_department_id": str(
                intake.requested_dependencia_id
            ),
            "submitted_by_original_capturer": is_original_capturer,
        },
        request_context=context,
    )
    return _transition_result(intake, previous, decision, context)


@transaction.atomic
def decide_department_intake(
    *, intake_request_id, actor_id, approve: bool,
    comment="", bypass_reason="", request_context=None, request=None,
):
    actor, _role = _require_any_module_permission(
        actor_id,
        PERMISSION_DEPARTMENT_APPROVE,
    )
    context = _context(request_context, request)
    intake = _lock_intake(intake_request_id)
    if intake.status != AssetIntakeStatus.SUBMITTED:
        raise InventoryStateError(
            "La solicitud no está pendiente de aceptación departamental."
        )

    authority = user_can_approve_department(
        actor.id, intake.requested_dependencia_id
    )
    if not authority.allowed:
        raise InventoryAuthorizationError(authority.reason)
    if authority.bypass_used and not str(bypass_reason).strip():
        raise InventoryBypassReasonRequired(
            "El bypass departamental requiere justificación."
        )
    if not approve and not str(comment).strip():
        raise InventoryValidationError(
            "El rechazo departamental requiere un motivo."
        )

    previous = intake.status
    now = timezone.now()
    intake.department_approved_by_id = actor.id if approve else None
    intake.department_approved_at = now if approve else None
    intake.department_rejection_reason = "" if approve else str(comment).strip()
    intake.status = (
        AssetIntakeStatus.DEPARTMENT_APPROVED
        if approve else AssetIntakeStatus.DEPARTMENT_REJECTED
    )
    intake.bypass_used = authority.bypass_used
    intake.bypass_reason = str(bypass_reason).strip() if authority.bypass_used else ""
    _validate_instance(intake)
    intake.save()

    decision_type = (
        AssetIntakeDecisionType.DEPARTMENT_APPROVE
        if approve else AssetIntakeDecisionType.DEPARTMENT_REJECT
    )
    decision = _create_decision(
        intake=intake, decision_type=decision_type,
        previous_status=previous, resulting_status=intake.status,
        actor_id=actor.id, context=context, comment=comment,
        bypass_used=authority.bypass_used,
        bypass_reason=bypass_reason,
    )
    log_inventory_event(
        action=InventoryAuditAction.APPROVE if approve else InventoryAuditAction.REJECT,
        level=InventoryAuditLevel.CRITICAL if authority.bypass_used else InventoryAuditLevel.SUCCESS,
        summary="Solicitud aceptada por la dependencia" if approve else "Solicitud rechazada por la dependencia",
        actor_id=actor.id, intake_request_id=intake.id, target=intake,
        reason=comment, payload={"decision_id": decision.id},
        bypass_used=authority.bypass_used,
        bypass_reason=bypass_reason,
        request_context=context,
    )
    return _transition_result(intake, previous, decision, context)


@transaction.atomic
def send_to_patrimony(
    *, intake_request_id, actor_id,
    request_context=None, request=None,
):
    actor, role = _require_any_module_permission(
        actor_id,
        PERMISSION_SUBMIT,
        PERMISSION_DEPARTMENT_APPROVE,
    )
    context = _context(request_context, request)
    intake = _lock_intake(intake_request_id)
    if intake.status != AssetIntakeStatus.DEPARTMENT_APPROVED:
        raise InventoryStateError(
            "La solicitud debe estar aceptada por la dependencia."
        )

    try:
        actor_context = get_user_organizational_context(
            actor.id,
            require_profile=not actor.has_global_bypass,
        )
    except CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc

    is_original_capturer = intake.submitted_by_id == actor.id
    can_operate_target = _can_operate_intake_for_department(
        actor=actor,
        role=role,
        actor_department_id=actor_context.department_id,
        target_department_id=intake.requested_dependencia_id,
    )
    can_approve_target = bool(
        role
        and role.has_permission(PERMISSION_DEPARTMENT_APPROVE)
        and actor_context.department_id
        == intake.requested_dependencia_id
    )

    if not (
        is_original_capturer
        or can_operate_target
        or can_approve_target
    ):
        raise InventoryAuthorizationError(
            "No puede enviar a Patrimonio una solicitud fuera de su alcance."
        )
    previous = intake.status
    intake.status = AssetIntakeStatus.UNDER_PATRIMONY_REVIEW
    _validate_instance(intake)
    intake.save()
    decision = _create_decision(
        intake=intake,
        decision_type=AssetIntakeDecisionType.SEND_TO_PATRIMONY,
        previous_status=previous, resulting_status=intake.status,
        actor_id=actor.id, context=context,
    )
    log_inventory_event(
        action=InventoryAuditAction.SUBMIT,
        summary="Solicitud enviada a validación patrimonial",
        actor_id=actor.id, intake_request_id=intake.id, target=intake,
        payload={
            "decision_id": decision.id,
            "target_department_id": str(
                intake.requested_dependencia_id
            ),
        },
        request_context=context,
    )
    return _transition_result(intake, previous, decision, context)


@transaction.atomic
def observe_patrimony_intake(
    *, intake_request_id, actor_id, observation,
    request_context=None, request=None,
):
    actor, bypass = _require_patrimony_validator(actor_id)
    context = _context(request_context, request)
    intake = _lock_intake(intake_request_id)
    if intake.status != AssetIntakeStatus.UNDER_PATRIMONY_REVIEW:
        raise InventoryStateError("La solicitud no está en revisión patrimonial.")
    normalized = _require_text(observation, field_name="observation")
    previous = intake.status
    intake.status = AssetIntakeStatus.OBSERVED
    intake.patrimony_validated_by_id = actor.id
    intake.patrimony_validated_at = timezone.now()
    intake.patrimony_observation = normalized
    _validate_instance(intake)
    intake.save()
    decision = _create_decision(
        intake=intake,
        decision_type=AssetIntakeDecisionType.PATRIMONY_OBSERVE,
        previous_status=previous, resulting_status=intake.status,
        actor_id=actor.id, context=context, comment=normalized,
    )
    log_inventory_event(
        action=InventoryAuditAction.REJECT,
        level=InventoryAuditLevel.WARNING,
        summary="Patrimonio emitió observaciones a la solicitud",
        actor_id=actor.id, intake_request_id=intake.id, target=intake,
        reason=normalized, payload={"decision_id": decision.id},
        request_context=context,
    )
    return _transition_result(intake, previous, decision, context)


@transaction.atomic
def approve_patrimony_intake(
    *, intake_request_id, actor_id, data: PatrimonyApprovalDTO,
    bypass_reason="", request_context=None, request=None,
):
    actor, bypass = _require_patrimony_validator(actor_id)
    if bypass and not str(bypass_reason).strip():
        raise InventoryBypassReasonRequired(
            "La validación patrimonial por root/manager requiere justificación."
        )
    context = _context(request_context, request)
    intake = _lock_intake(intake_request_id)
    if intake.status != AssetIntakeStatus.UNDER_PATRIMONY_REVIEW:
        raise InventoryStateError("La solicitud no está en revisión patrimonial.")

    expenditure = _get_active(ExpenditureObject, data.expenditure_object_id, label="El objeto del gasto")
    account = _get_active(AccountingAccount, data.accounting_account_id, label="La cuenta contable", required=False) or expenditure.accounting_account
    if expenditure.category_id != intake.category_id:
        raise InventoryValidationError("El objeto del gasto pertenece a otra categoría.")
    if account is None:
        raise InventoryConfigurationError("El objeto del gasto no tiene cuenta contable asociada.")
    if account.category_id not in {None, intake.category_id}:
        raise InventoryValidationError("La cuenta contable pertenece a otra categoría.")
    if data.physical_condition not in {v for v, _ in PhysicalCondition.choices}:
        raise InventoryValidationError("Condición física inválida.")

    previous = intake.status
    intake.expenditure_object = expenditure
    intake.accounting_account = account
    if data.residual_value is not None:
        intake.residual_value = _money(data.residual_value, field_name="residual_value")
    intake.status = AssetIntakeStatus.APPROVED
    intake.patrimony_validated_by_id = actor.id
    intake.patrimony_validated_at = timezone.now()
    intake.patrimony_observation = str(data.observation or "").strip()
    intake.bypass_used = intake.bypass_used or bypass
    if bypass:
        intake.bypass_reason = str(bypass_reason).strip()
    _validate_instance(intake)
    intake.save()

    decision = _create_decision(
        intake=intake,
        decision_type=AssetIntakeDecisionType.PATRIMONY_APPROVE,
        previous_status=previous, resulting_status=intake.status,
        actor_id=actor.id, context=context, comment=data.observation,
        bypass_used=bypass, bypass_reason=bypass_reason,
        payload={
            "physical_condition": data.physical_condition,
            "useful_life_months": data.useful_life_months,
        },
    )
    log_inventory_event(
        action=InventoryAuditAction.APPROVE,
        level=InventoryAuditLevel.CRITICAL if bypass else InventoryAuditLevel.SUCCESS,
        summary="Solicitud aprobada por Control Patrimonial",
        actor_id=actor.id, intake_request_id=intake.id, target=intake,
        payload={"decision_id": decision.id},
        bypass_used=bypass, bypass_reason=bypass_reason,
        request_context=context,
    )
    return _transition_result(intake, previous, decision, context)


def classify_capitalization(intake) -> CapitalizationResultDTO:
    expenditure = intake.expenditure_object
    if not expenditure or not intake.acquisition_date:
        raise InventoryConfigurationError(
            "La clasificación requiere objeto del gasto y fecha de adquisición."
        )

    if intake.category.nature == "IMMOVABLE":
        return CapitalizationResultDTO(
            asset_type_code=InventoryAssetTypeCode.BI,
            control_type=AssetControlType.CAPITALIZED_ASSET,
            is_capitalizable=True,
            uma_value_id=None, uma_value_applied=None,
            uma_multiplier_applied=None,
            capitalization_threshold_amount=None,
            rule_snapshot={"rule": "IMMOVABLE"},
        )

    rule = expenditure.capitalization_rule
    if rule == CapitalizationRule.MANUAL_REVIEW:
        raise InventoryConfigurationError(
            "El objeto del gasto requiere un dictamen contable manual."
        )

    if rule == CapitalizationRule.UMA_THRESHOLD:
        uma = UmaValue.objects.filter(
            effective_from__lte=intake.acquisition_date,
            effective_until__gte=intake.acquisition_date,
            is_active=True, is_deleted=False,
        ).first()
        if not uma:
            raise InventoryConfigurationError(
                "No existe UMA vigente para la fecha de adquisición."
            )
        multiplier = expenditure.uma_multiplier
        threshold = (uma.daily_value * multiplier).quantize(Decimal("0.01"))
        capitalizable = intake.acquisition_cost >= threshold
        return CapitalizationResultDTO(
            asset_type_code=InventoryAssetTypeCode.BM if capitalizable else InventoryAssetTypeCode.BP,
            control_type=AssetControlType.CAPITALIZED_ASSET if capitalizable else AssetControlType.INTERNAL_CONTROL,
            is_capitalizable=capitalizable,
            uma_value_id=uma.id,
            uma_value_applied=uma.daily_value,
            uma_multiplier_applied=multiplier,
            capitalization_threshold_amount=threshold,
            rule_snapshot={
                "rule": rule,
                "uma_year": uma.year,
                "uma_daily_value": str(uma.daily_value),
                "multiplier": str(multiplier),
                "threshold": str(threshold),
            },
        )

    capitalizable = rule == CapitalizationRule.ALWAYS_CAPITALIZE
    return CapitalizationResultDTO(
        asset_type_code=InventoryAssetTypeCode.BM if capitalizable else InventoryAssetTypeCode.BP,
        control_type=AssetControlType.CAPITALIZED_ASSET if capitalizable else AssetControlType.INTERNAL_CONTROL,
        is_capitalizable=capitalizable,
        uma_value_id=None, uma_value_applied=None,
        uma_multiplier_applied=None,
        capitalization_threshold_amount=None,
        rule_snapshot={"rule": rule},
    )


@transaction.atomic
def cancel_intake(
    *, intake_request_id, actor_id, reason,
    request_context=None, request=None,
):
    actor = get_user_identity(actor_id)
    context = _context(request_context, request)
    intake = _lock_intake(intake_request_id)
    normalized_reason = _require_text(reason, field_name="reason")

    if intake.status in {
        AssetIntakeStatus.REGISTERED,
        AssetIntakeStatus.CANCELLED,
    }:
        raise InventoryStateError(
            "La solicitud ya no puede cancelarse."
        )

    is_owner = intake.submitted_by_id == actor.id
    early_status = intake.status in {
        AssetIntakeStatus.DRAFT,
        AssetIntakeStatus.SUBMITTED,
        AssetIntakeStatus.DEPARTMENT_REJECTED,
        AssetIntakeStatus.OBSERVED,
    }
    role = get_module_role(actor.id)
    can_edit = bool(
        role and role.has_permission("can_edit_asset")
    )
    bypass = False

    if not (is_owner and early_status) and not can_edit:
        if actor.has_global_bypass:
            bypass = True
        else:
            raise InventoryAuthorizationError(
                "No cuenta con autoridad para cancelar la solicitud."
            )

    previous = intake.status
    intake.status = AssetIntakeStatus.CANCELLED
    if bypass:
        intake.bypass_used = True
        intake.bypass_reason = normalized_reason
    _validate_instance(intake)
    intake.save()

    decision = _create_decision(
        intake=intake,
        decision_type=AssetIntakeDecisionType.CANCEL,
        previous_status=previous,
        resulting_status=intake.status,
        actor_id=actor.id,
        context=context,
        comment=normalized_reason,
        bypass_used=bypass,
        bypass_reason=normalized_reason if bypass else "",
    )
    log_inventory_event(
        action=InventoryAuditAction.UPDATE,
        level=(
            InventoryAuditLevel.CRITICAL
            if bypass else InventoryAuditLevel.WARNING
        ),
        summary="Solicitud de alta cancelada",
        actor_id=actor.id,
        intake_request_id=intake.id,
        target=intake,
        reason=normalized_reason,
        payload={"decision_id": decision.id},
        bypass_used=bypass,
        bypass_reason=normalized_reason if bypass else "",
        request_context=context,
    )
    return _transition_result(intake, previous, decision, context)


@transaction.atomic
def register_approved_intake(
    *, intake_request_id, actor_id,
    physical_condition=None,
    useful_life_months=None,
    bypass_reason="", request_context=None, request=None,
):
    actor, bypass = _require_asset_registrar(actor_id)
    if bypass and not str(bypass_reason).strip():
        raise InventoryBypassReasonRequired(
            "El registro por root/manager requiere justificación."
        )
    context = _context(request_context, request)
    intake = _lock_intake(intake_request_id)
    if intake.status != AssetIntakeStatus.APPROVED:
        raise InventoryStateError("La solicitud no está aprobada para registro.")
    if hasattr(intake, "registered_asset"):
        raise InventoryConflictError("La solicitud ya generó un activo.")

    approval_decision = (
        intake.decisions
        .filter(
            decision_type=AssetIntakeDecisionType.PATRIMONY_APPROVE,
            is_deleted=False,
        )
        .order_by("-occurred_at")
        .first()
    )
    approved_payload = (
        approval_decision.payload
        if approval_decision else {}
    )
    physical_condition = (
        physical_condition
        or approved_payload.get("physical_condition")
        or PhysicalCondition.GOOD
    )
    useful_life_months = (
        useful_life_months
        or approved_payload.get("useful_life_months")
    )
    if physical_condition not in {
        value for value, _label in PhysicalCondition.choices
    }:
        raise InventoryValidationError(
            "La condición física aprobada no es válida."
        )

    classification = classify_capitalization(intake)
    folio = generate_inventory_folio(
        acquisition_date=intake.acquisition_date,
        expenditure_object_id=intake.expenditure_object_id,
        department_id=intake.requested_dependencia_id,
        asset_type_code=classification.asset_type_code,
        effective_on=timezone.localdate(),
    )
    department = get_department(intake.requested_dependencia_id)
    area_context = (
        get_area_context(intake.requested_area_id)
        if intake.requested_area_id else None
    )
    site_context = (
        get_site(intake.requested_sede_id)
        if intake.requested_sede_id else None
    )
    now = timezone.now()
    asset = Asset(
        source_intake_request=intake,
        official_inventory_number=folio.official_inventory_number,
        internal_inventory_number=folio.internal_inventory_number,
        name=intake.name, description=intake.description,
        category=intake.category,
        expenditure_object=intake.expenditure_object,
        accounting_account=intake.accounting_account,
        control_type=classification.control_type,
        patrimonial_status=AssetPatrimonialStatus.ACTIVE,
        operational_status=AssetOperationalStatus.AVAILABLE,
        physical_condition=physical_condition,
        acquisition_type=intake.acquisition_type,
        acquisition_date=intake.acquisition_date,
        reception_date=intake.reception_date,
        registration_date=timezone.localdate(),
        registered_at=now, registered_by_id=actor.id,
        acquisition_cost=intake.acquisition_cost,
        residual_value=intake.residual_value,
        useful_life_months=useful_life_months or (
            intake.accounting_account.default_useful_life_months
            if intake.accounting_account else None
        ),
        is_capitalizable=classification.is_capitalizable,
        uma_value_id=classification.uma_value_id,
        uma_value_applied=classification.uma_value_applied,
        uma_multiplier_applied=classification.uma_multiplier_applied,
        capitalization_threshold_amount=classification.capitalization_threshold_amount,
        capitalization_rule_snapshot=dict(classification.rule_snapshot),
        manufacturer=intake.manufacturer, model=intake.model,
        serial_number=intake.serial_number,
        supplier=intake.supplier, contract=intake.contract,
        origin_sede=intake.requested_sede,
        origin_dependencia=intake.requested_dependencia,
        origin_area=intake.requested_area,
        origin_dependencia_code_snapshot=department.normalized_code,
        origin_dependencia_name_snapshot=department.name,
        current_sede=intake.requested_sede,
        current_dependencia=intake.requested_dependencia,
        current_area=intake.requested_area,
        current_custodian=None,
        notes=intake.notes,
        extra_attributes=dict(intake.extra_attributes or {}),
    )
    _validate_instance(asset)
    asset.save(force_insert=True)

    performer = get_user_identity(actor.id)
    movement = InventoryMovement(
        asset=asset,
        movement_type=MovementType.REGISTRATION,
        to_dependencia_id=intake.requested_dependencia_id,
        to_dependencia_id_snapshot=intake.requested_dependencia_id,
        to_dependencia_name_snapshot=department.name,
        to_dependencia_code_snapshot=department.normalized_code,
        to_area_id=intake.requested_area_id,
        to_area_id_snapshot=intake.requested_area_id,
        to_area_name_snapshot=(
            area_context.name if area_context else ""
        ),
        to_sede_id=intake.requested_sede_id,
        to_sede_id_snapshot=intake.requested_sede_id,
        to_sede_name_snapshot=(
            site_context.name if site_context else ""
        ),
        condition_after=physical_condition,
        performed_by_id=actor.id,
        performed_by_name_snapshot=performer.display_name,
        performed_by_email_snapshot=performer.normalized_email,
        occurred_at=now, recorded_at=now,
        reason="Registro oficial derivado de solicitud de alta aprobada.",
        reference_folio=intake.request_number,
        reference_type=MovementReferenceType.INTAKE_REQUEST,
        reference_id=intake.id,
        bypass_used=bypass,
        bypass_reason=str(bypass_reason).strip() if bypass else "",
        payload={"folio_sequence_id": str(folio.sequence_id)},
    )
    _validate_instance(movement)
    movement.save(force_insert=True)

    previous = intake.status
    intake.status = AssetIntakeStatus.REGISTERED
    intake.bypass_used = intake.bypass_used or bypass
    if bypass:
        intake.bypass_reason = str(bypass_reason).strip()
    _validate_instance(intake)
    intake.save()
    decision = _create_decision(
        intake=intake,
        decision_type=AssetIntakeDecisionType.REGISTER_ASSET,
        previous_status=previous, resulting_status=intake.status,
        actor_id=actor.id, context=context,
        comment="Activo patrimonial registrado oficialmente.",
        bypass_used=bypass, bypass_reason=bypass_reason,
        payload={
            "asset_id": str(asset.id),
            "official_inventory_number": asset.official_inventory_number,
            "movement_id": str(movement.id),
        },
    )
    log_inventory_event(
        action=InventoryAuditAction.REGISTER,
        level=InventoryAuditLevel.CRITICAL if bypass else InventoryAuditLevel.SUCCESS,
        summary="Activo patrimonial registrado oficialmente",
        actor_id=actor.id, asset_id=asset.id,
        intake_request_id=intake.id, target=asset,
        new_value=model_snapshot(asset),
        payload={"decision_id": decision.id, "movement_id": movement.id},
        bypass_used=bypass, bypass_reason=bypass_reason,
        request_context=context,
    )
    return AssetRegistrationResultDTO(
        intake_request_id=intake.id,
        asset_id=asset.id,
        official_inventory_number=asset.official_inventory_number,
        internal_inventory_number=asset.internal_inventory_number,
        movement_id=movement.id,
        decision_id=decision.id,
        request_id=context.request_id,
        bypass_used=bypass,
    )


__all__ = [
    "approve_patrimony_intake",
    "cancel_intake",
    "classify_capitalization",
    "create_intake_draft",
    "decide_department_intake",
    "observe_patrimony_intake",
    "register_approved_intake",
    "send_to_patrimony",
    "submit_intake",
]

