from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID

from apps.inventory.dtos.common_dtos import ExternalReferenceDTO


@dataclass(frozen=True, slots=True)
class CreateDisposalRequestDTO:
    asset_id: UUID
    reason: str
    description: str
    legal_reference: str = ""
    technical_report_required: bool = False
    required_document_types: tuple[str, ...] = field(default_factory=tuple)
    source_reference: ExternalReferenceDTO | None = None


@dataclass(frozen=True, slots=True)
class SubmitDisposalRequestDTO:
    comment: str = ""


@dataclass(frozen=True, slots=True)
class ResolveDisposalStageDTO:
    stage: str
    decision: str
    comment: str
    bypass_reason: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FinalizeDisposalApprovalDTO:
    approve: bool
    comment: str
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class ExecuteDisposalDTO:
    executed_at: datetime
    execution_notes: str
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class CancelDisposalDTO:
    reason: str
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class DisposalTransitionResultDTO:
    disposal_request_id: UUID
    asset_id: UUID
    previous_status: str
    current_status: str
    approval_id: UUID | None = None
    movement_id: UUID | None = None
    bypass_used: bool = False


__all__ = [
    "CancelDisposalDTO",
    "CreateDisposalRequestDTO",
    "DisposalTransitionResultDTO",
    "ExecuteDisposalDTO",
    "FinalizeDisposalApprovalDTO",
    "ResolveDisposalStageDTO",
    "SubmitDisposalRequestDTO",
]
