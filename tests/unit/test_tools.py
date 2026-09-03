"""Unit tests for NOVA tool registry and risk classification."""

import pytest
from google.antigravity.types import BuiltinTools

from nova.tools.categories import ToolCategory
from nova.tools.metadata import ToolMetadata, ToolRiskLevel
from nova.tools.registry import ToolRegistry, nova_tool


def test_risk_level_ordering() -> None:
    assert ToolRiskLevel.READ_ONLY < ToolRiskLevel.LOW
    assert ToolRiskLevel.LOW < ToolRiskLevel.MEDIUM
    assert ToolRiskLevel.MEDIUM < ToolRiskLevel.HIGH
    assert ToolRiskLevel.HIGH < ToolRiskLevel.CRITICAL
    assert ToolRiskLevel.CRITICAL >= ToolRiskLevel.HIGH
    assert ToolRiskLevel.READ_ONLY <= ToolRiskLevel.READ_ONLY


def test_builtin_tool_registration(tool_registry: ToolRegistry) -> None:
    list_tool = tool_registry.get_metadata(BuiltinTools.LIST_DIR.value)
    assert list_tool is not None
    assert list_tool.risk_level == ToolRiskLevel.READ_ONLY
    assert list_tool.category == ToolCategory.FILESYSTEM
    assert not list_tool.mutates_state

    run_cmd = tool_registry.get_metadata(BuiltinTools.RUN_COMMAND.value)
    assert run_cmd is not None
    assert run_cmd.risk_level == ToolRiskLevel.CRITICAL
    assert run_cmd.category == ToolCategory.TERMINAL
    assert run_cmd.mutates_state
    assert run_cmd.requires_approval


def test_phase01_builtin_tools_strictly_read_only(tool_registry: ToolRegistry) -> None:
    phase01_tools = tool_registry.get_phase01_builtin_tools()
    allowed_values = {t.value for t in phase01_tools}

    # Must contain safe inspection tools
    assert BuiltinTools.LIST_DIR.value in allowed_values
    assert BuiltinTools.VIEW_FILE.value in allowed_values
    assert BuiltinTools.SEARCH_DIR.value in allowed_values
    assert BuiltinTools.FIND_FILE.value in allowed_values
    assert BuiltinTools.READ_URL_CONTENT.value in allowed_values
    assert BuiltinTools.FINISH.value in allowed_values

    # Must strictly exclude destructive or state-modifying tools
    assert BuiltinTools.RUN_COMMAND.value not in allowed_values
    assert BuiltinTools.CREATE_FILE.value not in allowed_values
    assert BuiltinTools.EDIT_FILE.value not in allowed_values


def test_tool_registry_filtering(tool_registry: ToolRegistry) -> None:
    fs_tools = tool_registry.list_tools(category=ToolCategory.FILESYSTEM)
    assert all(t.category == ToolCategory.FILESYSTEM for t in fs_tools)

    read_only_tools = tool_registry.list_tools(max_risk=ToolRiskLevel.READ_ONLY)
    assert all(t.risk_level == ToolRiskLevel.READ_ONLY for t in read_only_tools)


def test_nova_tool_decorator(tool_registry: ToolRegistry) -> None:
    @nova_tool(
        name="custom_math_tool",
        description="Calculates sum of two integers",
        category=ToolCategory.UTILITY,
        risk_level=ToolRiskLevel.READ_ONLY,
        registry=tool_registry,
    )
    def add(a: int, b: int) -> int:
        return a + b

    registered = tool_registry.get("custom_math_tool")
    assert registered is not None
    assert registered(3, 4) == 7
    assert registered.metadata.risk_level == ToolRiskLevel.READ_ONLY
    assert registered.metadata.description == "Calculates sum of two integers"
