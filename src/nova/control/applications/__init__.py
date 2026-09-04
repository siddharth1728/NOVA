"""Applications control package."""

from typing import Any

from nova.control.applications.discovery import WindowsAppDiscovery
from nova.control.applications.models import AppInfo, LaunchRequest, LaunchResult

__all__ = [
    "AppInfo",
    "LaunchRequest",
    "LaunchResult",
    "WindowsAppDiscovery",
    "WindowsApplicationController",
]


def __getattr__(name: str) -> Any:
    if name == "WindowsApplicationController":
        from nova.control.applications.launcher import WindowsApplicationController

        return WindowsApplicationController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

