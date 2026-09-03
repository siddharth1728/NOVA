"""Domain data models for NOVA's memory subsystem."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserPreference(BaseModel):
    """Personal preference or guideline specified by the user."""

    key: str = Field(description="Unique preference key, e.g. 'code_style'")
    value: Any = Field(description="Preference value")
    category: str = Field(default="general", description="Categorical grouping")
    description: str = Field(default="", description="Context or explanation")
    updated_at: str = Field(default_factory=_utc_now)


class EnvironmentFact(BaseModel):
    """Verified machine or environment property."""

    key: str = Field(description="Property identifier, e.g. 'python_version'")
    value: Any = Field(description="Fact value")
    category: str = Field(default="system", description="Fact domain: system, tools, paths")
    verified: bool = Field(default=True, description="Whether fact was directly observed")
    last_verified_at: str = Field(default_factory=_utc_now)


class TaskState(BaseModel):
    """State tracking for a high-level goal or task."""

    task_id: str = Field(description="Unique task identifier")
    goal: str = Field(description="Original natural language user goal")
    status: str = Field(default="pending", description="Status: pending, running, completed, failed")
    steps: list[str] = Field(default_factory=list, description="Planned or completed steps")
    context: dict[str, Any] = Field(default_factory=dict, description="Task metadata and context")
    updated_at: str = Field(default_factory=_utc_now)


class ExecutionRecord(BaseModel):
    """Audit and memory record of an executed action and its outcome."""

    record_id: str = Field(description="Unique record identifier")
    timestamp: str = Field(default_factory=_utc_now)
    task_id: str = Field(default="standalone", description="Associated task identifier")
    tool: str = Field(description="Tool invoked")
    args_summary: str = Field(description="Sanitized summary of arguments")
    outcome: str = Field(description="Execution summary or result")
    success: bool = Field(description="Whether operation completed successfully")
    verified: bool = Field(default=False, description="Whether post-action outcome was verified")


class LearnedWorkflow(BaseModel):
    """Repeatable procedural workflow synthesized from past successful executions."""

    workflow_id: str = Field(description="Unique workflow identifier")
    name: str = Field(description="Human-readable title")
    goal_pattern: str = Field(description="Trigger pattern or description of intent")
    steps: list[str] = Field(description="Ordered sequence of operations")
    success_count: int = Field(default=1, description="Number of times successfully executed")
    created_at: str = Field(default_factory=_utc_now)


class ProjectContext(BaseModel):
    """Contextual metadata regarding the target project or workspace."""

    project_name: str = Field(description="Name of the workspace or project")
    domain: str = Field(default="", description="Functional domain")
    tech_stack: list[str] = Field(default_factory=list, description="Languages, frameworks, tools")
    key_directories: list[str] = Field(default_factory=list, description="Primary source or config paths")
    architectural_notes: str = Field(default="", description="High-level design decisions")
    updated_at: str = Field(default_factory=_utc_now)
