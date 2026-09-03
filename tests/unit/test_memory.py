"""Unit tests for local-first memory subsystem."""

from nova.memory.models import (
    EnvironmentFact,
    ExecutionRecord,
    LearnedWorkflow,
    ProjectContext,
    TaskState,
    UserPreference,
)
from nova.memory.store import LocalFileMemoryStore


def test_user_preferences(memory_store: LocalFileMemoryStore) -> None:
    pref = UserPreference(key="code_style", value="pep8", description="Python formatting")
    memory_store.save_preference(pref)

    retrieved = memory_store.get_preference("code_style")
    assert retrieved is not None
    assert retrieved.key == "code_style"
    assert retrieved.value == "pep8"

    all_prefs = memory_store.list_preferences()
    assert len(all_prefs) == 1
    assert all_prefs[0].key == "code_style"


def test_environment_facts(memory_store: LocalFileMemoryStore) -> None:
    fact1 = EnvironmentFact(key="os", value="windows", category="system")
    fact2 = EnvironmentFact(key="python_version", value="3.11", category="runtime")
    memory_store.save_fact(fact1)
    memory_store.save_fact(fact2)

    assert memory_store.get_fact("os") is not None
    assert memory_store.get_fact("python_version") is not None
    assert len(memory_store.list_facts()) == 2

    runtime_facts = memory_store.list_facts(category="runtime")
    assert len(runtime_facts) == 1
    assert runtime_facts[0].key == "python_version"


def test_task_state(memory_store: LocalFileMemoryStore) -> None:
    task = TaskState(
        task_id="task_001",
        goal="Audit repository structure",
        status="running",
        steps=["list files", "read pyproject"],
    )
    memory_store.save_task_state(task)

    retrieved = memory_store.get_task_state("task_001")
    assert retrieved is not None
    assert retrieved.status == "running"
    assert len(retrieved.steps) == 2


def test_execution_records(memory_store: LocalFileMemoryStore) -> None:
    rec1 = ExecutionRecord(
        record_id="rec_1",
        tool="list_directory",
        args_summary="path=.",
        outcome="found 3 files",
        success=True,
    )
    rec2 = ExecutionRecord(
        record_id="rec_2",
        tool="view_file",
        args_summary="path=README.md",
        outcome="content read",
        success=True,
    )
    memory_store.record_execution(rec1)
    memory_store.record_execution(rec2)

    recent = memory_store.get_recent_executions(limit=10)
    assert len(recent) == 2
    # Ordered most recent first
    assert recent[0].record_id == "rec_2"
    assert recent[1].record_id == "rec_1"


def test_learned_workflows(memory_store: LocalFileMemoryStore) -> None:
    wf = LearnedWorkflow(
        workflow_id="wf_check_deps",
        name="Dependency Audit",
        goal_pattern="audit dependencies",
        steps=["read pyproject.toml", "check lockfile", "run audit"],
    )
    memory_store.save_workflow(wf)

    retrieved = memory_store.get_workflow("wf_check_deps")
    assert retrieved is not None
    assert retrieved.name == "Dependency Audit"
    assert len(retrieved.steps) == 3


def test_project_context(memory_store: LocalFileMemoryStore) -> None:
    ctx = ProjectContext(
        project_name="NOVA",
        domain="Personal AI Operating Layer",
        tech_stack=["Python", "Antigravity", "Pydantic"],
        key_directories=["src/nova", "tests"],
    )
    memory_store.save_project_context(ctx)

    retrieved = memory_store.get_project_context("NOVA")
    assert retrieved is not None
    assert retrieved.project_name == "NOVA"
    assert "Antigravity" in retrieved.tech_stack
