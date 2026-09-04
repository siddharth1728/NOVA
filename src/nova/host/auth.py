"""Device authentication, token issuing, and trust registry persistence."""

from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import secrets
from typing import Any
import jwt

from nova.errors import AuthenticationError, DeviceRevokedError
from nova.protocol.models import DeviceInfo, DeviceRole, DeviceStatus

logger = logging.getLogger("nova.host.auth")


class DeviceRegistry:
    """Persistent storage for authorized client devices."""

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._save_data({})

    def _load_data(self) -> dict[str, dict[str, Any]]:
        try:
            if not self.storage_path.exists():
                return {}
            content = self.storage_path.read_text(encoding="utf-8")
            if not content.strip():
                return {}
            return json.loads(content)
        except Exception as ex:
            logger.error("Failed to read device registry from %s: %s", self.storage_path, ex)
            return {}

    def _save_data(self, data: dict[str, dict[str, Any]]) -> None:
        temp_path = self.storage_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_path.replace(self.storage_path)

    def register_device(self, device: DeviceInfo) -> None:
        """Register or update an authorized device."""
        data = self._load_data()
        data[device.device_id] = device.model_dump()
        self._save_data(data)
        logger.info("Device registered/updated: %s (%s)", device.device_id, device.name)

    def get_device(self, device_id: str) -> DeviceInfo | None:
        """Retrieve device record by device ID."""
        data = self._load_data()
        raw = data.get(device_id)
        if not raw:
            return None
        return DeviceInfo(**raw)

    def list_devices(self) -> list[DeviceInfo]:
        """Return all recorded devices in the registry."""
        data = self._load_data()
        return [DeviceInfo(**item) for item in data.values()]

    def revoke_device(self, device_id: str) -> bool:
        """Mark a device as REVOKED, immediately denying future access."""
        data = self._load_data()
        if device_id not in data:
            return False
        data[device_id]["status"] = DeviceStatus.REVOKED.value
        self._save_data(data)
        logger.warning("Device revoked: %s", device_id)
        return True

    def update_last_seen(self, device_id: str) -> None:
        """Update the last_seen_at timestamp for a device."""
        data = self._load_data()
        if device_id in data:
            data[device_id]["last_seen_at"] = datetime.now(timezone.utc).isoformat()
            self._save_data(data)


class TokenManager:
    """Issues and validates signed JSON Web Tokens for client devices."""

    def __init__(self, secret_key: str | None = None, key_file: Path | None = None) -> None:
        if secret_key:
            self.secret = secret_key
        elif key_file and key_file.exists():
            self.secret = key_file.read_text(encoding="utf-8").strip()
        else:
            self.secret = secrets.token_urlsafe(48)
            if key_file:
                try:
                    key_file.parent.mkdir(parents=True, exist_ok=True)
                    key_file.write_text(self.secret, encoding="utf-8")
                except Exception as ex:
                    logger.warning("Could not persist host secret key: %s", ex)

        self.algorithm = "HS256"

    def issue_token(
        self,
        device: DeviceInfo,
        *,
        expires_delta: timedelta | None = None,
    ) -> tuple[str, str]:
        """Issue a signed JWT bearer token for the device.

        Returns:
            Tuple of (token_string, expires_at_iso_string)
        """
        now = datetime.now(timezone.utc)
        delta = expires_delta or timedelta(days=30)
        exp = now + delta

        payload = {
            "iss": "nova-windows-host",
            "aud": "nova-ios-client",
            "sub": device.device_id,
            "name": device.name,
            "role": device.role.value,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }

        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token, exp.isoformat()

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify token signature, expiration, issuer, and audience.

        Raises:
            AuthenticationError: If token is expired, tampered, or invalid.
        """
        try:
            claims = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                audience="nova-ios-client",
                issuer="nova-windows-host",
                options={"require": ["exp", "iat", "sub"]},
            )
            return claims
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Session token has expired. Please re-pair device.")
        except jwt.InvalidAudienceError:
            raise AuthenticationError("Invalid token audience.")
        except jwt.InvalidIssuerError:
            raise AuthenticationError("Invalid token issuer.")
        except Exception as ex:
            raise AuthenticationError(f"Invalid authentication token: {ex}")

    def authenticate_device(self, token: str, registry: DeviceRegistry) -> DeviceInfo:
        """Validate token and ensure device is active in the registry.

        Raises:
            AuthenticationError: If unauthenticated.
            DeviceRevokedError: If explicitly revoked.
        """
        claims = self.verify_token(token)
        device_id = claims.get("sub")
        if not device_id:
            raise AuthenticationError("Token missing device identity ('sub').")

        device = registry.get_device(device_id)
        if not device:
            raise AuthenticationError(f"Device '{device_id}' not found in host trust registry.")

        if device.status == DeviceStatus.REVOKED:
            raise DeviceRevokedError(f"Device '{device_id}' has been revoked by workstation host.")

        if device.status != DeviceStatus.ACTIVE:
            raise AuthenticationError(f"Device '{device_id}' is not in ACTIVE state ({device.status}).")

        registry.update_last_seen(device_id)
        return device
