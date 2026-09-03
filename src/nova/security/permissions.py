"""Permission evaluation engine and workspace boundary enforcement."""

from enum import Enum
import os
from pathlib import Path
import sys
from typing import Any

from nova.config.settings import NovaSettings, SecurityMode, get_settings
from nova.errors import PermissionDeniedError
from nova.security.risk import RiskEvaluator
from nova.tools.metadata import ToolRiskLevel
from nova.tools.registry import ToolRegistry, get_tool_registry

# Argument keys that represent filesystem paths in tool invocations
PATH_ARGUMENT_KEYS = frozenset(
    {"path", "file_path", "directory_path", "TargetFile", "SearchPath", "output_path", "dest"}
)


class PermissionDecision(str, Enum):
    """Enforceable decision on a requested action."""

    ALLOW = "ALLOW"
    ASK = "ASK"
    DENY = "DENY"


from nova.security.paths import is_confined


def check_workspace_containment(target_path: Path | str, workspace_root: Path | str) -> bool:
    """Verifies that target_path resides safely within workspace_root."""
    return is_confined(target_path, workspace_root)


class PermissionEngine:
    """Evaluates requested tool executions against security policies and boundaries."""

    def __init__(
        self,
        settings: NovaSettings | None = None,
        registry: ToolRegistry | None = None,
        risk_evaluator: RiskEvaluator | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.registry = registry or get_tool_registry()
        self.risk_evaluator = risk_evaluator or RiskEvaluator(self.registry)

    def extract_path_argument(self, args: dict[str, Any]) -> str | None:
        """Extracts any path argument from the tool argument dictionary."""
        for key in PATH_ARGUMENT_KEYS:
            if key in args and isinstance(args[key], str):
                return args[key]
        return None

    def evaluate(
        self,
        tool_name: str,
        args: dict[str, Any] | None = None,
    ) -> tuple[PermissionDecision, str]:
        """Evaluates whether a tool call should be allowed, requested, or denied.

        Args:
            tool_name: Name of tool being called.
            args: Optional argument payload.

        Returns:
            Tuple of (PermissionDecision, reason_string).
        """
        tool_args = args or {}

        # 1. Boundary Check: Confinement to workspace
        if path_arg := self.extract_path_argument(tool_args):
            if not check_workspace_containment(path_arg, self.settings.workspace_root):
                return (
                    PermissionDecision.DENY,
                    f"Path '{path_arg}' lies outside workspace root '{self.settings.workspace_root}'",
                )

        # 2. Risk Evaluation
        risk = self.risk_evaluator.evaluate_tool(tool_name, tool_args)
        mode = self.settings.security_mode

        # 3. Policy Decision Matrix
        if mode == SecurityMode.STRICT:
            if risk == ToolRiskLevel.READ_ONLY:
                return PermissionDecision.ALLOW, "Read-only operation allowed in STRICT mode"
            return (
                PermissionDecision.DENY,
                f"Tool '{tool_name}' ({risk.value}) is denied in STRICT mode (only READ_ONLY permitted)",
            )

        elif mode == SecurityMode.STANDARD:
            if risk == ToolRiskLevel.READ_ONLY:
                return PermissionDecision.ALLOW, "Read-only operation allowed"
            if risk == ToolRiskLevel.LOW:
                return PermissionDecision.ALLOW, "Low-risk operation allowed in STANDARD mode"
            if risk == ToolRiskLevel.MEDIUM:
                if self.settings.require_approval_for_medium_risk:
                    return PermissionDecision.ASK, f"Medium-risk tool '{tool_name}' requires confirmation"
                return PermissionDecision.ALLOW, "Medium-risk operation permitted by settings"
            return (
                PermissionDecision.DENY,
                f"Tool '{tool_name}' ({risk.value}) is denied in STANDARD mode",
            )

        elif mode == SecurityMode.PERMISSIVE:
            if risk in (ToolRiskLevel.READ_ONLY, ToolRiskLevel.LOW, ToolRiskLevel.MEDIUM):
                return PermissionDecision.ALLOW, f"Operation permitted in PERMISSIVE mode ({risk.value})"
            if risk == ToolRiskLevel.HIGH:
                return PermissionDecision.ASK, f"High-risk tool '{tool_name}' requires confirmation"
            return PermissionDecision.DENY, f"Critical risk tool '{tool_name}' denied even in PERMISSIVE mode"

        return PermissionDecision.DENY, "Unknown security policy configuration"

    def enforce_or_raise(self, tool_name: str, args: dict[str, Any] | None = None) -> PermissionDecision:
        """Evaluates permission and raises PermissionDeniedError if DENY."""
        decision, reason = self.evaluate(tool_name, args)
        if decision == PermissionDecision.DENY:
            risk = self.risk_evaluator.evaluate_tool(tool_name, args)
            path_arg = self.extract_path_argument(args or {})
            raise PermissionDeniedError(
                reason,
                tool_name=tool_name,
                risk_level=risk.value,
                target_path=path_arg,
            )
        return decision
