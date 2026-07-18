from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OperationContextDTO:
    actor_id: UUID
    request_id: UUID
    occurred_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str = ""
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class ExternalReferenceDTO:
    source_app: str
    source_model: str
    source_object_id: UUID
    reference_folio: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GeoPointDTO:
    latitude: str | None = None
    longitude: str | None = None


@dataclass(frozen=True, slots=True)
class ServiceResultDTO:
    object_id: UUID
    request_id: UUID
    status: str
    bypass_used: bool = False


__all__ = [
    "ExternalReferenceDTO",
    "GeoPointDTO",
    "OperationContextDTO",
    "ServiceResultDTO",
]
