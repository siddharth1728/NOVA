"""Abstract controller interfaces for the NOVA Computer Control Engine.

Establishes platform-independent contracts for application, window, input,
clipboard, process, UI automation, and screen management.
"""

from abc import ABC, abstractmethod
from typing import Any

from nova.control.applications.models import AppInfo, LaunchRequest, LaunchResult
from nova.control.automation.models import TargetingResult, UIElementInfo, UIElementTarget, VisionTarget
from nova.control.browsers.models import BrowserInfo, BrowserTab
from nova.control.clipboard.models import ClipboardContent, ClipboardType
from nova.control.input.models import InputResult, Key, MouseAction, MouseButton
from nova.control.processes.models import ProcessFilter, ProcessInfo, ProcessStopResult
from nova.control.windows.models import WindowBounds, WindowInfo, WindowTarget
from nova.protocol.models import EmergencyActionResponse, ScreenCaptureRequest, ScreenCaptureResponse


class ApplicationController(ABC):
    """Contract for application discovery and execution management."""

    @abstractmethod
    def list_applications(self, search: str | None = None) -> list[AppInfo]:
        """Enumerate installed or discoverable applications."""
        ...

    @abstractmethod
    def find_application(self, name_or_path: str) -> AppInfo | None:
        """Find a specific application by name, executable, or path."""
        ...

    @abstractmethod
    def launch_application(self, request: LaunchRequest) -> LaunchResult:
        """Safely launch an application and optionally wait for its window."""
        ...

    @abstractmethod
    def is_running(self, app_name: str) -> bool:
        """Check whether any instances of the application are running."""
        ...


class WindowController(ABC):
    """Contract for desktop window enumeration, targeting, and manipulation."""

    @abstractmethod
    def list_windows(self, visible_only: bool = True) -> list[WindowInfo]:
        """Enumerate top-level application windows."""
        ...

    @abstractmethod
    def get_window(self, hwnd: int) -> WindowInfo | None:
        """Retrieve details for a specific window handle."""
        ...

    @abstractmethod
    def get_foreground_window(self) -> WindowInfo | None:
        """Retrieve the currently focused foreground window."""
        ...

    @abstractmethod
    def resolve_target(self, target: WindowTarget) -> WindowInfo:
        """Deterministically resolve a target window, preventing ambiguous actions."""
        ...

    @abstractmethod
    def focus_window(self, hwnd: int) -> bool:
        """Bring window to foreground and assign active keyboard focus."""
        ...

    @abstractmethod
    def minimize_window(self, hwnd: int) -> bool:
        """Minimize the target window."""
        ...

    @abstractmethod
    def maximize_window(self, hwnd: int) -> bool:
        """Maximize the target window."""
        ...

    @abstractmethod
    def restore_window(self, hwnd: int) -> bool:
        """Restore window from minimized or maximized state."""
        ...

    @abstractmethod
    def close_window(self, hwnd: int) -> bool:
        """Send close request to window."""
        ...

    @abstractmethod
    def move_window(self, hwnd: int, x: int, y: int, width: int, height: int) -> WindowBounds:
        """Move and resize window to target bounds."""
        ...


class MouseController(ABC):
    """Contract for controlled mouse input injection."""

    @abstractmethod
    def get_position(self) -> tuple[int, int]:
        """Return current cursor position in desktop screen coordinates."""
        ...

    @abstractmethod
    def move(self, x: int, y: int, relative_to_hwnd: int | None = None) -> tuple[int, int]:
        """Move mouse cursor to coordinates."""
        ...

    @abstractmethod
    def click(
        self,
        button: MouseButton = MouseButton.LEFT,
        count: int = 1,
        x: int | None = None,
        y: int | None = None,
        relative_to_hwnd: int | None = None,
    ) -> InputResult:
        """Click mouse button at specified or current coordinates."""
        ...

    @abstractmethod
    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> InputResult:
        """Press and hold mouse button."""
        ...

    @abstractmethod
    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> InputResult:
        """Release mouse button."""
        ...

    @abstractmethod
    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        button: MouseButton = MouseButton.LEFT,
    ) -> InputResult:
        """Drag mouse from start to end coordinates."""
        ...

    @abstractmethod
    def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> InputResult:
        """Scroll vertical wheel."""
        ...


class KeyboardController(ABC):
    """Contract for controlled keyboard typing and combination injection."""

    @abstractmethod
    def type_text(self, text: str, target_hwnd: int | None = None) -> InputResult:
        """Type text string using layout-independent Unicode input."""
        ...

    @abstractmethod
    def press_key(self, key: Key | str, target_hwnd: int | None = None) -> InputResult:
        """Press down a specific key."""
        ...

    @abstractmethod
    def release_key(self, key: Key | str, target_hwnd: int | None = None) -> InputResult:
        """Release a held key."""
        ...

    @abstractmethod
    def send_combination(self, keys: list[Key | str], target_hwnd: int | None = None) -> InputResult:
        """Execute a key chord/combination (e.g. Ctrl+C) with safety validation."""
        ...


class ClipboardController(ABC):
    """Contract for clipboard inspection and manipulation."""

    @abstractmethod
    def read_text(self) -> str | None:
        """Read textual content currently in system clipboard."""
        ...

    @abstractmethod
    def write_text(self, text: str) -> bool:
        """Write text to system clipboard."""
        ...

    @abstractmethod
    def clear(self) -> bool:
        """Empty system clipboard contents."""
        ...

    @abstractmethod
    def inspect(self) -> ClipboardContent:
        """Inspect clipboard metadata without necessarily exposing full raw payload."""
        ...


class ProcessController(ABC):
    """Contract for process telemetry inspection and supervised termination."""

    @abstractmethod
    def list_processes(self, filter_criteria: ProcessFilter | None = None) -> list[ProcessInfo]:
        """Enumerate active processes with resource usage."""
        ...

    @abstractmethod
    def inspect_process(self, pid: int) -> ProcessInfo | None:
        """Inspect detailed telemetry for a single process."""
        ...

    @abstractmethod
    def stop_process(self, pid: int, force: bool = False) -> ProcessStopResult:
        """Terminate a process, enforcing protected process guards."""
        ...


class ScreenController(ABC):
    """Contract for display management and frame capture."""

    @abstractmethod
    def list_displays(self) -> list[dict[str, Any]]:
        """List connected monitors and desktop metrics."""
        ...

    @abstractmethod
    def capture(self, request: ScreenCaptureRequest | None = None) -> ScreenCaptureResponse:
        """Capture full desktop frame."""
        ...

    @abstractmethod
    def capture_window(self, hwnd: int, format: str = "png", quality: int = 80) -> ScreenCaptureResponse:
        """Capture isolated bounding rectangle of a specific window."""
        ...


class UIAutomationController(ABC):
    """Contract for Windows UI Automation semantic interaction."""

    @abstractmethod
    def inspect_tree(self, hwnd: int | None = None, max_depth: int = 3) -> list[UIElementInfo]:
        """Inspect semantic UI elements in window or desktop."""
        ...

    @abstractmethod
    def find_element(self, target: UIElementTarget, hwnd: int | None = None) -> UIElementInfo | None:
        """Locate element matching criteria."""
        ...

    @abstractmethod
    def invoke(self, target: UIElementTarget, hwnd: int | None = None) -> bool:
        """Trigger primary default action on UI element (e.g. click button)."""
        ...

    @abstractmethod
    def set_value(self, target: UIElementTarget, value: str, hwnd: int | None = None) -> bool:
        """Set edit or text value of UI element."""
        ...


class BrowserController(ABC):
    """Contract for web browser discovery and navigation."""

    @abstractmethod
    def list_browsers(self) -> list[BrowserInfo]:
        """List detected web browsers."""
        ...

    @abstractmethod
    def navigate(self, url: str, browser: str | None = None) -> bool:
        """Navigate browser to target URL."""
        ...


class PowerController(ABC):
    """Contract for workstation state management."""

    @abstractmethod
    def lock_workstation(self, dry_run: bool = False) -> EmergencyActionResponse:
        """Lock workstation session."""
        ...
