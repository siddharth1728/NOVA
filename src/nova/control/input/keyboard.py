"""Windows keyboard controller implementation supporting Unicode input and chord safety."""

import ctypes
from ctypes import wintypes
import logging
import time
import win32con
import win32gui

from nova.control.input.models import InputResult, Key
from nova.control.input.safety import is_safe_key_combination, normalize_key_name
from nova.control.interfaces import KeyboardController
from nova.errors import InputInjectionError, PermissionDeniedError, WindowNotFoundError

logger = logging.getLogger("nova.control.input.keyboard")


# Win32 SendInput Structures for Unicode keystrokes
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", INPUT_UNION),
    ]


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

# Mapping of canonical Key names to Win32 Virtual Key codes
VK_MAP: dict[str, int] = {
    "enter": win32con.VK_RETURN,
    "return": win32con.VK_RETURN,
    "escape": win32con.VK_ESCAPE,
    "esc": win32con.VK_ESCAPE,
    "tab": win32con.VK_TAB,
    "space": win32con.VK_SPACE,
    "backspace": win32con.VK_BACK,
    "delete": win32con.VK_DELETE,
    "del": win32con.VK_DELETE,
    "insert": win32con.VK_INSERT,
    "home": win32con.VK_HOME,
    "end": win32con.VK_END,
    "page_up": win32con.VK_PRIOR,
    "page_down": win32con.VK_NEXT,
    "up": win32con.VK_UP,
    "down": win32con.VK_DOWN,
    "left": win32con.VK_LEFT,
    "right": win32con.VK_RIGHT,
    "f1": win32con.VK_F1,
    "f2": win32con.VK_F2,
    "f3": win32con.VK_F3,
    "f4": win32con.VK_F4,
    "f5": win32con.VK_F5,
    "f6": win32con.VK_F6,
    "f7": win32con.VK_F7,
    "f8": win32con.VK_F8,
    "f9": win32con.VK_F9,
    "f10": win32con.VK_F10,
    "f11": win32con.VK_F11,
    "f12": win32con.VK_F12,
    "ctrl": win32con.VK_CONTROL,
    "control": win32con.VK_CONTROL,
    "alt": win32con.VK_MENU,
    "shift": win32con.VK_SHIFT,
    "win": win32con.VK_LWIN,
    "windows": win32con.VK_LWIN,
}


class WindowsKeyboardController(KeyboardController):
    """Authoritative Windows keyboard controller with Unicode injection and chord safety."""

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def _ensure_target_focused(self, target_hwnd: int | None) -> None:
        """Verify target window exists and is in the foreground before sending keystrokes."""
        if target_hwnd is not None:
            if not win32gui.IsWindow(target_hwnd):
                raise WindowNotFoundError(f"Target HWND {target_hwnd} does not exist", details={"hwnd": target_hwnd})
            if win32gui.GetForegroundWindow() != target_hwnd:
                try:
                    win32gui.SetForegroundWindow(target_hwnd)
                    time.sleep(0.08)
                except Exception as ex:
                    logger.warning("Could not bring target HWND %d to foreground: %s", target_hwnd, ex)

    def type_text(self, text: str, target_hwnd: int | None = None) -> InputResult:
        """Type text string using layout-independent Unicode SendInput."""
        if target_hwnd is not None and not self.dry_run:
            self._ensure_target_focused(target_hwnd)

        if self.dry_run:
            return InputResult(
                success=True,
                action="type_text",
                target_hwnd=target_hwnd,
                details={"characters": len(text), "preview": text[:20]},
            )

        # Build SendInput array for Unicode characters
        send_input_fn = ctypes.windll.user32.SendInput
        send_input_fn.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        send_input_fn.restype = wintypes.UINT

        for char in text:
            code_point = ord(char)
            # Key down
            inp_down = INPUT(type=INPUT_KEYBOARD)
            inp_down.u.ki = KEYBDINPUT(
                wVk=0,
                wScan=code_point,
                dwFlags=KEYEVENTF_UNICODE,
                time=0,
                dwExtraInfo=0,
            )
            # Key up
            inp_up = INPUT(type=INPUT_KEYBOARD)
            inp_up.u.ki = KEYBDINPUT(
                wVk=0,
                wScan=code_point,
                dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=0,
            )

            inputs = (INPUT * 2)(inp_down, inp_up)
            send_input_fn(2, inputs, ctypes.sizeof(INPUT))
            time.sleep(0.01)

        return InputResult(
            success=True,
            action="type_text",
            target_hwnd=target_hwnd,
            details={"characters": len(text), "preview": text[:20]},
        )

    def press_key(self, key: Key | str, target_hwnd: int | None = None) -> InputResult:
        """Press down a specific virtual key."""
        norm = normalize_key_name(key)
        vk = VK_MAP.get(norm)
        if vk is None and len(norm) == 1:
            vk = ord(norm.upper())

        if vk is None:
            return InputResult(success=False, action="press_key", message=f"Unknown key: {key}")

        if target_hwnd is not None and not self.dry_run:
            self._ensure_target_focused(target_hwnd)

        if self.dry_run:
            return InputResult(success=True, action="press_key", details={"key": norm, "vk": vk})

        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        return InputResult(success=True, action="press_key", details={"key": norm, "vk": vk})

    def release_key(self, key: Key | str, target_hwnd: int | None = None) -> InputResult:
        """Release a held virtual key."""
        norm = normalize_key_name(key)
        vk = VK_MAP.get(norm)
        if vk is None and len(norm) == 1:
            vk = ord(norm.upper())

        if vk is None:
            return InputResult(success=False, action="release_key", message=f"Unknown key: {key}")

        if self.dry_run:
            return InputResult(success=True, action="release_key", details={"key": norm, "vk": vk})

        ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        return InputResult(success=True, action="release_key", details={"key": norm, "vk": vk})

    def send_combination(self, keys: list[Key | str], target_hwnd: int | None = None) -> InputResult:
        """Execute a key combination (chord) with safety validation."""
        is_safe, reason = is_safe_key_combination(keys)
        if not is_safe:
            raise InputInjectionError(
                reason,
                details={"keys": [str(k) for k in keys]},
            )

        if target_hwnd is not None and not self.dry_run:
            self._ensure_target_focused(target_hwnd)

        normalized = [normalize_key_name(k) for k in keys]
        if self.dry_run:
            return InputResult(
                success=True,
                action="send_combination",
                target_hwnd=target_hwnd,
                details={"combination": "+".join(normalized), "mode": "DRY RUN"},
            )

        vk_codes: list[int] = []
        for k in normalized:
            vk = VK_MAP.get(k)
            if vk is None and len(k) == 1:
                vk = ord(k.upper())
            if vk is not None:
                vk_codes.append(vk)

        # Press down in order
        for vk in vk_codes:
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.02)

        time.sleep(0.04)

        # Release in reverse order
        for vk in reversed(vk_codes):
            ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.02)

        return InputResult(
            success=True,
            action="send_combination",
            target_hwnd=target_hwnd,
            details={"combination": "+".join(normalized)},
        )

    def press_combination(self, keys: list[Key | str], target_hwnd: int | None = None) -> InputResult:
        """Alias for send_combination."""
        return self.send_combination(keys, target_hwnd=target_hwnd)

