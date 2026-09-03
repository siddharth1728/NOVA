"""Integration test for end-to-end plan execution, empirical verification, and commit."""

from pathlib import Path
import pytest

from nova.config.settings import Environment, NovaSettings
from nova.memory.store import LocalFileMemoryStore
from nova.observability.audit import get_audit_trail
from nova.planning.executor import PlanExecutor
from nova.planning.models import PlanStatus
from nova.planning.planner import TaskPlanner


@pytest.fixture(autouse=True)
def configure_test_environment(temp_workspace: Path, temp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
    )
    import nova.config.settings
    monkeypatch.setattr(nova.config.settings, "_settings_instance", settings)


def test_end_to_end_project_scaffolding(temp_workspace: Path, temp_data_dir: Path) -> None:
    planner = TaskPlanner(workspace_root=temp_workspace)
    executor = PlanExecutor()

    goal = "Create a demo Java backend project structure called demo-api with README.md"
    plan = planner.create_plan_for_goal(goal)
    approved_hash = plan.plan_hash

    # Execute plan
    result = executor.execute(plan, approved_hash=approved_hash)

    assert result.success is True
    assert result.status == PlanStatus.COMMITTED
    assert result.completed_steps == len(plan.steps)
    assert result.rolled_back is False

    # Empirically verify physical disk state in temp_workspace
    project_dir = temp_workspace / "demo-api"
    src_main_java = project_dir / "src" / "main" / "java"
    src_test_java = project_dir / "src" / "test" / "java"
    readme_file = project_dir / "README.md"

    assert project_dir.exists() and project_dir.is_dir()
    assert src_main_java.exists() and src_main_java.is_dir()
    assert src_test_java.exists() and src_test_java.is_dir()
    assert readme_file.exists() and readme_file.is_file()
    assert "Demo-Api" in readme_file.read_text(encoding="utf-8")

    # Verify execution memory
    memory = LocalFileMemoryStore()
    records = memory.get_recent_executions(limit=10)
    assert len(records) > 0
    assert any(r.task_id == plan.plan_id and r.verified is True for r in records)
