from django.db import transaction
from django.utils import timezone

from apps.inventory.dtos import CreateInventoryMovementDTO, MovementResultDTO
from apps.inventory.integrations import core_directory
from apps.inventory.models import Asset, InventoryAuditAction, InventoryMovement
from .audit_service import log_inventory_event
from .common import lock_instance, require_text, validate_and_save


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
    if data.reference:
        movement.reference_type = data.reference.reference_type
        movement.reference_id = data.reference.reference_id
        movement.reference_folio = data.reference.reference_folio
    if data.corrects_movement_id:
        movement.corrects_movement_id = data.corrects_movement_id
    validate_and_save(movement)
    log_inventory_event(action=InventoryAuditAction.CREATE, actor_id=actor.id, asset_id=asset.id, target=movement, summary=movement.reason, request_context=request_context)
    return MovementResultDTO(movement_id=movement.id, asset_id=asset.id, movement_type=movement.movement_type, correlation_id=movement.correlation_id)


__all__ = ["create_movement"]
