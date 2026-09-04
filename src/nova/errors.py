"""NOVA typed exception hierarchy.

Provides structured, actionable errors across all subsystem domains.
"""

from typing import Any


class NovaError(Exception):
    """Base exception for all NOVA system errors."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v!r}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class ConfigurationError(NovaError):
    """Raised when configuration is invalid, missing, or contradictory."""


class AgentRuntimeError(NovaError):
    """Raised when agent session lifecycle or Antigravity runtime fails."""


class ToolExecutionError(NovaError):
    """Raised when tool execution encounters an unrecoverable failure."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str,
        tool_args: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {"tool_name": tool_name}
        if tool_args:
            merged["tool_args"] = tool_args
        if details:
            merged.update(details)
        super().__init__(message, details=merged)
        self.tool_name = tool_name
        self.tool_args = tool_args or {}


class PermissionDeniedError(NovaError):
    """Raised when an operation is prohibited by policy or risk boundaries."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str,
        risk_level: str | None = None,
        target_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {"tool_name": tool_name}
        if risk_level:
            merged["risk_level"] = risk_level
        if target_path:
            merged["target_path"] = target_path
        if details:
            merged.update(details)
        super().__init__(message, details=merged)
        self.tool_name = tool_name
        self.risk_level = risk_level
        self.target_path = target_path


class ValidationError(NovaError):
    """Raised when data schemas, inputs, or parameter constraints fail validation."""


class VerificationError(NovaError):
    """Raised when post-action verification determines expected outcomes were not achieved."""

    def __init__(
        self,
        message: str,
        *,
        expected: Any = None,
        observed: Any = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {}
        if expected is not None:
            merged["expected"] = expected
        if observed is not None:
            merged["observed"] = observed
        if details:
            merged.update(details)
        super().__init__(message, details=merged)
        self.expected = expected
        self.observed = observed


class ExternalServiceError(NovaError):
    """Raised when an external API or service connection fails."""


class ConflictError(NovaError):
    """Raised when a concurrency, collision, or stale-state conflict is detected."""

    def __init__(
        self,
        message: str,
        *,
        conflict_type: str,
        target_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {"conflict_type": conflict_type}
        if target_path:
            merged["target_path"] = target_path
        if details:
            merged.update(details)
        super().__init__(message, details=merged)
        self.conflict_type = conflict_type
        self.target_path = target_path


class RollbackFailedError(NovaError):
    """Raised when a transactional rollback encounters an unrecoverable failure.

    This represents a critical system integrity event.
    """

    def __init__(
        self,
        message: str,
        *,
        transaction_id: str,
        failed_operation: str,
        recovery_info: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {
            "transaction_id": transaction_id,
            "failed_operation": failed_operation,
        }
        if recovery_info:
            merged["recovery_info"] = recovery_info
        if details:
            merged.update(details)
        super().__init__(message, details=merged)
        self.transaction_id = transaction_id
        self.failed_operation = failed_operation
        self.recovery_info = recovery_info or {}


class PlanDriftError(NovaError):
    """Raised when an operation attempts to execute outside the bounds of the approved plan."""

    def __init__(
        self,
        message: str,
        *,
        plan_id: str,
        expected_hash: str,
        observed_hash: str | None = None,
        drift_reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {
            "plan_id": plan_id,
            "expected_hash": expected_hash,
        }
        if observed_hash:
            merged["observed_hash"] = observed_hash
        if drift_reason:
            merged["drift_reason"] = drift_reason
        if details:
            merged.update(details)
        super().__init__(message, details=merged)
        self.plan_id = plan_id
        self.expected_hash = expected_hash
        self.observed_hash = observed_hash
        self.drift_reason = drift_reason


class ProtocolError(NovaError):
    """Raised when incoming protocol envelopes or messages are malformed or invalid."""


class AuthenticationError(NovaError):
    """Raised when client device credentials, tokens, or pairing codes fail validation."""


class DeviceRevokedError(AuthenticationError):
    """Raised when a paired device has been explicitly revoked by the host workstation."""


class PairingExpiredError(AuthenticationError):
    """Raised when a pairing code or invitation window has expired."""


class CapabilityUnavailableError(NovaError):
    """Raised when a requested remote capability is unsupported or unavailable on the host."""


class RemoteExecutionDeniedError(PermissionDeniedError):
    """Raised when an operation requested over remote protocol is forbidden by remote policy."""

