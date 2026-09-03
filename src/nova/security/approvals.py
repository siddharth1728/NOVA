"""Human-in-the-loop approval interfaces and handlers."""

from abc import ABC, abstractmethod
import asyncio
from typing import Any

from nova.tools.metadata import ToolRiskLevel


class ApprovalHandler(ABC):
    """Abstract interface for interactive human authorization."""

    @abstractmethod
    async def request_approval(
        self,
        tool_name: str,
        args: dict[str, Any],
        risk_level: ToolRiskLevel,
        reason: str,
    ) -> bool:
        """Requests user confirmation for a restricted or medium/high risk operation.

        Args:
            tool_name: The name of the tool requested.
            args: The argument payload for the tool.
            risk_level: The risk tier assessed.
            reason: Explanation of why approval is required.

        Returns:
            True if authorized, False otherwise.
        """


class ConsoleApprovalHandler(ApprovalHandler):
    """Interactive terminal prompt asking the human operator for confirmation."""

    async def request_approval(
        self,
        tool_name: str,
        args: dict[str, Any],
        risk_level: ToolRiskLevel,
        reason: str,
    ) -> bool:
        print("\n" + "=" * 60)
        print("  NOVA ACTION APPROVAL REQUIRED")
        print("=" * 60)
        print(f"Tool       : {tool_name}")
        print(f"Risk Level : {risk_level.value}")
        print(f"Reason     : {reason}")
        print(f"Arguments  : {args}")
        print("-" * 60)

        # Run console input asynchronously to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None, lambda: input("Authorize this action? [y/N]: ").strip().lower()
            )
            approved = response in ("y", "yes")
            if approved:
                print("[NOVA Policy] Action APPROVED by user.")
            else:
                print("[NOVA Policy] Action REJECTED by user.")
            return approved
        except Exception:
            return False


class AutomatedApprovalHandler(ApprovalHandler):
    """Deterministic approval handler for automated testing and batch execution."""

    def __init__(self, approve_all: bool = False) -> None:
        self.approve_all = approve_all
        self.call_history: list[dict[str, Any]] = []

    async def request_approval(
        self,
        tool_name: str,
        args: dict[str, Any],
        risk_level: ToolRiskLevel,
        reason: str,
    ) -> bool:
        self.call_history.append(
            {
                "tool_name": tool_name,
                "args": args,
                "risk_level": risk_level,
                "reason": reason,
                "decision": self.approve_all,
            }
        )
        return self.approve_all
