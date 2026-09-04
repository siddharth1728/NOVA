"""Clipboard control package."""

from typing import Any

from nova.control.clipboard.models import ClipboardContent, ClipboardType

__all__ = [
    "ClipboardContent",
    "ClipboardType",
    "WindowsClipboardController",
]


def __getattr__(name: str) -> Any:
    if name == "WindowsClipboardController":
        from nova.control.clipboard.manager import WindowsClipboardController

        return WindowsClipboardController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

