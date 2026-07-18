from django.db.models import Q

from apps.inventory.models import (
    AssetDocument, AssetPhoto, DocumentValidationStatus,
    InventoryDocumentOwnerType,
)


class DocumentSelectors:
    @staticmethod
    def documents(*, owner_type=None, owner_id=None, document_type=None, validation_status=None, q=""):
        qs = AssetDocument.objects.filter(is_deleted=False).select_related("uploaded_by", "validated_by")
        if owner_type:
            qs = qs.filter(owner_type=owner_type)
        if owner_id:
            qs = qs.filter(owner_id=owner_id)
        if document_type:
            qs = qs.filter(document_type=document_type)
        if validation_status:
            qs = qs.filter(validation_status=validation_status)
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(original_filename__icontains=q) | Q(notes__icontains=q))
        return qs.order_by("-created_at")

    @classmethod
    def asset_documents(cls, asset_id):
        return cls.documents(owner_type=InventoryDocumentOwnerType.ASSET, owner_id=asset_id)

    @classmethod
    def pending_validation(cls):
        return cls.documents(validation_status=DocumentValidationStatus.PENDING)

    @staticmethod
    def photos(*, owner_type=None, owner_id=None, photo_type=None):
        qs = AssetPhoto.objects.filter(is_deleted=False).select_related("uploaded_by")
        if owner_type:
            qs = qs.filter(owner_type=owner_type)
        if owner_id:
            qs = qs.filter(owner_id=owner_id)
        if photo_type:
            qs = qs.filter(photo_type=photo_type)
        return qs.order_by("-created_at")

    @classmethod
    def asset_photos(cls, asset_id):
        return cls.photos(owner_type=InventoryDocumentOwnerType.ASSET, owner_id=asset_id)
