"""Integration tests for NOVA agent runtime and Antigravity SDK wiring."""

from unittest.mock import AsyncMock, patch
import pytest

from google.antigravity.types import BuiltinTools
from pydantic import SecretStr

from nova.agent.configuration import build_agent_config
from nova.agent.lifecycle import AgentState
from nova.agent.prompts import NOVA_IDENTITY_PROMPT
from nova.agent.runtime import NovaRuntime
from nova.config.settings import Environment, NovaSettings, SecurityMode
from nova.memory.store import LocalFileMemoryStore
from nova.observability.audit import AuditTrail


def test_agent_config_generation(temp_workspace, temp_data_dir) -> None:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
        security_mode=SecurityMode.STRICT,
        gemini_api_key=SecretStr("mock_api_key_for_config_test"),
    )

    config = build_agent_config(settings=settings)

    # Validate Antigravity LocalAgentConfig structure
    assert config.workspaces == [str(temp_workspace)]
    assert config.model == "gemini-3.8-flash"
    assert config.api_key == "mock_api_key_for_config_test"
    assert NOVA_IDENTITY_PROMPT in str(config.system_instructions)

    # Capabilities must strictly enforce read-only
    caps = config.capabilities
    assert not caps.enable_subagents
    enabled_tool_names = {t.value for t in caps.enabled_tools}
    assert BuiltinTools.LIST_DIR.value in enabled_tool_names
    assert BuiltinTools.RUN_COMMAND.value not in enabled_tool_names

    # Policies must be present
    assert len(config.policies) > 0


@pytest.mark.asyncio
async def test_runtime_query_lifecycle_with_mocked_harness(temp_workspace, temp_data_dir) -> None:
    """Tests the complete NOVA query lifecycle with verified safety and audit trail."""
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
        security_mode=SecurityMode.STRICT,
        gemini_api_key=SecretStr("mock_key_12345"),
    )
    memory = LocalFileMemoryStore(memory_dir=temp_data_dir / "memory")
    audit = AuditTrail(audit_dir=temp_data_dir / "audit")
    runtime = NovaRuntime(settings=settings, memory_store=memory, audit_trail=audit)

    # Mock the low-level Agent async context and chat response
    mock_tokens = ["[OBSERVED] ", "Found hello.txt in the workspace."]

    class AsyncTokenIterator:
        def __init__(self, tokens):
            self.tokens = list(tokens)

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self.tokens:
                raise StopAsyncIteration
            return self.tokens.pop(0)

    mock_chat_response = AsyncTokenIterator(mock_tokens)

    class MockAgentInstance:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def chat(self, prompt: str):
            return mock_chat_response

    with patch("nova.agent.runtime.Agent", return_value=MockAgentInstance()):
        response = await runtime.query("What files are available?")

        assert "Found hello.txt in the workspace." in response
        assert runtime.lifecycle.current_state == AgentState.IDLE

        # Verify memory recorded execution
        history = memory.get_recent_executions(limit=5)
        assert len(history) == 1
        assert history[0].tool == "agent_runtime"
        assert history[0].success is True
        assert history[0].verified is True


def test_simulate_query_offline(temp_workspace, temp_data_dir) -> None:
    """Tests the offline simulation pipeline with real local files and audit logging."""
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
        security_mode=SecurityMode.STRICT,
    )
    memory = LocalFileMemoryStore(memory_dir=temp_data_dir / "memory")
    audit = AuditTrail(audit_dir=temp_data_dir / "audit")
    runtime = NovaRuntime(settings=settings, memory_store=memory, audit_trail=audit)

    response = runtime.simulate_query("List files in workspace")
    assert "[OBSERVED]" in response
    assert "hello.txt" in response
    assert "[VERIFIED]" in response

    # Check audit record was created
    records = audit.read_recent_records(limit=5)
    assert len(records) > 0
    assert records[0].tool == "list_directory"
    assert records[0].success is True
