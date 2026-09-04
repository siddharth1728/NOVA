"""Integration tests for Phase 05 Computer Control REST API endpoints.

Validates:
- Authentication enforcement (unauthenticated 401).
- Window enumeration, focusing, and sizing.
- Application discovery and safe launching.
- Mouse move, click, and scroll injection.
- Keyboard typing and key press injection.
- Clipboard inspection and text updates.
- Process listing and protected process termination guards.
- UI Automation action execution.
- Computer action journal persistence.
All executed with dry_run=True for desktop safety.
"""

from starlette.testclient import TestClient
import pytest

from nova.agent.runtime import NovaRuntime
from nova.config.settings import NovaSettings
from nova.control.applications.launcher import WindowsApplicationController
from nova.control.automation.uia import WindowsUIAutomationController
from nova.control.clipboard.manager import WindowsClipboardController
from nova.control.input.keyboard import WindowsKeyboardController
from nova.control.input.mouse import WindowsMouseController
from nova.control.journal import ComputerActionJournal
from nova.control.processes.manager import WindowsProcessController
from nova.control.windows.manager import WindowsWindowController
from nova.host.auth import DeviceRegistry, TokenManager
from nova.host.pairing import PairingManager
from nova.host.server import create_host_app


@pytest.fixture
def test_host_env(tmp_path):
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

    journal = ComputerActionJournal(log_path=tmp_path / "journal.jsonl")

    # Safe dry-run controllers
    app = create_host_app(
        settings=settings,
        runtime=runtime,
        device_registry=device_registry,
        token_manager=token_manager,
        pairing_manager=pairing_manager,
        window_controller=WindowsWindowController(dry_run=True),
        application_controller=WindowsApplicationController(dry_run=True),
        mouse_controller=WindowsMouseController(dry_run=True),
        keyboard_controller=WindowsKeyboardController(dry_run=True),
        clipboard_controller=WindowsClipboardController(dry_run=True),
        process_controller=WindowsProcessController(dry_run=True),
        ui_automation_controller=WindowsUIAutomationController(dry_run=True),
        computer_journal=journal,
    )

    client = TestClient(app)

    # Register and authenticate test device
    code, _ = pairing_manager.generate_code()
    pair_resp = client.post(
        "/api/v1/pair",
        json={
            "pairing_code": code,
            "device_id": "iphone-integration-p5",
            "device_name": "Integration iPhone P5",
            "platform": "iOS",
        },
    )
    assert pair_resp.status_code == 200
    token = pair_resp.json()["token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    return client, auth_headers


def test_computer_unauthenticated_fails(test_host_env):
    client, _ = test_host_env
    endpoints = [
        ("GET", "/api/v1/computer/windows"),
        ("POST", "/api/v1/computer/windows/focus"),
        ("GET", "/api/v1/computer/apps"),
        ("POST", "/api/v1/computer/mouse/click"),
        ("POST", "/api/v1/computer/keyboard/type"),
        ("GET", "/api/v1/computer/clipboard"),
        ("GET", "/api/v1/computer/processes"),
        ("GET", "/api/v1/computer/journal"),
    ]
    for method, path in endpoints:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json={})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_computer_windows_api(test_host_env):
    client, headers = test_host_env

    # 1. Enumerate windows
    resp = client.get("/api/v1/computer/windows", headers=headers)
    assert resp.status_code == 200
    windows = resp.json()
    assert isinstance(windows, list)
    assert len(windows) >= 2
    hwnd = windows[0]["hwnd"]

    # 2. Focus window
    resp = client.post("/api/v1/computer/windows/focus", json={"hwnd": hwnd}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 3. Move/resize window
    resp = client.post(
        "/api/v1/computer/windows/bounds",
        json={"hwnd": hwnd, "x": 100, "y": 100, "width": 800, "height": 600},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 4. Close window
    resp = client.post("/api/v1/computer/windows/close", json={"hwnd": hwnd}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_computer_applications_api(test_host_env):
    client, headers = test_host_env

    # 1. List applications
    resp = client.get("/api/v1/computer/apps", headers=headers)
    assert resp.status_code == 200
    apps = resp.json()
    assert isinstance(apps, list)
    assert len(apps) > 0

    # 2. Launch safe application
    resp = client.post(
        "/api/v1/computer/apps/launch",
        json={"app_name_or_path": "notepad.exe"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 3. Block malicious script extension
    resp = client.post(
        "/api/v1/computer/apps/launch",
        json={"app_name_or_path": "malicious.bat"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "REMOTE_EXECUTION_DENIED"


def test_computer_mouse_api(test_host_env):
    client, headers = test_host_env

    # 1. Move
    resp = client.post("/api/v1/computer/mouse/move", json={"x": 300, "y": 200}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 2. Click
    resp = client.post("/api/v1/computer/mouse/click", json={"button": "left", "count": 1}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 3. Scroll
    resp = client.post("/api/v1/computer/mouse/scroll", json={"clicks": 3}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_computer_keyboard_api(test_host_env):
    client, headers = test_host_env

    # 1. Type
    resp = client.post("/api/v1/computer/keyboard/type", json={"text": "Hello NOVA"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 2. Safe press
    resp = client.post("/api/v1/computer/keyboard/press", json={"key": "enter"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 3. Dangerous combination blocked
    resp = client.post(
        "/api/v1/computer/keyboard/press",
        json={"keys": ["ctrl", "alt", "del"]},
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PERMISSION_DENIED"


def test_computer_clipboard_api(test_host_env):
    client, headers = test_host_env

    # 1. Write clipboard
    resp = client.post("/api/v1/computer/clipboard", json={"text": "Remote copied data"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_text"] is True
    assert data["hash_sha256"] is not None

    # 2. Read clipboard metadata & content
    resp = client.get("/api/v1/computer/clipboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_text"] is True
    assert data["hash_sha256"] is not None


def test_computer_processes_api(test_host_env):
    client, headers = test_host_env

    # 1. List processes
    resp = client.get("/api/v1/computer/processes?top=5", headers=headers)
    assert resp.status_code == 200
    procs = resp.json()
    assert isinstance(procs, list)
    assert len(procs) > 0

    # 2. Stop normal dry-run process
    resp = client.post("/api/v1/computer/processes/9999/stop", json={"force": False}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 3. Stop protected PID 4 must be rejected
    resp = client.post("/api/v1/computer/processes/4/stop", json={"force": True}, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PERMISSION_DENIED"


def test_computer_uia_and_journal_api(test_host_env):
    client, headers = test_host_env

    # 1. UIA Action
    resp = client.post(
        "/api/v1/computer/uia/action",
        json={"action": "invoke", "name": "File"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 2. Verify journal reflects actions recorded
    resp = client.get("/api/v1/computer/journal?limit=20", headers=headers)
    assert resp.status_code == 200
    records = resp.json()
    assert isinstance(records, list)
    assert len(records) > 0
