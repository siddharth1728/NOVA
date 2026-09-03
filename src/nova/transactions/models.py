"""Data models for transactional workspace operations and rollback tracking."""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OperationType(str, Enum):
    """Types of state-mutating filesystem operations."""

    CREATE_DIRECTORY = "CREATE_DIRECTORY"
    CREATE_FILE = "CREATE_FILE"
    EDIT_FILE = "EDIT_FILE"
    RENAME_FILE = "RENAME_FILE"
    MOVE_FILE = "MOVE_FILE"
    COPY_FILE = "COPY_FILE"


class TransactionStatus(str, Enum):
    """Lifecycle statuses of a workspace transaction."""

    STARTED = "STARTED"
    RUNNING = "RUNNING"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"


class OperationRecord(BaseModel):
    """Audit and rollback record for a single atomic filesystem mutation."""

    operation_id: str
    op_type: OperationType
    target_path: Path
    secondary_path: Path | None = None  # Original path for rename/move, source for copy
    backup_path: Path | None = None  # Snapshot path in .nova/backups/
    pre_hash: str | None = None  # SHA-256 before modification
    post_hash: str | None = None  # SHA-256 after modification
    pre_size: int | None = None
    post_size: int | None = None
    created_new: bool = False  # True if target did not exist prior to this operation
    rolled_back: bool = False
    timestamp: str = Field(default_factory=_utc_now)


class TransactionRecord(BaseModel):
    """Encompassing transaction tracking an atomic group of workspace operations."""

    transaction_id: str
    description: str = ""
    status: TransactionStatus = TransactionStatus.STARTED
    operations: list[OperationRecord] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utc_now)
    completed_at: str | None = None
    error: str | None = None
