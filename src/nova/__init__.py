"""NOVA: Local-First Personal AI Operating Layer.

Built on the Google Antigravity ecosystem.
"""

__version__ = "0.1.0"
__author__ = "NOVA Core Team"

from nova.errors import (
    AgentRuntimeError,
    ConfigurationError,
    ConflictError,
    ExternalServiceError,
    NovaError,
    PermissionDeniedError,
    PlanDriftError,
    RollbackFailedError,
    ToolExecutionError,
    ValidationError,
    VerificationError,
)

__all__ = [
    "__version__",
    "NovaError",
    "ConfigurationError",
    "ConflictError",
    "AgentRuntimeError",
    "ToolExecutionError",
    "PermissionDeniedError",
    "PlanDriftError",
    "RollbackFailedError",
    "ValidationError",
    "VerificationError",
    "ExternalServiceError",
]
