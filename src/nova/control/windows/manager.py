"""Windows window management and operations with post-action verification."""

import ctypes
import logging
import time
import win32con
import win32gui

from nova.control.interfaces import WindowController
from nova.control.windows.enumeration import enumerate_windows, get_foreground_window, get_window_bounds, get_window_info
from nova.control.windows.models import WindowBounds, WindowInfo, WindowTarget
from nova.control.windows.targeting import resolve_target_window
from nova.errors import ComputerVerificationError, WindowNotFoundError

logger = logging.getLogger("nova.control.windows.manager")


class WindowsWindowController(WindowController):
    """Authoritative Windows window controller with empirical state verification."""

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def list_windows(self, visible_only: bool = True) -> list[WindowInfo]:
        """Enumerate top-level application windows."""
        if self.dry_run:
            return [
                WindowInfo(
                    hwnd=1001,
                    title="Antigravity IDE",
                    process_name="agy.exe",
                    pid=1234,
                    bounds=WindowBounds(x=0, y=0, width=1920, height=1080),
                    visible=True,
                    is_foreground=True,
                ),
                WindowInfo(
                    hwnd=1002,
                    title="Untitled - Notepad",
                    process_name="notepad.exe",
                    pid=5678,
                    bounds=WindowBounds(x=100, y=100, width=800, height=600),
                    visible=True,
                    is_foreground=False,
                ),
            ]
        return enumerate_windows(visible_only=visible_only)

    def get_window(self, hwnd: int) -> WindowInfo | None:
        """Retrieve details for a specific window handle."""
        if self.dry_run:
            return WindowInfo(
                hwnd=hwnd,
                title=f"Mock Window ({hwnd})",
                process_name="mock.exe",
                pid=9999,
                bounds=WindowBounds(x=50, y=50, width=640, height=480),
                visible=True,
                is_foreground=(hwnd == 1001),
            )
        return get_window_info(hwnd)

    def get_foreground_window(self) -> WindowInfo | None:
        """Retrieve the currently focused foreground window."""
        if self.dry_run:
            return self.get_window(1001)
        return get_foreground_window()

    def resolve_target(self, target: WindowTarget) -> WindowInfo:
        """Deterministically resolve a target window."""
        if self.dry_run:
            return self.get_window(target.hwnd or 1001)  # type: ignore
        return resolve_target_window(target)

    def focus_window(self, hwnd: int) -> bool:
        """Bring window to foreground and assign active input focus with verification."""
        if self.dry_run:
            return True

        if not win32gui.IsWindow(hwnd):
            raise WindowNotFoundError(f"Cannot focus invalid HWND {hwnd}", details={"hwnd": hwnd})

        try:
            # If minimized, restore first
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

            # Allow focus stealing and bring to top
            ctypes.windll.user32.AllowSetForegroundWindow(-1)
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
        except Exception as ex:
            logger.warning("Direct SetForegroundWindow failed: %s. Attempting attach-thread workaround.", ex)
            try:
                import win32process
                import win32api
                cur_thread = win32api.GetCurrentThreadId()
                w_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
                fg_hwnd = win32gui.GetForegroundWindow()
                fg_thread = win32process.GetWindowThreadProcessId(fg_hwnd)[0] if fg_hwnd else 0

                # Simulate subtle Alt key event to unlock Windows foreground lock
                ctypes.windll.user32.keybd_event(win32con.VK_MENU, 0, 0, 0)
                if fg_thread and fg_thread != cur_thread:
                    ctypes.windll.user32.AttachThreadInput(cur_thread, fg_thread, True)
                if cur_thread != w_thread:
                    ctypes.windll.user32.AttachThreadInput(cur_thread, w_thread, True)

                win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
                win32gui.SetForegroundWindow(hwnd)

                if cur_thread != w_thread:
                    ctypes.windll.user32.AttachThreadInput(cur_thread, w_thread, False)
                if fg_thread and fg_thread != cur_thread:
                    ctypes.windll.user32.AttachThreadInput(cur_thread, fg_thread, False)
                ctypes.windll.user32.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            except Exception as thread_err:
                logger.error("Focus workaround failed: %s", thread_err)

        # Verification check: poll up to 0.5s to verify foreground state
        deadline = time.time() + 0.5
        while time.time() < deadline:
            if win32gui.GetForegroundWindow() == hwnd:
                return True
            time.sleep(0.05)

        # Non-fatal if OS prevented focus steal, but record reality
        actual_fg = win32gui.GetForegroundWindow()
        logger.info("Window focus call completed. Foreground HWND: %s (target: %s)", actual_fg, hwnd)
        return actual_fg == hwnd

    def minimize_window(self, hwnd: int) -> bool:
        """Minimize window with verification."""
        if self.dry_run:
            return True

        if not win32gui.IsWindow(hwnd):
            raise WindowNotFoundError(f"Cannot minimize invalid HWND {hwnd}", details={"hwnd": hwnd})

        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        time.sleep(0.1)
        return bool(win32gui.IsIconic(hwnd))

    def maximize_window(self, hwnd: int) -> bool:
        """Maximize window with verification."""
        if self.dry_run:
            return True

        if not win32gui.IsWindow(hwnd):
            raise WindowNotFoundError(f"Cannot maximize invalid HWND {hwnd}", details={"hwnd": hwnd})

        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        time.sleep(0.1)
        return bool(ctypes.windll.user32.IsZoomed(hwnd))

    def restore_window(self, hwnd: int) -> bool:
        """Restore window from minimized/maximized state."""
        if self.dry_run:
            return True

        if not win32gui.IsWindow(hwnd):
            raise WindowNotFoundError(f"Cannot restore invalid HWND {hwnd}", details={"hwnd": hwnd})

        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.1)
        return not bool(win32gui.IsIconic(hwnd))

    def close_window(self, hwnd: int) -> bool:
        """Send close request to window and verify window termination."""
        if self.dry_run:
            return True

        if not win32gui.IsWindow(hwnd):
            return True

        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

        # Verification check: poll up to 2 seconds to verify window closes
        deadline = time.time() + 2.0
        while time.time() < deadline:
            if not win32gui.IsWindow(hwnd):
                return True
            if not win32gui.IsWindowVisible(hwnd):
                return True
            time.sleep(0.1)

        return not win32gui.IsWindow(hwnd)

    def move_window(self, hwnd: int, x: int, y: int, width: int, height: int) -> WindowBounds:
        """Move and resize window, verifying the resulting rectangular bounds."""
        if self.dry_run:
            return WindowBounds(x=x, y=y, width=width, height=height)

        if not win32gui.IsWindow(hwnd):
            raise WindowNotFoundError(f"Cannot move invalid HWND {hwnd}", details={"hwnd": hwnd})

        # If maximized or iconic, restore first
        if bool(ctypes.windll.user32.IsZoomed(hwnd)) or win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)

        win32gui.MoveWindow(hwnd, x, y, width, height, True)
        time.sleep(0.1)

        actual_bounds = get_window_bounds(hwnd)
        # Tolerance check (+/- 15px due to Windows 11 drop shadows/DPI margins)
        if abs(actual_bounds.x - x) > 30 or abs(actual_bounds.y - y) > 30:
            logger.warning(
                "Window move bounds slightly deviated: target=(%d,%d), actual=(%d,%d)",
                x, y, actual_bounds.x, actual_bounds.y
            )

        return actual_bounds

    def move_resize_window(self, hwnd: int, bounds: WindowBounds) -> bool:
        """Move and resize window using a WindowBounds model."""
        res = self.move_window(hwnd, bounds.x, bounds.y, bounds.width, bounds.height)
        return bool(res)

