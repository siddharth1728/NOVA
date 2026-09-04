"""Integration tests for Phase 04 host hardening: health, idempotency, and task cancellation."""

import pytest
from starlette.testclient import TestClient

from nova.config.settings import NovaSettings
from nova.agent.runtime import NovaRuntime
from nova.host.auth import DeviceRegistry, TokenManager
from nova.host.pairing import PairingManager
from nova.host.tasks import TaskController
from nova.host.server import create_host_app
from nova.protocol.models import PROTOCOL_VERSION, SERVER_VERSION, TaskStatus


@pytest.fixture
def hardened_client(tmp_path):
    settings = NovaSettings(
        workspace_root=tmp_path / "workspace",
        data_dir=tmp_path / ".nova_hardened",
        host_secret="hardening-test-secret-at-least-32-bytes-long",
    )
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    (settings.workspace_root / "sample.py").write_text("# sample", encoding="utf-8")

    device_registry = DeviceRegistry(settings.devices_file)
    token_manager = TokenManager(secret_key=settings.host_secret.get_secret_value())
    pairing_manager = PairingManager(default_ttl_seconds=300)
    task_controller = TaskController()
    runtime = NovaRuntime(settings=settings)

    app = create_host_app(
        settings=settings,
        runtime=runtime,
        device_registry=device_registry,
        token_manager=token_manager,
        pairing_manager=pairing_manager,
        task_controller=task_controller,
    )

    client = TestClient(app)
    client.pairing_manager = pairing_manager
    client.task_controller = task_controller
    return client


def test_health_endpoint(hardened_client):
    # Unauthenticated health check
    resp = hardened_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"
    assert data["server_version"] == SERVER_VERSION
    assert data["protocol_version"] == PROTOCOL_VERSION
    assert data["uptime_seconds"] >= 0.0
    assert "host_name" in data
    assert "agent_state" in data
    assert data["active_tasks_count"] == 0


def test_request_idempotency_caching(hardened_client):
    # 1. Pair device
    code, _ = hardened_client.pairing_manager.generate_code()
    pair_resp = hardened_client.post(
        "/api/v1/pair",
        json={
            "pairing_code": code,
            "device_id": "iphone-idempotency",
            "device_name": "Idempotency Phone",
            "platform": "iOS",
        },
    )
    token = pair_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    client_req_id = "req-unique-uuid-12345"

    # 2. First submission
    resp1 = hardened_client.post(
        "/api/v1/agent/query",
        json={
            "query": "List files in workspace",
            "request_id": client_req_id,
        },
        headers=headers,
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "COMPLETED"
    task_id1 = data1["task_id"]

    # 3. Duplicate submission with identical request_id must return cached task result
    resp2 = hardened_client.post(
        "/api/v1/agent/query",
        json={
            "query": "List files in workspace",
            "request_id": client_req_id,
        },
        headers=headers,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["task_id"] == task_id1
    assert data2["request_id"] == client_req_id
    assert data2["response_text"] == data1["response_text"]


def test_task_inspection_and_cancellation(hardened_client):
    code, _ = hardened_client.pairing_manager.generate_code()
    pair_resp = hardened_client.post(
        "/api/v1/pair",
        json={
            "pairing_code": code,
            "device_id": "iphone-cancellation",
            "device_name": "Cancel Phone",
            "platform": "iOS",
        },
    )
    token = pair_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Register task directly in controller to test cancellation
    task = hardened_client.task_controller.register_task(
        query="Long running task",
        device_id="iphone-cancellation",
        request_id="req-cancel-test",
    )
    hardened_client.task_controller.transition_task(task.task_id, TaskStatus.EXECUTING)

    # 1. Inspect task status
    inspect_resp = hardened_client.get(f"/api/v1/agent/tasks/{task.task_id}", headers=headers)
    assert inspect_resp.status_code == 200
    assert inspect_resp.json()["status"] == "EXECUTING"

    # 2. Direct cancellation request
    cancel_resp = hardened_client.post(
        f"/api/v1/agent/tasks/{task.task_id}/cancel",
        json={"reason": "Stop operation requested"},
        headers=headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["success"] is True

    # 3. Task state must now be CANCELLED
    inspect_after = hardened_client.get(f"/api/v1/agent/tasks/{task.task_id}", headers=headers)
    assert inspect_after.json()["status"] == "CANCELLED"
