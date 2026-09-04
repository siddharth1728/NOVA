"""Unit tests for Windows control layer (telemetry, screen capture, power)."""

from nova.control.system import SystemMetricsProvider
from nova.control.screen import ScreenCaptureProvider
from nova.control.power import PowerControlProvider
from nova.protocol.models import ScreenCaptureRequest


def test_system_metrics_provider():
    provider = SystemMetricsProvider()
    metrics = provider.get_metrics()
    assert metrics.cpu_percent >= 0.0
    assert metrics.ram_total_gb > 0.0
    assert metrics.ram_used_gb > 0.0
    assert 0.0 <= metrics.ram_percent <= 100.0
    assert metrics.disk_total_gb > 0.0
    assert metrics.uptime_seconds >= 0.0
    assert metrics.hostname != ""
    assert metrics.os_version != ""


def test_screen_capture_provider_default():
    provider = ScreenCaptureProvider()
    resp = provider.capture()
    assert resp.format == "png"
    assert resp.width > 0
    assert resp.height > 0
    assert len(resp.image_base64) > 100
    assert resp.file_size_bytes > 0


def test_screen_capture_provider_resize_and_jpeg():
    provider = ScreenCaptureProvider()
    req = ScreenCaptureRequest(
        format="jpeg",
        max_width=400,
        max_height=300,
        quality=75,
    )
    resp = provider.capture(req)
    assert resp.format == "jpeg"
    assert resp.width <= 400
    assert resp.height <= 300
    assert len(resp.image_base64) > 50


def test_power_control_provider_dry_run():
    provider = PowerControlProvider()
    resp = provider.lock_workstation(dry_run=True)
    assert resp.action == "LOCK_WORKSTATION"
    assert resp.success is True
    assert "simulated" in resp.message.lower()
