"""Flujo transaccional de bajas patrimoniales."""

from uuid import uuid4

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.inventory.dtos import DisposalTransitionResultDTO
from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    Asset,
    AssetDocument,
    AssetLoan,
    AssetLoanStatus,
    AssetMovementRequest,
    AssetMovementRequestStatus,
    AssetOperationalStatus,
    AssetPatrimonialStatus,
    CustodyAssignment,
    CustodyStatus,
    DisposalApproval,
    DisposalApprovalDecision,
    DisposalApprovalStage,
    DisposalReason,
    DisposalRequest,
    DisposalStatus,
    DocumentValidationStatus,
    DocumentRequirementLevel,
    DocumentType,
    DisposalStageDocumentRequirement,
    InventoryAuditAction,
    InventoryDocumentOwnerType,
    InventoryMovement,
    MovementReferenceType,
    MovementType,
    PhysicalAuditItem,
    PhysicalAuditStatus,
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
OPEN_LOAN_STATUSES = {
    AssetLoanStatus.REQUESTED,
    AssetLoanStatus.DEPARTMENT_APPROVED,
    AssetLoanStatus.AUTHORIZED,
    AssetLoanStatus.DELIVERED,
    AssetLoanStatus.OVERDUE,
    AssetLoanStatus.RETURN_PENDING,
}
STAGE_PERMISSIONS = {
    DisposalApprovalStage.DEPARTMENT: "can_confirm_department_disposal",
    DisposalApprovalStage.TECHNICAL: "can_review_technical_disposal",
    DisposalApprovalStage.PATRIMONY: "can_review_patrimony_disposal",
    DisposalApprovalStage.LEGAL: "can_review_legal_disposal",
    DisposalApprovalStage.INTERNAL_CONTROL: "can_review_internal_control_disposal",
    DisposalApprovalStage.COUNCIL: "can_record_council_disposal",
    DisposalApprovalStage.FINAL_AUTHORIZATION: "can_finalize_disposal",
}


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


def _snapshot_requirements(disposal):
    """Congela el catálogo aplicable sin romper expedientes históricos."""
    rows = DisposalStageDocumentRequirement.objects.filter(
        is_active=True,
        is_deleted=False,
        stage__in=_required_stages(disposal),
        disposal_reason__in=("", disposal.reason),
    ).order_by("stage", "document_type")
    snapshot = [
        {
            "stage": row.stage,
            "document_type": row.document_type,
            "requirement_level": row.requirement_level,
            "instructions": row.instructions,
        }
        for row in rows
    ]
    defaults = (
        (
            DisposalApprovalStage.DEPARTMENT,
            DocumentType.DISPOSAL_REQUEST,
            "Oficio o solicitud de baja emitida por la dependencia responsable.",
        ),
        (
            DisposalApprovalStage.TECHNICAL,
            DocumentType.TECHNICAL_REPORT_REQUEST,
            "Oficio de Control Patrimonial solicitando el dictamen a Innovación/TI.",
        ),
        (
            DisposalApprovalStage.TECHNICAL,
            DocumentType.TECHNICAL_REPORT,
            "Dictamen técnico de baja emitido y firmado por Innovación/TI.",
        ),
        (
            DisposalApprovalStage.PATRIMONY,
            DocumentType.ACCOUNTING_DISPOSAL_REQUEST,
            "Oficio de Control Patrimonial solicitando la baja contable.",
        ),
        (
            DisposalApprovalStage.FINAL_AUTHORIZATION,
            DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION,
            "Constancia u oficio de Contabilidad con número y fecha de baja.",
        ),
    )
    for stage, document_type, instructions in reversed(defaults):
        if stage not in _required_stages(disposal):
            continue
        if not any(
            item["stage"] == stage and item["document_type"] == document_type
            for item in snapshot
        ):
            snapshot.insert(0, {
                "stage": stage,
                "document_type": document_type,
                "requirement_level": DocumentRequirementLevel.REQUIRED,
                "instructions": instructions,
            })
    return snapshot or list(disposal.required_document_types_snapshot or [])


_LEGACY_DOCUMENT_STAGES = {
    DocumentType.DISPOSAL_REQUEST: DisposalApprovalStage.DEPARTMENT,
    DocumentType.TECHNICAL_REPORT: DisposalApprovalStage.TECHNICAL,
    DocumentType.TECHNICAL_REPORT_REQUEST: DisposalApprovalStage.TECHNICAL,
    DocumentType.POLICE_REPORT: DisposalApprovalStage.LEGAL,
    DocumentType.COUNCIL_MINUTES: DisposalApprovalStage.COUNCIL,
    DocumentType.DISINCORPORATION_AUTHORIZATION: DisposalApprovalStage.FINAL_AUTHORIZATION,
    DocumentType.ACCOUNTING_DISPOSAL_REQUEST: DisposalApprovalStage.PATRIMONY,
    DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION: DisposalApprovalStage.FINAL_AUTHORIZATION,
}

_ALWAYS_REQUIRED_STAGE_DOCUMENTS = {
    DisposalApprovalStage.DEPARTMENT: DocumentType.DISPOSAL_REQUEST,
}


def _snapshot_document_pairs(disposal, *, required_only=False):
    pairs = set()
    for item in getattr(disposal, "required_document_types_snapshot", None) or []:
        if isinstance(item, dict):
            if required_only and item.get(
                "requirement_level", DocumentRequirementLevel.REQUIRED
            ) != DocumentRequirementLevel.REQUIRED:
                continue
            item_stage = item.get("stage")
            document_type = item.get("document_type")
        else:
            document_type = item
            item_stage = _LEGACY_DOCUMENT_STAGES.get(document_type)
        if item_stage and document_type:
            pairs.add((item_stage, document_type))
    # Compatibilidad para solicitudes enviadas antes de que estos documentos
    # administrativos formaran parte del snapshot por etapa.
    for stage, document_type in _ALWAYS_REQUIRED_STAGE_DOCUMENTS.items():
        pairs.add((stage, document_type))
    # Compatibilidad con expedientes creados cuando el flujo ya incluía la
    # etapa técnica, pero el snapshot todavía no conservaba su requisito. Si
    # la etapa existe, el dictamen no puede quedar sin tipo documental ni
    # acción de carga.
    technical_stage_required = bool(
        getattr(disposal, "technical_report_required", False)
        or getattr(disposal, "reason", None) in {
            DisposalReason.OBSOLESCENCE,
            DisposalReason.IRREPARABLE_DAMAGE,
            DisposalReason.DISASTER,
            DisposalReason.SCRAP,
        }
        or any(stage == DisposalApprovalStage.TECHNICAL for stage, _ in pairs)
    )
    if technical_stage_required:
        pairs.add((
            DisposalApprovalStage.TECHNICAL,
            DocumentType.TECHNICAL_REPORT,
        ))
        pairs.add((
            DisposalApprovalStage.TECHNICAL,
            DocumentType.TECHNICAL_REPORT_REQUEST,
        ))
    if not any(stage == DisposalApprovalStage.PATRIMONY for stage, _ in pairs):
        pairs.add((
            DisposalApprovalStage.PATRIMONY,
            DocumentType.ACCOUNTING_DISPOSAL_REQUEST,
        ))
    if not any(
        stage == DisposalApprovalStage.FINAL_AUTHORIZATION for stage, _ in pairs
    ):
        pairs.add((
            DisposalApprovalStage.FINAL_AUTHORIZATION,
            DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION,
        ))
    return pairs


def _requirement_pairs(disposal, *, stage=None):
    pairs = _snapshot_document_pairs(disposal, required_only=True)
    return {
        (item_stage, document_type)
        for item_stage, document_type in pairs
        if not stage or item_stage == stage
    }


def disposal_stage_document_types(disposal, stage):
    """Tipos exactos permitidos por el snapshot inmutable de la etapa."""
    return tuple(sorted(
        document_type
        for item_stage, document_type in _snapshot_document_pairs(disposal)
        if item_stage == stage
    ))


def _missing_documents(disposal, *, stage=None):
    missing = set()
    for required_stage, document_type in _requirement_pairs(disposal, stage=stage):
        approvals = disposal.approvals.filter(is_deleted=False)
        if required_stage:
            approvals = approvals.filter(stage=required_stage)
        exists = AssetDocument.objects.filter(
            owner_type=InventoryDocumentOwnerType.DISPOSAL_APPROVAL,
            owner_id__in=approvals.values("id"),
            document_type=document_type,
            validation_status=DocumentValidationStatus.VALIDATED,
            is_current_version=True,
            is_deleted=False,
        ).exists()
        if not exists:
            missing.add((required_stage, document_type))
    return missing


def _current_approval(disposal):
    approvals = {
        approval.stage: approval
        for approval in disposal.approvals.filter(is_deleted=False)
    }
    for stage in _required_stages(disposal):
        approval = approvals.get(stage)
        if approval and approval.decision in {
            DisposalApprovalDecision.PENDING,
            DisposalApprovalDecision.OBSERVED,
        }:
            return approval
    return None


def _status_for_current_stage(disposal):
    current = _current_approval(disposal)
    if current is None or current.stage == DisposalApprovalStage.FINAL_AUTHORIZATION:
        return DisposalStatus.AUTHORIZATION_PENDING
    if current.stage == DisposalApprovalStage.DEPARTMENT:
        return DisposalStatus.SUBMITTED
    if _missing_documents(disposal, stage=current.stage):
        return DisposalStatus.EVIDENCE_PENDING
    if current.stage == DisposalApprovalStage.TECHNICAL:
        return DisposalStatus.TECHNICAL_REVIEW
    return DisposalStatus.ADMINISTRATIVE_REVIEW


def _can_resolve_stage(actor, role, disposal, stage):
    permission = STAGE_PERMISSIONS[stage]
    if stage == DisposalApprovalStage.DEPARTMENT:
        authority = core_directory.user_can_approve_department(
            actor.id, disposal.asset.current_dependencia_id
        )
        return actor.has_global_bypass or (
            authority.allowed and _has(actor, role, permission)
        )
    return _has(actor, role, permission)


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
    blocking_loan = (
        AssetLoan.objects.select_for_update()
        .filter(
            asset_id=disposal.asset_id,
            status__in=OPEN_LOAN_STATUSES,
            is_deleted=False,
        )
        .order_by("-requested_at")
        .first()
    )
    if blocking_loan:
        raise InventoryStateError(
            f"El bien tiene el préstamo {blocking_loan.folio} vigente o en "
            "proceso. Registre y confirme su devolución antes de enviar la baja."
        )
    previous = disposal.status
    old = model_snapshot(disposal)
    for stage in _required_stages(disposal):
        DisposalApproval.objects.get_or_create(
            disposal_request=disposal,
            stage=stage,
            defaults={"decision": DisposalApprovalDecision.PENDING},
        )
    disposal.required_document_types_snapshot = _snapshot_requirements(disposal)
    disposal.status = DisposalStatus.SUBMITTED
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
        raise InventoryStateError(
            "La etapa de la dependencia se confirma automáticamente cuando Patrimonio valida su oficio."
        )
    if not _can_resolve_stage(actor, role, disposal, data.stage):
        raise InventoryAuthorizationError("No puede resolver esta etapa de la baja.")
    if disposal.status in {DisposalStatus.APPROVED, DisposalStatus.EXECUTED, DisposalStatus.CANCELLED}:
        raise InventoryStateError("El expediente ya no admite resoluciones.")
    try:
        approval = DisposalApproval.objects.select_for_update().get(
            disposal_request=disposal, stage=data.stage
        )
    except DisposalApproval.DoesNotExist as exc:
        raise InventoryValidationError("La etapa no corresponde a este expediente.") from exc
    current = _current_approval(disposal)
    if current is None or current.id != approval.id:
        raise InventoryStateError("Debe resolver primero la etapa anterior del expediente.")
    decision = data.decision
    comment = _text(data.comment)
    if decision not in {
        DisposalApprovalDecision.APPROVED,
        DisposalApprovalDecision.REJECTED,
        DisposalApprovalDecision.OBSERVED,
        DisposalApprovalDecision.NOT_REQUIRED,
    }:
        raise InventoryValidationError("Seleccione una decisión válida.")
    bypass_reason = _text(data.bypass_reason)
    if decision == DisposalApprovalDecision.NOT_REQUIRED and not actor.has_global_bypass:
        raise InventoryAuthorizationError(
            "Sólo el operador raíz puede declarar una etapa como no aplicable."
        )
    if decision == DisposalApprovalDecision.NOT_REQUIRED and not bypass_reason:
        raise InventoryValidationError("Indique el motivo de la excepción administrativa.")
    if decision == DisposalApprovalDecision.APPROVED and _missing_documents(
        disposal, stage=approval.stage
    ):
        raise InventoryStateError("Faltan documentos obligatorios validados en esta etapa.")
    previous = disposal.status
    old = model_snapshot(disposal)
    history = list((approval.payload or {}).get("decision_history", []))
    if approval.decision != DisposalApprovalDecision.PENDING:
        history.append({
            "decision": approval.decision,
            "comment": approval.comment,
            "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
            "decided_by_id": str(approval.decided_by_id) if approval.decided_by_id else None,
        })
    approval.payload = {**(approval.payload or {}), "decision_history": history}
    approval.decision = decision
    approval.decided_by_id = actor.id
    approval.decided_by_name_snapshot = actor.display_name
    approval.decided_by_email_snapshot = actor.normalized_email
    approval.decided_at = timezone.now()
    approval.comment = comment
    approval.bypass_used = bool(bypass_reason)
    approval.bypass_reason = bypass_reason
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
        disposal.status = _status_for_current_stage(disposal)
    _save(disposal)
    _audit(disposal, actor, InventoryAuditAction.APPROVE, "Etapa de baja resuelta", request, old)
    return _result(disposal, previous, approval=approval)


@transaction.atomic
def finalize_disposal_approval(*, disposal_id, actor_id, data, request=None):
    actor, _role = _require(actor_id, "can_finalize_disposal", AUTHORIZE_PERMISSION)
    disposal = _lock(disposal_id)
    if disposal.status != DisposalStatus.AUTHORIZATION_PENDING:
        raise InventoryStateError("La baja todavía no está lista para autorización final.")
    if _missing_documents(disposal):
        raise InventoryStateError("Faltan documentos obligatorios validados.")
    pending = disposal.approvals.filter(
        decision__in=(DisposalApprovalDecision.PENDING, DisposalApprovalDecision.OBSERVED)
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
    if (
        DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION
        in disposal_stage_document_types(
            disposal, DisposalApprovalStage.FINAL_AUTHORIZATION
        )
        and (
            not disposal.accounting_disposal_number
            or not disposal.accounting_disposal_date
        )
    ):
        raise InventoryStateError(
            "Debe integrar y validar el número, fecha y constancia de baja contable."
        )
    if data.executed_at > timezone.now():
        raise InventoryValidationError(
            "La fecha efectiva de la baja no puede ser futura."
        )
    if CustodyAssignment.objects.filter(
        asset_id=disposal.asset_id,
        status__in=(
            CustodyStatus.PENDING_AUTHORIZATION,
            CustodyStatus.PENDING_ACCEPTANCE,
            CustodyStatus.ACTIVE,
            CustodyStatus.RETURN_PENDING,
        ),
        is_deleted=False,
    ).exists():
        raise InventoryStateError(
            "La baja está autorizada, pero el bien conserva un resguardo "
            "vigente. Prepare su constancia de retiro e integre y valide el "
            "acuse firmado antes de ejecutar la baja."
        )
    if AssetLoan.objects.filter(
        asset_id=disposal.asset_id,
        status__in=(
            AssetLoanStatus.REQUESTED,
            AssetLoanStatus.DEPARTMENT_APPROVED,
            AssetLoanStatus.AUTHORIZED,
            AssetLoanStatus.DELIVERED,
            AssetLoanStatus.OVERDUE,
            AssetLoanStatus.RETURN_PENDING,
        ),
        is_deleted=False,
    ).exists():
        raise InventoryStateError("Debe cerrar el préstamo vigente antes de ejecutar la baja.")
    if AssetMovementRequest.objects.filter(
        asset_id=disposal.asset_id,
        status__in=(
            AssetMovementRequestStatus.PENDING_ORIGIN_APPROVAL,
            AssetMovementRequestStatus.PENDING_DESTINATION_ACCEPTANCE,
            AssetMovementRequestStatus.PENDING_PATRIMONY_EXECUTION,
        ),
        is_deleted=False,
    ).exists():
        raise InventoryStateError("El bien tiene un movimiento pendiente por concluir.")
    if PhysicalAuditItem.objects.filter(
        asset_id=disposal.asset_id,
        session__status__in=(
            PhysicalAuditStatus.FROZEN,
            PhysicalAuditStatus.IN_PROGRESS,
            PhysicalAuditStatus.RECONCILIATION,
        ),
        is_deleted=False,
    ).exists():
        raise InventoryStateError("El bien forma parte de una auditoría física abierta.")
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
    if disposal.status in {
        DisposalStatus.APPROVED,
        DisposalStatus.REJECTED,
        DisposalStatus.EXECUTED,
        DisposalStatus.CANCELLED,
    }:
        raise InventoryStateError("El expediente ya no puede cancelarse.")
    manages = _has(actor, role, MANAGE_PERMISSION)
    if disposal.requested_by_id != actor.id and not manages:
        raise InventoryAuthorizationError("Sólo el solicitante o Patrimonio puede cancelarlo.")
    if not manages and disposal.status not in {
        DisposalStatus.DRAFT,
        DisposalStatus.SUBMITTED,
    }:
        raise InventoryStateError(
            "La dependencia ya confirmó la solicitud; sólo Patrimonio puede cancelar el expediente."
        )
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
    "_current_approval",
    "_missing_documents",
    "_status_for_current_stage",
    "disposal_stage_document_types",
]
