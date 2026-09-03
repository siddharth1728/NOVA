"""Structured event types and audit data models for NOVA."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventType(str, Enum):
    """Lifecycle event taxonomy."""

    SESSION_STARTED = "SESSION_STARTED"
    SESSION_ENDED = "SESSION_ENDED"
    USER_REQUEST_RECEIVED = "USER_REQUEST_RECEIVED"
    PLAN_CREATED = "PLAN_CREATED"
    TOOL_REQUESTED = "TOOL_REQUESTED"
    TOOL_APPROVED = "TOOL_APPROVED"
    TOOL_DENIED = "TOOL_DENIED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    TOOL_FAILED = "TOOL_FAILED"
    VERIFICATION_STARTED = "VERIFICATION_STARTED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"


class NovaEvent(BaseModel):
    """Strongly typed telemetry event."""

    event_type: EventType
    timestamp: str = Field(default_factory=_utc_now)
    session_id: str = Field(default="")
    task_id: str = Field(default="")
    data: dict[str, Any] = Field(default_factory=dict)


class AuditRecord(BaseModel):
    """Structured record for the append-only security and operational audit trail."""

    timestamp: str = Field(default_factory=_utc_now)
    task_id: str = Field(default="standalone")
    session_id: str = Field(default="standalone")
    agent: str = Field(default="nova-core")
    tool: str = Field(description="Tool identifier")
    risk_level: str = Field(default="READ_ONLY")
    approval_state: str = Field(default="AUTO_ALLOWED")
    input_summary: str = Field(default="")
    result_summary: str = Field(default="")
    success: bool = Field(default=True)
    duration_ms: float = Field(default=0.0)
    error: str | None = Field(default=None)
