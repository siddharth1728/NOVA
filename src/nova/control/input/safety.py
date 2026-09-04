"""System key safety policies and sensitive combination interceptor."""

import logging

from nova.control.input.models import Key

logger = logging.getLogger("nova.control.input.safety")

# Critical combinations that trigger system security boundaries or severe desktop side-effects
BLOCKED_COMBINATIONS = [
    # Ctrl + Alt + Delete (Secure Attention Sequence)
    {"ctrl", "alt", "del"},
    {"ctrl", "alt", "delete"},
    # Win + L (Lock workstation - must use explicit emergency lock API)
    {"win", "l"},
    {"windows", "l"},
    # Win + X (Power user menu / shutdown shortcuts)
    {"win", "x"},
    {"windows", "x"},
    # Ctrl + Shift + Esc (Direct Task Manager invocation without approval)
    {"ctrl", "shift", "esc"},
    {"ctrl", "shift", "escape"},
]


def normalize_key_name(key: Key | str) -> str:
    """Normalize key name strings to lowercase stripped tokens."""
    if isinstance(key, Key):
        name = key.value.lower()
    else:
        name = str(key).lower().strip()

    # Aliases
    if name in ("return", "enter"):
        return "enter"
    if name in ("esc", "escape"):
        return "escape"
    if name in ("control", "ctrl"):
        return "ctrl"
    if name in ("windows", "win", "super", "cmd"):
        return "win"
    if name in ("del", "delete"):
        return "del"
    return name


def is_safe_key_combination(keys: list[Key | str]) -> tuple[bool, str]:
    """Evaluates whether a key combination is safe to inject into Windows.

    Returns:
        (is_safe, reason_string)
    """
    normalized_set = {normalize_key_name(k) for k in keys}

    for blocked in BLOCKED_COMBINATIONS:
        if blocked.issubset(normalized_set):
            comb_str = "+".join(sorted(normalized_set))
            return (
                False,
                f"Key combination '{comb_str}' is strictly blocked by NOVA system key safety policy",
            )

    return True, "Key combination permitted"
