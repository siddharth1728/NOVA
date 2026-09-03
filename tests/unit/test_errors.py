"""Unit tests for NOVA typed error hierarchy."""

from nova.errors import (
    AgentRuntimeError,
    ConfigurationError,
    ExternalServiceError,
    NovaError,
    PermissionDeniedError,
    ToolExecutionError,
    ValidationError,
    VerificationError,
)


def test_error_hierarchy() -> None:
    assert issubclass(ConfigurationError, NovaError)
    assert issubclass(AgentRuntimeError, NovaError)
    assert issubclass(ToolExecutionError, NovaError)
    assert issubclass(PermissionDeniedError, NovaError)
    assert issubclass(ValidationError, NovaError)
    assert issubclass(VerificationError, NovaError)
    assert issubclass(ExternalServiceError, NovaError)


def test_error_details_formatting() -> None:
    err = NovaError("Something broke", details={"key": "val", "count": 42})
    assert "Something broke" in str(err)
    assert "key='val'" in str(err)
    assert "count=42" in str(err)
    assert err.details == {"key": "val", "count": 42}


def test_tool_execution_error_attributes() -> None:
    err = ToolExecutionError("Failed to run", tool_name="search_dir", tool_args={"query": "foo"})
    assert err.tool_name == "search_dir"
    assert err.tool_args == {"query": "foo"}
    assert "search_dir" in str(err)


def test_permission_denied_error_attributes() -> None:
    err = PermissionDeniedError(
        "Access denied",
        tool_name="run_command",
        risk_level="CRITICAL",
        target_path="C:/windows/system32",
    )
    assert err.tool_name == "run_command"
    assert err.risk_level == "CRITICAL"
    assert err.target_path == "C:/windows/system32"


def test_verification_error_attributes() -> None:
    err = VerificationError(
        "Post-condition failed",
        expected="file created",
        observed="file not found",
    )
    assert err.expected == "file created"
    assert err.observed == "file not found"
