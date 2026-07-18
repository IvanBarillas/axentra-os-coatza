from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, BinaryIO, Mapping
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateDepreciationRunDTO:
    frequency: str
    period_year: int
    period_start: date
    period_end: date
    cutoff_at: datetime
    period_month: int | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class CalculateDepreciationDTO:
    run_id: UUID
    asset_ids: tuple[UUID, ...] = field(default_factory=tuple)
    recalculate: bool = False


@dataclass(frozen=True, slots=True)
class CompleteDepreciationRunDTO:
    notes: str = ""


@dataclass(frozen=True, slots=True)
class PostDepreciationRunDTO:
    posting_reference: str
    notes: str = ""
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class CreateAccountingExportDTO:
    export_type: str
    file_format: str
    destination_system: str
    period_start: date
    period_end: date
    cutoff_at: datetime
    filters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CreateReconciliationDTO:
    source_system: str
    period_start: date
    period_end: date
    cutoff_at: datetime
    source_file: BinaryIO
    source_filename: str


@dataclass(frozen=True, slots=True)
class ProcessReconciliationDTO:
    column_mapping: Mapping[str, str] = field(default_factory=dict)
    options: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReviewReconciliationItemDTO:
    result: str
    review_notes: str


@dataclass(frozen=True, slots=True)
class CloseReconciliationDTO:
    closing_notes: str
    bypass_reason: str = ""


@dataclass(frozen=True, slots=True)
class DepreciationRunResultDTO:
    run_id: UUID
    status: str
    asset_count: int
    error_count: int = 0


@dataclass(frozen=True, slots=True)
class ReconciliationResultDTO:
    reconciliation_id: UUID
    status: str
    matched_account_count: int
    different_account_count: int


__all__ = [
    "CalculateDepreciationDTO",
    "CloseReconciliationDTO",
    "CompleteDepreciationRunDTO",
    "CreateAccountingExportDTO",
    "CreateDepreciationRunDTO",
    "CreateReconciliationDTO",
    "DepreciationRunResultDTO",
    "PostDepreciationRunDTO",
    "ProcessReconciliationDTO",
    "ReconciliationResultDTO",
    "ReviewReconciliationItemDTO",
]
