from django.core.exceptions import ValidationError
from django.db import transaction

from apps.inventory.dtos import CorrectAssetDTO, UpdateAssetConditionDTO
from apps.inventory.models import AccountingAccount, Asset, AssetCategory, InventoryAuditAction
from .audit_service import log_model_change
from .common import lock_instance, require_text, validate_and_save


@transaction.atomic
def correct_asset(*, asset_id, data: CorrectAssetDTO, actor, request_context=None):
    asset = lock_instance(Asset, asset_id)
    before = {f.name: getattr(asset, f.name) for f in Asset._meta.concrete_fields}
    reason = require_text(data.reason, "reason")
    editable = ("name", "description", "serial_number", "acquisition_cost", "residual_value", "notes")
    for field in editable:
        value = getattr(data, field)
        if value is not None:
            setattr(asset, field, value)
    if data.category_id:
        asset.category = AssetCategory.objects.get(pk=data.category_id, is_active=True, is_deleted=False)
    if data.accounting_account_id:
        asset.accounting_account = AccountingAccount.objects.get(pk=data.accounting_account_id, is_active=True, is_deleted=False)
    if hasattr(asset, "extra_attributes") and data.extra_attributes:
        asset.extra_attributes = {**asset.extra_attributes, **dict(data.extra_attributes)}
    validate_and_save(asset)
    log_model_change(action=InventoryAuditAction.UPDATE, actor_id=actor.id, target=asset, before=before, after=asset, summary=f"Corrección patrimonial: {reason}", request_context=request_context, asset_id=asset.id)
    return asset


@transaction.atomic
def update_asset_condition(*, asset_id, data: UpdateAssetConditionDTO, actor, request_context=None):
    asset = lock_instance(Asset, asset_id)
    before = {"physical_condition": asset.physical_condition, "operational_status": asset.operational_status}
    require_text(data.reason, "reason")
    asset.physical_condition = data.physical_condition
    if data.operational_status:
        asset.operational_status = data.operational_status
    validate_and_save(asset)
    log_model_change(action=InventoryAuditAction.UPDATE, actor_id=actor.id, target=asset, before=before, after=asset, summary=f"Actualización de condición: {data.reason}", request_context=request_context, asset_id=asset.id)
    return asset


def delete_asset(*args, **kwargs):
    raise ValidationError("Los activos patrimoniales no se eliminan; utiliza el flujo formal de baja.")


__all__ = ["correct_asset", "delete_asset", "update_asset_condition"]
