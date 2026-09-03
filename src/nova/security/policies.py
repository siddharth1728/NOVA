"""Bridge between NOVA security architecture and native Google Antigravity policy hooks."""

from collections.abc import Awaitable, Callable
from typing import Any

from google.antigravity.hooks import policy
from google.antigravity.types import ToolCall

from nova.config.settings import NovaSettings, SecurityMode, get_settings
from nova.security.approvals import ApprovalHandler, ConsoleApprovalHandler
from nova.security.risk import RiskEvaluator
from nova.tools.metadata import ToolRiskLevel


def create_sdk_approval_adapter(
    handler: ApprovalHandler,
    risk_evaluator: RiskEvaluator,
) -> Callable[[ToolCall], Awaitable[bool]]:
    """Converts a NOVA ApprovalHandler into the native Antigravity AskUserHandler callable."""

    async def _sdk_handler(tool_call: ToolCall) -> bool:
        tool_name = tool_call.name.value if hasattr(tool_call.name, "value") else str(tool_call.name)
        risk = risk_evaluator.evaluate_tool(tool_name, tool_call.args)
        reason = f"Security policy requires human confirmation for {risk.value} tool call"
        return await handler.request_approval(
            tool_name=tool_name,
            args=tool_call.args,
            risk_level=risk,
            reason=reason,
        )

    return _sdk_handler


def build_antigravity_policies(
    settings: NovaSettings | None = None,
    approval_handler: ApprovalHandler | None = None,
) -> list[policy.Policy]:
    """Generates the list of native Antigravity policies enforcing NOVA's security model.

    Args:
        settings: Active NOVA configuration.
        approval_handler: Handler for interactive human approval.

    Returns:
        List of configured Antigravity Policy instances.
    """
    cfg = settings or get_settings()
    app_handler = approval_handler or ConsoleApprovalHandler()
    evaluator = RiskEvaluator()
    ask_adapter = create_sdk_approval_adapter(app_handler, evaluator)

    policies: list[policy.Policy] = []

    # 1. Workspace boundary enforcement
    # Native policy.workspace_only confines file-related tools to workspace directories
    workspace_str = str(cfg.workspace_root)
    policies.extend(policy.workspace_only([workspace_str]))

    # 2. Policy rules based on SecurityMode
    if cfg.security_mode == SecurityMode.STRICT:
        # Deny all destructive/privileged and write operations
        policies.append(policy.deny("run_command"))
        policies.append(policy.deny("create_file"))
        policies.append(policy.deny("edit_file"))
        policies.append(policy.deny("invoke_subagent"))

        # Explicitly allow safe read-only operations
        policies.append(policy.allow("list_directory"))
        policies.append(policy.allow("search_directory"))
        policies.append(policy.allow("find_file"))
        policies.append(policy.allow("view_file"))
        policies.append(policy.allow("read_url_content"))
        policies.append(policy.allow("finish"))

    elif cfg.security_mode == SecurityMode.STANDARD:
        # Terminal execution remains strictly blocked or requires approval
        policies.append(policy.deny("run_command"))

        # State modifying tools require interactive approval
        policies.append(policy.ask_user("create_file", handler=ask_adapter))
        policies.append(policy.ask_user("edit_file", handler=ask_adapter))
        policies.append(policy.ask_user("invoke_subagent", handler=ask_adapter))

        # Safe tools allowed
        policies.append(policy.allow("list_directory"))
        policies.append(policy.allow("search_directory"))
        policies.append(policy.allow("find_file"))
        policies.append(policy.allow("view_file"))
        policies.append(policy.allow("read_url_content"))
        policies.append(policy.allow("search_web"))
        policies.append(policy.allow("finish"))

    elif cfg.security_mode == SecurityMode.PERMISSIVE:
        # Experimental permissive mode
        policies.append(policy.ask_user("run_command", handler=ask_adapter))
        policies.append(policy.allow_all())

    return policies
