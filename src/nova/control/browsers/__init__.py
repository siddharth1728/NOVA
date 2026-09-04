"""Browsers package."""

from typing import Any

from nova.control.browsers.models import BrowserInfo, BrowserTab

__all__ = [
    "BrowserInfo",
    "BrowserTab",
    "WindowsBrowserController",
]


def __getattr__(name: str) -> Any:
    if name == "WindowsBrowserController":
        from nova.control.browsers.manager import WindowsBrowserController

        return WindowsBrowserController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

