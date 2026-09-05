"""Unit tests for NOVA configuration subsystem."""

from pathlib import Path
import pytest
from pydantic import SecretStr

from nova.config.settings import Environment, NovaSettings, SecurityMode
from nova.errors import ConfigurationError


def test_default_settings(temp_workspace: Path, temp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NOVA_SECURITY_MODE", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings = NovaSettings(
        _env_file=None,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
    )
    assert settings.environment == Environment.DEVELOPMENT
    assert settings.security_mode == SecurityMode.STRICT
    assert settings.model_name == "gemini-3.8-flash"
    assert settings.thinking_level == "high"
    assert settings.workspace_root == temp_workspace
    assert settings.data_dir == temp_data_dir
    assert settings.audit_dir == temp_data_dir / "audit"
    assert settings.memory_dir == temp_data_dir / "memory"


def test_secret_masking(temp_workspace: Path, temp_data_dir: Path) -> None:
    secret_key = "AIzaSyTestSecretKey1234567890"
    settings = NovaSettings(
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
        gemini_api_key=SecretStr(secret_key),
    )
    # Raw value access
    assert settings.get_api_key_value() == secret_key

    # Safe dump masks secret
    dumped = settings.safe_dump()
    assert dumped["gemini_api_key"] == "********"
    assert secret_key not in str(dumped)


def test_validate_for_live_inference_failure(temp_workspace: Path, temp_data_dir: Path) -> None:
    settings = NovaSettings(
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
        gemini_api_key=None,
    )
    # Ensure ambient env doesn't give a false positive
    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("GEMINI_API_KEY", raising=False)
        mp.delenv("GOOGLE_API_KEY", raising=False)
        with pytest.raises(ConfigurationError) as exc_info:
            settings.validate_for_live_inference()
        assert "Gemini API key is not configured" in str(exc_info.value)


def test_validate_for_live_inference_success(temp_workspace: Path, temp_data_dir: Path) -> None:
    settings = NovaSettings(
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
        gemini_api_key=SecretStr("valid_key_123"),
    )
    key = settings.validate_for_live_inference()
    assert key == "valid_key_123"
