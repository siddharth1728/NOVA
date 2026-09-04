"""NOVA Computer Control Tools for the Antigravity Agent Runtime.

Exposes native Windows application, window, input, clipboard, process, UI automation,
and screen capture capabilities under formal risk classifications.
"""

from typing import Any

from nova.control.applications.discovery import WindowsAppDiscovery
from nova.control.applications.launcher import WindowsApplicationController
from nova.control.applications.models import LaunchRequest
from nova.control.automation.models import UIElementTarget
from nova.control.automation.uia import WindowsUIAutomationController
from nova.control.browsers.manager import WindowsBrowserController
from nova.control.clipboard.manager import WindowsClipboardController
from nova.control.input.keyboard import WindowsKeyboardController
from nova.control.input.models import Key, MouseAction, MouseButton
from nova.control.input.mouse import WindowsMouseController
from nova.control.journal import ComputerActionJournal, ComputerActionRecord
from nova.control.processes.manager import WindowsProcessController
from nova.control.processes.models import ProcessFilter
from nova.control.screen import ScreenCaptureProvider
from nova.control.windows.manager import WindowsWindowController
from nova.control.windows.models import WindowTarget
from nova.tools.categories import ToolCategory
from nova.tools.metadata import ToolMetadata, ToolRiskLevel
from nova.tools.registry import ToolRegistry, get_tool_registry

# Shared controller singletons for tool handlers
_app_ctrl = WindowsApplicationController()
_win_ctrl = WindowsWindowController()
_mouse_ctrl = WindowsMouseController()
_kbd_ctrl = WindowsKeyboardController()
_clip_ctrl = WindowsClipboardController()
_proc_ctrl = WindowsProcessController()
_screen_ctrl = ScreenCaptureProvider()
_uia_ctrl = WindowsUIAutomationController()
_browser_ctrl = WindowsBrowserController()
_journal = ComputerActionJournal()


def get_journal() -> ComputerActionJournal:
    return _journal


# =============================================================================
# Tool Handlers
# =============================================================================


def handle_list_windows(visible_only: bool = True) -> list[dict[str, Any]]:
    """Enumerate top-level application windows on desktop."""
    windows = _win_ctrl.list_windows(visible_only=visible_only)
    return [w.model_dump() for w in windows]


def handle_focus_window(
    hwnd: int | None = None,
    title_pattern: str | None = None,
    app_name: str | None = None,
) -> dict[str, Any]:
    """Bring target window to foreground and verify focus."""
    target = WindowTarget(hwnd=hwnd, title_pattern=title_pattern, app_name=app_name)
    win = _win_ctrl.resolve_target(target)
    before_fg = _win_ctrl.get_foreground_window()

    success = _win_ctrl.focus_window(win.hwnd)
    after_fg = _win_ctrl.get_foreground_window()
    verified = (after_fg is not None and after_fg.hwnd == win.hwnd)

    record = ComputerActionRecord(
        action_type="focus_window",
        target_summary=f"HWND:{win.hwnd} ({win.title})",
        risk_level="LOW",
        before_state={"foreground_hwnd": before_fg.hwnd if before_fg else None},
        after_state={"foreground_hwnd": after_fg.hwnd if after_fg else None},
        verified=verified,
        verification_method="GetForegroundWindow",
        success=success,
    )
    _journal.record(record)

    return {
        "success": success,
        "action": "focus_window",
        "target": {"hwnd": win.hwnd, "title": win.title},
        "verified": verified,
    }


def handle_close_window(
    hwnd: int | None = None,
    title_pattern: str | None = None,
    app_name: str | None = None,
) -> dict[str, Any]:
    """Close an application window and verify it is terminated."""
    target = WindowTarget(hwnd=hwnd, title_pattern=title_pattern, app_name=app_name)
    win = _win_ctrl.resolve_target(target)

    success = _win_ctrl.close_window(win.hwnd)

    record = ComputerActionRecord(
        action_type="close_window",
        target_summary=f"HWND:{win.hwnd} ({win.title})",
        risk_level="HIGH",
        requires_approval=True,
        verified=success,
        verification_method="IsWindow",
        success=success,
    )
    _journal.record(record)

    return {
        "success": success,
        "action": "close_window",
        "target": {"hwnd": win.hwnd, "title": win.title},
        "verified": success,
    }


def handle_move_window(
    x: int,
    y: int,
    width: int,
    height: int,
    hwnd: int | None = None,
    title_pattern: str | None = None,
) -> dict[str, Any]:
    """Move and resize target window."""
    target = WindowTarget(hwnd=hwnd, title_pattern=title_pattern)
    win = _win_ctrl.resolve_target(target)
    bounds = _win_ctrl.move_window(win.hwnd, x, y, width, height)

    return {
        "success": True,
        "action": "move_window",
        "target": {"hwnd": win.hwnd, "title": win.title},
        "bounds": bounds.model_dump(),
    }


def handle_list_applications(search: str | None = None) -> list[dict[str, Any]]:
    """Enumerate discoverable applications on host PC."""
    apps = _app_ctrl.list_applications(search=search)
    return [a.model_dump() for a in apps]


def handle_launch_application(
    app_name_or_path: str,
    arguments: list[str] | None = None,
    wait_for_window: bool = True,
) -> dict[str, Any]:
    """Safely launch an application and observe process and window appearance."""
    req = LaunchRequest(
        app_name_or_path=app_name_or_path,
        arguments=arguments or [],
        wait_for_window=wait_for_window,
    )
    res = _app_ctrl.launch_application(req)

    record = ComputerActionRecord(
        action_type="launch_application",
        target_summary=app_name_or_path,
        risk_level="MEDIUM",
        after_state={"pid": res.pid, "hwnd": res.hwnd, "title": res.window_title},
        verified=res.success and (res.pid is not None),
        verification_method="ProcessWatchdog",
        success=res.success,
        message=res.message,
    )
    _journal.record(record)

    return res.model_dump()


def handle_list_displays() -> list[dict[str, Any]]:
    """Enumerate physical monitors and desktop geometry."""
    return _screen_ctrl.list_displays()


def handle_screenshot(
    hwnd: int | None = None,
    format: str = "png",
    quality: int = 80,
) -> dict[str, Any]:
    """Capture full desktop or specific window frame."""
    if hwnd is not None:
        resp = _screen_ctrl.capture_window(hwnd, format=format, quality=quality)
    else:
        resp = _screen_ctrl.capture()

    return {
        "timestamp": resp.timestamp,
        "width": resp.width,
        "height": resp.height,
        "format": resp.format,
        "file_size_bytes": resp.file_size_bytes,
        "image_base64_length": len(resp.image_base64),
    }


def handle_mouse_move(x: int, y: int, relative_to_hwnd: int | None = None) -> dict[str, Any]:
    """Move mouse cursor."""
    pos = _mouse_ctrl.move(x, y, relative_to_hwnd=relative_to_hwnd)
    return {"success": True, "action": "mouse_move", "position": {"x": pos[0], "y": pos[1]}}


def handle_mouse_click(
    button: str = "left",
    count: int = 1,
    x: int | None = None,
    y: int | None = None,
    relative_to_hwnd: int | None = None,
) -> dict[str, Any]:
    """Click mouse button."""
    btn = MouseButton(button.lower())
    res = _mouse_ctrl.click(button=btn, count=count, x=x, y=y, relative_to_hwnd=relative_to_hwnd)
    return res.model_dump()


def handle_mouse_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
) -> dict[str, Any]:
    """Drag mouse cursor."""
    btn = MouseButton(button.lower())
    res = _mouse_ctrl.drag(start_x, start_y, end_x, end_y, button=btn)
    return res.model_dump()


def handle_mouse_scroll(clicks: int, x: int | None = None, y: int | None = None) -> dict[str, Any]:
    """Scroll mouse wheel."""
    res = _mouse_ctrl.scroll(clicks, x=x, y=y)
    return res.model_dump()


def handle_keyboard_type(text: str, target_hwnd: int | None = None) -> dict[str, Any]:
    """Type Unicode text into active or target window."""
    res = _kbd_ctrl.type_text(text, target_hwnd=target_hwnd)
    return res.model_dump()


def handle_key_press(keys: list[str] | str, target_hwnd: int | None = None) -> dict[str, Any]:
    """Inject keystroke or key combination (chord) with system safety validation."""
    key_list = [keys] if isinstance(keys, str) else keys
    if len(key_list) == 1:
        res = _kbd_ctrl.press_key(key_list[0], target_hwnd=target_hwnd)
        _kbd_ctrl.release_key(key_list[0], target_hwnd=target_hwnd)
    else:
        res = _kbd_ctrl.send_combination(key_list, target_hwnd=target_hwnd)
    return res.model_dump()


def handle_clipboard_read() -> dict[str, Any]:
    """Read text from clipboard with sensitivity auditing."""
    text = _clip_ctrl.read_text()
    meta = _clip_ctrl.inspect()
    return {
        "has_text": meta.has_text,
        "text_length": meta.text_length,
        "hash_sha256": meta.hash_sha256,
        "text": text,
    }


def handle_clipboard_write(text: str) -> dict[str, Any]:
    """Write text to system clipboard and verify hash."""
    success = _clip_ctrl.write_text(text)
    meta = _clip_ctrl.inspect()
    return {
        "success": success,
        "text_length": len(text),
        "hash_sha256": meta.hash_sha256,
    }


def handle_clipboard_clear() -> dict[str, Any]:
    """Clear clipboard."""
    success = _clip_ctrl.clear()
    return {"success": success}


def handle_list_processes(
    name_substring: str | None = None,
    min_memory_mb: float | None = None,
    min_cpu_percent: float | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Enumerate running processes with resource usage."""
    filt = ProcessFilter(
        name_substring=name_substring,
        min_memory_mb=min_memory_mb,
        min_cpu_percent=min_cpu_percent,
        limit=limit,
    )
    procs = _proc_ctrl.list_processes(filt)
    return [p.model_dump() for p in procs]


def handle_inspect_process(pid: int) -> dict[str, Any] | None:
    """Inspect detailed telemetry for a specific process ID."""
    p = _proc_ctrl.inspect_process(pid)
    return p.model_dump() if p else None


def handle_stop_process(pid: int, force: bool = False) -> dict[str, Any]:
    """Supervised termination of a process, enforcing protected process guards."""
    res = _proc_ctrl.stop_process(pid=pid, force=force)

    record = ComputerActionRecord(
        action_type="stop_process",
        target_summary=f"PID:{pid} ({res.name})",
        risk_level="HIGH",
        requires_approval=True,
        verified=res.success,
        verification_method="psutil.wait_procs",
        success=res.success,
        message=res.message,
    )
    _journal.record(record)

    return res.model_dump()


def handle_uia_inspect(hwnd: int | None = None, max_depth: int = 3) -> list[dict[str, Any]]:
    """Inspect semantic UI elements in a window or top-level desktop."""
    elements = _uia_ctrl.inspect_tree(hwnd=hwnd, max_depth=max_depth)
    return [e.model_dump() for e in elements]


def handle_uia_invoke(
    name: str | None = None,
    automation_id: str | None = None,
    control_type: str | None = None,
    hwnd: int | None = None,
) -> dict[str, Any]:
    """Trigger primary action on a semantic UI element."""
    target = UIElementTarget(name=name, automation_id=automation_id, control_type=control_type)
    success = _uia_ctrl.invoke(target, hwnd=hwnd)
    return {"success": success, "action": "uia_invoke", "target": target.model_dump()}


def handle_uia_set_value(
    value: str,
    name: str | None = None,
    automation_id: str | None = None,
    control_type: str | None = None,
    hwnd: int | None = None,
) -> dict[str, Any]:
    """Set edit text or value of a semantic UI element."""
    target = UIElementTarget(name=name, automation_id=automation_id, control_type=control_type)
    success = _uia_ctrl.set_value(target, value=value, hwnd=hwnd)
    return {"success": success, "action": "uia_set_value", "target": target.model_dump()}


def handle_browser_navigate(url: str, browser: str | None = None) -> dict[str, Any]:
    """Navigate browser to a URL."""
    success = _browser_ctrl.navigate(url, browser=browser)
    return {"success": success, "url": url, "browser": browser}


# =============================================================================
# Registration
# =============================================================================


def register_computer_tools(registry: ToolRegistry | None = None) -> None:
    """Registers all Phase 05 Computer Control tools into the canonical ToolRegistry."""
    reg = registry or get_tool_registry()

    tool_specs = [
        # Windows Management
        (
            ToolMetadata(
                name="computer.list_windows",
                description="List visible top-level application windows with titles, PIDs, and bounds.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.READ_ONLY,
            ),
            handle_list_windows,
        ),
        (
            ToolMetadata(
                name="computer.focus_window",
                description="Bring a target window to foreground and assign active input focus.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.LOW,
            ),
            handle_focus_window,
        ),
        (
            ToolMetadata(
                name="computer.close_window",
                description="Close an application window (requires user confirmation).",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.HIGH,
                requires_approval=True,
                mutates_state=True,
            ),
            handle_close_window,
        ),
        (
            ToolMetadata(
                name="computer.move_window",
                description="Move and resize a window to target rectangular coordinates.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.MEDIUM,
                mutates_state=True,
            ),
            handle_move_window,
        ),

        # Applications
        (
            ToolMetadata(
                name="computer.list_applications",
                description="Discover installed, registered, and running Windows applications.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.READ_ONLY,
            ),
            handle_list_applications,
        ),
        (
            ToolMetadata(
                name="computer.launch_application",
                description="Safely launch an application and wait for its window to appear.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.MEDIUM,
                mutates_state=True,
            ),
            handle_launch_application,
        ),

        # Screens & Displays
        (
            ToolMetadata(
                name="computer.list_displays",
                description="Enumerate physical monitors, geometry, and virtual desktop coordinates.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.READ_ONLY,
            ),
            handle_list_displays,
        ),
        (
            ToolMetadata(
                name="computer.screenshot",
                description="Capture a desktop or window screenshot.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.LOW,
            ),
            handle_screenshot,
        ),

        # Mouse
        (
            ToolMetadata(
                name="computer.mouse_move",
                description="Move the mouse cursor to absolute or window-relative coordinates.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.LOW,
            ),
            handle_mouse_move,
        ),
        (
            ToolMetadata(
                name="computer.mouse_click",
                description="Click mouse button at specified or current coordinates.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.MEDIUM,
                mutates_state=True,
            ),
            handle_mouse_click,
        ),
        (
            ToolMetadata(
                name="computer.mouse_drag",
                description="Perform mouse drag gesture between coordinates.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.MEDIUM,
                mutates_state=True,
            ),
            handle_mouse_drag,
        ),
        (
            ToolMetadata(
                name="computer.mouse_scroll",
                description="Scroll the vertical mouse wheel.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.LOW,
            ),
            handle_mouse_scroll,
        ),

        # Keyboard
        (
            ToolMetadata(
                name="computer.keyboard_type",
                description="Type Unicode text into active or target window.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.MEDIUM,
                mutates_state=True,
            ),
            handle_keyboard_type,
        ),
        (
            ToolMetadata(
                name="computer.key_press",
                description="Send a keystroke or safe key combination (chord) to Windows.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.MEDIUM,
                mutates_state=True,
            ),
            handle_key_press,
        ),

        # Clipboard
        (
            ToolMetadata(
                name="computer.clipboard_read",
                description="Read textual content from the system clipboard.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.MEDIUM,
                accesses_sensitive_data=True,
            ),
            handle_clipboard_read,
        ),
        (
            ToolMetadata(
                name="computer.clipboard_write",
                description="Write text to system clipboard.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.MEDIUM,
                mutates_state=True,
            ),
            handle_clipboard_write,
        ),
        (
            ToolMetadata(
                name="computer.clipboard_clear",
                description="Clear system clipboard contents.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.MEDIUM,
                mutates_state=True,
            ),
            handle_clipboard_clear,
        ),

        # Processes
        (
            ToolMetadata(
                name="computer.list_processes",
                description="List active processes with CPU and memory usage.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.READ_ONLY,
            ),
            handle_list_processes,
        ),
        (
            ToolMetadata(
                name="computer.inspect_process",
                description="Inspect detailed telemetry for a specific Process ID.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.READ_ONLY,
            ),
            handle_inspect_process,
        ),
        (
            ToolMetadata(
                name="computer.stop_process",
                description="Supervised termination of a process (enforces protected system process guards).",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.HIGH,
                requires_approval=True,
                mutates_state=True,
            ),
            handle_stop_process,
        ),

        # UI Automation
        (
            ToolMetadata(
                name="computer.uia_inspect",
                description="Inspect semantic UI elements in a window or desktop.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.READ_ONLY,
            ),
            handle_uia_inspect,
        ),
        (
            ToolMetadata(
                name="computer.uia_invoke",
                description="Trigger primary action on a semantic UI element (e.g. click button).",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.MEDIUM,
                mutates_state=True,
            ),
            handle_uia_invoke,
        ),
        (
            ToolMetadata(
                name="computer.uia_set_value",
                description="Set edit text or value of a semantic UI element.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.MEDIUM,
                mutates_state=True,
            ),
            handle_uia_set_value,
        ),

        # Browsers
        (
            ToolMetadata(
                name="computer.browser_navigate",
                description="Navigate web browser to a URL.",
                category=ToolCategory.COMPUTER,
                risk_level=ToolRiskLevel.MEDIUM,
            ),
            handle_browser_navigate,
        ),
    ]

    for meta, handler in tool_specs:
        reg.register(meta, handler=handler)


register_computer_tools()

