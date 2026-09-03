"""Negative security tests: Proving that unsafe, out-of-boundary, and prohibited actions are blocked."""

from pathlib import Path
import pytest

from nova.config.settings import Environment, NovaSettings, SecurityMode
from nova.errors import ConfigurationError, PermissionDeniedError
from nova.security.permissions import PermissionDecision, PermissionEngine
from nova.tools.registry import ToolRegistry


def test_blocked_path_traversal(temp_workspace: Path, tool_registry: ToolRegistry) -> None:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        security_mode=SecurityMode.STRICT,
    )
    engine = PermissionEngine(settings=settings, registry=tool_registry)

    # Attempt directory traversal attacks
    traversal_paths = [
        "../../etc/passwd",
        "../..\\Windows\\System32",
        str(temp_workspace / ".." / "outside.txt"),
        "C:/Users",
    ]
    for bad_path in traversal_paths:
        decision, reason = engine.evaluate("view_file", {"path": bad_path})
        assert decision == PermissionDecision.DENY
        assert "outside workspace" in reason


def test_blocked_critical_tools_in_all_modes(temp_workspace: Path, tool_registry: ToolRegistry) -> None:
    # run_command must be DENIED in STRICT mode
    strict_engine = PermissionEngine(
        settings=NovaSettings(workspace_root=temp_workspace, security_mode=SecurityMode.STRICT),
        registry=tool_registry,
    )
    assert strict_engine.evaluate("run_command", {"CommandLine": "dir"})[0] == PermissionDecision.DENY

    # run_command must be DENIED in STANDARD mode
    standard_engine = PermissionEngine(
        settings=NovaSettings(workspace_root=temp_workspace, security_mode=SecurityMode.STANDARD),
        registry=tool_registry,
    )
    assert standard_engine.evaluate("run_command", {"CommandLine": "echo 1"})[0] == PermissionDecision.DENY


def test_blocked_destructive_file_operations_in_strict(temp_workspace: Path, tool_registry: ToolRegistry) -> None:
    strict_engine = PermissionEngine(
        settings=NovaSettings(workspace_root=temp_workspace, security_mode=SecurityMode.STRICT),
        registry=tool_registry,
    )
    for tool in ("create_file", "edit_file"):
        decision, reason = strict_engine.evaluate(tool, {"file_path": str(temp_workspace / "a.txt")})
        assert decision == PermissionDecision.DENY
        assert "STRICT mode" in reason


def test_blocked_missing_credentials_fails_closed(temp_workspace: Path, temp_data_dir: Path) -> None:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
        gemini_api_key=None,
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("GEMINI_API_KEY", raising=False)
        mp.delenv("GOOGLE_API_KEY", raising=False)
        with pytest.raises(ConfigurationError):
            settings.validate_for_live_inference()
