"""Risk assessment engine for tool operations."""

from typing import Any

from nova.tools.metadata import ToolRiskLevel
from nova.tools.registry import ToolRegistry, get_tool_registry


class RiskEvaluator:
    """Evaluates tool invocations and classifies the operational risk."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or get_tool_registry()

    def evaluate_tool(self, tool_name: str, args: dict[str, Any] | None = None) -> ToolRiskLevel:
        """Determines the effective risk level for a tool call.

        Args:
            tool_name: Canonical tool identifier.
            args: Optional tool argument payload.

        Returns:
            The determined ToolRiskLevel.
        """
        meta = self.registry.get_metadata(tool_name)
        if meta is None:
            # Unknown tools default to CRITICAL risk (fail-safe)
            return ToolRiskLevel.CRITICAL

        base_risk = meta.risk_level

        # Dynamic risk escalation based on arguments
        if tool_name == "run_command" and args:
            cmd = str(args.get("CommandLine", "")).lower()
            destructive_keywords = ["rm", "del", "format", "drop", "truncate", "shutdown", "reboot"]
            if any(k in cmd for k in destructive_keywords):
                return ToolRiskLevel.CRITICAL

        return base_risk
