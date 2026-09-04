"""Win32 window enumeration and inspection primitives."""

import logging
import os
import psutil
import win32con
import win32gui
import win32process

from nova.control.windows.models import WindowBounds, WindowInfo

logger = logging.getLogger("nova.control.windows.enumeration")


def get_window_bounds(hwnd: int) -> WindowBounds:
    """Retrieve bounding screen coordinates of a window."""
    try:
        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        return WindowBounds(
            x=left,
            y=top,
            width=max(0, right - left),
            height=max(0, bottom - top),
        )
    except Exception:
        return WindowBounds(x=0, y=0, width=0, height=0)


def get_window_info(hwnd: int) -> WindowInfo | None:
    """Construct structured WindowInfo for a specific HWND."""
    if not win32gui.IsWindow(hwnd):
        return None

    try:
        import ctypes
        title = win32gui.GetWindowText(hwnd) or ""
        visible = bool(win32gui.IsWindowVisible(hwnd))
        is_iconic = bool(win32gui.IsIconic(hwnd))
        is_zoomed = bool(ctypes.windll.user32.IsZoomed(hwnd))
        fg_hwnd = win32gui.GetForegroundWindow()
        is_fg = (hwnd == fg_hwnd)

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process_name = "unknown"
        try:
            p = psutil.Process(pid)
            process_name = p.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        bounds = get_window_bounds(hwnd)

        return WindowInfo(
            hwnd=hwnd,
            title=title,
            process_name=process_name,
            pid=pid,
            bounds=bounds,
            visible=visible,
            is_foreground=is_fg,
            is_minimized=is_iconic,
            is_maximized=is_zoomed,
        )
    except Exception as ex:
        logger.debug("Failed to inspect hwnd %d: %s", hwnd, ex)
        return None


def get_foreground_window() -> WindowInfo | None:
    """Return structured WindowInfo for the currently focused foreground window."""
    try:
        fg_hwnd = win32gui.GetForegroundWindow()
        if fg_hwnd:
            return get_window_info(fg_hwnd)
    except Exception:
        pass
    return None


def enumerate_windows(visible_only: bool = True) -> list[WindowInfo]:
    """Enumerate top-level desktop windows matching visibility criteria."""
    results: list[WindowInfo] = []
    seen_hwnds: set[int] = set()

    def enum_callback(hwnd: int, extra: list[WindowInfo]):
        if hwnd in seen_hwnds or not win32gui.IsWindow(hwnd):
            return True
        seen_hwnds.add(hwnd)

        # Check visibility
        is_vis = bool(win32gui.IsWindowVisible(hwnd))
        if visible_only and not is_vis:
            return True

        title = win32gui.GetWindowText(hwnd)
        # Skip nameless utility/tool windows if visible_only
        if visible_only and not title.strip():
            return True

        info = get_window_info(hwnd)
        if info:
            # Skip 0-dimension hidden background helper windows
            if visible_only and (info.bounds.width <= 0 or info.bounds.height <= 0):
                return True
            extra.append(info)
        return True

    # 1. Enumerate current thread desktop
    try:
        win32gui.EnumWindows(enum_callback, results)
    except Exception as ex:
        logger.error("EnumWindows failed: %s", ex)

    # 2. Also enumerate Default interactive desktop on WinSta0
    try:
        import ctypes
        user32 = ctypes.windll.user32
        DESKTOP_ENUMERATE = 0x0040
        DESKTOP_READOBJECTS = 0x0001
        h_desk = user32.OpenDesktopW("Default", 0, False, DESKTOP_ENUMERATE | DESKTOP_READOBJECTS)
        if h_desk:
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

            def desk_callback(h, _):
                if h:
                    enum_callback(int(h), results)
                return True

            cb_fn = WNDENUMPROC(desk_callback)
            user32.EnumDesktopWindows(h_desk, cb_fn, 0)
            user32.CloseDesktop(h_desk)
    except Exception as ex:
        logger.debug("EnumDesktopWindows on Default desktop failed: %s", ex)

    # Sort foreground window first, then by title
    results.sort(key=lambda w: (not w.is_foreground, w.title.lower()))
    return results


