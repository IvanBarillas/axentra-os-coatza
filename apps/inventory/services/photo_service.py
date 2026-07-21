"""Servicios de evidencia fotográfica del expediente patrimonial."""

from hashlib import sha256

from django.db import transaction

from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    Asset,
    AssetPhoto,
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
    InventoryValidationError,
)


PHOTO_PERMISSION = "can_manage_photos"


def _file_hash(uploaded_file):
    digest = sha256()
    chunks = uploaded_file.chunks() if hasattr(uploaded_file, "chunks") else iter(lambda: uploaded_file.read(64 * 1024), b"")
    for chunk in chunks:
        digest.update(chunk)
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    return digest.hexdigest()


@transaction.atomic
def upload_asset_photo(*, asset_id, data, actor_id, request=None):
    try:
        actor = core_directory.get_user_identity(actor_id)
        role = core_directory.get_module_role(actor.id)
    except core_directory.CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc
    if not actor.has_global_bypass and not (role and role.has_permission(PHOTO_PERMISSION)):
        raise InventoryAuthorizationError(
            "La operación requiere el permiso [can_manage_photos]."
        )
    try:
        asset = Asset.objects.get(pk=asset_id, is_deleted=False)
    except Asset.DoesNotExist as exc:
        raise InventoryValidationError("El activo no existe.") from exc
    if data.owner_type != InventoryDocumentOwnerType.ASSET or data.owner_id != asset.id:
        raise InventoryValidationError(
            "La fotografía debe pertenecer al expediente del activo abierto."
        )
    image = data.image
    geolocation = data.geolocation
    photo = AssetPhoto(
        owner_type=InventoryDocumentOwnerType.ASSET,
        owner_id=asset.id,
        photo_type=data.photo_type,
        image=image,
        original_filename=data.original_filename,
        content_type=data.content_type,
        file_size=getattr(image, "size", None),
        sha256_hash=_file_hash(image),
        uploaded_by_id=actor.id,
        uploaded_by_name_snapshot=actor.display_name,
        uploaded_by_email_snapshot=actor.normalized_email,
        caption=str(data.caption or "").strip(),
        is_required_evidence=data.is_required_evidence,
        latitude=(geolocation.latitude if geolocation else None),
        longitude=(geolocation.longitude if geolocation else None),
    )
    photo.full_clean()
    photo.save()
    log_inventory_event(
        action=InventoryAuditAction.UPLOAD,
        summary="Fotografía agregada al expediente patrimonial",
        actor_id=actor.id,
        asset_id=asset.id,
        target=photo,
        old_value={},
        new_value=model_snapshot(photo),
        request_context=build_audit_request_context(request),
    )
    return photo
