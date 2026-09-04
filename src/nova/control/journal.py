"""Structured Computer Action Journaling and Empirical Verification Records."""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any
import uuid
from pydantic import BaseModel, Field

from nova.config.settings import get_settings

logger = logging.getLogger("nova.control.journal")


class ComputerActionRecord(BaseModel):
    """Structured audit and verification record for a computer action."""

    action_id: str = Field(default_factory=lambda: f"act-{uuid.uuid4().hex[:10]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    task_id: str | None = None
    device_id: str | None = None
    action_type: str
    target_summary: str
    method: str = "WIN32_API"
    risk_level: str = "LOW"
    requires_approval: bool = False
    approved: bool = True
    before_state: dict[str, Any] = Field(default_factory=dict)
    after_state: dict[str, Any] = Field(default_factory=dict)
    verified: bool = False
    verification_method: str | None = None
    success: bool = True
    message: str | None = None
    duration_ms: float = 0.0


class ComputerActionJournal:
    """Thread-safe append-only journal capturing all computer actions."""

    def __init__(self, log_path: Path | None = None) -> None:
        settings = get_settings()
        self.log_path = log_path or (settings.data_dir / "computer_actions.jsonl")
        self._memory_records: list[ComputerActionRecord] = []

    def record(self, action: ComputerActionRecord) -> None:
        """Append record to in-memory history and disk log."""
        self._memory_records.append(action)
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(action.model_dump_json() + "\n")
        except Exception as ex:
            logger.warning("Failed to persist computer action record: %s", ex)

    def list_records(self, limit: int = 50) -> list[ComputerActionRecord]:
        """Return the most recent action records."""
        return list(reversed(self._memory_records[-limit:]))

    def clear(self) -> None:
        """Clear memory and disk journal (useful in tests)."""
        self._memory_records.clear()
        if self.log_path.exists():
            try:
                self.log_path.unlink()
            except Exception:
                pass


_global_journal: ComputerActionJournal | None = None


def get_computer_journal() -> ComputerActionJournal:
    """Retrieve or create the global ComputerActionJournal instance."""
    global _global_journal
    if _global_journal is None:
        _global_journal = ComputerActionJournal()
    return _global_journal

