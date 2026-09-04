"""Remote Task Controller managing execution lifecycle, idempotency, and direct cancellation."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from nova.protocol.models import TaskRecord, TaskStatus

logger = logging.getLogger("nova.host.tasks")


class TaskController:
    """Authoritative task coordinator for remote agent requests.

    Enforces idempotency, tracks active lifecycle states, and handles direct task cancellation.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}  # task_id -> TaskRecord
        self._async_handles: dict[str, asyncio.Task[Any]] = {}  # task_id -> asyncio.Task
        self._request_id_map: dict[str, str] = {}  # request_id -> task_id (for idempotency)
        self._lock = asyncio.Lock()

    def get_task(self, task_id: str) -> TaskRecord | None:
        """Look up a task record by ID."""
        return self._tasks.get(task_id)

    def get_task_by_request_id(self, request_id: str) -> TaskRecord | None:
        """Check for existing task associated with a client idempotency request_id."""
        task_id = self._request_id_map.get(request_id)
        if task_id:
            return self._tasks.get(task_id)
        return None

    def active_tasks_count(self) -> int:
        """Count tasks currently in an active (in-flight) state."""
        return sum(
            1 for t in self._tasks.values()
            if t.status in (TaskStatus.QUEUED, TaskStatus.PLANNING, TaskStatus.EXECUTING, TaskStatus.VERIFYING)
        )

    def register_task(self, query: str, device_id: str, request_id: str | None = None) -> TaskRecord:
        """Register a new task in QUEUED state."""
        req_id = request_id or str(uuid.uuid4())
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        record = TaskRecord(
            task_id=task_id,
            request_id=req_id,
            device_id=device_id,
            query=query,
            status=TaskStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )

        self._tasks[task_id] = record
        self._request_id_map[req_id] = task_id
        return record

    def bind_handle(self, task_id: str, handle: asyncio.Task[Any]) -> None:
        """Bind active asyncio execution handle to task for direct cancellation."""
        self._async_handles[task_id] = handle

    def transition_task(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        response_text: str | None = None,
        error: str | None = None,
    ) -> TaskRecord | None:
        """Transition task to a new state and record timestamp."""
        record = self._tasks.get(task_id)
        if not record:
            return None

        # Cannot transition out of terminal states
        if record.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return record

        now = datetime.now(timezone.utc).isoformat()
        updated_data = record.model_dump()
        updated_data["status"] = status
        updated_data["updated_at"] = now
        if response_text is not None:
            updated_data["response_text"] = response_text
        if error is not None:
            updated_data["error"] = error

        updated_record = TaskRecord(**updated_data)
        self._tasks[task_id] = updated_record

        # Cleanup handle if finished
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            self._async_handles.pop(task_id, None)

        return updated_record

    def cancel_task(self, task_id: str, reason: str = "User cancelled from mobile client") -> bool:
        """Directly cancel an active task without LLM interpretation."""
        record = self._tasks.get(task_id)
        if not record:
            return False

        if record.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            logger.info("Task %s is already in terminal state (%s), cannot cancel", task_id, record.status)
            return False

        handle = self._async_handles.pop(task_id, None)
        if handle and not handle.done():
            handle.cancel()
            logger.info("Directly cancelled asyncio handle for task %s (reason: %s)", task_id, reason)

        self.transition_task(task_id, TaskStatus.CANCELLED, error=f"Cancelled: {reason}")
        return True
