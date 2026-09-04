"""Windows mouse controller implementation using Win32 API."""

import logging
import time
import win32api
import win32con
import win32gui

from nova.control.input.models import InputResult, MouseAction, MouseButton
from nova.control.interfaces import MouseController
from nova.errors import WindowNotFoundError

logger = logging.getLogger("nova.control.input.mouse")


class WindowsMouseController(MouseController):
    """Authoritative Windows mouse controller supporting absolute and window-relative coordinates."""

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._mock_pos: tuple[int, int] = (100, 100)

    def get_position(self) -> tuple[int, int]:
        """Return current mouse position in desktop screen coordinates."""
        if self.dry_run:
            return self._mock_pos
        try:
            return win32api.GetCursorPos()
        except Exception as ex:
            logger.error("GetCursorPos failed: %s", ex)
            return (0, 0)

    def _resolve_coordinates(self, x: int, y: int, relative_to_hwnd: int | None = None) -> tuple[int, int]:
        """Convert window-relative coordinates to absolute screen coordinates if HWND provided."""
        if relative_to_hwnd is not None:
            if not win32gui.IsWindow(relative_to_hwnd):
                raise WindowNotFoundError(f"Target HWND {relative_to_hwnd} does not exist", details={"hwnd": relative_to_hwnd})
            rect = win32gui.GetWindowRect(relative_to_hwnd)
            return (rect[0] + x, rect[1] + y)
        return (x, y)

    def move(self, x: int, y: int, relative_to_hwnd: int | None = None) -> tuple[int, int]:
        """Move cursor to target coordinates."""
        abs_x, abs_y = self._resolve_coordinates(x, y, relative_to_hwnd)
        if self.dry_run:
            self._mock_pos = (abs_x, abs_y)
            return self._mock_pos

        win32api.SetCursorPos((abs_x, abs_y))
        return (abs_x, abs_y)

    def click(
        self,
        button: MouseButton = MouseButton.LEFT,
        count: int = 1,
        x: int | None = None,
        y: int | None = None,
        relative_to_hwnd: int | None = None,
    ) -> InputResult:
        """Click mouse button at specified or current coordinates."""
        if x is not None and y is not None:
            abs_x, abs_y = self.move(x, y, relative_to_hwnd)
        else:
            abs_x, abs_y = self.get_position()

        if self.dry_run:
            return InputResult(
                success=True,
                action=f"{button.value}_click" if count == 1 else f"{button.value}_double_click",
                target_hwnd=relative_to_hwnd,
                details={"x": abs_x, "y": abs_y, "button": button.value, "count": count},
            )

        down_flag, up_flag = self._get_button_flags(button)

        for i in range(count):
            win32api.mouse_event(down_flag, abs_x, abs_y, 0, 0)
            time.sleep(0.03)
            win32api.mouse_event(up_flag, abs_x, abs_y, 0, 0)
            if i < count - 1:
                time.sleep(0.1)

        return InputResult(
            success=True,
            action=f"{button.value}_click",
            target_hwnd=relative_to_hwnd,
            details={"x": abs_x, "y": abs_y, "button": button.value, "count": count},
        )

    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> InputResult:
        """Press and hold mouse button."""
        x, y = self.get_position()
        if self.dry_run:
            return InputResult(success=True, action="mouse_down", details={"button": button.value})

        down_flag, _ = self._get_button_flags(button)
        win32api.mouse_event(down_flag, x, y, 0, 0)
        return InputResult(success=True, action="mouse_down", details={"button": button.value, "x": x, "y": y})

    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> InputResult:
        """Release held mouse button."""
        x, y = self.get_position()
        if self.dry_run:
            return InputResult(success=True, action="mouse_up", details={"button": button.value})

        _, up_flag = self._get_button_flags(button)
        win32api.mouse_event(up_flag, x, y, 0, 0)
        return InputResult(success=True, action="mouse_up", details={"button": button.value, "x": x, "y": y})

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        button: MouseButton = MouseButton.LEFT,
    ) -> InputResult:
        """Perform mouse drag gesture."""
        if self.dry_run:
            self._mock_pos = (end_x, end_y)
            return InputResult(
                success=True,
                action="drag",
                details={"start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y},
            )

        self.move(start_x, start_y)
        time.sleep(0.05)
        self.mouse_down(button)
        time.sleep(0.05)

        # Interpolate movement smoothly
        steps = 10
        for i in range(1, steps + 1):
            curr_x = int(start_x + (end_x - start_x) * (i / steps))
            curr_y = int(start_y + (end_y - start_y) * (i / steps))
            self.move(curr_x, curr_y)
            time.sleep(0.01)

        time.sleep(0.05)
        self.mouse_up(button)

        return InputResult(
            success=True,
            action="drag",
            details={"start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y},
        )

    def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> InputResult:
        """Scroll vertical wheel."""
        if x is not None and y is not None:
            self.move(x, y)
        curr_x, curr_y = self.get_position()

        if self.dry_run:
            return InputResult(success=True, action="scroll", details={"clicks": clicks, "x": curr_x, "y": curr_y})

        wheel_delta = clicks * win32con.WHEEL_DELTA
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, curr_x, curr_y, wheel_delta, 0)
        return InputResult(success=True, action="scroll", details={"clicks": clicks, "x": curr_x, "y": curr_y})

    def _get_button_flags(self, button: MouseButton) -> tuple[int, int]:
        """Return (DOWN_FLAG, UP_FLAG) for Win32 mouse_event."""
        if button == MouseButton.RIGHT:
            return (win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP)
        elif button == MouseButton.MIDDLE:
            return (win32con.MOUSEEVENTF_MIDDLEDOWN, win32con.MOUSEEVENTF_MIDDLEUP)
        return (win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP)
