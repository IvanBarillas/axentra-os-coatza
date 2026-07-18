from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID

from apps.inventory.dtos.common_dtos import GeoPointDTO


@dataclass(frozen=True, slots=True)
class CreatePhysicalAuditSessionDTO:
    name: str
    fiscal_year: int
    scope: str
    site_id: UUID | None = None
    department_id: UUID | None = None
    area_id: UUID | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class FreezePhysicalAuditDTO:
    snapshot_at: datetime
    comment: str = ""


@dataclass(frozen=True, slots=True)
class StartPhysicalAuditDTO:
    started_at: datetime
    comment: str = ""


@dataclass(frozen=True, slots=True)
class ScanPhysicalAuditItemDTO:
    scanned_inventory_number: str
    observed_condition: str
    observed_site_id: UUID | None = None
    observed_department_id: UUID | None = None
    observed_area_id: UUID | None = None
    observed_custodian_id: UUID | None = None
    discrepancy_reason: str = ""
    geolocation: GeoPointDTO | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True, slots=True)
class RegisterUnlistedAuditItemDTO:
    scanned_inventory_number: str
    observed_condition: str = ""
    observed_site_id: UUID | None = None
    observed_department_id: UUID | None = None
    observed_area_id: UUID | None = None
    observed_custodian_id: UUID | None = None
    geolocation: GeoPointDTO | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True, slots=True)
class MarkAuditItemNotFoundDTO:
    reason: str


@dataclass(frozen=True, slots=True)
class ReconcilePhysicalAuditItemDTO:
    result: str
    notes: str
    create_corrective_movement: bool = False


@dataclass(frozen=True, slots=True)
class ClosePhysicalAuditDTO:
    closing_summary: str


@dataclass(frozen=True, slots=True)
class CancelPhysicalAuditDTO:
    reason: str
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class PhysicalAuditTransitionResultDTO:
    session_id: UUID
    previous_status: str
    current_status: str
    expected_assets_count: int = 0
    processed_assets_count: int = 0


__all__ = [
    "CancelPhysicalAuditDTO",
    "ClosePhysicalAuditDTO",
    "CreatePhysicalAuditSessionDTO",
    "FreezePhysicalAuditDTO",
    "MarkAuditItemNotFoundDTO",
    "PhysicalAuditTransitionResultDTO",
    "ReconcilePhysicalAuditItemDTO",
    "RegisterUnlistedAuditItemDTO",
    "ScanPhysicalAuditItemDTO",
    "StartPhysicalAuditDTO",
]
