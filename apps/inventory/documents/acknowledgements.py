"""Relación entre documentos emitidos por Inventory y sus acuses."""

from dataclasses import dataclass

from apps.inventory.models import (
    AssetDocument,
    DocumentType,
    DocumentValidationStatus,
    InventoryDocumentOwnerType,
)


@dataclass(frozen=True, slots=True)
class AcknowledgementSpec:
    generated_type: str
    acknowledgement_type: str
    owner_types: tuple[str, ...]
    generated_label: str
    acknowledgement_label: str


@dataclass(frozen=True, slots=True)
class AcknowledgementState:
    code: str
    label: str
    color: str
    document: AssetDocument | None = None


ACKNOWLEDGEMENT_SPECS = {
    DocumentType.CUSTODY_RECEIPT: AcknowledgementSpec(
        DocumentType.CUSTODY_RECEIPT,
        DocumentType.SIGNED_CUSTODY_RECEIPT,
        (
            InventoryDocumentOwnerType.CUSTODY_ASSIGNMENT,
            InventoryDocumentOwnerType.CUSTODY_DOCUMENT,
        ),
        "Vale de resguardo",
        "Acuse firmado de resguardo",
    ),
    DocumentType.LOAN_RECEIPT: AcknowledgementSpec(
        DocumentType.LOAN_RECEIPT,
        DocumentType.SIGNED_LOAN_RECEIPT,
        (InventoryDocumentOwnerType.LOAN,),
        "Vale de préstamo",
        "Acuse firmado de préstamo",
    ),
    DocumentType.RETURN_RECEIPT: AcknowledgementSpec(
        DocumentType.RETURN_RECEIPT,
        DocumentType.SIGNED_RETURN_RECEIPT,
        (
            InventoryDocumentOwnerType.LOAN,
            InventoryDocumentOwnerType.CUSTODY_DOCUMENT,
        ),
        "Constancia de devolución",
        "Acuse firmado de devolución",
    ),
    DocumentType.TRANSFER_RECEIPT: AcknowledgementSpec(
        DocumentType.TRANSFER_RECEIPT,
        DocumentType.SIGNED_TRANSFER_RECEIPT,
        (InventoryDocumentOwnerType.MOVEMENT_REQUEST,),
        "Acta de transferencia",
        "Acuse firmado de transferencia",
    ),
    DocumentType.DISPOSAL_MINUTES: AcknowledgementSpec(
        DocumentType.DISPOSAL_MINUTES,
        DocumentType.SIGNED_DISPOSAL_MINUTES,
        (InventoryDocumentOwnerType.DISPOSAL_REQUEST,),
        "Acta de baja",
        "Acuse firmado del acta de baja",
    ),
    DocumentType.PHYSICAL_AUDIT_REPORT: AcknowledgementSpec(
        DocumentType.PHYSICAL_AUDIT_REPORT,
        DocumentType.SIGNED_PHYSICAL_AUDIT_REPORT,
        (InventoryDocumentOwnerType.PHYSICAL_AUDIT_SESSION,),
        "Reporte de auditoría física",
        "Acuse firmado de auditoría física",
    ),
}


def get_acknowledgement_spec(generated_type, owner_type=None):
    normalized = str(generated_type or "").strip().upper()
    spec = ACKNOWLEDGEMENT_SPECS.get(normalized)
    if spec is None:
        raise ValueError("El documento generado no tiene un acuse configurado.")
    if owner_type and str(owner_type).strip().upper() not in spec.owner_types:
        raise ValueError("El tipo de expediente no corresponde al documento generado.")
    return spec


def get_acknowledgement_state(*, owner_type, owner_id, generated_type):
    spec = get_acknowledgement_spec(generated_type, owner_type)
    document = (
        AssetDocument.objects.filter(
            owner_type=owner_type,
            owner_id=owner_id,
            document_type=spec.acknowledgement_type,
            is_current_version=True,
            is_deleted=False,
        )
        .order_by("-uploaded_at", "-created_at")
        .first()
    )
    if document is None:
        return AcknowledgementState(
            "PENDING_SIGNATURE",
            "Pendiente de firma",
            "amber",
        )
    if document.validation_status == DocumentValidationStatus.VALIDATED:
        return AcknowledgementState(
            "VALIDATED",
            "Acuse validado",
            "emerald",
            document,
        )
    if document.validation_status == DocumentValidationStatus.REJECTED:
        return AcknowledgementState(
            "OBSERVED",
            "Acuse observado",
            "red",
            document,
        )
    return AcknowledgementState(
        "UPLOADED",
        "Acuse integrado",
        "blue",
        document,
    )


__all__ = [
    "ACKNOWLEDGEMENT_SPECS",
    "AcknowledgementSpec",
    "AcknowledgementState",
    "get_acknowledgement_spec",
    "get_acknowledgement_state",
]
