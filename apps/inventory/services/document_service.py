"""Carga, versionado y validación de documentos de Inventory."""

from hashlib import sha256

from django.db import transaction
from django.utils import timezone

from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    AssetDocument,
    DisposalApproval,
    DisposalApprovalDecision,
    DisposalStageDocumentRequirement,
    DisposalStatus,
    DocumentRequirementLevel,
    DocumentValidationEvent,
    DocumentValidationEventType,
    DocumentValidationStatus,
    InventoryAuditAction,
    InventoryDocumentOwnerType,
)
from apps.inventory.services.audit_service import (
    build_audit_request_context,
    log_inventory_event,
    model_snapshot,
)
from apps.inventory.services.exceptions import (
    InventoryAuthorizationError,
    InventoryStateError,
    InventoryValidationError,
)


def _text(value):
    return str(value or "").strip()


def _actor(actor_id, permission):
    try:
        actor = core_directory.get_user_identity(actor_id)
        role = core_directory.get_module_role(actor.id)
    except core_directory.CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc
    if not actor.has_global_bypass and not (role and role.has_permission(permission)):
        raise InventoryAuthorizationError("No cuenta con permiso para esta operación documental.")
    return actor


def _hash(uploaded_file):
    digest = sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest()


def _approval(approval_id):
    try:
        return DisposalApproval.objects.select_related(
            "disposal_request", "disposal_request__asset"
        ).get(pk=approval_id, is_deleted=False)
    except DisposalApproval.DoesNotExist as exc:
        raise InventoryValidationError("La etapa de baja no existe.") from exc


def _event(document, event_type, previous, actor, request, comment=""):
    context = build_audit_request_context(request)
    event = DocumentValidationEvent(
        document=document,
        event_type=event_type,
        previous_status=previous,
        resulting_status=document.validation_status,
        actor_id=actor.id,
        actor_name_snapshot=actor.display_name,
        actor_email_snapshot=actor.normalized_email,
        comment=_text(comment),
        ip_address=context.ip_address,
        user_agent=context.user_agent,
        payload=model_snapshot(document),
    )
    event.full_clean()
    event.save()


def _refresh_disposal(disposal):
    """Avanza de evidencia pendiente cuando ya no falta ningún PDF requerido."""
    approvals = disposal.approvals.filter(is_deleted=False)
    for approval in approvals:
        requirements = DisposalStageDocumentRequirement.objects.filter(
            is_active=True,
            is_deleted=False,
            stage=approval.stage,
            requirement_level=DocumentRequirementLevel.REQUIRED,
        ).filter(disposal_reason__in=("", disposal.reason))
        for requirement in requirements:
            exists = AssetDocument.objects.filter(
                owner_type=InventoryDocumentOwnerType.DISPOSAL_APPROVAL,
                owner_id=approval.id,
                document_type=requirement.document_type,
                validation_status=DocumentValidationStatus.VALIDATED,
                is_current_version=True,
                is_deleted=False,
            ).exists()
            if not exists:
                return False
    if disposal.status == DisposalStatus.EVIDENCE_PENDING:
        unresolved = approvals.filter(
            decision=DisposalApprovalDecision.PENDING
        ).exclude(stage="FINAL_AUTHORIZATION")
        disposal.status = (
            DisposalStatus.AUTHORIZATION_PENDING
            if not unresolved.exists()
            else DisposalStatus.ADMINISTRATIVE_REVIEW
        )
        disposal.full_clean()
        disposal.save()
    return True


@transaction.atomic
def upload_disposal_stage_document(*, approval_id, data, actor_id, request=None):
    actor = _actor(actor_id, "can_manage_documents")
    approval = _approval(approval_id)
    if approval.disposal_request.status in {
        DisposalStatus.EXECUTED, DisposalStatus.CANCELLED
    }:
        raise InventoryStateError("El expediente ya no admite documentos.")
    if data.owner_type != InventoryDocumentOwnerType.DISPOSAL_APPROVAL or data.owner_id != approval.id:
        raise InventoryValidationError("El documento no corresponde a la etapa abierta.")
    requirement = DisposalStageDocumentRequirement.objects.filter(
        is_active=True,
        is_deleted=False,
        stage=approval.stage,
        document_type=data.document_type,
        disposal_reason__in=("", approval.disposal_request.reason),
    ).first()
    uploaded = data.file
    document = AssetDocument(
        owner_type=InventoryDocumentOwnerType.DISPOSAL_APPROVAL,
        owner_id=approval.id,
        document_type=data.document_type,
        title=_text(data.title),
        description=_text(data.description),
        file=uploaded,
        original_filename=data.original_filename,
        content_type=data.content_type,
        file_size=getattr(uploaded, "size", None),
        sha256_hash=_hash(uploaded),
        access_level=data.access_level,
        is_required_evidence=bool(
            requirement and requirement.requirement_level == DocumentRequirementLevel.REQUIRED
        ),
        external_reference=_text(data.external_reference),
        uploaded_by_id=actor.id,
        uploaded_by_name_snapshot=actor.display_name,
        uploaded_by_email_snapshot=actor.normalized_email,
        metadata={"disposal_stage": approval.stage},
    )
    document.full_clean()
    document.save()
    _event(document, DocumentValidationEventType.UPLOADED, "", actor, request)
    log_inventory_event(
        action=InventoryAuditAction.UPLOAD,
        summary="Documento agregado a una etapa de baja",
        actor_id=actor.id,
        asset_id=approval.disposal_request.asset_id,
        target=document,
        new_value=model_snapshot(document),
        request_context=build_audit_request_context(request),
    )
    return document


@transaction.atomic
def resolve_inventory_document(*, document_id, data, actor_id, request=None):
    actor = _actor(actor_id, "can_validate_documents")
    try:
        document = AssetDocument.objects.select_for_update().get(
            pk=document_id, is_deleted=False, is_current_version=True
        )
    except AssetDocument.DoesNotExist as exc:
        raise InventoryValidationError("El documento no existe o fue sustituido.") from exc
    if document.validation_status not in {
        DocumentValidationStatus.PENDING,
        DocumentValidationStatus.REJECTED,
    }:
        raise InventoryStateError("El documento no está pendiente de validación.")
    previous = document.validation_status
    document.validated_by_id = actor.id
    document.validated_at = timezone.now()
    document.validation_notes = _text(data.comment)
    if data.approve:
        document.validation_status = DocumentValidationStatus.VALIDATED
        document.rejection_reason = ""
        event_type = DocumentValidationEventType.VALIDATED
    else:
        if not _text(data.comment):
            raise InventoryValidationError("Indique el motivo del rechazo.")
        document.validation_status = DocumentValidationStatus.REJECTED
        document.rejection_reason = _text(data.comment)
        event_type = DocumentValidationEventType.REJECTED
    document.full_clean()
    document.save()
    _event(document, event_type, previous, actor, request, data.comment)
    if document.owner_type == InventoryDocumentOwnerType.DISPOSAL_APPROVAL:
        approval = _approval(document.owner_id)
        _refresh_disposal(approval.disposal_request)
    return document


__all__ = ["resolve_inventory_document", "upload_disposal_stage_document"]
