"""Data models for Phase 09 Agentic Task Execution and Multi-Step Workflows."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from nova.planning.models import Plan, PlanStep
from nova.protocol.models import TaskStatus
from nova.tools.metadata import ToolRiskLevel


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ObservationDomain(str, Enum):
    """Domain source of an empirical observation."""

    WINDOWS = "WINDOWS"
    BROWSER = "BROWSER"
    FILESYSTEM = "FILESYSTEM"
    PROCESS = "PROCESS"
    SCREEN = "SCREEN"
    CLIPBOARD = "CLIPBOARD"
    APPLICATION = "APPLICATION"
    GENERAL = "GENERAL"


class TaskApprovalState(str, Enum):
    """Approval lifecycle for restricted or high-risk tasks/steps."""

    NONE = "NONE"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class FailureClassification(str, Enum):
    """Classification of step execution failures for adaptive handling."""

    RECOVERABLE = "RECOVERABLE"
    NON_RECOVERABLE = "NON_RECOVERABLE"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


class ReversibilityType(str, Enum):
    """Whether mutations performed by a step can be reversed."""

    REVERSIBLE = "REVERSIBLE"
    PARTIALLY_REVERSIBLE = "PARTIALLY_REVERSIBLE"
    NON_REVERSIBLE = "NON_REVERSIBLE"


class Observation(BaseModel):
    """Normalized empirical observation captured across control domains.

    Enforces epistemic honesty: tool outputs and raw web contents are bounded
    and tagged with safety flags before passing to orchestrator reasoning.
    """

    source: ObservationDomain
    timestamp: str = Field(default_factory=_utc_now_iso)
    entity: str = Field(description="Target identifier: window title, tab_id, file path, PID, etc.")
    state: str = Field(description="Observed state: exists, active, open, terminated, text_match, etc.")
    relevant_attributes: dict[str, Any] = Field(default_factory=dict, description="Bounded attributes")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    safety_flags: list[str] = Field(default_factory=list, description="e.g. prompt_injection_flagged")


class StepApprovalRequest(BaseModel):
    """Explicit human authorization request for a high-risk or policy-gated step."""

    task_id: str
    step_id: int
    tool: str
    args: dict[str, Any]
    target: str
    risk_level: ToolRiskLevel
    reason: str
    requested_at: str = Field(default_factory=_utc_now_iso)
    expires_at: str
    approved_by: str | None = None


class StepRetryRecord(BaseModel):
    """Telemetry record for a step retry attempt."""

    step_id: int
    attempt: int
    error: str
    timestamp: str = Field(default_factory=_utc_now_iso)
    recovered: bool = False


class TaskProgress(BaseModel):
    """Empirical progress report reflecting actual step milestones."""

    total_steps: int = 0
    completed_steps: int = 0
    current_step_id: int | None = None
    current_step_description: str | None = None
    percent: float = 0.0


class TaskArtifact(BaseModel):
    """Structured verifiable artifact produced by a task."""

    artifact_id: str
    type: str = Field(description="file, browser_result, screenshot, clipboard, report")
    path: str | None = None
    source: str = Field(description="Domain or tool that generated this artifact")
    created_at: str = Field(default_factory=_utc_now_iso)
    task_id: str
    verification_state: str = "verified"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Structured result returned upon task completion."""

    task_id: str
    status: TaskStatus
    summary: str
    steps_completed: int
    steps_failed: int
    artifacts: list[TaskArtifact] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    verification: str = "passed"
    duration_seconds: float = 0.0


class OrchestratedTask(BaseModel):
    """First-class durable task model with lifecycle state and recovery data."""

    task_id: str
    request_id: str
    device_id: str
    query: str
    status: TaskStatus = TaskStatus.QUEUED
    created_at: str = Field(default_factory=_utc_now_iso)
    started_at: str | None = None
    completed_at: str | None = None
    actor: str = "user"
    plan: Plan | None = None
    current_step_index: int = 0
    progress: TaskProgress = Field(default_factory=TaskProgress)
    risk_level: ToolRiskLevel = ToolRiskLevel.LOW
    approval_state: TaskApprovalState = TaskApprovalState.NONE
    pending_approval: StepApprovalRequest | None = None
    result: TaskResult | None = None
    error: str | None = None
    cancellation_requested: bool = False
    cancellation_reason: str | None = None
    artifacts: list[TaskArtifact] = Field(default_factory=list)
    retry_history: list[StepRetryRecord] = Field(default_factory=list)
    pause_reason: str | None = None
    context_summary: list[str] = Field(default_factory=list)
