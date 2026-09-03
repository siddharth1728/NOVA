"""Integration test for failure handling, LIFO rollback, and workspace restoration."""

from pathlib import Path
import pytest

from nova.config.settings import Environment, NovaSettings
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


def test_multi_step_failure_triggers_lifo_rollback_and_restores_workspace(temp_workspace: Path) -> None:
    planner = TaskPlanner(workspace_root=temp_workspace)
    executor = PlanExecutor()

    # Capture initial workspace files
    initial_files = sorted([p.relative_to(temp_workspace) for p in temp_workspace.rglob("*")])

    goal = "Create a demo Java backend project structure called rollback-test with README.md"
    plan = planner.create_plan_for_goal(goal)
    approved_hash = plan.plan_hash

    # Deliberately fail on step 3
    result = executor.execute(
        plan,
        approved_hash=approved_hash,
        simulate_failure_at_step=3,
    )

    assert result.success is False
    assert result.status == PlanStatus.ROLLED_BACK
    assert result.rolled_back is True
    assert result.rollback_verified is True
    assert "Controlled test failure triggered at step 3" in (result.error or "")

    # Empirically verify that newly created project folder was rolled back
    project_dir = temp_workspace / "rollback-test"
    assert not project_dir.exists()

    # Verify workspace state matches initial files
    current_files = sorted([p.relative_to(temp_workspace) for p in temp_workspace.rglob("*")])
    assert current_files == initial_files
