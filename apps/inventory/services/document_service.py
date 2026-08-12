"""Carga, versionado y validación de documentos de Inventory."""

from datetime import date
from hashlib import sha256

from django.db import transaction
from django.utils import timezone

from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    AssetDocument,
    Asset,
    AssetIntakeRequest,
    AssetLoan,
    AssetMovementRequest,
    CustodyAssignment,
    CustodyDocument,
    CustodyDocumentType,
    DisposalRequest,
    DisposalApproval,
    DisposalApprovalDecision,
    DisposalStageDocumentRequirement,
    DisposalStatus,
    DocumentRequirementLevel,
    DocumentValidationEvent,
    DocumentValidationEventType,
    DocumentValidationStatus,
    DocumentType,
    InventoryAuditAction,
    InventoryDocumentOwnerType,
    InventoryMovement,
    PhysicalAuditSession,
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


def _actor(actor_id, *permissions):
    try:
        actor = core_directory.get_user_identity(actor_id)
        role = core_directory.get_module_role(actor.id)
    except core_directory.CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc
    if not actor.has_global_bypass and not (
        role and any(role.has_permission(permission) for permission in permissions)
    ):
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


def helpdesk_disposal_workflow_available():
    """Indica si Helpdesk puede asumir la integración documental técnica."""
    try:
        from apps.shared.module_sdk.services import get_module_runtime_status

        status = get_module_runtime_status("helpdesk")
    except Exception:
        # Inventory debe seguir operando aun cuando el satélite opcional no
        # exista o su registro todavía no haya sido aprovisionado.
        return False
    return bool(status and status.available)


def disposal_stage_document_upload_permissions(
    stage,
    *,
    document_type=None,
    helpdesk_available=None,
):
    """Permisos de carga; Patrimonio actúa como custodio, no como emisor."""
    if (
        stage == "TECHNICAL"
        and document_type == DocumentType.TECHNICAL_REPORT_REQUEST
    ):
        return ("can_review_patrimony_disposal",)
    if (
        stage == "PATRIMONY"
        and document_type == DocumentType.ACCOUNTING_DISPOSAL_REQUEST
    ):
        return ("can_review_patrimony_disposal",)
    if (
        stage == "FINAL_AUTHORIZATION"
        and document_type == DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION
    ):
        return ("can_finalize_disposal", "can_review_patrimony_disposal")
    permissions = {
        "DEPARTMENT": ("can_confirm_department_disposal",),
        "TECHNICAL": ("can_review_technical_disposal",),
        "PATRIMONY": ("can_review_patrimony_disposal",),
        "LEGAL": ("can_review_legal_disposal",),
        "INTERNAL_CONTROL": ("can_review_internal_control_disposal",),
        "COUNCIL": ("can_record_council_disposal",),
        "FINAL_AUTHORIZATION": ("can_finalize_disposal",),
    }.get(stage, ())
    if stage == "TECHNICAL":
        if helpdesk_available is None:
            helpdesk_available = helpdesk_disposal_workflow_available()
        if not helpdesk_available:
            permissions += ("can_review_patrimony_disposal",)
    elif stage == "FINAL_AUTHORIZATION":
        permissions += ("can_review_patrimony_disposal",)
    return permissions


_DOCUMENT_OWNER_MODELS = {
    InventoryDocumentOwnerType.ASSET: Asset,
    InventoryDocumentOwnerType.INTAKE_REQUEST: AssetIntakeRequest,
    InventoryDocumentOwnerType.CUSTODY_ASSIGNMENT: CustodyAssignment,
    InventoryDocumentOwnerType.CUSTODY_DOCUMENT: CustodyDocument,
    InventoryDocumentOwnerType.MOVEMENT: InventoryMovement,
    InventoryDocumentOwnerType.MOVEMENT_REQUEST: AssetMovementRequest,
    InventoryDocumentOwnerType.LOAN: AssetLoan,
    InventoryDocumentOwnerType.DISPOSAL_REQUEST: DisposalRequest,
    InventoryDocumentOwnerType.PHYSICAL_AUDIT_SESSION: PhysicalAuditSession,
}


def _document_owner(owner_type, owner_id):
    model = _DOCUMENT_OWNER_MODELS.get(owner_type)
    if model is None:
        raise InventoryValidationError("Este tipo de expediente no admite carga documental general.")
    try:
        return model.objects.get(pk=owner_id, is_deleted=False)
    except model.DoesNotExist as exc:
        raise InventoryValidationError("El expediente propietario no existe o no está disponible.") from exc


def _owner_asset_id(owner_type, owner):
    if owner_type == InventoryDocumentOwnerType.ASSET:
        return owner.id
    if hasattr(owner, "asset_id"):
        return owner.asset_id
    if owner_type == InventoryDocumentOwnerType.INTAKE_REQUEST:
        return getattr(getattr(owner, "registered_asset", None), "id", None)
    return None


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


def _refresh_disposal(disposal, *, validator=None, document=None, request=None):
    """Reconcilia, en orden, las etapas cubiertas por documentos validados.

    Una evidencia puede validarse antes de que la etapa previa quede completa.
    Cuando finalmente se integra el documento faltante, este recorrido retoma
    todas las etapas consecutivas ya documentadas sin pedir una segunda
    validación ni un clic adicional.
    """
    from apps.inventory.services.disposal_service import (
        _current_approval,
        _missing_documents,
        _status_for_current_stage,
    )

    closing_document_types = {
        "TECHNICAL": DocumentType.TECHNICAL_REPORT,
        "PATRIMONY": DocumentType.ACCOUNTING_DISPOSAL_REQUEST,
        "FINAL_AUTHORIZATION": DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION,
    }
    changed = False

    # El límite evita que una configuración de etapas defectuosa produzca un
    # ciclo infinito. En la práctica se recorrerán sólo las aprobaciones del
    # expediente.
    for _ in range(16):
        current = _current_approval(disposal)
        if not current or _missing_documents(disposal, stage=current.stage):
            break

        now = timezone.now()
        if current.stage == "DEPARTMENT":
            current.decision = DisposalApprovalDecision.APPROVED
            current.decided_by_id = disposal.requested_by_id
            current.decided_by_name_snapshot = disposal.requested_by_name_snapshot
            current.decided_by_email_snapshot = disposal.requested_by_email_snapshot
            current.decided_at = now
            current.comment = (
                "Confirmación automática: solicitud enviada por la dependencia "
                "y oficio validado por Patrimonio."
            )
            current.payload = {
                **(current.payload or {}),
                "automatic_resolution": True,
                "trigger": "validated_department_disposal_request",
                "validated_by_id": str(validator.id) if validator else None,
                "validated_at": now.isoformat(),
            }
            current.full_clean()
            current.save()
            changed = True
            if validator:
                log_inventory_event(
                    action=InventoryAuditAction.APPROVE,
                    summary=(
                        "Etapa de la dependencia confirmada automáticamente "
                        "al validar su oficio de baja"
                    ),
                    actor_id=validator.id,
                    asset_id=disposal.asset_id,
                    target=current,
                    new_value=model_snapshot(current),
                    request_context=build_audit_request_context(request),
                )
            continue

        closing_type = closing_document_types.get(current.stage)
        if not closing_type:
            # Las etapas jurídica, OIC o Cabildo conservan su resolución
            # explícita cuando estén habilitadas por la política municipal.
            break

        closing_document = (
            AssetDocument.objects.filter(
                owner_type=InventoryDocumentOwnerType.DISPOSAL_APPROVAL,
                owner_id=current.id,
                document_type=closing_type,
                validation_status=DocumentValidationStatus.VALIDATED,
                is_current_version=True,
                is_deleted=False,
            )
            .order_by("-validated_at", "-uploaded_at")
            .first()
        )
        if not closing_document:
            break

        metadata = closing_document.metadata or {}
        current.decision = DisposalApprovalDecision.APPROVED
        current.decided_by_id = validator.id if validator else None
        current.decided_by_name_snapshot = (
            validator.display_name if validator else "Control Patrimonial"
        )
        current.decided_by_email_snapshot = (
            validator.normalized_email if validator else ""
        )
        current.decided_at = now
        current.comment = (
            "Etapa confirmada automáticamente mediante su documento formal "
            "validado."
        )
        current.payload = {
            **(current.payload or {}),
            "automatic_resolution": True,
            "trigger": "validated_custodial_document",
            "document_id": str(closing_document.id),
            "issuing_authority": metadata.get("issuing_authority", ""),
            "issuing_official_role": metadata.get(
                "issuing_official_role", ""
            ),
            "document_date": metadata.get("document_date", ""),
            "validated_by_id": str(validator.id) if validator else None,
            "validated_at": now.isoformat(),
        }
        current.full_clean()
        current.save()
        changed = True
        if current.stage == "FINAL_AUTHORIZATION":
            accounting_date = metadata.get("document_date")
            try:
                parsed_accounting_date = (
                    date.fromisoformat(accounting_date)
                    if accounting_date
                    else None
                )
            except (TypeError, ValueError):
                parsed_accounting_date = None
            disposal.status = DisposalStatus.APPROVED
            disposal.final_approved_by_id = validator.id if validator else None
            disposal.final_approved_at = now
            disposal.accounting_disposal_number = closing_document.external_reference
            disposal.accounting_disposal_date = parsed_accounting_date
            disposal.full_clean()
            disposal.save()
        if validator:
            log_inventory_event(
                action=InventoryAuditAction.APPROVE,
                summary=(
                    "Etapa de baja confirmada mediante documento formal validado"
                ),
                actor_id=validator.id,
                asset_id=disposal.asset_id,
                target=current,
                new_value=model_snapshot(current),
                request_context=build_audit_request_context(request),
            )
        if current.stage == "FINAL_AUTHORIZATION":
            break
    if disposal.status not in {
        DisposalStatus.REJECTED,
        DisposalStatus.APPROVED,
        DisposalStatus.EXECUTED,
        DisposalStatus.CANCELLED,
    }:
        disposal.status = _status_for_current_stage(disposal)
        disposal.full_clean()
        disposal.save()
    return changed


@transaction.atomic
def upload_disposal_stage_document(*, approval_id, data, actor_id, request=None):
    approval = _approval(approval_id)
    from apps.inventory.services.disposal_service import (
        _missing_documents,
        disposal_stage_document_types,
    )

    allowed_document_types = disposal_stage_document_types(
        approval.disposal_request,
        approval.stage,
    )
    if data.document_type not in allowed_document_types:
        raise InventoryValidationError(
            "El tipo de documento no corresponde a esta etapa de la baja."
        )
    stage_permissions = disposal_stage_document_upload_permissions(
        approval.stage,
        document_type=data.document_type,
    )
    if not stage_permissions:
        raise InventoryAuthorizationError(
            "La etapa no tiene un responsable documental configurado."
        )
    actor = _actor(actor_id, *stage_permissions)
    actor_role = core_directory.get_module_role(actor.id)
    native_stage_permission = {
        "TECHNICAL": "can_review_technical_disposal",
        "FINAL_AUTHORIZATION": "can_finalize_disposal",
    }.get(approval.stage)
    custodial_document_types = {
        DocumentType.TECHNICAL_REPORT,
        DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION,
    }
    integrated_by_patrimony = bool(
        data.document_type in custodial_document_types
        and actor_role
        and actor_role.has_permission("can_review_patrimony_disposal")
        and not actor_role.has_permission(native_stage_permission)
        and not actor.has_global_bypass
    )
    if approval.disposal_request.status in {
        DisposalStatus.EXECUTED, DisposalStatus.CANCELLED
    }:
        raise InventoryStateError("El expediente ya no admite documentos.")
    if data.owner_type != InventoryDocumentOwnerType.DISPOSAL_APPROVAL or data.owner_id != approval.id:
        raise InventoryValidationError("El documento no corresponde a la etapa abierta.")
    missing_types = {
        document_type
        for _stage, document_type in _missing_documents(
            approval.disposal_request,
            stage=approval.stage,
        )
    }
    if data.document_type not in missing_types:
        raise InventoryStateError(
            "El documento obligatorio de esta etapa ya fue integrado y validado."
        )
    replaced = (
        AssetDocument.objects.select_for_update()
        .filter(
            owner_type=InventoryDocumentOwnerType.DISPOSAL_APPROVAL,
            owner_id=approval.id,
            document_type=data.document_type,
            is_current_version=True,
            is_deleted=False,
        )
        .order_by("-version_number", "-uploaded_at")
        .first()
    )
    if replaced and replaced.validation_status != DocumentValidationStatus.REJECTED:
        raise InventoryStateError(
            "Ya existe un documento vigente pendiente de validación para esta etapa."
        )
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
            not requirement
            or requirement.requirement_level == DocumentRequirementLevel.REQUIRED
        ),
        external_reference=_text(data.external_reference),
        uploaded_by_id=actor.id,
        uploaded_by_name_snapshot=actor.display_name,
        uploaded_by_email_snapshot=actor.normalized_email,
        metadata={
            **dict(data.metadata or {}),
            "disposal_stage": approval.stage,
            "replacement_of": str(replaced.id) if replaced else None,
            "integrated_by_patrimony": integrated_by_patrimony,
            "integrator_role": "CONTROL_PATRIMONIAL" if integrated_by_patrimony else "STAGE_OWNER",
        },
        document_group_id=replaced.document_group_id if replaced else None,
        version_number=replaced.version_number + 1 if replaced else 1,
        replaces_document=replaced,
    )
    if not replaced:
        document.document_group_id = document._meta.get_field(
            "document_group_id"
        ).get_default()
    else:
        previous_status = replaced.validation_status
        replaced.is_current_version = False
        replaced.validation_status = DocumentValidationStatus.SUPERSEDED
        replaced.save(update_fields=[
            "is_current_version",
            "validation_status",
            "updated_at",
        ])
        _event(
            replaced,
            DocumentValidationEventType.SUPERSEDED,
            previous_status,
            actor,
            request,
            "Documento observado sustituido por una nueva versión.",
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
def upload_inventory_document(
    *, data, actor_id, authorized_owner, request=None,
    required_permission="can_manage_documents",
):
    """Carga un PDF a un expediente interno previamente autorizado por scope."""
    actor = _actor(actor_id, required_permission)
    owner = _document_owner(data.owner_type, data.owner_id)
    if (
        authorized_owner.__class__ is not owner.__class__
        or authorized_owner.pk != owner.pk
    ):
        raise InventoryAuthorizationError(
            "El expediente autorizado no corresponde al documento solicitado."
        )
    uploaded = data.file
    replaced = (
        AssetDocument.objects.select_for_update()
        .filter(
            owner_type=data.owner_type,
            owner_id=data.owner_id,
            document_type=data.document_type,
            validation_status=DocumentValidationStatus.REJECTED,
            is_current_version=True,
            is_deleted=False,
        )
        .order_by("-uploaded_at", "-created_at")
        .first()
    )
    if replaced:
        previous_status = replaced.validation_status
        replaced.is_current_version = False
        replaced.validation_status = DocumentValidationStatus.SUPERSEDED
        replaced.save(update_fields=[
            "is_current_version", "validation_status", "updated_at",
        ])
        _event(
            replaced,
            DocumentValidationEventType.SUPERSEDED,
            previous_status,
            actor,
            request,
            "Acuse observado sustituido por una nueva versión.",
        )
    document = AssetDocument(
        owner_type=data.owner_type,
        owner_id=data.owner_id,
        document_type=data.document_type,
        title=_text(data.title),
        description=_text(data.description),
        file=uploaded,
        original_filename=data.original_filename,
        content_type=data.content_type,
        file_size=getattr(uploaded, "size", None),
        sha256_hash=_hash(uploaded),
        access_level=data.access_level,
        is_required_evidence=bool(data.is_required_evidence),
        external_reference=_text(data.external_reference),
        uploaded_by_id=actor.id,
        uploaded_by_name_snapshot=actor.display_name,
        uploaded_by_email_snapshot=actor.normalized_email,
        metadata={"source": "inventory_context_upload"},
        document_group_id=(
            replaced.document_group_id if replaced else None
        ),
        version_number=(replaced.version_number + 1 if replaced else 1),
        replaces_document=replaced,
    )
    if not replaced:
        # Se conserva el default UUID del modelo; asignar None lo anularía.
        document.document_group_id = document._meta.get_field(
            "document_group_id"
        ).get_default()
    document.full_clean()
    document.save()
    _event(document, DocumentValidationEventType.UPLOADED, "", actor, request)
    log_inventory_event(
        action=InventoryAuditAction.UPLOAD,
        summary="Documento agregado al expediente de Inventory",
        actor_id=actor.id,
        asset_id=_owner_asset_id(data.owner_type, owner),
        target=document,
        new_value=model_snapshot(document),
        request_context=build_audit_request_context(request),
    )
    return document


@transaction.atomic
def resolve_inventory_document(
    *,
    document_id,
    data,
    actor_id,
    request=None,
    required_permission="can_validate_documents",
):
    actor = _actor(actor_id, required_permission)
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
    if (
        document.owner_type == InventoryDocumentOwnerType.DISPOSAL_APPROVAL
        and document.validation_status == DocumentValidationStatus.REJECTED
    ):
        raise InventoryStateError(
            "El documento observado debe sustituirse antes de una nueva validación."
        )
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
        _refresh_disposal(
            approval.disposal_request,
            validator=actor,
            document=document,
            request=request,
        )
    if (
        data.approve
        and document.owner_type == InventoryDocumentOwnerType.CUSTODY_DOCUMENT
    ):
        owner = CustodyDocument.objects.select_for_update().get(
            pk=document.owner_id,
            is_deleted=False,
        )
        from apps.inventory.services.custody_document_service import (
            activate_custody_document,
            finalize_custody_release_document,
        )
        if (
            owner.document_type == CustodyDocumentType.ASSIGNMENT
            and document.document_type == DocumentType.SIGNED_CUSTODY_RECEIPT
        ):
            activate_custody_document(
                document_id=owner.id,
                actor_id=actor.id,
                request=request,
            )
        elif (
            owner.document_type == CustodyDocumentType.RELEASE
            and document.document_type == DocumentType.SIGNED_RETURN_RECEIPT
        ):
            finalize_custody_release_document(
                document_id=owner.id,
                actor_id=actor.id,
                request=request,
            )
    return document


__all__ = ["resolve_inventory_document", "upload_disposal_stage_document", "upload_inventory_document"]
