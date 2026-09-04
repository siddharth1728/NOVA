"""Process management package."""

from typing import Any

from nova.control.processes.models import ProcessFilter, ProcessInfo, ProcessStopResult

__all__ = [
    "ProcessFilter",
    "ProcessInfo",
    "ProcessStopResult",
    "WindowsProcessController",
]


def __getattr__(name: str) -> Any:
    if name == "WindowsProcessController":
        from nova.control.processes.manager import WindowsProcessController

        return WindowsProcessController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

