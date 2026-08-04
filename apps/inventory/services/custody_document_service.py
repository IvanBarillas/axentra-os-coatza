"""Creación masiva y sustitución histórica de resguardos."""

from types import SimpleNamespace
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    Asset,
    AssetOperationalStatus,
    CustodyAcceptanceMethod,
    CustodyAssigneeMode,
    CustodyAssignment,
    CustodyDocument,
    CustodyDocumentItem,
    CustodyDocumentStatus,
    CustodyDocumentType,
    CustodyEventType,
    CustodyStatus,
    InventoryAuditAction,
)
from apps.inventory.services.audit_service import (
    build_audit_request_context,
    log_inventory_event,
    model_snapshot,
)
from apps.inventory.services.custody_service import (
    _event,
    _require_permission,
    create_custody_assignment,
)
from apps.inventory.services.exceptions import (
    InventoryStateError,
    InventoryValidationError,
)


MANAGE_PERMISSION = "can_manage_custody"
OPEN_STATUSES = {
    CustodyStatus.DRAFT,
    CustodyStatus.PENDING_AUTHORIZATION,
    CustodyStatus.PENDING_ACCEPTANCE,
    CustodyStatus.ACTIVE,
    CustodyStatus.RETURN_PENDING,
}


@transaction.atomic
def activate_custody_document(*, document_id, actor_id, request=None):
    """Activa todo el lote con el único acuse firmado del documento masivo."""
    actor = _require_permission(actor_id, MANAGE_PERMISSION)
    context = build_audit_request_context(request)
    document = (
        CustodyDocument.objects.select_for_update()
        .prefetch_related("items__custody_assignment__asset")
        .get(pk=document_id, is_deleted=False)
    )
    if document.document_type != CustodyDocumentType.ASSIGNMENT:
        raise InventoryStateError("El documento no es un resguardo de entrega.")
    if document.status != CustodyDocumentStatus.IN_PROCESS:
        raise InventoryStateError(
            "El documento masivo no admite activación desde su estado actual."
        )
    items = list(document.items.all())
    allowed = {
        CustodyStatus.DRAFT,
        CustodyStatus.REJECTED,
        CustodyStatus.PENDING_AUTHORIZATION,
        CustodyStatus.PENDING_ACCEPTANCE,
    }
    if not items or any(
        item.custody_assignment.status not in allowed for item in items
    ):
        raise InventoryStateError(
            "Todos los resguardos del lote deben continuar pendientes de firma."
        )

    now = timezone.now()
    for item in items:
        custody = item.custody_assignment
        previous = custody.status
        custody.status = CustodyStatus.ACTIVE
        custody.authorized_by_id = actor.id
        custody.authorized_at = now
        custody.delivered_by_id = actor.id
        custody.delivered_at = now
        custody.accepted_by_id = custody.assigned_to_id
        custody.accepted_at = now
        custody.acceptance_method = CustodyAcceptanceMethod.HANDWRITTEN_SIGNATURE
        custody.assigned_at = now
        custody.delivery_observations = (
            f"Activado mediante el acuse masivo {document.folio}."
        )
        custody.asset.current_custodian_id = custody.assigned_to_id
        custody.asset.operational_status = AssetOperationalStatus.ASSIGNED
        custody.asset.full_clean()
        custody.asset.save()
        custody.full_clean()
        custody.save()
        _event(
            custody,
            CustodyEventType.ACCEPTED,
            previous,
            actor,
            context,
            comment=f"Acuse masivo {document.folio} integrado y validado.",
        )
        log_inventory_event(
            action=InventoryAuditAction.ASSIGN,
            summary="Resguardo activado mediante acuse masivo",
            actor_id=actor.id,
            asset_id=custody.asset_id,
            target=custody,
            old_value={"status": previous},
            new_value=model_snapshot(custody),
            payload={"custody_document_id": str(document.id)},
            request_context=context,
        )

    document.status = CustodyDocumentStatus.ACTIVE
    document.full_clean()
    document.save(update_fields=["status", "updated_at"])
    return document


def _resolve_responsible(*, department, mode, assigned_to_id):
    if mode == CustodyAssigneeMode.DEPARTMENT_MANAGER:
        user_id = department.manager_user_id
        if not user_id:
            raise InventoryValidationError(
                "La dependencia no tiene titular o encargado registrado."
            )
    elif mode == CustodyAssigneeMode.PUBLIC_SERVANT:
        user_id = assigned_to_id
        if not user_id:
            raise InventoryValidationError(
                "Seleccione al servidor público responsable."
            )
    else:
        raise InventoryValidationError(
            "El tipo de responsable no es válido."
        )
    return core_directory.get_user_identity(user_id)


@transaction.atomic
def create_custody_document(
    *,
    department_id,
    asset_ids,
    assignee_mode,
    assigned_to_id,
    notes,
    bypass_reason,
    actor_id,
    request=None,
    replacement_of=None,
):
    actor = _require_permission(actor_id, MANAGE_PERMISSION)
    try:
        department = core_directory.get_department(department_id)
        responsible = _resolve_responsible(
            department=department,
            mode=assignee_mode,
            assigned_to_id=assigned_to_id,
        )
    except core_directory.CoreDirectoryError as exc:
        raise InventoryValidationError(str(exc)) from exc

    unique_asset_ids = list(dict.fromkeys(asset_ids))
    if not unique_asset_ids:
        raise InventoryValidationError(
            "Seleccione al menos un bien patrimonial."
        )

    assets = list(
        Asset.objects.select_for_update()
        .filter(
            id__in=unique_asset_ids,
            current_dependencia_id=department.id,
            is_deleted=False,
        )
        .order_by("official_inventory_number", "name")
    )
    if len(assets) != len(unique_asset_ids):
        raise InventoryValidationError(
            "Uno o más bienes no existen o no pertenecen a la dependencia."
        )

    if CustodyAssignment.objects.filter(
        asset_id__in=unique_asset_ids,
        is_deleted=False,
        status__in=OPEN_STATUSES,
    ).exists():
        raise InventoryStateError(
            "Uno o más bienes ya tienen un resguardo vigente o en proceso."
        )

    document = CustodyDocument(
        folio=(
            f"RMG-{timezone.localdate():%Y}-"
            f"{uuid4().hex[:10].upper()}"
        ),
        department_id=department.id,
        department_name_snapshot=department.name,
        department_code_snapshot=department.code or "",
        status=CustodyDocumentStatus.IN_PROCESS,
        assignee_mode=assignee_mode,
        assigned_to_id_snapshot=responsible.id,
        assigned_to_name_snapshot=responsible.display_name,
        assigned_to_email_snapshot=responsible.normalized_email,
        prepared_by_id=actor.id,
        replacement_of=replacement_of,
        notes=str(notes or "").strip(),
    )
    document.full_clean()
    document.save()

    for asset in assets:
        custody = create_custody_assignment(
            data=SimpleNamespace(
                asset_id=asset.id,
                assignee_mode=assignee_mode,
                assigned_to_id=(
                    responsible.id
                    if assignee_mode == CustodyAssigneeMode.PUBLIC_SERVANT
                    else None
                ),
                notes=notes,
                bypass_reason=bypass_reason,
            ),
            actor_id=actor.id,
            request=request,
        )
        CustodyDocumentItem.objects.create(
            document=document,
            custody_assignment=custody,
            asset_id_snapshot=asset.id,
            inventory_number_snapshot=asset.display_inventory_number,
            asset_name_snapshot=asset.name,
            serial_number_snapshot=asset.serial_number or "",
        )

    return document


@transaction.atomic
def create_custody_release_document(
    *, document_id, reason, actor_id, request=None
):
    """Prepara una liberación masiva sin cerrar todavía los resguardos."""
    actor = _require_permission(actor_id, MANAGE_PERMISSION)
    source = (
        CustodyDocument.objects.select_for_update()
        .prefetch_related("items__custody_assignment")
        .get(pk=document_id, is_deleted=False)
    )
    if source.document_type != CustodyDocumentType.ASSIGNMENT:
        raise InventoryStateError(
            "Sólo un documento de resguardo puede generar una liberación."
        )
    if source.is_historical:
        raise InventoryStateError("El resguardo ya pertenece al histórico.")
    if source.release_documents.filter(
        is_deleted=False,
        status__in={CustodyDocumentStatus.DRAFT, CustodyDocumentStatus.IN_PROCESS},
    ).exists():
        raise InventoryStateError(
            "Este resguardo ya tiene una liberación pendiente de firma."
        )
    active_items = [
        item for item in source.items.all()
        if item.custody_assignment.status in {
            CustodyStatus.ACTIVE,
            CustodyStatus.RETURN_PENDING,
        }
    ]
    if not active_items:
        raise InventoryStateError(
            "El documento no contiene resguardos activos para liberar."
        )
    reason = str(reason or "").strip()
    if not reason:
        raise InventoryValidationError("Indique el motivo de la liberación.")

    release = CustodyDocument(
        folio=f"LIB-{timezone.localdate():%Y}-{uuid4().hex[:10].upper()}",
        document_type=CustodyDocumentType.RELEASE,
        department_id=source.department_id,
        department_name_snapshot=source.department_name_snapshot,
        department_code_snapshot=source.department_code_snapshot,
        status=CustodyDocumentStatus.IN_PROCESS,
        assignee_mode=source.assignee_mode,
        assigned_to_id_snapshot=source.assigned_to_id_snapshot,
        assigned_to_name_snapshot=source.assigned_to_name_snapshot,
        assigned_to_email_snapshot=source.assigned_to_email_snapshot,
        prepared_by_id=actor.id,
        source_document=source,
        received_by_id_snapshot=actor.id,
        received_by_name_snapshot=actor.display_name,
        received_by_email_snapshot=actor.normalized_email,
        notes=reason,
    )
    release.full_clean()
    release.save()
    for item in active_items:
        CustodyDocumentItem.objects.create(
            document=release,
            custody_assignment=item.custody_assignment,
            asset_id_snapshot=item.asset_id_snapshot,
            inventory_number_snapshot=item.inventory_number_snapshot,
            asset_name_snapshot=item.asset_name_snapshot,
            serial_number_snapshot=item.serial_number_snapshot,
        )
    return release


@transaction.atomic
def finalize_custody_release_document(
    *, document_id, actor_id, request=None
):
    """Cierra atómicamente el lote después de integrar el acuse firmado."""
    actor = _require_permission(actor_id, MANAGE_PERMISSION)
    context = build_audit_request_context(request)
    release = (
        CustodyDocument.objects.select_for_update()
        .prefetch_related("items__custody_assignment__asset")
        .get(pk=document_id, is_deleted=False)
    )
    if release.document_type != CustodyDocumentType.RELEASE:
        raise InventoryStateError("El documento no es una liberación.")
    if release.status != CustodyDocumentStatus.IN_PROCESS:
        raise InventoryStateError("La liberación ya fue procesada.")
    items = list(release.items.all())
    if not items or any(
        item.custody_assignment.status not in {
            CustodyStatus.ACTIVE,
            CustodyStatus.RETURN_PENDING,
        }
        for item in items
    ):
        raise InventoryStateError(
            "Todos los resguardos deben continuar vigentes para cerrar el lote."
        )

    now = timezone.now()
    for item in items:
        custody = item.custody_assignment
        previous = custody.status
        custody.status = CustodyStatus.RETURNED
        custody.returned_by_id = custody.assigned_to_id
        custody.received_return_by_id = actor.id
        custody.returned_at = now
        custody.return_condition = custody.asset.physical_condition
        custody.return_observations = release.notes
        custody.asset.current_custodian_id = None
        # La ubicación institucional se conserva; sólo termina la responsabilidad.
        custody.asset.save(update_fields=["current_custodian", "updated_at"])
        custody.full_clean()
        custody.save()
        _event(
            custody,
            CustodyEventType.RETURNED,
            previous,
            actor,
            context,
            comment=f"Liberación masiva {release.folio}: {release.notes}",
        )

    source = CustodyDocument.objects.select_for_update().get(
        pk=release.source_document_id,
        is_deleted=False,
    )
    source.status = CustodyDocumentStatus.CLOSED
    source.closed_by_id = actor.id
    source.closed_at = now
    source.closure_reason = f"Liberado mediante {release.folio}."
    source.full_clean()
    source.save()

    release.status = CustodyDocumentStatus.CLOSED
    release.closed_by_id = actor.id
    release.closed_at = now
    release.closure_reason = release.notes
    release.full_clean()
    release.save()
    return release


@transaction.atomic
def close_custody_document(*, document_id, reason, actor_id):
    actor = _require_permission(actor_id, MANAGE_PERMISSION)
    document = (
        CustodyDocument.objects.select_for_update()
        .prefetch_related("items__custody_assignment")
        .get(pk=document_id, is_deleted=False)
    )
    if document.is_historical:
        raise InventoryStateError(
            "El documento ya pertenece al histórico."
        )
    if any(
        item.custody_assignment.status in OPEN_STATUSES
        for item in document.items.all()
    ):
        raise InventoryStateError(
            "No puede finalizar el documento mientras tenga resguardos "
            "vigentes o en proceso."
        )
    reason = str(reason or "").strip()
    if not reason:
        raise InventoryValidationError(
            "Indique el motivo de finalización."
        )
    document.status = CustodyDocumentStatus.CLOSED
    document.closed_by_id = actor.id
    document.closed_at = timezone.now()
    document.closure_reason = reason
    document.full_clean()
    document.save()
    return document


@transaction.atomic
def replace_custody_document(
    *,
    document_id,
    assignee_mode,
    assigned_to_id,
    reason,
    actor_id,
    request=None,
):
    actor = _require_permission(actor_id, MANAGE_PERMISSION)
    context = build_audit_request_context(request)
    document = (
        CustodyDocument.objects.select_for_update()
        .prefetch_related("items__custody_assignment__asset")
        .get(pk=document_id, is_deleted=False)
    )
    if document.is_historical:
        raise InventoryStateError(
            "El documento ya pertenece al histórico y no puede sustituirse."
        )

    reason = str(reason or "").strip()
    if not reason:
        raise InventoryValidationError("Indique el motivo del cambio.")

    asset_ids = []
    now = timezone.now()
    for item in document.items.all():
        custody = item.custody_assignment
        asset_ids.append(custody.asset_id)
        if custody.status in {
            CustodyStatus.ACTIVE,
            CustodyStatus.RETURN_PENDING,
        }:
            previous = custody.status
            custody.status = CustodyStatus.RETURNED
            custody.returned_by_id = custody.assigned_to_id
            custody.received_return_by_id = actor.id
            custody.returned_at = now
            custody.return_condition = custody.asset.physical_condition
            custody.return_observations = reason
            custody.asset.current_custodian_id = None
            custody.asset.save(
                update_fields=["current_custodian", "updated_at"]
            )
            custody.full_clean()
            custody.save()
            _event(
                custody,
                CustodyEventType.RETURNED,
                previous,
                actor,
                context,
                comment=reason,
            )
        elif custody.status in {
            CustodyStatus.DRAFT,
            CustodyStatus.PENDING_AUTHORIZATION,
            CustodyStatus.PENDING_ACCEPTANCE,
            CustodyStatus.REJECTED,
        }:
            previous = custody.status
            custody.status = CustodyStatus.CANCELLED
            custody.cancelled_by_id = actor.id
            custody.cancelled_at = now
            custody.cancellation_reason = reason
            custody.full_clean()
            custody.save()
            _event(
                custody,
                CustodyEventType.CANCELLED,
                previous,
                actor,
                context,
                comment=reason,
            )

    replacement = create_custody_document(
        department_id=document.department_id,
        asset_ids=asset_ids,
        assignee_mode=assignee_mode,
        assigned_to_id=assigned_to_id,
        notes=f"Sustituye al documento {document.folio}.",
        bypass_reason="",
        actor_id=actor.id,
        request=request,
        replacement_of=document,
    )
    document.status = CustodyDocumentStatus.REPLACED
    document.closed_by_id = actor.id
    document.closed_at = now
    document.closure_reason = reason
    document.full_clean()
    document.save()
    return replacement


__all__ = [
    "close_custody_document",
    "create_custody_document",
    "create_custody_release_document",
    "finalize_custody_release_document",
    "replace_custody_document",
]
