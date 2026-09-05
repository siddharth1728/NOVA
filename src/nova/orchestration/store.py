"""Durable task persistence and crash recovery management."""

import json
import logging
from pathlib import Path
from typing import Any

from nova.config.settings import get_settings
from nova.orchestration.models import OrchestratedTask
from nova.protocol.models import TaskStatus

logger = logging.getLogger("nova.orchestration.store")


class TaskStore:
    """Persistent storage for OrchestratedTask records with crash recovery."""

    def __init__(self, storage_dir: Path | None = None) -> None:
        if storage_dir is None:
            self.storage_dir = (get_settings().workspace_root / ".nova" / "tasks").resolve()
        else:
            self.storage_dir = storage_dir.resolve()

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, OrchestratedTask] = {}
        self._request_id_index: dict[str, str] = {}
        self._load_existing_tasks()

    def _load_existing_tasks(self) -> None:
        """Load persisted task JSON files from disk into cache."""
        for file in self.storage_dir.glob("task_*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                task = OrchestratedTask.model_validate(data)
                self._cache[task.task_id] = task
                if task.request_id:
                    self._request_id_index[task.request_id] = task.task_id
            except Exception as e:
                logger.warning("Failed to load task file %s: %s", file.name, e)

    def save_task(self, task: OrchestratedTask) -> None:
        """Save task to memory cache and persist to disk atomically."""
        self._cache[task.task_id] = task
        if task.request_id:
            self._request_id_index[task.request_id] = task.task_id

        target_file = self.storage_dir / f"{task.task_id}.json"
        tmp_file = self.storage_dir / f"{task.task_id}.json.tmp"
        try:
            tmp_file.write_text(task.model_dump_json(indent=2), encoding="utf-8")
            tmp_file.replace(target_file)
        except Exception as e:
            logger.error("Failed to persist task %s to disk: %s", task.task_id, e)

    def get_task(self, task_id: str) -> OrchestratedTask | None:
        """Retrieve task by task_id."""
        return self._cache.get(task_id)

    def get_task_by_request_id(self, request_id: str) -> OrchestratedTask | None:
        """Retrieve task by client request_id (idempotency key)."""
        task_id = self._request_id_index.get(request_id)
        if task_id:
            return self.get_task(task_id)
        return None

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 50,
    ) -> list[OrchestratedTask]:
        """List tasks ordered by creation time descending."""
        tasks = list(self._cache.values())
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    def recover_interrupted_tasks(self) -> int:
        """Safely marks any tasks left in EXECUTING/PLANNING as PAUSED with recovery requirement.

        Enforces Section 42 safety invariant: Never blindly replay potentially
        destructive actions after a host crash.
        """
        recovered_count = 0
        active_states = (TaskStatus.EXECUTING, TaskStatus.PLANNING, TaskStatus.VERIFYING)

        for task in list(self._cache.values()):
            if task.status in active_states:
                logger.warning(
                    "Interrupted task [%s] found in state %s during recovery. Safely pausing.",
                    task.task_id,
                    task.status.value,
                )
                task.status = TaskStatus.PAUSED
                task.pause_reason = "Host restarted: Execution paused for environment re-validation"
                self.save_task(task)
                recovered_count += 1

        return recovered_count
