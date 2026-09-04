"""Host pairing manager for PIN-code device onboarding."""

from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import secrets
import socket
from typing import NamedTuple

from nova.errors import PairingExpiredError
from nova.host.auth import DeviceRegistry, TokenManager
from nova.protocol.models import DeviceInfo, DeviceRole, DeviceStatus, PairingRequest, PairingResponse

logger = logging.getLogger("nova.host.pairing")


class ActiveCode(NamedTuple):
    code: str
    expires_at: datetime


class PairingManager:
    """Manages ephemeral 6-digit pairing codes for secure device linking."""

    def __init__(self, default_ttl_seconds: int = 300, storage_path: Path | None = None) -> None:
        self.default_ttl = default_ttl_seconds
        self.storage_path = storage_path
        self._codes: dict[str, datetime] = {}
        if self.storage_path and self.storage_path.exists():
            self._load_from_storage()

    def _load_from_storage(self) -> None:
        if not self.storage_path or not self.storage_path.exists():
            return
        try:
            import json
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            for code, exp_str in data.items():
                self._codes[code] = datetime.fromisoformat(exp_str)
        except Exception as ex:
            logger.warning("Failed to load pairing codes from %s: %s", self.storage_path, ex)

    def _save_to_storage(self) -> None:
        if not self.storage_path:
            return
        try:
            import json
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {c: exp.isoformat() for c, exp in self._codes.items()}
            self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as ex:
            logger.warning("Failed to save pairing codes to %s: %s", self.storage_path, ex)

    def _purge_expired(self) -> None:
        if self.storage_path:
            self._load_from_storage()
        now = datetime.now(timezone.utc)
        expired = [c for c, exp in self._codes.items() if exp <= now]
        if expired:
            for c in expired:
                del self._codes[c]
            if self.storage_path:
                self._save_to_storage()

    def generate_code(self, ttl_seconds: int | None = None) -> tuple[str, datetime]:
        """Generate a random 6-digit PIN code with an expiration window."""
        self._purge_expired()
        ttl = ttl_seconds or self.default_ttl
        # 6-digit zero-padded number
        code = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        self._codes[code] = expires_at
        if self.storage_path:
            self._save_to_storage()
        logger.info("Generated new host pairing code: %s (expires in %ds)", code, ttl)
        return code, expires_at

    def get_latest_active_code(self) -> tuple[str, datetime] | None:
        """Return the most recently generated active pairing code if still valid."""
        self._purge_expired()
        if not self._codes:
            return None
        # Return code with furthest expiry
        latest = max(self._codes.items(), key=lambda item: item[1])
        return latest[0], latest[1]

    def verify_and_pair(
        self,
        request: PairingRequest,
        registry: DeviceRegistry,
        token_manager: TokenManager,
    ) -> PairingResponse:
        """Validate pairing code, register device in trust store, and issue session token."""
        self._purge_expired()

        code = request.pairing_code.strip()
        if code not in self._codes:
            logger.warning("Pairing attempt failed: Invalid or expired code '%s'", code)
            raise PairingExpiredError("Invalid or expired pairing code. Please generate a new code on host.")

        # Consume code so it cannot be re-used
        del self._codes[code]
        if self.storage_path:
            self._save_to_storage()

        # Register or update device
        device = DeviceInfo(
            device_id=request.device_id,
            name=request.device_name,
            platform=request.platform,
            role=DeviceRole.CONTROLLER,
            status=DeviceStatus.ACTIVE,
            paired_at=datetime.now(timezone.utc).isoformat(),
            last_seen_at=datetime.now(timezone.utc).isoformat(),
        )
        registry.register_device(device)

        # Issue bearer token
        token, expires_at = token_manager.issue_token(device)

        logger.info(
            "Device successfully paired: %s (%s) on %s",
            device.name,
            device.device_id,
            device.platform,
        )

        return PairingResponse(
            token=token,
            device_id=device.device_id,
            host_name=socket.gethostname(),
            server_version="0.1.0",
            expires_at=expires_at,
        )
