"""Evidencias documentales y fotográficas de auditoría física."""

from hashlib import sha256

from django.db import transaction

from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    AssetDocument,
    AssetPhoto,
    DocumentValidationStatus,
    InventoryDocumentOwnerType,
    PhysicalAuditItem,
    PhysicalAuditSession,
)
from apps.inventory.services.exceptions import (
    InventoryAuthorizationError,
    InventoryValidationError,
)


AUDIT_OWNER_TYPES = {
    InventoryDocumentOwnerType.PHYSICAL_AUDIT_SESSION,
    InventoryDocumentOwnerType.PHYSICAL_AUDIT_ITEM,
}


def _actor(actor_id):
    try:
        actor = core_directory.get_user_identity(actor_id)
        role = core_directory.get_module_role(actor.id)
    except core_directory.CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc
    allowed = actor.has_global_bypass or (
        role and (
            role.has_permission("can_manage_physical_audits")
            or role.has_permission("can_scan_physical_audits")
        )
    )
    if not allowed:
        raise InventoryAuthorizationError(
            "No cuenta con permiso para agregar evidencias de auditoría física."
        )
    return actor


def _owner(owner_type, owner_id):
    if owner_type == InventoryDocumentOwnerType.PHYSICAL_AUDIT_SESSION:
        model = PhysicalAuditSession
    elif owner_type == InventoryDocumentOwnerType.PHYSICAL_AUDIT_ITEM:
        model = PhysicalAuditItem
    else:
        raise InventoryValidationError("El propietario de la evidencia no es válido.")
    try:
        return model.objects.get(pk=owner_id, is_deleted=False)
    except model.DoesNotExist as exc:
        raise InventoryValidationError("El registro de auditoría no existe.") from exc


def _hash(uploaded):
    digest = sha256()
    for chunk in uploaded.chunks():
        digest.update(chunk)
    uploaded.seek(0)
    return digest.hexdigest()


@transaction.atomic
def upload_physical_audit_document(*, data, actor_id):
    actor = _actor(actor_id)
    if data.owner_type not in AUDIT_OWNER_TYPES:
        raise InventoryValidationError("El documento no pertenece a una auditoría física.")
    _owner(data.owner_type, data.owner_id)
    uploaded = data.file
    document = AssetDocument(
        owner_type=data.owner_type, owner_id=data.owner_id,
        document_type=data.document_type, title=str(data.title or "").strip(),
        description=str(data.description or "").strip(), file=uploaded,
        original_filename=data.original_filename, content_type=data.content_type,
        file_size=getattr(uploaded, "size", None), sha256_hash=_hash(uploaded),
        access_level=data.access_level, is_required_evidence=data.is_required_evidence,
        external_reference=str(data.external_reference or "").strip(),
        uploaded_by_id=actor.id, uploaded_by_name_snapshot=actor.display_name,
        uploaded_by_email_snapshot=actor.normalized_email,
        validation_status=DocumentValidationStatus.PENDING,
    )
    document.full_clean()
    document.save()
    return document


@transaction.atomic
def upload_physical_audit_photo(*, data, actor_id):
    actor = _actor(actor_id)
    if data.owner_type not in AUDIT_OWNER_TYPES:
        raise InventoryValidationError("La fotografía no pertenece a una auditoría física.")
    _owner(data.owner_type, data.owner_id)
    uploaded = data.image
    geo = data.geolocation
    photo = AssetPhoto(
        owner_type=data.owner_type, owner_id=data.owner_id,
        photo_type=data.photo_type, image=uploaded,
        original_filename=data.original_filename, content_type=data.content_type,
        file_size=getattr(uploaded, "size", None), sha256_hash=_hash(uploaded),
        uploaded_by_id=actor.id, uploaded_by_name_snapshot=actor.display_name,
        uploaded_by_email_snapshot=actor.normalized_email,
        caption=str(data.caption or "").strip(),
        is_required_evidence=data.is_required_evidence,
        latitude=geo.latitude if geo else None,
        longitude=geo.longitude if geo else None,
    )
    photo.full_clean()
    photo.save()
    return photo


__all__ = ["upload_physical_audit_document", "upload_physical_audit_photo"]
