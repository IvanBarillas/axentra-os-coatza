from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID

from apps.inventory.dtos.common_dtos import (
    ExternalReferenceDTO,
    GeoPointDTO,
)


@dataclass(frozen=True, slots=True)
class OrganizationalDestinationDTO:
    department_id: UUID | None = None
    area_id: UUID | None = None
    site_id: UUID | None = None
    user_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateInventoryMovementDTO:
    asset_id: UUID
    movement_type: str
    reason: str
    occurred_at: datetime
    destination: OrganizationalDestinationDTO | None = None
    condition_after: str = ""
    reference: ExternalReferenceDTO | None = None
    corrects_movement_id: UUID | None = None
    bypass_reason: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TransferAssetDTO:
    asset_id: UUID
    destination_department_id: UUID
    reason: str
    destination_area_id: UUID | None = None
    destination_site_id: UUID | None = None
    destination_custodian_id: UUID | None = None
    occurred_at: datetime | None = None
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class ReassignAssetDTO:
    asset_id: UUID
    new_custodian_id: UUID
    reason: str
    department_id: UUID | None = None
    area_id: UUID | None = None
    site_id: UUID | None = None
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ChangeAssetLocationDTO:
    asset_id: UUID
    reason: str
    department_id: UUID | None = None
    area_id: UUID | None = None
    site_id: UUID | None = None
    geolocation: GeoPointDTO | None = None
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class MaintenanceMovementDTO:
    asset_id: UUID
    reason: str
    service_order_reference: ExternalReferenceDTO
    physical_condition: str = ""
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class MovementResultDTO:
    movement_id: UUID
    asset_id: UUID
    movement_type: str
    correlation_id: UUID


__all__ = [
    "ChangeAssetLocationDTO",
    "CreateInventoryMovementDTO",
    "MaintenanceMovementDTO",
    "MovementResultDTO",
    "OrganizationalDestinationDTO",
    "ReassignAssetDTO",
    "TransferAssetDTO",
]
