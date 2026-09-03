"""Tool metadata and risk classification types."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from nova.tools.categories import ToolCategory


class ToolRiskLevel(str, Enum):
    """5-tier risk taxonomy for tool execution."""

    READ_ONLY = "READ_ONLY"  # Pure observation, inspects without mutations
    LOW = "LOW"  # Minor non-destructive operations (e.g. web search, questions)
    MEDIUM = "MEDIUM"  # Reversible state mutations (e.g. creating or editing a file in workspace)
    HIGH = "HIGH"  # Irreversible modifications, external transmissions, or deletions
    CRITICAL = "CRITICAL"  # Shell commands, arbitrary process execution, privileged host access

    @property
    def score(self) -> int:
        """Numeric rank for risk comparisons."""
        order = {
            ToolRiskLevel.READ_ONLY: 0,
            ToolRiskLevel.LOW: 1,
            ToolRiskLevel.MEDIUM: 2,
            ToolRiskLevel.HIGH: 3,
            ToolRiskLevel.CRITICAL: 4,
        }
        return order[self]

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, ToolRiskLevel):
            return self.score >= other.score
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, ToolRiskLevel):
            return self.score > other.score
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if isinstance(other, ToolRiskLevel):
            return self.score <= other.score
        return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, ToolRiskLevel):
            return self.score < other.score
        return NotImplemented


class ToolMetadata(BaseModel):
    """Formal descriptor for tool capabilities and safety constraints."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Unique tool identifier")
    description: str = Field(description="Human and model-readable description of functionality")
    category: ToolCategory = Field(description="Domain category")
    risk_level: ToolRiskLevel = Field(
        default=ToolRiskLevel.READ_ONLY,
        description="Assigned safety risk tier",
    )
    requires_approval: bool = Field(
        default=False,
        description="Whether tool invocation mandates human-in-the-loop authorization",
    )
    mutates_state: bool = Field(
        default=False,
        description="Whether execution alters workspace or environment state",
    )
    accesses_sensitive_data: bool = Field(
        default=False,
        description="Whether tool can read credentials or private host information",
    )
    is_reversible: bool = Field(
        default=True,
        description="Whether effects of the tool can be safely rolled back",
    )
    input_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON schema representing input arguments",
    )
    output_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON schema representing return payload",
    )
