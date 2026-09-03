"""Extensible Tool Registry for NOVA.

Maintains metadata, safety annotations, and callable wrappers for all tools.
"""

from collections.abc import Callable
import inspect
from typing import Any

from google.antigravity.types import BuiltinTools

from nova.errors import ValidationError
from nova.tools.categories import ToolCategory
from nova.tools.metadata import ToolMetadata, ToolRiskLevel


class RegisteredTool:
    """Encapsulates a callable tool alongside its safety metadata."""

    def __init__(self, metadata: ToolMetadata, handler: Callable[..., Any] | None = None) -> None:
        self.metadata = metadata
        self.handler = handler

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self.handler is None:
            raise RuntimeError(f"Tool {self.metadata.name} is a native built-in without a direct Python handler.")
        return self.handler(*args, **kwargs)


class ToolRegistry:
    """Thread-safe registry of all tools available to the NOVA system."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._register_antigravity_builtins()

    def _register_antigravity_builtins(self) -> None:
        """Populates canonical metadata for Google Antigravity builtin tools."""
        builtins = [
            ToolMetadata(
                name=BuiltinTools.LIST_DIR.value,
                description="List directory contents and file metadata.",
                category=ToolCategory.FILESYSTEM,
                risk_level=ToolRiskLevel.READ_ONLY,
                requires_approval=False,
                mutates_state=False,
                is_reversible=True,
            ),
            ToolMetadata(
                name=BuiltinTools.SEARCH_DIR.value,
                description="Search for regex patterns within directory files (ripgrep).",
                category=ToolCategory.FILESYSTEM,
                risk_level=ToolRiskLevel.READ_ONLY,
                requires_approval=False,
                mutates_state=False,
                is_reversible=True,
            ),
            ToolMetadata(
                name=BuiltinTools.FIND_FILE.value,
                description="Find files matching glob or name patterns.",
                category=ToolCategory.FILESYSTEM,
                risk_level=ToolRiskLevel.READ_ONLY,
                requires_approval=False,
                mutates_state=False,
                is_reversible=True,
            ),
            ToolMetadata(
                name=BuiltinTools.VIEW_FILE.value,
                description="Read contents of text or supported binary files.",
                category=ToolCategory.FILESYSTEM,
                risk_level=ToolRiskLevel.READ_ONLY,
                requires_approval=False,
                mutates_state=False,
                is_reversible=True,
            ),
            ToolMetadata(
                name=BuiltinTools.READ_URL_CONTENT.value,
                description="Fetch static markdown content from a public URL.",
                category=ToolCategory.UTILITY,
                risk_level=ToolRiskLevel.READ_ONLY,
                requires_approval=False,
                mutates_state=False,
                is_reversible=True,
            ),
            ToolMetadata(
                name=BuiltinTools.FINISH.value,
                description="Conclude task and return structured output.",
                category=ToolCategory.UTILITY,
                risk_level=ToolRiskLevel.READ_ONLY,
                requires_approval=False,
                mutates_state=False,
                is_reversible=True,
            ),
            ToolMetadata(
                name=BuiltinTools.CREATE_FILE.value,
                description="Create a new file with specified content.",
                category=ToolCategory.FILESYSTEM,
                risk_level=ToolRiskLevel.MEDIUM,
                requires_approval=False,
                mutates_state=True,
                is_reversible=True,
            ),
            ToolMetadata(
                name=BuiltinTools.EDIT_FILE.value,
                description="Modify existing file contents using targeted replacements.",
                category=ToolCategory.FILESYSTEM,
                risk_level=ToolRiskLevel.MEDIUM,
                requires_approval=False,
                mutates_state=True,
                is_reversible=True,
            ),
            ToolMetadata(
                name=BuiltinTools.ASK_QUESTION.value,
                description="Prompt the user with clarifying interactive questions.",
                category=ToolCategory.UTILITY,
                risk_level=ToolRiskLevel.LOW,
                requires_approval=False,
                mutates_state=False,
                is_reversible=True,
            ),
            ToolMetadata(
                name=BuiltinTools.START_SUBAGENT.value,
                description="Spawn a delegated subagent session for specialized sub-tasks.",
                category=ToolCategory.SUBAGENT,
                risk_level=ToolRiskLevel.MEDIUM,
                requires_approval=True,
                mutates_state=False,
                is_reversible=True,
            ),
            ToolMetadata(
                name=BuiltinTools.GENERATE_IMAGE.value,
                description="Generate or transform images via AI.",
                category=ToolCategory.UTILITY,
                risk_level=ToolRiskLevel.LOW,
                requires_approval=False,
                mutates_state=False,
                is_reversible=True,
            ),
            ToolMetadata(
                name=BuiltinTools.SEARCH_WEB.value,
                description="Perform live web search queries.",
                category=ToolCategory.UTILITY,
                risk_level=ToolRiskLevel.LOW,
                requires_approval=False,
                mutates_state=False,
                is_reversible=True,
            ),
            ToolMetadata(
                name=BuiltinTools.RUN_COMMAND.value,
                description="Execute arbitrary shell commands on the host operating system.",
                category=ToolCategory.TERMINAL,
                risk_level=ToolRiskLevel.CRITICAL,
                requires_approval=True,
                mutates_state=True,
                is_reversible=False,
            ),
        ]
        for meta in builtins:
            self.register(meta, handler=None)

    def register(self, metadata: ToolMetadata, handler: Callable[..., Any] | None = None) -> None:
        """Registers a tool with its associated safety metadata."""
        if not metadata.name:
            raise ValidationError("Tool name cannot be empty")
        self._tools[metadata.name] = RegisteredTool(metadata=metadata, handler=handler)

    def get(self, name: str) -> RegisteredTool | None:
        """Retrieve tool entry by canonical name."""
        return self._tools.get(name)

    def get_metadata(self, name: str) -> ToolMetadata | None:
        """Retrieve tool metadata by canonical name."""
        tool = self._tools.get(name)
        return tool.metadata if tool else None

    def list_tools(
        self,
        *,
        category: ToolCategory | None = None,
        max_risk: ToolRiskLevel | None = None,
    ) -> list[ToolMetadata]:
        """Lists registered tools filtered by category or maximum risk tolerance."""
        results: list[ToolMetadata] = []
        for tool in self._tools.values():
            meta = tool.metadata
            if category and meta.category != category:
                continue
            if max_risk and meta.risk_level > max_risk:
                continue
            results.append(meta)
        return results

    def get_phase01_builtin_tools(self) -> list[BuiltinTools]:
        """Returns the strictly safe, read-only builtin tools for Phase 01."""
        read_only_names = {
            m.name for m in self.list_tools(max_risk=ToolRiskLevel.READ_ONLY)
        }
        # Map back to BuiltinTools enums
        return [b for b in BuiltinTools if b.value in read_only_names]


# Default application-level registry
_default_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Returns the shared ToolRegistry singleton."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry


def nova_tool(
    name: str | None = None,
    *,
    description: str | None = None,
    category: ToolCategory = ToolCategory.UTILITY,
    risk_level: ToolRiskLevel = ToolRiskLevel.LOW,
    requires_approval: bool = False,
    mutates_state: bool = False,
    is_reversible: bool = True,
    registry: ToolRegistry | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to register a custom Python function in the NOVA tool registry."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = name or fn.__name__
        tool_desc = description or inspect.getdoc(fn) or f"Custom tool {tool_name}"

        meta = ToolMetadata(
            name=tool_name,
            description=tool_desc,
            category=category,
            risk_level=risk_level,
            requires_approval=requires_approval,
            mutates_state=mutates_state,
            is_reversible=is_reversible,
        )

        reg = registry or get_tool_registry()
        reg.register(meta, handler=fn)
        return fn

    return decorator
