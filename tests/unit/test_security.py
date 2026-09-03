"""Unit tests for NOVA security, permissions, and policy bridge."""

from pathlib import Path
import pytest

from nova.config.settings import Environment, NovaSettings, SecurityMode
from nova.errors import PermissionDeniedError
from nova.security.approvals import AutomatedApprovalHandler
from nova.security.permissions import (
    PermissionDecision,
    PermissionEngine,
    check_workspace_containment,
)
from nova.security.policies import build_antigravity_policies
from nova.tools.metadata import ToolRiskLevel
from nova.tools.registry import ToolRegistry


def test_workspace_containment_valid(temp_workspace: Path) -> None:
    # Exact workspace root
    assert check_workspace_containment(temp_workspace, temp_workspace)

    # File directly in workspace
    assert check_workspace_containment(temp_workspace / "hello.txt", temp_workspace)

    # Nested file
    assert check_workspace_containment(temp_workspace / "sub" / "nested.py", temp_workspace)


def test_workspace_containment_escape_attempt(temp_workspace: Path) -> None:
    # Parent directory escape
    escape_path = temp_workspace / ".." / "system32"
    assert not check_workspace_containment(escape_path, temp_workspace)

    # Root drive / external path
    assert not check_workspace_containment(Path("C:/Windows/System32"), temp_workspace)


def test_permission_engine_strict_mode(temp_workspace: Path, tool_registry: ToolRegistry) -> None:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        security_mode=SecurityMode.STRICT,
    )
    engine = PermissionEngine(settings=settings, registry=tool_registry)

    # 1. Safe read-only within workspace -> ALLOW
    decision, _ = engine.evaluate("list_directory", {"directory_path": str(temp_workspace)})
    assert decision == PermissionDecision.ALLOW

    # 2. Safe read-only outside workspace -> DENY
    decision, reason = engine.evaluate("list_directory", {"directory_path": "C:/Windows"})
    assert decision == PermissionDecision.DENY
    assert "outside workspace" in reason

    # 3. Medium-risk file edit in STRICT -> DENY
    decision, _ = engine.evaluate("edit_file", {"file_path": str(temp_workspace / "hello.txt")})
    assert decision == PermissionDecision.DENY

    # 4. Critical run_command in STRICT -> DENY
    decision, _ = engine.evaluate("run_command", {"CommandLine": "ls"})
    assert decision == PermissionDecision.DENY


def test_permission_engine_enforce_or_raise(temp_workspace: Path, tool_registry: ToolRegistry) -> None:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        security_mode=SecurityMode.STRICT,
    )
    engine = PermissionEngine(settings=settings, registry=tool_registry)

    with pytest.raises(PermissionDeniedError) as exc_info:
        engine.enforce_or_raise("run_command", {"CommandLine": "format C:"})
    assert exc_info.value.tool_name == "run_command"
    assert exc_info.value.risk_level == "CRITICAL"


def test_permission_engine_standard_mode_ask(temp_workspace: Path, tool_registry: ToolRegistry) -> None:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        security_mode=SecurityMode.STANDARD,
        require_approval_for_medium_risk=True,
    )
    engine = PermissionEngine(settings=settings, registry=tool_registry)

    decision, reason = engine.evaluate("create_file", {"path": str(temp_workspace / "new.txt")})
    assert decision == PermissionDecision.ASK
    assert "requires confirmation" in reason


@pytest.mark.asyncio
async def test_automated_approval_handlers() -> None:
    approver = AutomatedApprovalHandler(approve_all=True)
    rejector = AutomatedApprovalHandler(approve_all=False)

    res1 = await approver.request_approval("create_file", {}, ToolRiskLevel.MEDIUM, "Test")
    assert res1 is True
    assert len(approver.call_history) == 1

    res2 = await rejector.request_approval("run_command", {}, ToolRiskLevel.CRITICAL, "Test")
    assert res2 is False
    assert len(rejector.call_history) == 1


def test_build_antigravity_policies(test_settings: NovaSettings) -> None:
    policies = build_antigravity_policies(test_settings)
    assert len(policies) > 0
    # Confirms policies object list generates without exception
