"""Activación simplificada mediante carga del resguardo firmado."""

from hashlib import sha256

from django.db import transaction
from django.utils import timezone

from apps.inventory.workflows.custody_workflow import (
    uses_simple_custody_workflow,
)
from apps.inventory.models import (
    AssetDocument,
    AssetOperationalStatus,
    CustodyAcceptanceMethod,
    CustodyEventType,
    CustodyStatus,
    DocumentAccessLevel,
    DocumentType,
    DocumentValidationEvent,
    DocumentValidationEventType,
    InventoryAuditAction,
    InventoryDocumentOwnerType,
)
from apps.inventory.services.audit_service import (
    build_audit_request_context,
    log_inventory_event,
    model_snapshot,
)
from apps.inventory.services.custody_service import (
    MANAGE_PERMISSION,
    _event,
    _lock,
    _require_permission,
    _validate_save,
)
from apps.inventory.services.exceptions import (
    InventoryStateError,
    InventoryValidationError,
)


def _file_hash(uploaded_file):
    digest = sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest()


@transaction.atomic
def activate_custody_with_signed_document(
    *,
    custody_id,
    signed_at,
    uploaded_file,
    notes,
    actor_id,
    request=None,
):
    if not uses_simple_custody_workflow():
        raise InventoryStateError(
            "La activación directa sólo está disponible en el flujo simple."
        )
    actor = _require_permission(actor_id, MANAGE_PERMISSION)
    context = build_audit_request_context(request)
    custody = _lock(custody_id)
    if custody.status not in {
        CustodyStatus.DRAFT,
        CustodyStatus.REJECTED,
        CustodyStatus.PENDING_AUTHORIZATION,
        CustodyStatus.PENDING_ACCEPTANCE,
    }:
        raise InventoryStateError(
            "El resguardo no admite la carga de firma desde su estado actual."
        )
    if not uploaded_file:
        raise InventoryValidationError(
            "Seleccione el resguardo firmado."
        )

    previous = custody.status
    document = AssetDocument(
        owner_type=InventoryDocumentOwnerType.CUSTODY_ASSIGNMENT,
        owner_id=custody.id,
        document_type=DocumentType.SIGNED_CUSTODY_RECEIPT,
        title=f"Resguardo firmado {custody.folio}",
        description=str(notes or "").strip(),
        file=uploaded_file,
        original_filename=uploaded_file.name,
        content_type=(
            getattr(uploaded_file, "content_type", "")
            or "application/pdf"
        ),
        file_size=getattr(uploaded_file, "size", None),
        sha256_hash=_file_hash(uploaded_file),
        access_level=DocumentAccessLevel.INTERNAL,
        is_required_evidence=True,
        document_date=signed_at.date(),
        external_reference=custody.folio,
        uploaded_by_id=actor.id,
        uploaded_by_name_snapshot=actor.display_name,
        uploaded_by_email_snapshot=actor.normalized_email,
        metadata={
            "source": "custody_simple_workflow",
            "signed_at": signed_at.isoformat(),
        },
    )
    document.full_clean()
    document.save()
    document_event = DocumentValidationEvent(
        document=document,
        event_type=DocumentValidationEventType.UPLOADED,
        previous_status="",
        resulting_status=document.validation_status,
        actor_id=actor.id,
        actor_name_snapshot=actor.display_name,
        actor_email_snapshot=actor.normalized_email,
        comment="Resguardo firmado agregado al expediente.",
        ip_address=context.ip_address,
        user_agent=context.user_agent,
        payload=model_snapshot(document),
    )
    document_event.full_clean()
    document_event.save()

    custody.status = CustodyStatus.ACTIVE
    custody.authorized_by_id = actor.id
    custody.authorized_at = signed_at
    custody.delivered_by_id = actor.id
    custody.delivered_at = signed_at
    custody.accepted_by_id = custody.assigned_to_id
    custody.accepted_at = signed_at
    custody.acceptance_method = (
        CustodyAcceptanceMethod.HANDWRITTEN_SIGNATURE
    )
    custody.assigned_at = signed_at
    custody.delivery_observations = str(notes or "").strip()
    custody.asset.current_custodian_id = custody.assigned_to_id
    custody.asset.operational_status = AssetOperationalStatus.ASSIGNED
    custody.asset.full_clean()
    custody.asset.save()
    _validate_save(custody)

    _event(
        custody,
        CustodyEventType.ACCEPTED,
        previous,
        actor,
        context,
        comment=(
            "Resguardo firmado adjuntado y responsabilidad activada."
        ),
    )
    log_inventory_event(
        action=InventoryAuditAction.ASSIGN,
        summary="Resguardo firmado y activado",
        actor_id=actor.id,
        asset_id=custody.asset_id,
        target=custody,
        old_value={"status": previous},
        new_value=model_snapshot(custody),
        payload={"document_id": str(document.id)},
        request_context=context,
    )
    return custody, document


__all__ = ["activate_custody_with_signed_document"]
