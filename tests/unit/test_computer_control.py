"""Unit tests for Phase 05 Computer Control Engine.

Ensures absolute safety: dry_run mode is active so that the user's real mouse,
keyboard, windows, and processes are NEVER disturbed during test execution.
"""

from datetime import datetime, timezone
import pytest

from nova.control.applications.discovery import WindowsAppDiscovery
from nova.control.applications.launcher import WindowsApplicationController
from nova.control.applications.models import AppInfo, LaunchRequest
from nova.control.automation.models import UIElementInfo, UIElementTarget, VisionTarget
from nova.control.automation.targeting import DeterministicTargetingCascade
from nova.control.automation.uia import WindowsUIAutomationController
from nova.control.automation.vision import VisionFallbackTargeter
from nova.control.clipboard.manager import WindowsClipboardController
from nova.control.input.keyboard import WindowsKeyboardController
from nova.control.input.models import Key, KeyCombination, MouseAction, MouseButton
from nova.control.input.mouse import WindowsMouseController
from nova.control.input.safety import is_safe_key_combination, normalize_key_name
from nova.control.journal import ComputerActionJournal, ComputerActionRecord
from nova.control.processes.manager import WindowsProcessController
from nova.control.processes.models import ProcessFilter
from nova.control.windows.enumeration import enumerate_windows
from nova.control.windows.manager import WindowsWindowController
from nova.control.windows.models import WindowBounds, WindowInfo, WindowTarget
from nova.control.windows.targeting import resolve_target_window
from nova.errors import (
    AmbiguousTargetError,
    ApplicationLaunchError,
    InputInjectionError,
    ProtectedProcessError,
    StaleVisionTargetError,
    VisionConfidenceError,
    WindowNotFoundError,
)


# =============================================================================
# 1. Window Enumeration and Targeting Tests
# =============================================================================


def test_window_enumeration():
    windows = enumerate_windows(visible_only=False)
    assert isinstance(windows, list)


def test_window_controller_list_windows_dry_run():
    ctrl = WindowsWindowController(dry_run=True)
    windows = ctrl.list_windows()
    assert len(windows) >= 2
    assert windows[0].hwnd == 1001
    assert windows[0].process_name == "agy.exe"
    assert windows[0].pid == 1234
    assert windows[0].is_foreground is True


def test_window_targeting_by_hwnd():
    mock_windows = [
        WindowInfo(hwnd=1001, title="Editor", pid=10, process_name="code.exe", bounds=WindowBounds(x=0, y=0, width=800, height=600), visible=True),
        WindowInfo(hwnd=1002, title="Terminal", pid=20, process_name="pwsh.exe", bounds=WindowBounds(x=0, y=0, width=600, height=400), visible=True),
    ]
    target = WindowTarget(hwnd=1002)
    resolved = resolve_target_window(target, mock_windows)
    assert resolved.hwnd == 1002
    assert resolved.title == "Terminal"


def test_window_targeting_ambiguous_fails():
    mock_windows = [
        WindowInfo(hwnd=101, title="Document 1 - Notepad", pid=11, process_name="notepad.exe", bounds=WindowBounds(x=0, y=0, width=400, height=300), visible=True),
        WindowInfo(hwnd=102, title="Document 2 - Notepad", pid=12, process_name="notepad.exe", bounds=WindowBounds(x=0, y=0, width=400, height=300), visible=True),
    ]
    target = WindowTarget(app_name="notepad")
    with pytest.raises(AmbiguousTargetError) as exc_info:
        resolve_target_window(target, mock_windows)
    assert "Ambiguous window target" in str(exc_info.value)
    assert len(exc_info.value.candidates) == 2


def test_window_targeting_not_found():
    mock_windows = [
        WindowInfo(hwnd=201, title="Browser", pid=5, process_name="chrome.exe", bounds=WindowBounds(x=0, y=0, width=800, height=600), visible=True),
    ]
    target = WindowTarget(exact_title="NonExistentWindowXYZ")
    with pytest.raises(WindowNotFoundError):
        resolve_target_window(target, mock_windows)


# =============================================================================
# 2. Window Controller (with dry_run safe mode)
# =============================================================================


def test_window_controller_dry_run_operations():
    ctrl = WindowsWindowController(dry_run=True)
    # Focus
    assert ctrl.focus_window(9999) is True
    # Move
    bounds = WindowBounds(x=100, y=100, width=800, height=600)
    assert ctrl.move_resize_window(9999, bounds) is True
    # Minimize / Maximize / Restore
    assert ctrl.minimize_window(9999) is True
    assert ctrl.maximize_window(9999) is True
    assert ctrl.restore_window(9999) is True
    # Close
    assert ctrl.close_window(9999) is True


# =============================================================================
# 3. Mouse and Keyboard Input Safety (dry_run mode)
# =============================================================================


def test_mouse_controller_dry_run_safety():
    ctrl = WindowsMouseController(dry_run=True)
    pos = ctrl.move(500, 400)
    assert pos == (500, 400)

    res_click = ctrl.click(MouseButton.LEFT)
    assert res_click.success is True
    assert res_click.action == "left_click"

    res_drag = ctrl.drag(100, 100, 200, 200)
    assert res_drag.success is True

    res_scroll = ctrl.scroll(120)
    assert res_scroll.success is True


def test_keyboard_controller_dry_run_safety():
    ctrl = WindowsKeyboardController(dry_run=True)
    res_type = ctrl.type_text("Hello World")
    assert res_type.success is True
    assert res_type.details.get("characters") == 11

    res_press = ctrl.press_key("Enter")
    assert res_press.success is True

    res_combo = ctrl.press_combination(["ctrl", "c"])
    assert res_combo.success is True


def test_keyboard_sensitive_key_safety_blocks():
    # Ctrl+Alt+Del must be denied
    is_safe, _ = is_safe_key_combination(["ctrl", "alt", "delete"])
    assert is_safe is False
    is_safe, _ = is_safe_key_combination(["ctrl", "alt", "del"])
    assert is_safe is False

    # Win+L must be denied
    is_safe, _ = is_safe_key_combination(["win", "l"])
    assert is_safe is False

    # Win+X must be denied
    is_safe, _ = is_safe_key_combination(["win", "x"])
    assert is_safe is False

    # Standard safe combinations must pass
    is_safe, _ = is_safe_key_combination(["ctrl", "c"])
    assert is_safe is True
    is_safe, _ = is_safe_key_combination(["ctrl", "v"])
    assert is_safe is True
    is_safe, _ = is_safe_key_combination(["alt", "tab"])
    assert is_safe is True


def test_keyboard_controller_rejects_dangerous_combo():
    ctrl = WindowsKeyboardController(dry_run=True)
    with pytest.raises(InputInjectionError) as exc_info:
        ctrl.press_combination(["ctrl", "alt", "del"])
    assert "blocked by nova system key safety policy" in str(exc_info.value).lower()


# =============================================================================
# 4. Clipboard Controller Tests
# =============================================================================


def test_clipboard_controller_read_and_write():
    ctrl = WindowsClipboardController(dry_run=True)
    test_text = "nova_test_clipboard_value_987"
    assert ctrl.write_text(test_text) is True
    assert ctrl.read_text() == test_text

    content = ctrl.inspect()
    assert content.has_text is True
    assert content.text_length == len(test_text)
    assert content.hash_sha256 is not None

    assert ctrl.clear() is True
    cleared = ctrl.inspect()
    assert cleared.has_text is False


# =============================================================================
# 5. Process Controller & Protected Process Guard
# =============================================================================


def test_process_controller_list_and_filter():
    ctrl = WindowsProcessController()
    pfilter = ProcessFilter(limit=10)
    procs = ctrl.list_processes(pfilter)
    assert len(procs) > 0
    assert procs[0].pid >= 0
    assert procs[0].name != ""


def test_process_controller_blocks_protected_process():
    ctrl = WindowsProcessController(dry_run=True)
    # PID 4 is always Windows System
    with pytest.raises(ProtectedProcessError) as exc_info:
        ctrl.stop_process(4)
    assert "protected" in str(exc_info.value).lower()


# =============================================================================
# 6. Application Discovery & Launch Protection
# =============================================================================


def test_application_discovery():
    discovery = WindowsAppDiscovery()
    apps = discovery.list_applications()
    assert isinstance(apps, list)
    assert len(apps) > 0
    names = [a.name.lower() for a in apps]
    assert any("notepad" in n or "edge" in n or "calc" in n for n in names)


def test_application_controller_prohibits_script_extensions():
    ctrl = WindowsApplicationController(dry_run=True)
    req = LaunchRequest(app_name_or_path="malicious_script.bat")
    with pytest.raises(ApplicationLaunchError) as exc_info:
        ctrl.launch_application(req)
    assert "Direct script execution is prohibited" in str(exc_info.value)


# =============================================================================
# 7. UI Automation & Vision Fallback Layer
# =============================================================================


def test_ui_automation_element_search():
    ctrl = WindowsUIAutomationController(dry_run=True)
    tree = ctrl.inspect_tree()
    assert len(tree) >= 3
    target = UIElementTarget(name="File")
    element = ctrl.find_element(target)
    assert element is not None
    assert element.name == "File"


def test_vision_fallback_confidence_enforcement():
    targeter = VisionFallbackTargeter(min_confidence=0.80)
    low_conf_target = VisionTarget(
        screen_id="screen-0",
        capture_timestamp=datetime.now(timezone.utc).isoformat(),
        x=50,
        y=50,
        width=100,
        height=30,
        confidence=0.50,
        description="Submit button",
    )
    with pytest.raises(VisionConfidenceError) as exc_info:
        targeter.validate_target(low_conf_target)
    assert "below required threshold" in str(exc_info.value).lower()


def test_vision_fallback_stale_target_rejection():
    targeter = VisionFallbackTargeter(max_age_seconds=2.0)
    stale_timestamp = datetime.fromtimestamp(100.0, timezone.utc).isoformat()
    stale_target = VisionTarget(
        screen_id="screen-0",
        capture_timestamp=stale_timestamp,
        x=50,
        y=50,
        width=200,
        height=30,
        confidence=0.95,
        description="Search box",
    )
    with pytest.raises(StaleVisionTargetError) as exc_info:
        targeter.validate_target(stale_target)
    assert "is stale" in str(exc_info.value).lower()


def test_deterministic_targeting_cascade_uia_first():
    uia_ctrl = WindowsUIAutomationController(dry_run=True)
    cascade = DeterministicTargetingCascade(uia_controller=uia_ctrl)
    res = cascade.resolve(ui_target=UIElementTarget(name="File"))
    assert res.success is True
    assert res.method == "UI_AUTOMATION"
    assert res.element is not None
    assert res.element.name == "File"


# =============================================================================
# 8. Computer Action Journaling & Verification
# =============================================================================


def test_computer_action_journal_recording(tmp_path):
    journal_path = tmp_path / "test_actions.jsonl"
    journal = ComputerActionJournal(log_path=journal_path)

    record = ComputerActionRecord(
        action_type="WINDOW_FOCUS",
        target_summary="HWND 1234 (Notepad)",
        risk_level="LOW",
        device_id="iphone-001",
        success=True,
        verified=True,
        verification_method="FOREGROUND_HWND_CHECK",
        duration_ms=12.5,
    )
    journal.record(record)

    records = journal.list_records(limit=10)
    assert len(records) == 1
    assert records[0].action_type == "WINDOW_FOCUS"
    assert records[0].verified is True
    assert journal_path.exists()
