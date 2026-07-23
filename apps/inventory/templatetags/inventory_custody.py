from django import template

from apps.inventory.workflows.custody_workflow import (
    get_custody_workflow_mode,
)
from apps.inventory.models import (
    AssetDocument,
    DocumentType,
    InventoryDocumentOwnerType,
)


register = template.Library()


@register.simple_tag
def custody_workflow_mode():
    return get_custody_workflow_mode()


@register.simple_tag
def custody_signed_document(custody):
    return (
        AssetDocument.objects.filter(
            owner_type=InventoryDocumentOwnerType.CUSTODY_ASSIGNMENT,
            owner_id=custody.id,
            document_type=DocumentType.SIGNED_CUSTODY_RECEIPT,
            is_current_version=True,
            is_deleted=False,
        )
        .order_by("-created_at")
        .first()
    )


@register.filter
def invoice_number(record):
    return str(
        (getattr(record, "extra_attributes", None) or {}).get(
            "invoice_number",
            "",
        )
    ).strip()


__all__ = ["custody_signed_document", "custody_workflow_mode", "invoice_number"]
