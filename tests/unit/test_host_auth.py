"""Unit tests for host authentication and device trust registry."""

from datetime import timedelta
import pytest
from nova.errors import AuthenticationError, DeviceRevokedError
from nova.host.auth import DeviceRegistry, TokenManager
from nova.protocol.models import DeviceInfo, DeviceRole, DeviceStatus


def test_device_registry_crud(tmp_path):
    storage_file = tmp_path / "devices.json"
    registry = DeviceRegistry(storage_file)

    dev = DeviceInfo(device_id="iphone-1", name="Alice iPhone", platform="iOS")
    registry.register_device(dev)

    loaded = registry.get_device("iphone-1")
    assert loaded is not None
    assert loaded.device_id == "iphone-1"
    assert loaded.status == DeviceStatus.ACTIVE

    # Update last seen
    registry.update_last_seen("iphone-1")
    updated = registry.get_device("iphone-1")
    assert updated.last_seen_at is not None

    # Revoke
    assert registry.revoke_device("iphone-1") is True
    revoked = registry.get_device("iphone-1")
    assert revoked.status == DeviceStatus.REVOKED

    # Unknown device revocation
    assert registry.revoke_device("unknown") is False


def test_token_manager_issue_and_verify(tmp_path):
    key_file = tmp_path / "host_secret.key"
    token_mgr = TokenManager(key_file=key_file)
    registry = DeviceRegistry(tmp_path / "devices.json")

    dev = DeviceInfo(device_id="iphone-2", name="Bob iPhone")
    registry.register_device(dev)

    token, exp = token_mgr.issue_token(dev)
    assert token != ""
    assert exp != ""

    # Successful authentication
    authenticated_dev = token_mgr.authenticate_device(token, registry)
    assert authenticated_dev.device_id == "iphone-2"

    # Revocation causes DeviceRevokedError
    registry.revoke_device("iphone-2")
    with pytest.raises(DeviceRevokedError):
        token_mgr.authenticate_device(token, registry)


def test_token_manager_expired_token(tmp_path):
    token_mgr = TokenManager(secret_key="test-secret-key-12345678901234567890")
    registry = DeviceRegistry(tmp_path / "devices.json")

    dev = DeviceInfo(device_id="iphone-3", name="Charlie iPhone")
    registry.register_device(dev)

    # Issue with negative delta (already expired)
    token, _ = token_mgr.issue_token(dev, expires_delta=timedelta(seconds=-10))

    with pytest.raises(AuthenticationError, match="expired"):
        token_mgr.authenticate_device(token, registry)


def test_token_manager_tampered_token(tmp_path):
    token_mgr = TokenManager(secret_key="secret-key-1-at-least-32-bytes-long-for-hmac")
    token_mgr2 = TokenManager(secret_key="secret-key-2-at-least-32-bytes-long-for-hmac")
    registry = DeviceRegistry(tmp_path / "devices.json")

    dev = DeviceInfo(device_id="iphone-4", name="Dave iPhone")
    registry.register_device(dev)

    # Token signed with a different key
    token, _ = token_mgr2.issue_token(dev)

    with pytest.raises(AuthenticationError, match="Invalid"):
        token_mgr.authenticate_device(token, registry)
