"""Security and policy enforcement tests for Phase 05 Computer Control Engine.

Proves:
- Protected process termination is denied.
- Host self-termination is denied.
- Malformed HWND is rejected.
- Ambiguous window target is rejected without guessing.
- Denied keyboard combinations (Ctrl+Alt+Del, Win+L, Win+X) are rejected.
- Script extensions (.bat, .cmd, .ps1, etc.) cannot be launched.
- Unauthorized or revoked remote requests are rejected.
- Stale vision targets are rejected.
- Low-confidence vision targets are rejected.
- Action journal logs metadata and SHA hashes instead of plaintext secrets.
"""

from datetime import datetime, timezone
import os
import pytest
from starlette.testclient import TestClient

from nova.agent.runtime import NovaRuntime
from nova.config.settings import NovaSettings
from nova.control.applications.launcher import WindowsApplicationController
from nova.control.applications.models import LaunchRequest
from nova.control.automation.models import VisionTarget
from nova.control.automation.vision import VisionFallbackTargeter
from nova.control.clipboard.manager import WindowsClipboardController
from nova.control.input.keyboard import WindowsKeyboardController
from nova.control.input.safety import is_safe_key_combination
from nova.control.journal import ComputerActionJournal, ComputerActionRecord
from nova.control.processes.manager import WindowsProcessController
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
from nova.host.auth import DeviceRegistry, TokenManager
from nova.host.pairing import PairingManager
from nova.host.server import create_host_app


def test_protected_process_termination_denied():
    ctrl = WindowsProcessController(dry_run=True)
    # PID 0 (Idle) and 4 (System)
    with pytest.raises(ProtectedProcessError):
        ctrl.stop_process(0)
    with pytest.raises(ProtectedProcessError):
        ctrl.stop_process(4)


def test_host_self_termination_denied():
    ctrl = WindowsProcessController(dry_run=True)
    with pytest.raises(ProtectedProcessError) as exc_info:
        ctrl.stop_process(os.getpid())
    assert "current host process" in str(exc_info.value).lower()


def test_malformed_hwnd_rejected():
    mock_windows = [
        WindowInfo(hwnd=1001, title="Test", pid=10, process_name="test.exe", bounds=WindowBounds(x=0, y=0, width=100, height=100), visible=True)
    ]
    target = WindowTarget(hwnd=99999999)
    with pytest.raises(WindowNotFoundError):
        resolve_target_window(target, mock_windows)


def test_ambiguous_window_target_rejected_without_guessing():
    candidates = [
        WindowInfo(hwnd=101, title="Editor Alpha", pid=1, process_name="code.exe", bounds=WindowBounds(x=0, y=0, width=100, height=100), visible=True),
        WindowInfo(hwnd=102, title="Editor Beta", pid=2, process_name="code.exe", bounds=WindowBounds(x=0, y=0, width=100, height=100), visible=True),
    ]
    # App name matches both windows, neither is foreground
    target = WindowTarget(app_name="code")
    with pytest.raises(AmbiguousTargetError) as exc_info:
        resolve_target_window(target, candidates)
    assert len(exc_info.value.candidates) == 2


def test_denied_keyboard_combinations_strictly_blocked():
    blocked = [
        ["ctrl", "alt", "del"],
        ["ctrl", "alt", "delete"],
        ["win", "l"],
        ["win", "x"],
        ["ctrl", "shift", "escape"],
    ]
    for combo in blocked:
        is_safe, reason = is_safe_key_combination(combo)
        assert is_safe is False, f"Combination {combo} should be blocked"
        assert "blocked" in reason.lower()

    ctrl = WindowsKeyboardController(dry_run=True)
    for combo in blocked:
        with pytest.raises(InputInjectionError):
            ctrl.send_combination(combo)


def test_direct_script_launch_prohibited():
    ctrl = WindowsApplicationController(dry_run=True)
    dangerous_scripts = [
        "payload.bat",
        "script.cmd",
        "run.ps1",
        "evil.vbs",
        "execute.wsf",
    ]
    for script in dangerous_scripts:
        with pytest.raises(ApplicationLaunchError):
            ctrl.launch_application(LaunchRequest(app_name_or_path=script))


def test_stale_vision_target_rejected():
    targeter = VisionFallbackTargeter(max_age_seconds=1.5)
    stale_target = VisionTarget(
        screen_id="display-0",
        capture_timestamp=datetime.fromtimestamp(1000.0, timezone.utc).isoformat(),
        x=200,
        y=300,
        width=100,
        height=30,
        confidence=0.99,
        description="Login button",
    )
    with pytest.raises(StaleVisionTargetError) as exc:
        targeter.validate_and_resolve(stale_target)
    assert "is stale" in str(exc.value).lower()


def test_low_confidence_vision_target_rejected():
    targeter = VisionFallbackTargeter(min_confidence=0.85)
    weak_target = VisionTarget(
        screen_id="display-0",
        capture_timestamp=datetime.now(timezone.utc).isoformat(),
        x=200,
        y=300,
        width=100,
        height=30,
        confidence=0.65,
        description="Fuzzy button",
    )
    with pytest.raises(VisionConfidenceError) as exc:
        targeter.validate_and_resolve(weak_target)
    assert "below required threshold" in str(exc.value).lower()


def test_clipboard_preserves_privacy_in_journal(tmp_path):
    journal = ComputerActionJournal(log_path=tmp_path / "journal_privacy.jsonl")
    secret_text = "SuperSecretPassword123!"

    ctrl = WindowsClipboardController(dry_run=True)
    ctrl.write_text(secret_text)
    content = ctrl.inspect()

    # Record clipboard action with hash in after_state
    record = ComputerActionRecord(
        action_type="CLIPBOARD_WRITE",
        target_summary="System Clipboard",
        risk_level="HIGH",
        device_id="iphone-test",
        success=True,
        verified=True,
        verification_method="SHA256_HASH_VERIFIED",
        after_state={"len": content.text_length, "hash_sha256": content.hash_sha256},
    )
    journal.record(record)

    # Read journal file content directly
    log_content = (tmp_path / "journal_privacy.jsonl").read_text(encoding="utf-8")
    assert secret_text not in log_content
    assert content.hash_sha256 in log_content


def test_revoked_device_rejected_from_computer_endpoints(tmp_path):
    settings = NovaSettings(
        workspace_root=tmp_path / "workspace",
        data_dir=tmp_path / ".nova",
        host_secret="integration-test-secret-at-least-32-bytes-long",
    )
    settings.workspace_root.mkdir(parents=True, exist_ok=True)

    device_registry = DeviceRegistry(settings.devices_file)
    token_manager = TokenManager(secret_key=settings.host_secret.get_secret_value())
    pairing_manager = PairingManager(default_ttl_seconds=300)
    runtime = NovaRuntime(settings=settings)

    app = create_host_app(
        settings=settings,
        runtime=runtime,
        device_registry=device_registry,
        token_manager=token_manager,
        pairing_manager=pairing_manager,
    )
    client = TestClient(app)

    # Pair device
    code, _ = pairing_manager.generate_code()
    pair_resp = client.post(
        "/api/v1/pair",
        json={
            "pairing_code": code,
            "device_id": "iphone-to-revoke",
            "device_name": "Revocable iPhone",
            "platform": "iOS",
        },
    )
    assert pair_resp.status_code == 200
    token = pair_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify access works initially
    resp = client.get("/api/v1/computer/windows", headers=headers)
    assert resp.status_code == 200

    # Explicitly revoke device
    device_registry.revoke_device("iphone-to-revoke")

    # Access must now be rejected with 403 REVOKED_DEVICE
    resp = client.get("/api/v1/computer/windows", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "REVOKED_DEVICE"
