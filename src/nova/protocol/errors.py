"""NOVA Protocol error definitions and formatting utilities."""

from enum import Enum
from typing import Any


class ProtocolErrorCode(str, Enum):
    """Standardized error codes for NOVA Remote Protocol v1."""

    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    REVOKED_DEVICE = "REVOKED_DEVICE"
    PAIRING_EXPIRED = "PAIRING_EXPIRED"
    INVALID_PAIRING_CODE = "INVALID_PAIRING_CODE"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    REMOTE_EXECUTION_DENIED = "REMOTE_EXECUTION_DENIED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_CANCELLED = "TASK_CANCELLED"
    TASK_FAILED = "TASK_FAILED"
    DUPLICATE_REQUEST = "DUPLICATE_REQUEST"
    PROTOCOL_VERSION_MISMATCH = "PROTOCOL_VERSION_MISMATCH"
    HOST_UNAVAILABLE = "HOST_UNAVAILABLE"
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def format_error_payload(
    code: ProtocolErrorCode | str,
    message: str,
    details: dict[str, Any] | None = None,
    protocol_version: str = "1.0.0",
) -> dict[str, Any]:
    """Format a standard JSON error payload for REST and WebSocket responses."""
    code_val = code.value if isinstance(code, ProtocolErrorCode) else str(code)
    return {
        "success": False,
        "protocol_version": protocol_version,
        "error": {
            "code": code_val,
            "message": message,
            "details": details or {},
        },
    }
