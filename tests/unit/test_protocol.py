"""Unit tests for NOVA Remote Protocol models and errors."""

import pytest
from pydantic import ValidationError

from nova.protocol.errors import ProtocolErrorCode, format_error_payload
from nova.protocol.models import (
    DeviceInfo,
    DeviceRole,
    DeviceStatus,
    PairingRequest,
    PairingResponse,
    ScreenCaptureRequest,
    ScreenCaptureResponse,
    SystemMetrics,
    SystemStatus,
    AgentStatus,
    RemoteQueryRequest,
    RemoteQueryResponse,
    CapabilitiesMatrix,
    CapabilityInfo,
)


def test_format_error_payload():
    payload = format_error_payload(
        ProtocolErrorCode.UNAUTHENTICATED,
        "Token invalid",
        {"reason": "expired"},
    )
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNAUTHENTICATED"
    assert payload["error"]["message"] == "Token invalid"
    assert payload["error"]["details"] == {"reason": "expired"}


def test_pairing_request_validation():
    req = PairingRequest(
        pairing_code="123456",
        device_id="iphone-test-1",
        device_name="Test iPhone",
        platform="iOS",
    )
    assert req.pairing_code == "123456"
    assert req.device_id == "iphone-test-1"

    with pytest.raises(ValidationError):
        # Code must be exactly 6 characters
        PairingRequest(
            pairing_code="123",
            device_id="iphone-test-1",
            device_name="Test iPhone",
        )


def test_device_info_defaults():
    dev = DeviceInfo(device_id="dev-123", name="My Phone")
    assert dev.platform == "iOS"
    assert dev.role == DeviceRole.CONTROLLER
    assert dev.status == DeviceStatus.ACTIVE
    assert dev.paired_at is not None
    assert dev.last_seen_at is None


def test_system_status_serialization():
    metrics = SystemMetrics(
        cpu_percent=12.5,
        ram_total_gb=16.0,
        ram_used_gb=8.0,
        ram_percent=50.0,
        disk_total_gb=500.0,
        disk_used_gb=250.0,
        disk_percent=50.0,
        uptime_seconds=3600.0,
        boot_time="2026-09-04T00:00:00Z",
        os_version="Windows 11",
        hostname="WORKSTATION-1",
    )
    agent = AgentStatus(
        state="IDLE",
        active_plan_id=None,
        workspace_root="C:\\KaryaSetu",
        tools_registered=6,
        uptime_seconds=120.0,
    )
    status = SystemStatus(system=metrics, agent=agent)
    data = status.model_dump()
    assert data["system"]["cpu_percent"] == 12.5
    assert data["agent"]["state"] == "IDLE"


def test_screen_capture_models():
    req = ScreenCaptureRequest(quality=90)
    assert req.format == "png"
    assert req.quality == 90

    with pytest.raises(ValidationError):
        ScreenCaptureRequest(quality=150)

    res = ScreenCaptureResponse(
        width=1920,
        height=1080,
        image_base64="aGVsbG8=",
        file_size_bytes=5,
    )
    assert res.width == 1920
    assert res.file_size_bytes == 5


def test_capabilities_matrix():
    cap = CapabilityInfo(
        name="desktop_screen_capture",
        available=True,
        risk_level="READ_ONLY",
        description="Capture desktop screenshot",
    )
    matrix = CapabilitiesMatrix(capabilities=[cap])
    assert len(matrix.capabilities) == 1
    assert matrix.capabilities[0].name == "desktop_screen_capture"
