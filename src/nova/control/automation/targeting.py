"""Authoritative deterministic targeting cascade engine."""

import logging
from typing import Any

from nova.control.automation.models import TargetingResult, UIElementTarget, VisionTarget
from nova.control.automation.uia import WindowsUIAutomationController
from nova.control.automation.vision import VisionFallbackTargeter
from nova.control.windows.manager import WindowsWindowController
from nova.control.windows.models import WindowTarget
from nova.errors import TargetNotFoundError

logger = logging.getLogger("nova.control.automation.targeting")


class DeterministicTargetingCascade:
    """Executes targeting resolution according to NOVA's determinism hierarchy:

    Win32 API -> UI Automation -> Vision Fallback
    """

    def __init__(
        self,
        window_controller: WindowsWindowController | None = None,
        uia_controller: WindowsUIAutomationController | None = None,
        vision_targeter: VisionFallbackTargeter | None = None,
    ) -> None:
        self.window_ctrl = window_controller or WindowsWindowController()
        self.uia_ctrl = uia_controller or WindowsUIAutomationController()
        self.vision_targeter = vision_targeter or VisionFallbackTargeter()

    def resolve(
        self,
        *,
        window_target: WindowTarget | None = None,
        ui_target: UIElementTarget | None = None,
        vision_target: VisionTarget | None = None,
    ) -> TargetingResult:
        """Resolve targeting criteria along the deterministic hierarchy."""
        # 1. Tier 1: Direct Win32 Window Resolution
        if window_target is not None:
            try:
                win = self.window_ctrl.resolve_target(window_target)
                return TargetingResult(
                    method="WIN32_API",
                    success=True,
                    hwnd=win.hwnd,
                    coordinates=(win.bounds.x + win.bounds.width // 2, win.bounds.y + win.bounds.height // 2),
                    confidence=1.0,
                )
            except Exception as ex:
                logger.info("Tier 1 Win32 API targeting did not match: %s", ex)

        # 2. Tier 2: Windows UI Automation Semantic Element
        if ui_target is not None:
            hwnd = window_target.hwnd if window_target else None
            el = self.uia_ctrl.find_element(ui_target, hwnd=hwnd)
            if el is not None:
                coords = None
                if el.bounds:
                    coords = (el.bounds.x + el.bounds.width // 2, el.bounds.y + el.bounds.height // 2)
                return TargetingResult(
                    method="UI_AUTOMATION",
                    success=True,
                    hwnd=hwnd,
                    element=el,
                    coordinates=coords,
                    confidence=1.0,
                )

        # 3. Tier 3: Controlled Computer Vision Fallback
        if vision_target is not None:
            try:
                coords = self.vision_targeter.validate_and_resolve(vision_target)
                return TargetingResult(
                    method="VISION",
                    success=True,
                    coordinates=coords,
                    confidence=vision_target.confidence,
                    fallback_reason="No deterministic Win32 or UIA selector was matched; fell back to vision candidate.",
                )
            except Exception as ex:
                logger.warning("Tier 3 Vision targeting rejected: %s", ex)
                raise

        raise TargetNotFoundError(
            "Target could not be resolved across Win32 API, UI Automation, or Vision layers.",
            details={"window_target": window_target, "ui_target": ui_target},
        )
