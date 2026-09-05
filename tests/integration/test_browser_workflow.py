"""Integration tests for Phase 08 Browser REST API endpoints."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from starlette.testclient import TestClient

from nova.agent.runtime import NovaRuntime
from nova.config.settings import NovaSettings
from nova.control.browsers.models import BrowserTab
from nova.host.auth import DeviceRegistry, TokenManager
from nova.host.pairing import PairingManager
from nova.host.server import create_host_app


@pytest.fixture
def browser_test_env(tmp_path):
    settings = NovaSettings(
        workspace_root=tmp_path / "workspace",
        data_dir=tmp_path / ".nova",
        host_secret="integration-test-secret-at-least-32-bytes-long",
        browser_enabled=True,
    )
    settings.workspace_root.mkdir(parents=True, exist_ok=True)

    device_registry = DeviceRegistry(settings.devices_file)
    token_manager = TokenManager(secret_key=settings.host_secret.get_secret_value())
    pairing_manager = PairingManager(default_ttl_seconds=300)

    runtime = NovaRuntime(settings=settings)

    mock_browser_controller = MagicMock()
    mock_browser_controller.browser = MagicMock()
    mock_browser_controller.list_tabs = AsyncMock(return_value=[])
    mock_browser_controller.new_tab = AsyncMock()

    app = create_host_app(
        settings=settings,
        runtime=runtime,
        device_registry=device_registry,
        token_manager=token_manager,
        pairing_manager=pairing_manager,
        browser_controller=mock_browser_controller,
    )

    client = TestClient(app)

    # Register and authenticate test device via pairing flow
    code, _ = pairing_manager.generate_code()
    pair_resp = client.post(
        "/api/v1/pair",
        json={
            "pairing_code": code,
            "device_id": "test-ios-browser-client",
            "device_name": "Integration Test iPhone",
            "platform": "iOS",
        },
    )
    assert pair_resp.status_code == 200
    token_data = pair_resp.json()

    client.device_registry = device_registry
    client.token_manager = token_manager
    client.device_id = "test-ios-browser-client"
    client.token = token_data["token"]
    client.mock_browser_controller = mock_browser_controller
    return client


def test_browser_unauthenticated_requests(browser_test_env):
    """Unauthenticated requests must fail with 401 UNAUTHENTICATED."""
    # No auth header
    resp = browser_test_env.get("/api/v1/browser/status")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"

    # Malformed auth header
    resp = browser_test_env.get(
        "/api/v1/browser/status",
        headers={"Authorization": "Basic 12345"},
    )
    assert resp.status_code == 401

    # Invalid token signature
    resp = browser_test_env.get(
        "/api/v1/browser/status",
        headers={"Authorization": "Bearer invalid.fake.token"},
    )
    assert resp.status_code == 401


def test_browser_revoked_device(browser_test_env):
    """Revoked device must be blocked with 403 REVOKED_DEVICE."""
    headers = {"Authorization": f"Bearer {browser_test_env.token}"}
    browser_test_env.device_registry.revoke_device(browser_test_env.device_id)

    resp = browser_test_env.get("/api/v1/browser/status", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "REVOKED_DEVICE"


def test_browser_status_endpoint(browser_test_env):
    """Authenticated status check returns subsystem flags."""
    headers = {"Authorization": f"Bearer {browser_test_env.token}"}
    resp = browser_test_env.get("/api/v1/browser/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert "running" in data
    assert "headless" in data
    assert "protocol_version" in data


def test_browser_tabs_endpoints_mocked(browser_test_env):
    """Test listing and creating browser tabs via REST API."""
    headers = {"Authorization": f"Bearer {browser_test_env.token}"}

    mock_tab = BrowserTab(tab_id="tab_test_01", title="Test Page", url="https://example.com", is_active=True)
    browser_test_env.mock_browser_controller.list_tabs.return_value = [mock_tab]
    browser_test_env.mock_browser_controller.new_tab.return_value = mock_tab

    # 1. List tabs
    resp = browser_test_env.get("/api/v1/browser/tabs", headers=headers)
    assert resp.status_code == 200
    tabs = resp.json()
    assert len(tabs) == 1
    assert tabs[0]["tab_id"] == "tab_test_01"
    assert tabs[0]["title"] == "Test Page"

    # 2. Create tab
    resp = browser_test_env.post(
        "/api/v1/browser/tabs",
        headers=headers,
        json={"url": "https://example.com"},
    )
    assert resp.status_code == 200
    new_tab = resp.json()
    assert new_tab["tab_id"] == "tab_test_01"
    browser_test_env.mock_browser_controller.new_tab.assert_awaited_once_with("https://example.com")

    # 3. Focus tab
    browser_test_env.mock_browser_controller.focus_tab = AsyncMock(return_value=True)
    resp = browser_test_env.post("/api/v1/browser/tabs/tab_test_01/focus", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 4. Close tab
    browser_test_env.mock_browser_controller.close_tab = AsyncMock(return_value=True)
    resp = browser_test_env.delete("/api/v1/browser/tabs/tab_test_01", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True
