"""NOVA Protocol error definitions and formatting utilities."""

from enum import Enum
from typing import Any


class ProtocolErrorCode(str, Enum):
    """Standardized error codes for NOVA Remote Protocol v1."""

    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    REVOKED_DEVICE = "REVOKED_DEVICE"
    PAIRING_EXPIRED = "PAIRING_EXPIRED"
    INVALID_PAIRING_CODE = "INVALID_PAIRING_CODE"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    REMOTE_EXECUTION_DENIED = "REMOTE_EXECUTION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def format_error_payload(
    code: ProtocolErrorCode | str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Format a standard JSON error payload for REST and WebSocket responses."""
    code_val = code.value if isinstance(code, ProtocolErrorCode) else str(code)
    return {
        "success": False,
        "error": {
            "code": code_val,
            "message": message,
            "details": details or {},
        },
    }
