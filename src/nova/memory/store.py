"""Local-first file-based memory store implementation for NOVA."""

import json
from pathlib import Path
import threading
from typing import Any

from nova.config.settings import get_settings
from nova.memory.interface import MemoryStore
from nova.memory.models import (
    EnvironmentFact,
    ExecutionRecord,
    LearnedWorkflow,
    ProjectContext,
    TaskState,
    UserPreference,
)


class LocalFileMemoryStore(MemoryStore):
    """Stores structured memory domains as local JSON files in the data directory."""

    def __init__(self, memory_dir: Path | None = None) -> None:
        self.memory_dir = (memory_dir or get_settings().memory_dir).resolve()
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _get_domain_path(self, domain: str) -> Path:
        return self.memory_dir / f"{domain}.json"

    def _read_domain(self, domain: str) -> dict[str, Any]:
        path = self._get_domain_path(domain)
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_domain(self, domain: str, data: dict[str, Any]) -> None:
        path = self._get_domain_path(domain)
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(path)

    # Preferences
    def save_preference(self, preference: UserPreference) -> None:
        with self._lock:
            data = self._read_domain("preferences")
            data[preference.key] = preference.model_dump()
            self._write_domain("preferences", data)

    def get_preference(self, key: str) -> UserPreference | None:
        with self._lock:
            data = self._read_domain("preferences")
            raw = data.get(key)
            return UserPreference.model_validate(raw) if raw else None

    def list_preferences(self) -> list[UserPreference]:
        with self._lock:
            data = self._read_domain("preferences")
            return [UserPreference.model_validate(v) for v in data.values()]

    # Facts
    def save_fact(self, fact: EnvironmentFact) -> None:
        with self._lock:
            data = self._read_domain("facts")
            data[fact.key] = fact.model_dump()
            self._write_domain("facts", data)

    def get_fact(self, key: str) -> EnvironmentFact | None:
        with self._lock:
            data = self._read_domain("facts")
            raw = data.get(key)
            return EnvironmentFact.model_validate(raw) if raw else None

    def list_facts(self, category: str | None = None) -> list[EnvironmentFact]:
        with self._lock:
            data = self._read_domain("facts")
            facts = [EnvironmentFact.model_validate(v) for v in data.values()]
            if category:
                return [f for f in facts if f.category == category]
            return facts

    # Tasks
    def save_task_state(self, task: TaskState) -> None:
        with self._lock:
            data = self._read_domain("tasks")
            data[task.task_id] = task.model_dump()
            self._write_domain("tasks", data)

    def get_task_state(self, task_id: str) -> TaskState | None:
        with self._lock:
            data = self._read_domain("tasks")
            raw = data.get(task_id)
            return TaskState.model_validate(raw) if raw else None

    # Executions
    def record_execution(self, record: ExecutionRecord) -> None:
        with self._lock:
            data = self._read_domain("executions")
            records: list[dict[str, Any]] = data.get("history", [])
            records.append(record.model_dump())
            data["history"] = records[-1000:]
            self._write_domain("executions", data)

    def get_recent_executions(self, limit: int = 20) -> list[ExecutionRecord]:
        with self._lock:
            data = self._read_domain("executions")
            raw_list = data.get("history", [])
            selected = raw_list[-limit:]
            return [ExecutionRecord.model_validate(r) for r in reversed(selected)]

    # Workflows
    def save_workflow(self, workflow: LearnedWorkflow) -> None:
        with self._lock:
            data = self._read_domain("workflows")
            data[workflow.workflow_id] = workflow.model_dump()
            self._write_domain("workflows", data)

    def get_workflow(self, workflow_id: str) -> LearnedWorkflow | None:
        with self._lock:
            data = self._read_domain("workflows")
            raw = data.get(workflow_id)
            return LearnedWorkflow.model_validate(raw) if raw else None

    def list_workflows(self) -> list[LearnedWorkflow]:
        with self._lock:
            data = self._read_domain("workflows")
            return [LearnedWorkflow.model_validate(w) for w in data.values()]

    # Project Context
    def save_project_context(self, context: ProjectContext) -> None:
        with self._lock:
            data = self._read_domain("projects")
            data[context.project_name] = context.model_dump()
            self._write_domain("projects", data)

    def get_project_context(self, project_name: str) -> ProjectContext | None:
        with self._lock:
            data = self._read_domain("projects")
            raw = data.get(project_name)
            return ProjectContext.model_validate(raw) if raw else None
