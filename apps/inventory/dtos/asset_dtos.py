from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID

from apps.inventory.dtos.common_dtos import GeoPointDTO


@dataclass(frozen=True, slots=True)
class CorrectAssetDTO:
    reason: str
    name: str | None = None
    description: str | None = None
    category_id: UUID | None = None
    accounting_account_id: UUID | None = None
    serial_number: str | None = None
    acquisition_cost: Decimal | None = None
    residual_value: Decimal | None = None
    notes: str | None = None
    extra_attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UpdateAssetConditionDTO:
    physical_condition: str
    reason: str
    operational_status: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateAssetLocationDTO:
    department_id: UUID
    site_id: UUID | None = None
    area_id: UUID | None = None
    custodian_id: UUID | None = None
    reason: str = ""
    geolocation: GeoPointDTO | None = None


@dataclass(frozen=True, slots=True)
class AssetStateResultDTO:
    asset_id: UUID
    previous_patrimonial_status: str
    patrimonial_status: str
    previous_operational_status: str
    operational_status: str
    movement_id: UUID | None = None


__all__ = [
    "AssetStateResultDTO",
    "CorrectAssetDTO",
    "UpdateAssetConditionDTO",
    "UpdateAssetLocationDTO",
]
