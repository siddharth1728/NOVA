"""Operational telemetry and metrics collection for task orchestration."""

from dataclasses import dataclass, field
import threading
import time


@dataclass
class TaskMetricsTracker:
    """Thread-safe telemetry tracker for multi-step task orchestration."""

    tasks_started: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_cancelled: int = 0
    steps_executed: int = 0
    steps_retried: int = 0
    steps_replanned: int = 0
    approval_requests: int = 0
    approval_denials: int = 0
    verification_failures: int = 0
    total_task_duration: float = 0.0
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def record_task_started(self) -> None:
        with self._lock:
            self.tasks_started += 1

    def record_task_completed(self, duration_seconds: float) -> None:
        with self._lock:
            self.tasks_completed += 1
            self.total_task_duration += duration_seconds

    def record_task_failed(self) -> None:
        with self._lock:
            self.tasks_failed += 1

    def record_task_cancelled(self) -> None:
        with self._lock:
            self.tasks_cancelled += 1

    def record_step_executed(self) -> None:
        with self._lock:
            self.steps_executed += 1

    def record_step_retried(self) -> None:
        with self._lock:
            self.steps_retried += 1

    def record_step_replanned(self) -> None:
        with self._lock:
            self.steps_replanned += 1

    def record_approval_request(self) -> None:
        with self._lock:
            self.approval_requests += 1

    def record_approval_denied(self) -> None:
        with self._lock:
            self.approval_denials += 1

    def record_verification_failure(self) -> None:
        with self._lock:
            self.verification_failures += 1

    @property
    def average_task_duration(self) -> float:
        with self._lock:
            if self.tasks_completed == 0:
                return 0.0
            return round(self.total_task_duration / self.tasks_completed, 3)

    def to_dict(self) -> dict[str, float | int]:
        with self._lock:
            return {
                "tasks_started": self.tasks_started,
                "tasks_completed": self.tasks_completed,
                "tasks_failed": self.tasks_failed,
                "tasks_cancelled": self.tasks_cancelled,
                "steps_executed": self.steps_executed,
                "steps_retried": self.steps_retried,
                "steps_replanned": self.steps_replanned,
                "approval_requests": self.approval_requests,
                "approval_denials": self.approval_denials,
                "verification_failures": self.verification_failures,
                "average_task_duration": self.average_task_duration,
            }


_global_metrics = TaskMetricsTracker()


def get_task_metrics() -> TaskMetricsTracker:
    return _global_metrics
