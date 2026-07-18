from dataclasses import dataclass, field
from typing import Any, BinaryIO, Mapping
from uuid import UUID

from apps.inventory.dtos.common_dtos import GeoPointDTO


@dataclass(frozen=True, slots=True)
class UploadInventoryDocumentDTO:
    owner_type: str
    owner_id: UUID
    document_type: str
    title: str
    file: BinaryIO
    original_filename: str
    content_type: str = ""
    description: str = ""
    access_level: str = "INTERNAL"
    is_required_evidence: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SubmitDocumentValidationDTO:
    comment: str = ""


@dataclass(frozen=True, slots=True)
class ResolveDocumentValidationDTO:
    approve: bool
    comment: str
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class ReplaceInventoryDocumentDTO:
    file: BinaryIO
    original_filename: str
    content_type: str = ""
    reason: str = ""


@dataclass(frozen=True, slots=True)
class UploadInventoryPhotoDTO:
    owner_type: str
    owner_id: UUID
    photo_type: str
    image: BinaryIO
    original_filename: str
    content_type: str = ""
    caption: str = ""
    is_required_evidence: bool = False
    geolocation: GeoPointDTO | None = None


@dataclass(frozen=True, slots=True)
class ResolvePhotoValidationDTO:
    approve: bool
    comment: str = ""


@dataclass(frozen=True, slots=True)
class DocumentOperationResultDTO:
    document_id: UUID
    owner_type: str
    owner_id: UUID
    validation_status: str
    version_number: int


__all__ = [
    "DocumentOperationResultDTO",
    "ReplaceInventoryDocumentDTO",
    "ResolveDocumentValidationDTO",
    "ResolvePhotoValidationDTO",
    "SubmitDocumentValidationDTO",
    "UploadInventoryDocumentDTO",
    "UploadInventoryPhotoDTO",
]
