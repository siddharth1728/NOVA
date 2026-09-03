"""Pytest configuration and shared fixtures for NOVA test suite."""

from pathlib import Path
import tempfile
from typing import Generator

import pytest

from nova.config.settings import Environment, NovaSettings, SecurityMode, get_settings
from nova.memory.store import LocalFileMemoryStore
from nova.observability.audit import AuditTrail
from nova.security.approvals import AutomatedApprovalHandler
from nova.security.permissions import PermissionEngine
from nova.tools.registry import ToolRegistry


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Provides an isolated temporary workspace directory."""
    with tempfile.TemporaryDirectory(prefix="nova_test_ws_") as tmp_dir:
        ws = Path(tmp_dir).resolve()
        # Create some dummy files for testing
        (ws / "hello.txt").write_text("Hello NOVA", encoding="utf-8")
        (ws / "sub").mkdir()
        (ws / "sub" / "nested.py").write_text("# nested", encoding="utf-8")
        yield ws


@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Provides an isolated temporary data directory."""
    with tempfile.TemporaryDirectory(prefix="nova_test_data_") as tmp_dir:
        yield Path(tmp_dir).resolve()


@pytest.fixture
def test_settings(temp_workspace: Path, temp_data_dir: Path) -> NovaSettings:
    """Provides test configuration with isolated directories."""
    return NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
        security_mode=SecurityMode.STRICT,
        model_name="gemini-3.8-flash",
    )


@pytest.fixture
def tool_registry() -> ToolRegistry:
    """Provides fresh ToolRegistry instance."""
    return ToolRegistry()


@pytest.fixture
def permission_engine(test_settings: NovaSettings, tool_registry: ToolRegistry) -> PermissionEngine:
    """Provides configured PermissionEngine."""
    return PermissionEngine(settings=test_settings, registry=tool_registry)


@pytest.fixture
def memory_store(temp_data_dir: Path) -> LocalFileMemoryStore:
    """Provides isolated LocalFileMemoryStore."""
    return LocalFileMemoryStore(memory_dir=temp_data_dir / "memory")


@pytest.fixture
def audit_trail(temp_data_dir: Path) -> AuditTrail:
    """Provides isolated AuditTrail logger."""
    return AuditTrail(audit_dir=temp_data_dir / "audit")


@pytest.fixture
def auto_approver() -> AutomatedApprovalHandler:
    """Provides approval handler that approves requests."""
    return AutomatedApprovalHandler(approve_all=True)


@pytest.fixture
def auto_rejector() -> AutomatedApprovalHandler:
    """Provides approval handler that rejects requests."""
    return AutomatedApprovalHandler(approve_all=False)
