from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateAssetLoanDTO:
    asset_id: UUID
    borrower_name: str
    origin_department_id: UUID
    due_at: datetime
    purpose: str
    borrower_id: UUID | None = None
    borrower_email: str = ""
    borrower_position: str = ""
    external_borrower: bool = False
    external_organization: str = ""
    external_identification: str = ""
    origin_area_id: UUID | None = None
    origin_site_id: UUID | None = None
    destination_department_id: UUID | None = None
    destination_area_id: UUID | None = None
    destination_site_id: UUID | None = None
    external_destination: str = ""


@dataclass(frozen=True, slots=True)
class DepartmentLoanDecisionDTO:
    approve: bool
    comment: str = ""
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class AuthorizeAssetLoanDTO:
    approve: bool
    comment: str = ""
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class DeliverAssetLoanDTO:
    delivered_at: datetime
    delivery_condition: str
    notes: str = ""


@dataclass(frozen=True, slots=True)
class RequestLoanReturnDTO:
    requested_at: datetime
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ReturnAssetLoanDTO:
    returned_at: datetime
    return_condition: str
    returned_by_id: UUID
    notes: str = ""


@dataclass(frozen=True, slots=True)
class CancelAssetLoanDTO:
    reason: str
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class LoanTransitionResultDTO:
    loan_id: UUID
    asset_id: UUID
    previous_status: str
    current_status: str
    movement_id: UUID | None = None
    bypass_used: bool = False


__all__ = [
    "AuthorizeAssetLoanDTO",
    "CancelAssetLoanDTO",
    "CreateAssetLoanDTO",
    "DeliverAssetLoanDTO",
    "DepartmentLoanDecisionDTO",
    "LoanTransitionResultDTO",
    "RequestLoanReturnDTO",
    "ReturnAssetLoanDTO",
]
