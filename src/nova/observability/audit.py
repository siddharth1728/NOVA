"""Append-only audit trail logging with secret scrubbing."""

import json
from pathlib import Path
import threading
from typing import Any

from nova.config.settings import get_settings
from nova.observability.events import AuditRecord
from nova.observability.logging import redact_sensitive_data


class AuditTrail:
    """Thread-safe append-only audit trail logger."""

    def __init__(self, audit_dir: Path | None = None) -> None:
        self.audit_dir = (audit_dir or get_settings().audit_dir).resolve()
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.audit_dir / "audit.jsonl"
        self._lock = threading.Lock()

    def record(self, entry: AuditRecord) -> None:
        """Appends a sanitized AuditRecord to the audit log."""
        # Sanitize summary and payload representation
        sanitized_input = redact_sensitive_data(entry.input_summary)
        sanitized_result = redact_sensitive_data(entry.result_summary)

        safe_record = entry.model_copy(
            update={
                "input_summary": str(sanitized_input),
                "result_summary": str(sanitized_result),
            }
        )

        with self._lock:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(safe_record.model_dump_json() + "\n")

    def log_tool_invocation(
        self,
        *,
        tool: str,
        risk_level: str,
        approval_state: str,
        inputs: Any,
        results: Any,
        success: bool = True,
        duration_ms: float = 0.0,
        error: str | None = None,
        session_id: str = "standalone",
        task_id: str = "standalone",
    ) -> AuditRecord:
        """Convenience method to construct and record an audit entry for a tool call."""
        record = AuditRecord(
            session_id=session_id,
            task_id=task_id,
            tool=tool,
            risk_level=risk_level,
            approval_state=approval_state,
            input_summary=str(inputs),
            result_summary=str(results),
            success=success,
            duration_ms=duration_ms,
            error=error,
        )
        self.record(record)
        return record

    def read_recent_records(self, limit: int = 50) -> list[AuditRecord]:
        """Reads the most recent audit records from disk."""
        if not self.log_file.exists():
            return []

        records: list[AuditRecord] = []
        with self._lock:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines[-limit:]):
                    stripped = line.strip()
                    if stripped:
                        try:
                            records.append(AuditRecord.model_validate_json(stripped))
                        except Exception:
                            continue
        return records


# Shared singleton instance
_default_audit_trail: AuditTrail | None = None


def get_audit_trail() -> AuditTrail:
    """Provides application-wide AuditTrail singleton tracking active configuration."""
    global _default_audit_trail
    current_dir = get_settings().audit_dir.resolve()
    if _default_audit_trail is None or _default_audit_trail.audit_dir != current_dir:
        _default_audit_trail = AuditTrail(audit_dir=current_dir)
    return _default_audit_trail
