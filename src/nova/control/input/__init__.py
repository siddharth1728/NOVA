"""Input control package."""

from typing import Any

from nova.control.input.models import InputResult, Key, KeyCombination, MouseAction, MouseButton
from nova.control.input.safety import is_safe_key_combination, normalize_key_name

__all__ = [
    "InputResult",
    "Key",
    "KeyCombination",
    "MouseAction",
    "MouseButton",
    "WindowsKeyboardController",
    "WindowsMouseController",
    "is_safe_key_combination",
    "normalize_key_name",
]


def __getattr__(name: str) -> Any:
    if name == "WindowsKeyboardController":
        from nova.control.input.keyboard import WindowsKeyboardController

        return WindowsKeyboardController
    if name == "WindowsMouseController":
        from nova.control.input.mouse import WindowsMouseController

        return WindowsMouseController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

