from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FolioScope:
    policy_id: UUID
    municipality_code: str
    fiscal_year: int
    conac_code: str
    dependency_id: UUID
    dependency_code: str
    asset_type_code: str
    progressive_length: int


@dataclass(frozen=True, slots=True)
class GenerateInventoryFolioDTO:
    fiscal_year: int
    expenditure_object_id: UUID
    department_id: UUID
    asset_type_code: str


@dataclass(frozen=True, slots=True)
class GeneratedInventoryFolio:
    official_inventory_number: str
    internal_inventory_number: str
    progressive_number: int
    sequence_id: UUID
    scope: FolioScope


__all__ = [
    "FolioScope",
    "GenerateInventoryFolioDTO",
    "GeneratedInventoryFolio",
]
