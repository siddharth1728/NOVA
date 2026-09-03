"""Abstract interface for NOVA memory store backends."""

from abc import ABC, abstractmethod

from nova.memory.models import (
    EnvironmentFact,
    ExecutionRecord,
    LearnedWorkflow,
    ProjectContext,
    TaskState,
    UserPreference,
)


class MemoryStore(ABC):
    """Abstract interface defining storage and retrieval across memory domains."""

    # User Preferences
    @abstractmethod
    def save_preference(self, preference: UserPreference) -> None:
        """Saves or updates a user preference."""

    @abstractmethod
    def get_preference(self, key: str) -> UserPreference | None:
        """Retrieves a user preference by key."""

    @abstractmethod
    def list_preferences(self) -> list[UserPreference]:
        """Lists all stored preferences."""

    # Environment Facts
    @abstractmethod
    def save_fact(self, fact: EnvironmentFact) -> None:
        """Saves or updates an environment fact."""

    @abstractmethod
    def get_fact(self, key: str) -> EnvironmentFact | None:
        """Retrieves an environment fact by key."""

    @abstractmethod
    def list_facts(self, category: str | None = None) -> list[EnvironmentFact]:
        """Lists all environment facts, optionally filtered by category."""

    # Task States
    @abstractmethod
    def save_task_state(self, task: TaskState) -> None:
        """Persists state for an active or completed task."""

    @abstractmethod
    def get_task_state(self, task_id: str) -> TaskState | None:
        """Retrieves task state by task identifier."""

    # Execution Records
    @abstractmethod
    def record_execution(self, record: ExecutionRecord) -> None:
        """Records an action execution entry."""

    @abstractmethod
    def get_recent_executions(self, limit: int = 20) -> list[ExecutionRecord]:
        """Retrieves the most recent execution records."""

    # Learned Workflows
    @abstractmethod
    def save_workflow(self, workflow: LearnedWorkflow) -> None:
        """Saves a learned procedure."""

    @abstractmethod
    def get_workflow(self, workflow_id: str) -> LearnedWorkflow | None:
        """Retrieves a workflow by identifier."""

    @abstractmethod
    def list_workflows(self) -> list[LearnedWorkflow]:
        """Lists all learned workflows."""

    # Project Context
    @abstractmethod
    def save_project_context(self, context: ProjectContext) -> None:
        """Persists project context."""

    @abstractmethod
    def get_project_context(self, project_name: str) -> ProjectContext | None:
        """Retrieves project context by name."""
