"""Windows UI Automation and accessible control inspection provider."""

import logging
from typing import Any
import win32con
import win32gui

from nova.control.automation.models import UIElementInfo, UIElementTarget
from nova.control.interfaces import UIAutomationController
from nova.control.windows.models import WindowBounds
from nova.errors import TargetNotFoundError, WindowNotFoundError

logger = logging.getLogger("nova.control.automation.uia")


class WindowsUIAutomationController(UIAutomationController):
    """Inspects and interacts with semantic UI elements using Windows controls and accessibility."""

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def inspect_tree(self, hwnd: int | None = None, max_depth: int = 3) -> list[UIElementInfo]:
        """Inspect semantic UI elements in a window or top-level desktop."""
        if self.dry_run:
            return [
                UIElementInfo(
                    name="File",
                    automation_id="Menu_File",
                    control_type="MenuItem",
                    class_name="MenuItem",
                    bounds=WindowBounds(x=10, y=30, width=40, height=20),
                    is_enabled=True,
                    is_visible=True,
                ),
                UIElementInfo(
                    name="Text Editor",
                    automation_id="Edit_1",
                    control_type="Edit",
                    class_name="Edit",
                    bounds=WindowBounds(x=10, y=60, width=780, height=500),
                    is_enabled=True,
                    is_visible=True,
                    value="Sample text in editor",
                ),
                UIElementInfo(
                    name="Save",
                    automation_id="Btn_Save",
                    control_type="Button",
                    class_name="Button",
                    bounds=WindowBounds(x=200, y=570, width=80, height=30),
                    is_enabled=True,
                    is_visible=True,
                ),
            ]

        target_hwnd = hwnd or win32gui.GetForegroundWindow()
        if not target_hwnd or not win32gui.IsWindow(target_hwnd):
            return []

        elements: list[UIElementInfo] = []

        def enum_child(child_hwnd: int, acc: list[UIElementInfo]):
            if not win32gui.IsWindowVisible(child_hwnd):
                return True

            text = win32gui.GetWindowText(child_hwnd) or ""
            cls_name = win32gui.GetClassName(child_hwnd) or ""
            is_enabled = bool(win32gui.IsWindowEnabled(child_hwnd))

            # Derive accessible ControlType from Win32 class
            cls_lower = cls_name.lower()
            if "button" in cls_lower:
                c_type = "Button"
            elif "edit" in cls_lower or "rich" in cls_lower:
                c_type = "Edit"
            elif "combobox" in cls_lower:
                c_type = "ComboBox"
            elif "listbox" in cls_lower:
                c_type = "ListBox"
            elif "static" in cls_lower:
                c_type = "Text"
            elif "menu" in cls_lower:
                c_type = "MenuItem"
            else:
                c_type = "Pane"

            rect = win32gui.GetWindowRect(child_hwnd)
            w = max(0, rect[2] - rect[0])
            h = max(0, rect[3] - rect[1])

            if w > 0 and h > 0:
                acc.append(
                    UIElementInfo(
                        name=text if text else f"{cls_name}_{child_hwnd}",
                        automation_id=f"hwnd_{child_hwnd}",
                        control_type=c_type,
                        class_name=cls_name,
                        bounds=WindowBounds(x=rect[0], y=rect[1], width=w, height=h),
                        is_enabled=is_enabled,
                        is_visible=True,
                        value=text if c_type == "Edit" else None,
                    )
                )
            return True

        try:
            win32gui.EnumChildWindows(target_hwnd, enum_child, elements)
        except Exception as ex:
            logger.warning("EnumChildWindows failed on hwnd %d: %s", target_hwnd, ex)

        return elements

    def find_element(self, target: UIElementTarget, hwnd: int | None = None) -> UIElementInfo | None:
        """Locate element matching criteria."""
        elements = self.inspect_tree(hwnd=hwnd)

        for el in elements:
            # 1. AutomationId exact match
            if target.automation_id and el.automation_id == target.automation_id:
                return el

            # 2. Name + ControlType match
            if target.name and target.control_type:
                if target.name.lower() in el.name.lower() and el.control_type.lower() == target.control_type.lower():
                    return el

            # 3. Name match
            if target.name and target.name.lower() in el.name.lower():
                return el

            # 4. ControlType match
            if target.control_type and target.control_type.lower() == el.control_type.lower():
                return el

        return None

    def invoke(self, target: UIElementTarget, hwnd: int | None = None) -> bool:
        """Trigger primary action on UI element."""
        if self.dry_run:
            return True

        el = self.find_element(target, hwnd=hwnd)
        if not el:
            raise TargetNotFoundError(f"UI Element matching {target} not found", details=target.model_dump())

        # Extract child HWND if present in automation_id
        if el.automation_id.startswith("hwnd_"):
            try:
                child_hwnd = int(el.automation_id.split("_")[1])
                if win32gui.IsWindow(child_hwnd):
                    # Win32 BM_CLICK message
                    win32gui.SendMessage(child_hwnd, win32con.BM_CLICK, 0, 0)
                    return True
            except Exception:
                pass

        # Fallback: Click element center coordinate
        if el.bounds:
            cx = el.bounds.x + el.bounds.width // 2
            cy = el.bounds.y + el.bounds.height // 2
            import win32api
            win32api.SetCursorPos((cx, cy))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, cx, cy, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, cx, cy, 0, 0)
            return True

        return False

    def set_value(self, target: UIElementTarget, value: str, hwnd: int | None = None) -> bool:
        """Set edit or text value of UI element."""
        if self.dry_run:
            return True

        el = self.find_element(target, hwnd=hwnd)
        if not el:
            raise TargetNotFoundError(f"UI Element matching {target} not found", details=target.model_dump())

        if el.automation_id.startswith("hwnd_"):
            try:
                child_hwnd = int(el.automation_id.split("_")[1])
                if win32gui.IsWindow(child_hwnd):
                    win32gui.SendMessage(child_hwnd, win32con.WM_SETTEXT, 0, value)
                    return True
            except Exception as ex:
                logger.error("WM_SETTEXT failed: %s", ex)

        return False

    def invoke_element(self, element: UIElementInfo) -> bool:
        """Invoke action on a resolved UIElementInfo."""
        return self.invoke(UIElementTarget(name=element.name, automation_id=element.automation_id, control_type=element.control_type))

    def set_element_value(self, element: UIElementInfo, value: str) -> bool:
        """Set text value on a resolved UIElementInfo."""
        return self.set_value(UIElementTarget(name=element.name, automation_id=element.automation_id, control_type=element.control_type), value)

