"""Integration test for critical failure handling when rollback itself fails."""

from pathlib import Path
import pytest

from nova.config.settings import Environment, NovaSettings
from nova.errors import RollbackFailedError
from nova.planning.executor import PlanExecutor
from nova.planning.planner import TaskPlanner
from nova.transactions.manager import get_transaction_manager
from nova.transactions.models import TransactionStatus


@pytest.fixture(autouse=True)
def configure_test_environment(temp_workspace: Path, temp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
    )
    import nova.config.settings
    monkeypatch.setattr(nova.config.settings, "_settings_instance", settings)


def test_critical_rollback_failure_handling(temp_workspace: Path) -> None:
    planner = TaskPlanner(workspace_root=temp_workspace)
    executor = PlanExecutor()
    tx_mgr = get_transaction_manager()

    goal = "Create a demo project structure called rollback-fail-test with README.md"
    plan = planner.create_plan_for_goal(goal)
    approved_hash = plan.plan_hash

    # Trigger failure at step 2, and also simulate rollback failure
    with pytest.raises(RollbackFailedError) as exc_info:
        executor.execute(
            plan,
            approved_hash=approved_hash,
            simulate_failure_at_step=2,
            simulate_rollback_failure=True,
        )

    err = exc_info.value
    assert err.transaction_id == plan.plan_id
    assert "recovery_info" in err.details

    # Check that transaction status in manager is ROLLBACK_FAILED
    tx_record = tx_mgr.get_transaction(plan.plan_id)
    assert tx_record is not None
    assert tx_record.status == TransactionStatus.ROLLBACK_FAILED
    assert tx_record.error is not None
