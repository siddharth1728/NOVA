"""Automation and targeting package."""

from typing import Any

from nova.control.automation.models import TargetingResult, UIElementInfo, UIElementTarget, VisionTarget

__all__ = [
    "DeterministicTargetingCascade",
    "TargetingResult",
    "UIElementInfo",
    "UIElementTarget",
    "VisionFallbackTargeter",
    "VisionTarget",
    "WindowsUIAutomationController",
]


def __getattr__(name: str) -> Any:
    if name == "WindowsUIAutomationController":
        from nova.control.automation.uia import WindowsUIAutomationController

        return WindowsUIAutomationController
    if name == "DeterministicTargetingCascade":
        from nova.control.automation.targeting import DeterministicTargetingCascade

        return DeterministicTargetingCascade
    if name == "VisionFallbackTargeter":
        from nova.control.automation.vision import VisionFallbackTargeter

        return VisionFallbackTargeter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


