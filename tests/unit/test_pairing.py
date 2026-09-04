"""Unit tests for host pairing manager."""

import pytest
from nova.errors import PairingExpiredError
from nova.host.auth import DeviceRegistry, TokenManager
from nova.host.pairing import PairingManager
from nova.protocol.models import DeviceStatus, PairingRequest


def test_pairing_code_generation():
    pm = PairingManager(default_ttl_seconds=300)
    code, exp = pm.generate_code()
    assert len(code) == 6
    assert code.isdigit()
    assert exp is not None

    latest = pm.get_latest_active_code()
    assert latest is not None
    assert latest[0] == code


def test_pairing_flow_success_and_consumption(tmp_path):
    pm = PairingManager(default_ttl_seconds=300)
    registry = DeviceRegistry(tmp_path / "devices.json")
    token_mgr = TokenManager(secret_key="pairing-test-key-at-least-32-bytes-long")

    code, _ = pm.generate_code()

    req = PairingRequest(
        pairing_code=code,
        device_id="dev-phone-1",
        device_name="My iPhone",
        platform="iOS",
    )

    resp = pm.verify_and_pair(req, registry, token_mgr)
    assert resp.device_id == "dev-phone-1"
    assert resp.token != ""

    # Device is stored in registry as ACTIVE
    dev = registry.get_device("dev-phone-1")
    assert dev is not None
    assert dev.status == DeviceStatus.ACTIVE

    # Single-use: using the same code again must fail!
    with pytest.raises(PairingExpiredError):
        pm.verify_and_pair(req, registry, token_mgr)


def test_pairing_code_expired(tmp_path):
    pm = PairingManager(default_ttl_seconds=-10)  # already expired
    registry = DeviceRegistry(tmp_path / "devices.json")
    token_mgr = TokenManager(secret_key="pairing-test-key")

    code, _ = pm.generate_code(ttl_seconds=-10)

    req = PairingRequest(
        pairing_code=code,
        device_id="dev-phone-2",
        device_name="My iPhone 2",
        platform="iOS",
    )

    with pytest.raises(PairingExpiredError):
        pm.verify_and_pair(req, registry, token_mgr)
