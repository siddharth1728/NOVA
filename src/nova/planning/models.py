"""Data models for multi-step plans and plan integrity verification."""

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field

from nova.tools.metadata import ToolRiskLevel


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PlanStepStatus(str, Enum):
    """Execution status of an individual plan step."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class PlanStatus(str, Enum):
    """Overall status of a multi-step plan."""

    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class PlanStep(BaseModel):
    """A single discrete, dependency-tracked operational milestone."""

    step_id: int = Field(description="1-based unique step index")
    description: str = Field(description="Human-readable step intent")
    tool: str = Field(description="Tool to invoke")
    args: dict[str, Any] = Field(default_factory=dict, description="Tool invocation parameters")
    target: str = Field(description="Target file or directory path")
    dependencies: list[int] = Field(default_factory=list, description="IDs of prerequisite steps")
    expected_postcondition: dict[str, Any] = Field(
        default_factory=dict,
        description="Expected filesystem assertions (e.g. {'exists': True, 'type': 'file'})",
    )
    risk_level: ToolRiskLevel = Field(default=ToolRiskLevel.MEDIUM)
    status: PlanStepStatus = Field(default=PlanStepStatus.PENDING)


class Plan(BaseModel):
    """Multi-step plan with deterministic cryptographic identity."""

    plan_id: str
    goal: str
    workspace_root: str
    steps: list[PlanStep] = Field(default_factory=list)
    risk_ceiling: ToolRiskLevel = Field(default=ToolRiskLevel.MEDIUM)
    plan_hash: str = Field(default="")
    status: PlanStatus = Field(default=PlanStatus.DRAFT)
    created_at: str = Field(default_factory=_utc_now)
    approved_hash: str | None = None

    def compute_plan_hash(self) -> str:
        """Computes a deterministic SHA-256 digest of all execution-critical step data.

        Prevents plan drift and ensures runtime execution matches user approval.
        """
        canonical_steps = []
        for s in sorted(self.steps, key=lambda x: x.step_id):
            canonical_steps.append(
                {
                    "step_id": s.step_id,
                    "tool": s.tool,
                    "args": s.args,
                    "target": s.target,
                    "dependencies": sorted(s.dependencies),
                    "risk_level": s.risk_level.value,
                    "postcondition": s.expected_postcondition,
                }
            )

        envelope = {
            "goal": self.goal,
            "workspace_root": self.workspace_root,
            "steps": canonical_steps,
        }

        canonical_json = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
