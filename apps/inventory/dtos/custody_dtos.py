from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateCustodyAssignmentDTO:
    asset_id: UUID
    assignee_mode: str
    assigned_at: datetime
    assigned_to_id: UUID | None = None
    notes: str = ""
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class AuthorizeCustodyAssignmentDTO:
    comment: str = ""
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class AcceptCustodyAssignmentDTO:
    acceptance_method: str
    signature_hash: str = ""
    comment: str = ""


@dataclass(frozen=True, slots=True)
class RejectCustodyAssignmentDTO:
    reason: str


@dataclass(frozen=True, slots=True)
class ReturnCustodyAssignmentDTO:
    returned_at: datetime
    physical_condition: str
    notes: str = ""


@dataclass(frozen=True, slots=True)
class CancelCustodyAssignmentDTO:
    reason: str
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class CustodyTransitionResultDTO:
    custody_assignment_id: UUID
    asset_id: UUID
    previous_status: str
    current_status: str
    event_id: UUID
    movement_id: UUID | None = None
    bypass_used: bool = False


__all__ = [
    "AcceptCustodyAssignmentDTO",
    "AuthorizeCustodyAssignmentDTO",
    "CancelCustodyAssignmentDTO",
    "CreateCustodyAssignmentDTO",
    "CustodyTransitionResultDTO",
    "RejectCustodyAssignmentDTO",
    "ReturnCustodyAssignmentDTO",
]

