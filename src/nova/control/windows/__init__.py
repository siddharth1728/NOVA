"""Windows window management package."""

from typing import Any

from nova.control.windows.enumeration import enumerate_windows, get_foreground_window, get_window_bounds, get_window_info
from nova.control.windows.models import WindowBounds, WindowInfo, WindowTarget
from nova.control.windows.targeting import resolve_target_window

__all__ = [
    "WindowBounds",
    "WindowInfo",
    "WindowTarget",
    "WindowsWindowController",
    "enumerate_windows",
    "get_foreground_window",
    "get_window_bounds",
    "get_window_info",
    "resolve_target_window",
]


def __getattr__(name: str) -> Any:
    if name == "WindowsWindowController":
        from nova.control.windows.manager import WindowsWindowController

        return WindowsWindowController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

