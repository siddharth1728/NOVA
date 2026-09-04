"""Typed configuration system for NOVA."""

from enum import Enum
import os
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from nova.errors import ConfigurationError


class Environment(str, Enum):
    """Runtime environment modes."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class SecurityMode(str, Enum):
    """NOVA operational security profiles."""

    STRICT = "strict"  # Read-only operations allowed, all write/execution tools denied
    STANDARD = "standard"  # Read-only allowed; low/medium risk requires explicit approval
    PERMISSIVE = "permissive"  # Experimental: allows non-destructive modifications


class NovaSettings(BaseSettings):
    """Central configuration for NOVA operating layer."""

    model_config = SettingsConfigDict(
        env_prefix="NOVA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Active runtime environment mode",
    )

    # Model & Reasoning
    model_name: str = Field(
        default="gemini-3.8-flash",
        description="Target model identifier",
    )
    thinking_level: str = Field(
        default="high",
        description="Gemini extended reasoning level (minimal, low, medium, high, extra_high)",
    )

    # API Credentials (can also be sourced from ambient GEMINI_API_KEY)
    gemini_api_key: SecretStr | None = Field(
        default=None,
        description="Google Gemini API key for model inference",
    )

    # File System & Boundaries
    workspace_root: Path = Field(
        default_factory=Path.cwd,
        description="Confinement directory root for all agent operations",
    )
    data_dir: Path = Field(
        default_factory=lambda: Path.cwd() / ".nova",
        description="Local-first data directory for state, audit, and memory",
    )

    # Security & Policy
    security_mode: SecurityMode = Field(
        default=SecurityMode.STRICT,
        description="Enforced security profile",
    )
    require_approval_for_medium_risk: bool = Field(
        default=True,
        description="Whether medium risk actions trigger human approval",
    )

    # Logging & Observability
    log_level: str = Field(
        default="INFO",
        description="Logging level threshold",
    )

    # Host & Remote Control (Phase 03)
    host_bind: str = Field(
        default="127.0.0.1",
        description="Network interface for the Windows Host service to bind to",
    )
    host_port: int = Field(
        default=8000,
        description="TCP port for the Windows Host service",
    )
    host_secret: SecretStr | None = Field(
        default=None,
        description="Secret key for JWT device authentication (auto-generated if None)",
    )
    pairing_code_ttl_seconds: int = Field(
        default=300,
        description="Time-to-live for ephemeral 6-digit pairing codes in seconds",
    )
    device_token_expire_days: int = Field(
        default=30,
        description="Validity period for device session tokens in days",
    )

    @field_validator("workspace_root", mode="after")
    @classmethod
    def _resolve_workspace_root(cls, v: Path) -> Path:
        resolved = v.resolve()
        return resolved

    @field_validator("data_dir", mode="after")
    @classmethod
    def _resolve_data_dir(cls, v: Path) -> Path:
        resolved = v.resolve()
        return resolved

    @property
    def audit_dir(self) -> Path:
        """Directory path for append-only audit trails."""
        return self.data_dir / "audit"

    @property
    def memory_dir(self) -> Path:
        """Directory path for local-first memory storage."""
        return self.data_dir / "memory"

    @property
    def devices_file(self) -> Path:
        """File path for persistent device trust registry."""
        return self.data_dir / "devices.json"

    def get_api_key_value(self) -> str | None:
        """Retrieve raw API key string safely, checking ambient env if unset."""
        if self.gemini_api_key:
            return self.gemini_api_key.get_secret_value()
        # Fall back to standard ambient GEMINI_API_KEY or GOOGLE_API_KEY
        return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    def validate_for_live_inference(self) -> str:
        """Ensures API key is available before starting a live agent session.

        Raises:
            ConfigurationError: If no API key is present with instructions.
        """
        key = self.get_api_key_value()
        if not key or not key.strip():
            raise ConfigurationError(
                "Gemini API key is not configured. Live model communication requires a valid key.\n"
                "Please set GEMINI_API_KEY in your .env file or environment:\n"
                "  $env:GEMINI_API_KEY = 'your_key_here'\n"
                "Obtain a key at https://aistudio.google.com/"
            )
        return key

    def safe_dump(self) -> dict[str, Any]:
        """Returns a sanitized dictionary of settings with secrets masked."""
        data = self.model_dump()
        if data.get("gemini_api_key"):
            data["gemini_api_key"] = "********"
        else:
            data["gemini_api_key"] = None
        data["workspace_root"] = str(self.workspace_root)
        data["data_dir"] = str(self.data_dir)
        return data


# Global singleton cache
_settings_instance: NovaSettings | None = None


def get_settings(*, reload: bool = False, **overrides: Any) -> NovaSettings:
    """Provides application-wide typed settings instance."""
    global _settings_instance
    if _settings_instance is None or reload or overrides:
        _settings_instance = NovaSettings(**overrides)
    return _settings_instance
