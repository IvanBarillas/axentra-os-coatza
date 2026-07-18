from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuditRequestContext:
    request_id: UUID
    ip_address: str | None = None
    user_agent: str = ""


@dataclass(frozen=True, slots=True)
class CreateAuditEventDTO:
    action: str
    summary: str
    actor_id: UUID | None = None
    level: str = "INFO"
    asset_id: UUID | None = None
    intake_request_id: UUID | None = None
    target_model: str = ""
    target_id: UUID | None = None
    reason: str = ""
    old_value: Mapping[str, Any] = field(default_factory=dict)
    new_value: Mapping[str, Any] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)
    bypass_used: bool = False
    bypass_reason: str = ""
    occurred_at: datetime | None = None


__all__ = ["AuditRequestContext", "CreateAuditEventDTO"]
