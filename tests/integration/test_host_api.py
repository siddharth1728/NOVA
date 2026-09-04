"""Integration tests for NOVA Windows Host REST API and vertical slices."""

from starlette.testclient import TestClient
import pytest

from nova.config.settings import NovaSettings
from nova.agent.runtime import NovaRuntime
from nova.host.auth import DeviceRegistry, TokenManager
from nova.host.pairing import PairingManager
from nova.host.server import create_host_app


@pytest.fixture
def host_client(tmp_path):
    settings = NovaSettings(
        workspace_root=tmp_path / "workspace",
        data_dir=tmp_path / ".nova",
        host_secret="integration-test-secret-at-least-32-bytes-long",
    )
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    # Create sample file for workspace inspection
    (settings.workspace_root / "hello.txt").write_text("Hello NOVA", encoding="utf-8")

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
    # Store references for test access
    client.pairing_manager = pairing_manager
    client.device_registry = device_registry
    return client


def test_unauthenticated_requests_fail(host_client):
    # Missing token
    resp = host_client.get("/api/v1/status")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"

    # Invalid token
    resp = host_client.get("/api/v1/status", headers={"Authorization": "Bearer invalid-token"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_pairing_and_authenticated_status_flow(host_client):
    # 1. Host generates 6-digit pairing code
    code, _ = host_client.pairing_manager.generate_code()

    # 2. iPhone submits pairing request
    pair_resp = host_client.post(
        "/api/v1/pair",
        json={
            "pairing_code": code,
            "device_id": "iphone-integration-1",
            "device_name": "Integration iPhone",
            "platform": "iOS",
        },
    )
    assert pair_resp.status_code == 200
    data = pair_resp.json()
    token = data["token"]
    assert token != ""
    assert data["device_id"] == "iphone-integration-1"

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Request real system status telemetry (Vertical Slice 1)
    status_resp = host_client.get("/api/v1/status", headers=headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "system" in status_data
    assert "agent" in status_data
    assert status_data["system"]["cpu_percent"] >= 0.0
    assert status_data["system"]["ram_percent"] >= 0.0
    assert status_data["system"]["disk_percent"] >= 0.0
    assert status_data["agent"]["state"] in ("INITIALIZING", "READY", "IDLE")

    # 4. Request screen capture (Vertical Slice 2)
    screen_resp = host_client.post(
        "/api/v1/screen/capture",
        json={"format": "png", "max_width": 640},
        headers=headers,
    )
    assert screen_resp.status_code == 200
    screen_data = screen_resp.json()
    assert screen_data["format"] == "png"
    assert screen_data["width"] <= 640
    assert len(screen_data["image_base64"]) > 100
    assert screen_data["file_size_bytes"] > 0

    # 5. Discover capabilities matrix
    cap_resp = host_client.get("/api/v1/capabilities", headers=headers)
    assert cap_resp.status_code == 200
    caps = cap_resp.json()["capabilities"]
    assert any(c["name"] == "desktop_telemetry" for c in caps)
    # Ensure arbitrary shell execution is blocked!
    shell_cap = next(c for c in caps if c["name"] == "arbitrary_shell_execution")
    assert shell_cap["available"] is False

    # 6. Dispatch remote agent query (Vertical Slice 3)
    query_resp = host_client.post(
        "/api/v1/agent/query",
        json={"query": "List files in workspace and verify project layout"},
        headers=headers,
    )
    assert query_resp.status_code == 200
    query_data = query_resp.json()
    assert query_data["status"] == "COMPLETED"
    assert query_data["verification_passed"] is True
    assert "OBSERVED" in query_data["response_text"]
    assert "hello.txt" in query_data["response_text"]

    # 7. Emergency Lock (dry run)
    lock_resp = host_client.post(
        "/api/v1/emergency/lock?dry_run=true",
        headers=headers,
        json={"reason": "Testing emergency lock"},
    )
    assert lock_resp.status_code == 200
    assert lock_resp.json()["success"] is True


def test_device_revocation_denies_subsequent_calls(host_client):
    code, _ = host_client.pairing_manager.generate_code()
    pair_resp = host_client.post(
        "/api/v1/pair",
        json={
            "pairing_code": code,
            "device_id": "iphone-to-revoke",
            "device_name": "Temporary iPhone",
            "platform": "iOS",
        },
    )
    token = pair_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify device works
    assert host_client.get("/api/v1/status", headers=headers).status_code == 200

    # Revoke device
    revoke_resp = host_client.post(
        "/api/v1/devices/iphone-to-revoke/revoke",
        headers=headers,
    )
    assert revoke_resp.status_code == 200

    # Subsequent call with same token must fail with 403 REVOKED_DEVICE
    status_resp = host_client.get("/api/v1/status", headers=headers)
    assert status_resp.status_code == 403
    assert status_resp.json()["error"]["code"] == "REVOKED_DEVICE"
