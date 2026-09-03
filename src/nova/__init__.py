"""NOVA: Local-First Personal AI Operating Layer.

Built on the Google Antigravity ecosystem.
"""

__version__ = "0.1.0"
__author__ = "NOVA Core Team"

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

__all__ = [
    "__version__",
    "NovaError",
    "ConfigurationError",
    "AgentRuntimeError",
    "ToolExecutionError",
    "PermissionDeniedError",
    "ValidationError",
    "VerificationError",
    "ExternalServiceError",
]
