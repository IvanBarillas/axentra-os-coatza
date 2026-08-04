from django.db import transaction
from django.utils import timezone
from uuid import uuid4

from apps.inventory.dtos import (
    ChangeAssetLocationDTO,
    CreateInventoryMovementDTO,
    MovementResultDTO,
    OrganizationalDestinationDTO,
    ReassignAssetDTO,
    TransferAssetDTO,
)
from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    Asset,
    AssetMovementRequest,
    AssetMovementRequestStatus,
    CustodyAssignment,
    CustodyDocument,
    CustodyDocumentStatus,
    CustodyDocumentType,
    CustodyEventType,
    CustodyStatus,
    InventoryAuditAction,
    InventoryMovement,
    MovementType,
)
from apps.inventory.services.exceptions import (
    InventoryAuthorizationError,
    InventoryStateError,
    InventoryValidationError,
)
from .audit_service import log_inventory_event
from .audit_service import build_audit_request_context
from .common import lock_instance, require_text, validate_and_save
from .custody_service import _event as custody_event


@transaction.atomic
def create_movement(*, data: CreateInventoryMovementDTO, actor, request_context=None):
    asset = lock_instance(Asset, data.asset_id)
    destination = data.destination
    movement = InventoryMovement(
        asset=asset,
        movement_type=data.movement_type,
        reason=require_text(data.reason, "reason"),
        occurred_at=data.occurred_at or timezone.now(),
        performed_by=actor,
        from_dependencia=asset.current_dependencia,
        from_area=asset.current_area,
        from_sede=asset.current_sede,
        from_user=asset.current_custodian,
        condition_before=asset.physical_condition,
        condition_after=data.condition_after or asset.physical_condition,
        payload=dict(data.payload),
        performed_by_name_snapshot=(actor.get_full_name() or actor.email).strip(),
        performed_by_email_snapshot=actor.email or "",
        from_dependencia_id_snapshot=asset.current_dependencia_id,
        from_dependencia_name_snapshot=str(asset.current_dependencia or ""),
        from_dependencia_code_snapshot=getattr(asset.current_dependencia, "codigo_presupuestal", "") or "",
        from_area_id_snapshot=asset.current_area_id,
        from_area_name_snapshot=str(asset.current_area or ""),
        from_sede_id_snapshot=asset.current_sede_id,
        from_sede_name_snapshot=str(asset.current_sede or ""),
        from_user_id_snapshot=asset.current_custodian_id,
        from_user_name_snapshot=(asset.current_custodian.get_full_name() or asset.current_custodian.email).strip() if asset.current_custodian else "",
        from_user_email_snapshot=asset.current_custodian.email if asset.current_custodian else "",
        bypass_used=bool(data.bypass_reason),
        bypass_reason=(data.bypass_reason or "").strip(),
    )
    if destination:
        movement.to_dependencia_id = destination.department_id
        movement.to_area_id = destination.area_id
        movement.to_sede_id = destination.site_id
        movement.to_user_id = destination.user_id
        if destination.department_id:
            identity = core_directory.get_department(destination.department_id)
            movement.to_dependencia_id_snapshot = identity.id
            movement.to_dependencia_name_snapshot = identity.name
            movement.to_dependencia_code_snapshot = identity.code
        if destination.area_id:
            area = core_directory.get_area_context(destination.area_id)
            movement.to_area_id_snapshot = area.id
            movement.to_area_name_snapshot = area.name
        if destination.site_id:
            site = core_directory.get_site(destination.site_id)
            movement.to_sede_id_snapshot = site.id
            movement.to_sede_name_snapshot = site.name
        if destination.user_id:
            user = core_directory.get_user_identity(destination.user_id)
            movement.to_user_id_snapshot = user.id
            movement.to_user_name_snapshot = user.display_name
            movement.to_user_email_snapshot = user.email
    if data.reference:
        movement.reference_type = data.reference.reference_type
        movement.reference_id = data.reference.reference_id
        movement.reference_folio = data.reference.reference_folio
    if data.corrects_movement_id:
        movement.corrects_movement_id = data.corrects_movement_id
    validate_and_save(movement)
    update_fields = []
    if destination:
        definitive_transfer = data.movement_type == MovementType.TRANSFER
        if destination.department_id is not None:
            asset.current_dependencia_id = destination.department_id
            update_fields.append("current_dependencia")
        if destination.area_id is not None or definitive_transfer:
            asset.current_area_id = destination.area_id
            update_fields.append("current_area")
        if destination.site_id is not None or definitive_transfer:
            asset.current_sede_id = destination.site_id
            update_fields.append("current_sede")
        if destination.user_id is not None or definitive_transfer:
            asset.current_custodian_id = destination.user_id
            update_fields.append("current_custodian")
    if data.condition_after:
        asset.physical_condition = data.condition_after
        update_fields.append("physical_condition")
    if update_fields:
        asset.save(update_fields=[*dict.fromkeys(update_fields), "updated_at"])
    log_inventory_event(action=InventoryAuditAction.CREATE, actor_id=actor.id, asset_id=asset.id, target=movement, summary=movement.reason, request_context=request_context)
    return MovementResultDTO(movement_id=movement.id, asset_id=asset.id, movement_type=movement.movement_type, correlation_id=movement.correlation_id)


def execute_transfer(*, data: TransferAssetDTO, actor, request_context=None):
    return create_movement(
        data=CreateInventoryMovementDTO(
            asset_id=data.asset_id,
            movement_type=MovementType.TRANSFER,
            reason=data.reason,
            occurred_at=data.occurred_at or timezone.now(),
            destination=OrganizationalDestinationDTO(
                department_id=data.destination_department_id,
                area_id=data.destination_area_id,
                site_id=data.destination_site_id,
                user_id=data.destination_custodian_id,
            ),
            bypass_reason=data.bypass_reason,
        ),
        actor=actor,
        request_context=request_context,
    )


def execute_reassignment(*, data: ReassignAssetDTO, actor, request_context=None):
    asset = Asset.objects.get(pk=data.asset_id, is_deleted=False)
    _, department_id, area_id, site_id, user_id = _request_payload(
        data, asset,
    )
    return create_movement(
        data=CreateInventoryMovementDTO(
            asset_id=data.asset_id,
            movement_type=MovementType.REASSIGNMENT,
            reason=data.reason,
            occurred_at=data.occurred_at or timezone.now(),
            destination=OrganizationalDestinationDTO(
                department_id=department_id,
                area_id=area_id,
                site_id=site_id,
                user_id=user_id,
            ),
        ),
        actor=actor,
        request_context=request_context,
    )


def execute_location_change(*, data: ChangeAssetLocationDTO, actor, request_context=None):
    asset = Asset.objects.get(pk=data.asset_id, is_deleted=False)
    _, department_id, area_id, site_id, _ = _request_payload(data, asset)
    return create_movement(
        data=CreateInventoryMovementDTO(
            asset_id=data.asset_id,
            movement_type=MovementType.LOCATION_CHANGE,
            reason=data.reason,
            occurred_at=data.occurred_at or timezone.now(),
            destination=OrganizationalDestinationDTO(
                department_id=department_id,
                area_id=area_id,
                site_id=site_id,
            ),
            payload={
                "latitude": str(data.geolocation.latitude) if data.geolocation and data.geolocation.latitude is not None else None,
                "longitude": str(data.geolocation.longitude) if data.geolocation and data.geolocation.longitude is not None else None,
            },
        ),
        actor=actor,
        request_context=request_context,
    )


def _movement_actor(actor_id, *permissions):
    actor = core_directory.get_user_identity(actor_id)
    role = core_directory.get_module_role(actor.id)
    if not actor.has_global_bypass and not (role and any(role.has_permission(permission) for permission in permissions)):
        raise InventoryAuthorizationError("No cuenta con autorización para esta etapa del movimiento.")
    return actor


def can_authorize_department_movement(*, actor_id, department_id):
    """Resuelve autoridad departamental sin conceder operación global.

    El titular formal conserva autoridad. Además, una persona adscrita a la
    dependencia puede recibir explícitamente ``can_authorize_movements`` como
    delegación funcional.
    """
    actor = core_directory.get_user_identity(actor_id)
    if actor.has_global_bypass:
        return True
    formal_authority = core_directory.user_can_approve_department(
        actor.id,
        department_id,
    )
    if formal_authority.allowed:
        return True
    try:
        context = core_directory.get_user_organizational_context(
            actor.id,
            require_profile=True,
        )
    except core_directory.CoreDirectoryError:
        return False
    role = core_directory.get_module_role(actor.id)
    return bool(
        context.department_id == department_id
        and role
        and role.has_permission("can_authorize_movements")
    )


def _request_payload(data, asset):
    if isinstance(data, TransferAssetDTO):
        if data.destination_department_id == asset.current_dependencia_id:
            raise InventoryValidationError(
                "Para conservar la misma dependencia utilice cambio de ubicación o reasignación."
            )
        allowed_department_ids = {
            item.id for item in core_directory.list_departments(
                site_id=data.destination_site_id,
            )
        }
        if data.destination_department_id not in allowed_department_ids:
            raise InventoryValidationError(
                "La dependencia destino no tiene presencia en la sede seleccionada."
            )
        return MovementType.TRANSFER, data.destination_department_id, data.destination_area_id, data.destination_site_id, data.destination_custodian_id
    if isinstance(data, ReassignAssetDTO):
        if not asset.current_dependencia_id:
            raise InventoryValidationError(
                "El bien no tiene una dependencia vigente para reasignarlo."
            )
        if asset.current_custodian_id == data.new_custodian_id:
            raise InventoryValidationError(
                "El servidor público seleccionado ya es el resguardatario vigente."
            )
        return (
            MovementType.REASSIGNMENT,
            asset.current_dependencia_id,
            asset.current_area_id,
            asset.current_sede_id,
            data.new_custodian_id,
        )
    if not asset.current_dependencia_id:
        raise InventoryValidationError(
            "El bien no tiene una dependencia vigente para cambiar su ubicación."
        )
    if not data.site_id or not data.area_id:
        raise InventoryValidationError(
            "Seleccione la sede y el área operativa de destino."
        )
    allowed_site_ids = {
        item.id for item in core_directory.list_sites(
            department_id=asset.current_dependencia_id,
        )
    }
    if data.site_id not in allowed_site_ids:
        raise InventoryValidationError(
            "La dependencia vigente no tiene presencia en la sede seleccionada."
        )
    area = core_directory.get_area_context(data.area_id)
    if (
        area.department_id != asset.current_dependencia_id
        or area.site_id != data.site_id
    ):
        raise InventoryValidationError(
            "El área seleccionada no pertenece a la dependencia y sede permitidas."
        )
    if (
        asset.current_sede_id == data.site_id
        and asset.current_area_id == data.area_id
    ):
        raise InventoryValidationError(
            "El bien ya se encuentra en la sede y área seleccionadas."
        )
    return (
        MovementType.LOCATION_CHANGE,
        asset.current_dependencia_id,
        data.area_id,
        data.site_id,
        None,
    )


@transaction.atomic
def create_movement_request(*, data, actor_id, request=None):
    actor = core_directory.get_user_identity(actor_id)
    asset = lock_instance(Asset, data.asset_id)
    movement_type, department_id, area_id, site_id, user_id = _request_payload(
        data, asset,
    )
    core_directory.validate_organizational_context(
        department_id=department_id,
        area_id=area_id,
        site_id=site_id,
    )
    if user_id and not core_directory.user_belongs_to_department(user_id, department_id):
        raise InventoryAuthorizationError("El resguardatario destino no pertenece a la dependencia seleccionada.")
    role = core_directory.get_module_role(actor.id)
    patrimony_operator = actor.has_global_bypass or bool(role and role.has_permission("can_manage_movements"))
    origin_authority = can_authorize_department_movement(
        actor_id=actor.id,
        department_id=asset.current_dependencia_id,
    )
    department_transfer = isinstance(data, TransferAssetDTO) and origin_authority
    if not patrimony_operator and not department_transfer:
        raise InventoryAuthorizationError(
            "Sólo Patrimonio o el titular de la dependencia origen pueden solicitar este movimiento."
        )
    bypass_reason = str(getattr(data, "bypass_reason", "") or "").strip()
    if bypass_reason and not actor.has_global_bypass:
        raise InventoryAuthorizationError(
            "Sólo un usuario con bypass global puede omitir las aprobaciones."
        )
    if not patrimony_operator:
        actor_context = core_directory.get_user_organizational_context(actor.id, require_profile=True)
        if actor_context.department_id != asset.current_dependencia_id:
            raise InventoryAuthorizationError("Sólo puede solicitar movimientos de bienes pertenecientes a su dependencia.")
    request_status = (
        AssetMovementRequestStatus.PENDING_PATRIMONY_EXECUTION
        if patrimony_operator
        else AssetMovementRequestStatus.PENDING_ORIGIN_APPROVAL
    )
    origin_approved_by_id = None
    origin_approved_at = None
    is_interdepartmental_transfer = (
        movement_type == MovementType.TRANSFER
        and department_id != asset.current_dependencia_id
    )
    if is_interdepartmental_transfer:
        # Una transferencia nunca entra directamente al inventario destino.
        # Si la solicita el propio director de origen, su solicitud equivale a
        # la autorización de salida; todavía debe aceptar la dependencia destino.
        if actor.has_global_bypass and bypass_reason:
            request_status = AssetMovementRequestStatus.PENDING_PATRIMONY_EXECUTION
        else:
            try:
                actor_context = core_directory.get_user_organizational_context(
                    actor.id,
                    require_profile=False,
                )
            except core_directory.CoreDirectoryError:
                actor_context = None
            actor_is_origin_authority = bool(
                actor_context
                and actor_context.department_id == asset.current_dependencia_id
                and origin_authority
            )
            if actor_is_origin_authority:
                request_status = AssetMovementRequestStatus.PENDING_DESTINATION_ACCEPTANCE
                origin_approved_by_id = actor.id
                origin_approved_at = timezone.now()
            else:
                request_status = AssetMovementRequestStatus.PENDING_ORIGIN_APPROVAL
    movement_request = AssetMovementRequest(
        folio=f"MOV-{timezone.localdate():%Y}-{uuid4().hex[:8].upper()}",
        asset=asset,
        movement_type=movement_type,
        status=request_status,
        requested_by_id=actor.id,
        reason=require_text(data.reason, "reason"),
        occurred_at=data.occurred_at,
        origin_dependencia=asset.current_dependencia,
        origin_area=asset.current_area,
        origin_sede=asset.current_sede,
        origin_custodian=asset.current_custodian,
        destination_dependencia_id=department_id,
        destination_area_id=area_id,
        destination_sede_id=site_id,
        destination_custodian_id=user_id,
        origin_approved_by_id=origin_approved_by_id,
        origin_approved_at=origin_approved_at,
        bypass_used=bool(bypass_reason),
        bypass_reason=bypass_reason,
    )
    validate_and_save(movement_request)
    log_inventory_event(action=InventoryAuditAction.CREATE, actor_id=actor.id, asset_id=asset.id, target=movement_request, summary="Solicitud de movimiento creada", request=request)
    return movement_request


@transaction.atomic
def approve_movement_origin(*, request_id, actor_id, approve=True, comment="", request=None):
    actor = core_directory.get_user_identity(actor_id)
    item = AssetMovementRequest.objects.select_for_update().select_related("asset").get(pk=request_id, is_deleted=False)
    if item.status != AssetMovementRequestStatus.PENDING_ORIGIN_APPROVAL:
        raise InventoryStateError("La solicitud no está pendiente de autorización de origen.")
    authority = can_authorize_department_movement(
        actor_id=actor.id,
        department_id=item.origin_dependencia_id,
    )
    if not authority:
        raise InventoryAuthorizationError("Sólo el titular de la dependencia origen puede resolver esta etapa.")
    if not approve:
        item.status = AssetMovementRequestStatus.REJECTED
        item.rejection_reason = require_text(comment, "comment")
    else:
        item.origin_approved_by_id = actor.id
        item.origin_approved_at = timezone.now()
        different_department = item.destination_dependencia_id and item.destination_dependencia_id != item.origin_dependencia_id
        item.status = AssetMovementRequestStatus.PENDING_DESTINATION_ACCEPTANCE if different_department else AssetMovementRequestStatus.PENDING_PATRIMONY_EXECUTION
    validate_and_save(item)
    log_inventory_event(action=InventoryAuditAction.APPROVE if approve else InventoryAuditAction.REJECT, actor_id=actor.id, asset_id=item.asset_id, target=item, summary="Decisión de la dependencia origen sobre movimiento", reason=comment, request=request)
    return item


@transaction.atomic
def accept_movement_destination(
    *, request_id, actor_id, approve=True, comment="",
    destination_area_id=None, destination_custodian_id=None, request=None,
):
    actor = core_directory.get_user_identity(actor_id)
    item = AssetMovementRequest.objects.select_for_update().get(pk=request_id, is_deleted=False)
    if item.status != AssetMovementRequestStatus.PENDING_DESTINATION_ACCEPTANCE:
        raise InventoryStateError("La solicitud no está pendiente de aceptación de destino.")
    authority = can_authorize_department_movement(
        actor_id=actor.id,
        department_id=item.destination_dependencia_id,
    )
    if not authority:
        raise InventoryAuthorizationError("Sólo el titular de la dependencia destino puede aceptar esta transferencia.")
    if not approve:
        item.status = AssetMovementRequestStatus.REJECTED
        item.rejection_reason = require_text(comment, "comment")
    else:
        if destination_area_id:
            core_directory.validate_organizational_context(
                department_id=item.destination_dependencia_id,
                area_id=destination_area_id,
                site_id=item.destination_sede_id,
            )
            item.destination_area_id = destination_area_id
        if destination_custodian_id:
            if not core_directory.user_belongs_to_department(
                destination_custodian_id,
                item.destination_dependencia_id,
            ):
                raise InventoryAuthorizationError(
                    "El resguardatario no pertenece a la dependencia destino."
                )
            item.destination_custodian_id = destination_custodian_id
        item.destination_accepted_by_id = actor.id
        item.destination_accepted_at = timezone.now()
        item.status = AssetMovementRequestStatus.PENDING_PATRIMONY_EXECUTION
    validate_and_save(item)
    log_inventory_event(action=InventoryAuditAction.APPROVE if approve else InventoryAuditAction.REJECT, actor_id=actor.id, asset_id=item.asset_id, target=item, summary="Decisión de la dependencia destino sobre movimiento", reason=comment, request=request)
    return item


def _close_transfer_custodies(*, asset_id, actor, reason, request_context):
    """Cierra la responsabilidad de origen al transferir la propiedad."""
    context = request_context or build_audit_request_context(None)
    now = timezone.now()
    custodies = list(
        CustodyAssignment.objects.select_for_update().filter(
            asset_id=asset_id,
            is_deleted=False,
            status__in={
                CustodyStatus.DRAFT,
                CustodyStatus.PENDING_AUTHORIZATION,
                CustodyStatus.PENDING_ACCEPTANCE,
                CustodyStatus.REJECTED,
                CustodyStatus.ACTIVE,
                CustodyStatus.RETURN_PENDING,
            },
        )
    )
    for custody in custodies:
        previous = custody.status
        if previous in {CustodyStatus.ACTIVE, CustodyStatus.RETURN_PENDING}:
            custody.status = CustodyStatus.RETURNED
            custody.returned_by_id = custody.assigned_to_id
            custody.received_return_by_id = actor.id
            custody.returned_at = max(now, custody.assigned_at or now)
            custody.return_condition = custody.asset.physical_condition
            custody.return_observations = reason
            event_type = CustodyEventType.RETURNED
        else:
            custody.status = CustodyStatus.CANCELLED
            custody.cancelled_by_id = actor.id
            custody.cancelled_at = now
            custody.cancellation_reason = reason
            event_type = CustodyEventType.CANCELLED
        custody.full_clean()
        custody.save()
        custody_event(
            custody,
            event_type,
            previous,
            actor,
            context,
            comment=reason,
        )

    document_ids = {
        item.document_id
        for custody in custodies
        for item in custody.document_items.select_related("document").filter(
            document__document_type=CustodyDocumentType.ASSIGNMENT,
            document__is_deleted=False,
        )
    }
    for document in CustodyDocument.objects.select_for_update().filter(
        id__in=document_ids,
        is_deleted=False,
    ):
        if document.is_historical:
            continue
        has_open_items = document.items.filter(
            custody_assignment__status__in={
                CustodyStatus.DRAFT,
                CustodyStatus.PENDING_AUTHORIZATION,
                CustodyStatus.PENDING_ACCEPTANCE,
                CustodyStatus.REJECTED,
                CustodyStatus.ACTIVE,
                CustodyStatus.RETURN_PENDING,
            },
        ).exists()
        if not has_open_items:
            document.status = CustodyDocumentStatus.CLOSED
            document.closed_by_id = actor.id
            document.closed_at = max(now, document.prepared_at or now)
            document.closure_reason = reason
            document.full_clean()
            document.save()


@transaction.atomic
def execute_approved_movement(*, request_id, actor, request_context=None):
    actor_identity = _movement_actor(actor.id, "can_manage_movements")
    item = AssetMovementRequest.objects.select_for_update().select_related("asset").get(pk=request_id, is_deleted=False)
    if item.status != AssetMovementRequestStatus.PENDING_PATRIMONY_EXECUTION:
        raise InventoryStateError("El movimiento todavía no cuenta con todas las autorizaciones.")
    dto = CreateInventoryMovementDTO(
        asset_id=item.asset_id,
        movement_type=item.movement_type,
        reason=item.reason,
        occurred_at=item.occurred_at or timezone.now(),
        destination=OrganizationalDestinationDTO(item.destination_dependencia_id, item.destination_area_id, item.destination_sede_id, item.destination_custodian_id),
        bypass_reason=item.bypass_reason,
        payload={"movement_request_id": str(item.id), "movement_request_folio": item.folio},
    )
    result = create_movement(data=dto, actor=actor, request_context=request_context)
    if item.movement_type == MovementType.TRANSFER:
        _close_transfer_custodies(
            asset_id=item.asset_id,
            actor=actor_identity,
            reason=f"Transferencia {item.folio}: {item.reason}",
            request_context=request_context,
        )
    item.status = AssetMovementRequestStatus.EXECUTED
    item.executed_by_id = actor.id
    item.executed_at = timezone.now()
    item.resulting_movement_id = result.movement_id
    validate_and_save(item)
    return item


__all__ = ["accept_movement_destination", "approve_movement_origin", "can_authorize_department_movement", "create_movement", "create_movement_request", "execute_approved_movement", "execute_location_change", "execute_reassignment", "execute_transfer"]
