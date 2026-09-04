"""Unit tests for capability registry."""

from nova.control.capabilities import CapabilityRegistry


def test_capability_registry_matrix():
    reg = CapabilityRegistry()
    matrix = reg.get_matrix()
    assert matrix.version == "1.0.0"
    assert len(matrix.capabilities) >= 5

    names = {c.name: c for c in matrix.capabilities}
    assert "desktop_telemetry" in names
    assert names["desktop_telemetry"].available is True

    assert "desktop_screen_capture" in names
    assert names["desktop_screen_capture"].available is True

    assert "arbitrary_shell_execution" in names
    # Must be unavailable remotely!
    assert names["arbitrary_shell_execution"].available is False
    assert names["arbitrary_shell_execution"].risk_level == "BLOCKED_DANGEROUS"
