"""Tool categorization taxonomy for NOVA."""

from enum import Enum


class ToolCategory(str, Enum):
    """Categorical domain for tool functions."""

    FILESYSTEM = "filesystem"
    TERMINAL = "terminal"
    BROWSER = "browser"
    MEMORY = "memory"
    SYSTEM = "system"
    COMPUTER = "computer"
    UTILITY = "utility"
    SUBAGENT = "subagent"
