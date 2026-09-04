"""Integration security tests for NOVA remote protocol and negative paths."""

import pytest
from starlette.testclient import TestClient

from nova.agent.runtime import NovaRuntime
from nova.config.settings import NovaSettings
from nova.host.auth import DeviceRegistry, TokenManager
from nova.host.pairing import PairingManager
from nova.host.server import create_host_app


@pytest.fixture
def test_setup(tmp_path):
    settings = NovaSettings(
        workspace_root=tmp_path / "sec_ws",
        data_dir=tmp_path / ".nova_sec",
        host_secret="security-test-secret-at-least-32-bytes-long",
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
    return client, pairing_manager, device_registry, token_manager


def test_remote_shell_execution_strictly_blocked(test_setup):
    client, pairing_manager, _, _ = test_setup

    # Pair a device
    code, _ = pairing_manager.generate_code()
    pair_resp = client.post(
        "/api/v1/pair",
        json={
            "pairing_code": code,
            "device_id": "sec-tester",
            "device_name": "Security Tester",
            "platform": "iOS",
        },
    )
    token = pair_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to request shell execution over remote protocol
    bad_queries = [
        "run_command: powershell -ExecutionPolicy Bypass",
        "Please use powershell to read system files",
        "execute cmd.exe /c dir",
        "rmdir /s /q c:\\",
    ]

    for q in bad_queries:
        resp = client.post(
            "/api/v1/agent/query",
            json={"query": q},
            headers=headers,
        )
        assert resp.status_code == 403, f"Query '{q}' should have been rejected with 403"
        data = resp.json()
        assert data["error"]["code"] == "REMOTE_EXECUTION_DENIED"


def test_invalid_and_expired_pairing_codes(test_setup):
    client, pairing_manager, _, _ = test_setup

    # 1. Non-existent code
    resp = client.post(
        "/api/v1/pair",
        json={
            "pairing_code": "000000",
            "device_id": "phone-fail",
            "device_name": "Phone",
            "platform": "iOS",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "PAIRING_EXPIRED"

    # 2. Malformed code (not 6 digits)
    resp = client.post(
        "/api/v1/pair",
        json={
            "pairing_code": "123",
            "device_id": "phone-fail",
            "device_name": "Phone",
            "platform": "iOS",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "MALFORMED_REQUEST"

    # 3. Expired code
    code, _ = pairing_manager.generate_code(ttl_seconds=-5)
    resp = client.post(
        "/api/v1/pair",
        json={
            "pairing_code": code,
            "device_id": "phone-fail",
            "device_name": "Phone",
            "platform": "iOS",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "PAIRING_EXPIRED"
