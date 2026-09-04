"""Integration test for WebSocket real-time event streaming."""

from starlette.testclient import TestClient
import pytest

from nova.agent.runtime import NovaRuntime
from nova.config.settings import NovaSettings
from nova.host.auth import DeviceRegistry, TokenManager
from nova.host.pairing import PairingManager
from nova.host.server import create_host_app


def test_websocket_streaming(tmp_path):
    settings = NovaSettings(
        workspace_root=tmp_path / "ws_ws",
        data_dir=tmp_path / ".nova_ws",
        host_secret="ws-streaming-test-secret-at-least-32-bytes",
    )
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    device_registry = DeviceRegistry(settings.devices_file)
    token_manager = TokenManager(secret_key=settings.host_secret.get_secret_value())
    pairing_manager = PairingManager()
    runtime = NovaRuntime(settings=settings)

    app = create_host_app(
        settings=settings,
        runtime=runtime,
        device_registry=device_registry,
        token_manager=token_manager,
        pairing_manager=pairing_manager,
    )

    client = TestClient(app)

    # 1. Unauthenticated WS connection is rejected
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/v1/events"):
            pass

    # 2. Pair device to obtain valid token
    code, _ = pairing_manager.generate_code()
    pair_resp = client.post(
        "/api/v1/pair",
        json={
            "pairing_code": code,
            "device_id": "iphone-ws",
            "device_name": "iPhone WS",
            "platform": "iOS",
        },
    )
    token = pair_resp.json()["token"]

    # 3. Connect to WebSocket with token query param
    with client.websocket_connect(f"/ws/v1/events?token={token}") as ws:
        # Should receive initial welcome event
        welcome = ws.receive_json()
        assert welcome["event_type"] == "welcome"
        assert welcome["device_id"] == "iphone-ws"

        # Send ping, receive pong
        ws.send_json({"action": "ping"})
        pong = ws.receive_json()
        assert pong["event_type"] == "pong"
