"""Unit tests for observability and audit trail subsystem."""

from pathlib import Path

from nova.observability.audit import AuditTrail
from nova.observability.events import AuditRecord, EventType, NovaEvent
from nova.observability.logging import redact_sensitive_data


def test_secret_redaction_patterns() -> None:
    # 1. API key in string
    raw_str = "Connecting with key AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6 to service"
    redacted = redact_sensitive_data(raw_str)
    assert "AIzaSy" not in redacted
    assert "[REDACTED]" in redacted

    # 2. Bearer token in string
    bearer_str = "Authorization: Bearer secret_access_token_value_abc123"
    redacted_bearer = redact_sensitive_data(bearer_str)
    assert "secret_access_token" not in redacted_bearer
    assert "[REDACTED]" in redacted_bearer

    # 3. Sensitive dictionary keys
    sensitive_dict = {
        "user": "siddu",
        "api_key": "raw_secret_value",
        "password": "my_password",
        "nested": {
            "token": "nested_token",
            "safe_field": "visible",
        },
    }
    clean = redact_sensitive_data(sensitive_dict)
    assert clean["user"] == "siddu"
    assert clean["api_key"] == "[REDACTED]"
    assert clean["password"] == "[REDACTED]"
    assert clean["nested"]["token"] == "[REDACTED]"
    assert clean["nested"]["safe_field"] == "visible"


def test_audit_trail_logging_and_retrieval(audit_trail: AuditTrail) -> None:
    # Log a harmless tool execution
    record1 = audit_trail.log_tool_invocation(
        tool="list_directory",
        risk_level="READ_ONLY",
        approval_state="APPROVED",
        inputs={"path": "src/"},
        results={"count": 5},
        success=True,
        duration_ms=12.5,
    )

    # Log an operation with sensitive data
    record2 = audit_trail.log_tool_invocation(
        tool="test_tool",
        risk_level="LOW",
        approval_state="APPROVED",
        inputs={"api_key": "AIzaSyHiddenSecretKey12345678901234"},
        results={"status": "ok"},
        success=True,
        duration_ms=5.0,
    )

    recent = audit_trail.read_recent_records(limit=10)
    assert len(recent) == 2
    assert recent[0].tool == "test_tool"
    assert recent[1].tool == "list_directory"

    # Verify secret is redacted on disk
    raw_content = audit_trail.log_file.read_text(encoding="utf-8")
    assert "AIzaSyHiddenSecretKey" not in raw_content
    assert "[REDACTED]" in raw_content
