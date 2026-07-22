"""Flujo transaccional de bajas patrimoniales."""

from uuid import uuid4

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.inventory.dtos import DisposalTransitionResultDTO
from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    Asset,
    AssetDocument,
    AssetOperationalStatus,
    AssetPatrimonialStatus,
    DisposalApproval,
    DisposalApprovalDecision,
    DisposalApprovalStage,
    DisposalReason,
    DisposalRequest,
    DisposalStatus,
    DocumentValidationStatus,
    InventoryAuditAction,
    InventoryDocumentOwnerType,
    InventoryMovement,
    MovementReferenceType,
    MovementType,
)
from apps.inventory.services.audit_service import (
    build_audit_request_context,
    log_inventory_event,
    model_snapshot,
)
from apps.inventory.services.exceptions import (
    InventoryAuthorizationError,
    InventoryConflictError,
    InventoryStateError,
    InventoryValidationError,
)


REQUEST_PERMISSION = "can_request_disposals"
MANAGE_PERMISSION = "can_manage_disposals"
AUTHORIZE_PERMISSION = "can_authorize_disposals"
EXECUTE_PERMISSION = "can_execute_disposals"


def _text(value):
    return str(value or "").strip()


def _actor(actor_id):
    try:
        identity = core_directory.get_user_identity(actor_id)
        role = core_directory.get_module_role(identity.id)
    except core_directory.CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc
    return identity, role


def _has(identity, role, *permissions):
    return identity.has_global_bypass or bool(
        role and any(role.has_permission(permission) for permission in permissions)
    )


def _require(actor_id, *permissions):
    identity, role = _actor(actor_id)
    if _has(identity, role, *permissions):
        return identity, role
    raise InventoryAuthorizationError(
        "No cuenta con permisos para realizar esta operación."
    )


def _lock(disposal_id):
    try:
        return (
            DisposalRequest.objects.select_for_update()
            .select_related("asset")
            .get(pk=disposal_id, is_deleted=False)
        )
    except DisposalRequest.DoesNotExist as exc:
        raise InventoryValidationError("El expediente de baja no existe.") from exc


def _save(instance):
    instance.full_clean()
    try:
        instance.save()
    except IntegrityError as exc:
        raise InventoryConflictError(
            "El activo ya tiene una solicitud de baja abierta."
        ) from exc


def _audit(disposal, actor, action, summary, request, old=None):
    log_inventory_event(
        action=action,
        summary=summary,
        actor_id=actor.id,
        asset_id=disposal.asset_id,
        target=disposal,
        old_value=old or {},
        new_value=model_snapshot(disposal),
        request_context=build_audit_request_context(request),
        bypass_used=disposal.bypass_used,
        bypass_reason=disposal.bypass_reason,
    )


def _result(disposal, previous, *, approval=None, movement=None):
    return DisposalTransitionResultDTO(
        disposal_request_id=disposal.id,
        asset_id=disposal.asset_id,
        previous_status=previous,
        current_status=disposal.status,
        approval_id=approval.id if approval else None,
        movement_id=movement.id if movement else None,
        bypass_used=disposal.bypass_used,
    )


def _required_stages(disposal):
    stages = [DisposalApprovalStage.DEPARTMENT]
    if disposal.technical_report_required or disposal.reason in {
        DisposalReason.OBSOLESCENCE,
        DisposalReason.IRREPARABLE_DAMAGE,
        DisposalReason.DISASTER,
        DisposalReason.SCRAP,
    }:
        stages.append(DisposalApprovalStage.TECHNICAL)
    stages.append(DisposalApprovalStage.PATRIMONY)
    if disposal.reason in {
        DisposalReason.THEFT,
        DisposalReason.LOSS,
        DisposalReason.DONATION,
        DisposalReason.SALE,
        DisposalReason.LEGAL_DISINCORPORATION,
    }:
        stages.append(DisposalApprovalStage.LEGAL)
    if disposal.reason in {
        DisposalReason.SCRAP,
        DisposalReason.DONATION,
        DisposalReason.SALE,
        DisposalReason.DESTRUCTION,
        DisposalReason.LEGAL_DISINCORPORATION,
    }:
        stages.extend(
            [DisposalApprovalStage.INTERNAL_CONTROL, DisposalApprovalStage.COUNCIL]
        )
    stages.append(DisposalApprovalStage.FINAL_AUTHORIZATION)
    return tuple(dict.fromkeys(stages))


def _missing_documents(disposal):
    required = set(disposal.required_document_types_snapshot or [])
    if not required:
        return set()
    approval_ids = disposal.approvals.filter(is_deleted=False).values("id")
    available = set(
        AssetDocument.objects.filter(
            owner_type=InventoryDocumentOwnerType.DISPOSAL_APPROVAL,
            owner_id__in=approval_ids,
            validation_status=DocumentValidationStatus.VALIDATED,
            is_current_version=True,
            is_deleted=False,
        ).values_list("document_type", flat=True)
    )
    return required - available


@transaction.atomic
def create_disposal_request(*, data, actor_id, request=None):
    actor, role = _require(actor_id, REQUEST_PERMISSION, MANAGE_PERMISSION)
    try:
        asset = Asset.objects.select_for_update().get(
            pk=data.asset_id, is_deleted=False
        )
    except Asset.DoesNotExist as exc:
        raise InventoryValidationError("El activo no existe.") from exc
    if asset.patrimonial_status != AssetPatrimonialStatus.ACTIVE:
        raise InventoryStateError("Sólo puede solicitarse la baja de un activo vigente.")
    if not actor.has_global_bypass and not _has(actor, role, MANAGE_PERMISSION):
        context = core_directory.get_user_organizational_context(
            actor.id, require_profile=True
        )
        if context.department_id != asset.current_dependencia_id:
            raise InventoryAuthorizationError(
                "Sólo puede solicitar la baja de bienes de su dependencia."
            )
    source = data.source_reference
    disposal = DisposalRequest(
        folio=f"BAJ-{timezone.localdate():%Y}-{uuid4().hex[:10].upper()}",
        asset=asset,
        reason=data.reason,
        requested_by_id=actor.id,
        requested_by_name_snapshot=actor.display_name,
        requested_by_email_snapshot=actor.normalized_email,
        description=_text(data.description),
        legal_reference=_text(data.legal_reference),
        technical_report_required=data.technical_report_required,
        required_document_types_snapshot=list(data.required_document_types),
        source_app=source.source_app if source else "",
        source_model=source.source_model if source else "",
        source_object_id=source.source_object_id if source else None,
    )
    _save(disposal)
    _audit(disposal, actor, InventoryAuditAction.CREATE, "Solicitud de baja creada", request)
    return disposal


@transaction.atomic
def submit_disposal_request(*, disposal_id, actor_id, data, request=None):
    actor, role = _require(actor_id, REQUEST_PERMISSION, MANAGE_PERMISSION)
    disposal = _lock(disposal_id)
    if (
        disposal.requested_by_id != actor.id
        and not _has(actor, role, MANAGE_PERMISSION)
    ):
        raise InventoryAuthorizationError("Sólo el solicitante o Patrimonio puede enviarla.")
    if disposal.status != DisposalStatus.DRAFT:
        raise InventoryStateError("La solicitud no puede enviarse desde su estado actual.")
    previous = disposal.status
    old = model_snapshot(disposal)
    for stage in _required_stages(disposal):
        DisposalApproval.objects.get_or_create(
            disposal_request=disposal,
            stage=stage,
            defaults={"decision": DisposalApprovalDecision.PENDING},
        )
    disposal.status = (
        DisposalStatus.EVIDENCE_PENDING
        if _missing_documents(disposal)
        else DisposalStatus.TECHNICAL_REVIEW
        if disposal.technical_report_required
        else DisposalStatus.ADMINISTRATIVE_REVIEW
    )
    disposal.asset.patrimonial_status = AssetPatrimonialStatus.PENDING_DISPOSAL
    disposal.asset.full_clean()
    disposal.asset.save()
    _save(disposal)
    _audit(disposal, actor, InventoryAuditAction.SUBMIT, "Solicitud de baja enviada", request, old)
    return _result(disposal, previous)


@transaction.atomic
def resolve_disposal_stage(*, disposal_id, actor_id, data, request=None):
    actor, role = _actor(actor_id)
    disposal = _lock(disposal_id)
    if data.stage == DisposalApprovalStage.DEPARTMENT:
        authority = core_directory.user_can_approve_department(
            actor.id, disposal.asset.current_dependencia_id
        )
        allowed = authority.allowed or _has(actor, role, MANAGE_PERMISSION)
    elif data.stage in {DisposalApprovalStage.TECHNICAL, DisposalApprovalStage.PATRIMONY}:
        allowed = _has(actor, role, MANAGE_PERMISSION, AUTHORIZE_PERMISSION)
    else:
        allowed = _has(actor, role, AUTHORIZE_PERMISSION)
    if not allowed:
        raise InventoryAuthorizationError("No puede resolver esta etapa de la baja.")
    if disposal.status in {DisposalStatus.APPROVED, DisposalStatus.EXECUTED, DisposalStatus.CANCELLED}:
        raise InventoryStateError("El expediente ya no admite resoluciones.")
    try:
        approval = DisposalApproval.objects.select_for_update().get(
            disposal_request=disposal, stage=data.stage
        )
    except DisposalApproval.DoesNotExist as exc:
        raise InventoryValidationError("La etapa no corresponde a este expediente.") from exc
    if approval.decision != DisposalApprovalDecision.PENDING:
        raise InventoryStateError("La etapa ya fue resuelta.")
    decision = data.decision
    comment = _text(data.comment)
    if decision not in {
        DisposalApprovalDecision.APPROVED,
        DisposalApprovalDecision.REJECTED,
        DisposalApprovalDecision.OBSERVED,
        DisposalApprovalDecision.NOT_REQUIRED,
    }:
        raise InventoryValidationError("Seleccione una decisión válida.")
    previous = disposal.status
    old = model_snapshot(disposal)
    approval.decision = decision
    approval.decided_by_id = actor.id
    approval.decided_by_name_snapshot = actor.display_name
    approval.decided_by_email_snapshot = actor.normalized_email
    approval.decided_at = timezone.now()
    approval.comment = comment
    approval.bypass_used = bool(_text(data.bypass_reason))
    approval.bypass_reason = _text(data.bypass_reason)
    if approval.bypass_used and not actor.has_global_bypass:
        raise InventoryAuthorizationError(
            "Sólo el operador raíz puede utilizar una excepción administrativa."
        )
    approval.full_clean()
    approval.save()
    if decision == DisposalApprovalDecision.REJECTED:
        disposal.status = DisposalStatus.REJECTED
        disposal.rejected_by_id = actor.id
        disposal.rejected_at = timezone.now()
        disposal.rejection_reason = comment
        disposal.asset.patrimonial_status = AssetPatrimonialStatus.ACTIVE
        disposal.asset.full_clean()
        disposal.asset.save()
    elif decision == DisposalApprovalDecision.OBSERVED:
        disposal.status = DisposalStatus.EVIDENCE_PENDING
    else:
        unresolved = disposal.approvals.filter(
            decision=DisposalApprovalDecision.PENDING
        ).exclude(stage=DisposalApprovalStage.FINAL_AUTHORIZATION)
        disposal.status = (
            DisposalStatus.EVIDENCE_PENDING
            if _missing_documents(disposal)
            else DisposalStatus.AUTHORIZATION_PENDING
            if not unresolved.exists()
            else DisposalStatus.ADMINISTRATIVE_REVIEW
        )
    _save(disposal)
    _audit(disposal, actor, InventoryAuditAction.APPROVE, "Etapa de baja resuelta", request, old)
    return _result(disposal, previous, approval=approval)


@transaction.atomic
def finalize_disposal_approval(*, disposal_id, actor_id, data, request=None):
    actor, _role = _require(actor_id, AUTHORIZE_PERMISSION)
    disposal = _lock(disposal_id)
    if disposal.status != DisposalStatus.AUTHORIZATION_PENDING:
        raise InventoryStateError("La baja todavía no está lista para autorización final.")
    if _missing_documents(disposal):
        raise InventoryStateError("Faltan documentos obligatorios validados.")
    pending = disposal.approvals.filter(
        decision=DisposalApprovalDecision.PENDING
    ).exclude(stage=DisposalApprovalStage.FINAL_AUTHORIZATION)
    if pending.exists():
        raise InventoryStateError("Existen etapas de revisión pendientes.")
    final = disposal.approvals.get(stage=DisposalApprovalStage.FINAL_AUTHORIZATION)
    previous = disposal.status
    old = model_snapshot(disposal)
    now = timezone.now()
    final.decision = (
        DisposalApprovalDecision.APPROVED
        if data.approve else DisposalApprovalDecision.REJECTED
    )
    final.decided_by_id = actor.id
    final.decided_by_name_snapshot = actor.display_name
    final.decided_by_email_snapshot = actor.normalized_email
    final.decided_at = now
    final.comment = _text(data.comment)
    final.full_clean()
    final.save()
    if data.approve:
        disposal.status = DisposalStatus.APPROVED
        disposal.final_approved_by_id = actor.id
        disposal.final_approved_at = now
    else:
        disposal.status = DisposalStatus.REJECTED
        disposal.rejected_by_id = actor.id
        disposal.rejected_at = now
        disposal.rejection_reason = _text(data.comment)
        disposal.asset.patrimonial_status = AssetPatrimonialStatus.ACTIVE
        disposal.asset.full_clean()
        disposal.asset.save()
    _save(disposal)
    _audit(disposal, actor, InventoryAuditAction.APPROVE if data.approve else InventoryAuditAction.REJECT, "Autorización final de baja", request, old)
    return _result(disposal, previous, approval=final)


@transaction.atomic
def execute_disposal(*, disposal_id, actor_id, data, request=None):
    actor, _role = _require(actor_id, EXECUTE_PERMISSION)
    disposal = _lock(disposal_id)
    if disposal.status != DisposalStatus.APPROVED:
        raise InventoryStateError("Sólo puede ejecutarse una baja aprobada.")
    if data.executed_at > timezone.now():
        raise InventoryValidationError(
            "La fecha efectiva de la baja no puede ser futura."
        )
    previous = disposal.status
    old = model_snapshot(disposal)
    disposal.status = DisposalStatus.EXECUTED
    disposal.executed_by_id = actor.id
    disposal.executed_at = data.executed_at
    disposal.execution_notes = _text(data.execution_notes)
    disposal.asset.patrimonial_status = AssetPatrimonialStatus.DISPOSED
    disposal.asset.operational_status = AssetOperationalStatus.OUT_OF_SERVICE
    disposal.asset.full_clean()
    disposal.asset.save()
    movement = InventoryMovement(
        asset=disposal.asset,
        movement_type=MovementType.DISPOSAL_EXECUTED,
        performed_by_id=actor.id,
        performed_by_name_snapshot=actor.display_name,
        performed_by_email_snapshot=actor.normalized_email,
        occurred_at=data.executed_at,
        recorded_at=timezone.now(),
        reason=disposal.execution_notes,
        reference_folio=disposal.folio,
        reference_type=MovementReferenceType.DISPOSAL_REQUEST,
        reference_id=disposal.id,
        condition_before=disposal.asset.physical_condition,
        condition_after=disposal.asset.physical_condition,
    )
    movement.full_clean()
    movement.save()
    _save(disposal)
    _audit(disposal, actor, InventoryAuditAction.DISPOSAL, "Baja patrimonial ejecutada", request, old)
    return _result(disposal, previous, movement=movement)


@transaction.atomic
def cancel_disposal(*, disposal_id, actor_id, data, request=None):
    actor, role = _require(actor_id, REQUEST_PERMISSION, MANAGE_PERMISSION)
    disposal = _lock(disposal_id)
    if disposal.status in {DisposalStatus.APPROVED, DisposalStatus.EXECUTED, DisposalStatus.CANCELLED}:
        raise InventoryStateError("El expediente ya no puede cancelarse.")
    if disposal.requested_by_id != actor.id and not _has(actor, role, MANAGE_PERMISSION):
        raise InventoryAuthorizationError("Sólo el solicitante o Patrimonio puede cancelarlo.")
    previous = disposal.status
    old = model_snapshot(disposal)
    disposal.status = DisposalStatus.CANCELLED
    disposal.cancelled_by_id = actor.id
    disposal.cancelled_at = timezone.now()
    disposal.cancellation_reason = _text(data.reason)
    disposal.asset.patrimonial_status = AssetPatrimonialStatus.ACTIVE
    disposal.asset.full_clean()
    disposal.asset.save()
    _save(disposal)
    _audit(disposal, actor, InventoryAuditAction.REJECT, "Solicitud de baja cancelada", request, old)
    return _result(disposal, previous)


__all__ = [
    "cancel_disposal",
    "create_disposal_request",
    "execute_disposal",
    "finalize_disposal_approval",
    "resolve_disposal_stage",
    "submit_disposal_request",
]
