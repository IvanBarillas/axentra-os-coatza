from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateAssetIntakeDTO:
    name: str
    category_id: UUID
    requested_department_id: UUID
    acquisition_type: str
    acquisition_cost: Decimal
    description: str = ""
    expenditure_object_id: UUID | None = None
    accounting_account_id: UUID | None = None
    acquisition_date: date | None = None
    reception_date: date | None = None
    residual_value: Decimal = Decimal("0.00")
    manufacturer_id: UUID | None = None
    model_id: UUID | None = None
    serial_number: str | None = None
    supplier_id: UUID | None = None
    contract_id: UUID | None = None
    requested_site_id: UUID | None = None
    requested_area_id: UUID | None = None
    proposed_custodian_id: UUID | None = None
    notes: str = ""
    extra_attributes: Mapping[str, Any] = field(default_factory=dict)
    source_app: str = ""
    source_model: str = ""
    source_object_id: UUID | None = None
    source_folio: str = ""


@dataclass(frozen=True, slots=True)
class UpdateAssetIntakeDTO:
    name: str
    category_id: UUID
    requested_department_id: UUID
    acquisition_type: str
    acquisition_cost: Decimal
    description: str = ""
    expenditure_object_id: UUID | None = None
    accounting_account_id: UUID | None = None
    acquisition_date: date | None = None
    reception_date: date | None = None
    residual_value: Decimal = Decimal("0.00")
    manufacturer_id: UUID | None = None
    model_id: UUID | None = None
    serial_number: str | None = None
    supplier_id: UUID | None = None
    contract_id: UUID | None = None
    requested_site_id: UUID | None = None
    requested_area_id: UUID | None = None
    proposed_custodian_id: UUID | None = None
    notes: str = ""
    extra_attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DepartmentIntakeDecisionDTO:
    approve: bool
    comment: str = ""
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class PatrimonyApprovalDTO:
    expenditure_object_id: UUID
    accounting_account_id: UUID | None = None
    physical_condition: str = "GOOD"
    residual_value: Decimal | None = None
    useful_life_months: int | None = None
    observation: str = ""


@dataclass(frozen=True, slots=True)
class PatrimonyObservationDTO:
    observation: str


@dataclass(frozen=True, slots=True)
class CancelAssetIntakeDTO:
    reason: str
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class CapitalizationResultDTO:
    asset_type_code: str
    control_type: str
    is_capitalizable: bool
    uma_value_id: UUID | None
    uma_value_applied: Decimal | None
    uma_multiplier_applied: Decimal | None
    capitalization_threshold_amount: Decimal | None
    rule_snapshot: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class IntakeTransitionResultDTO:
    intake_request_id: UUID
    request_number: str
    previous_status: str
    current_status: str
    decision_id: UUID
    request_id: UUID
    bypass_used: bool = False


@dataclass(frozen=True, slots=True)
class AssetRegistrationResultDTO:
    intake_request_id: UUID
    asset_id: UUID
    official_inventory_number: str
    internal_inventory_number: str
    movement_id: UUID
    decision_id: UUID
    request_id: UUID
    bypass_used: bool = False


__all__ = [
    "AssetRegistrationResultDTO",
    "CancelAssetIntakeDTO",
    "CapitalizationResultDTO",
    "CreateAssetIntakeDTO",
    "DepartmentIntakeDecisionDTO",
    "IntakeTransitionResultDTO",
    "PatrimonyApprovalDTO",
    "PatrimonyObservationDTO",
    "UpdateAssetIntakeDTO",
]
