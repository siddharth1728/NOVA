"""Comprehensive unit tests for Phase 09 Agentic Task Orchestration."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import pytest

from nova.config.settings import Environment, NovaSettings, SecurityMode
from nova.errors import PermissionDeniedError, PlanDriftError, ValidationError, VerificationError
from nova.orchestration.engine import TaskOrchestrator
from nova.orchestration.loop_detector import LoopDetector
from nova.orchestration.models import (
    ObservationDomain,
    OrchestratedTask,
    TaskApprovalState,
    TaskStatus,
)
from nova.orchestration.observations import ObservationCollector
from nova.orchestration.planner import WorkflowPlanner
from nova.orchestration.store import TaskStore
from nova.orchestration.verifier import MultiDomainVerifier
from nova.planning.models import Plan, PlanStep, PlanStepStatus
from nova.tools.categories import ToolCategory
from nova.tools.metadata import ToolMetadata, ToolRiskLevel
from nova.tools.registry import ToolRegistry, get_tool_registry



@pytest.fixture(autouse=True)
def configure_test_workspace(temp_workspace: Path, temp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> NovaSettings:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
        security_mode=SecurityMode.PERMISSIVE,
        require_approval_for_medium_risk=False,
    )
    import nova.config.settings
    monkeypatch.setattr(nova.config.settings, "_settings_instance", settings)
    return settings


@pytest.fixture
def clean_orchestrator(temp_workspace: Path, configure_test_workspace: NovaSettings) -> TaskOrchestrator:
    """Create isolated TaskOrchestrator scoped to temporary workspace."""
    store_dir = temp_workspace / ".nova" / "tasks"
    store = TaskStore(storage_dir=store_dir)
    planner = WorkflowPlanner(workspace_root=temp_workspace)
    orch = TaskOrchestrator(
        settings=configure_test_workspace,
        store=store,
        planner=planner,
    )
    orch.approval_timeout = 3.0
    return orch



class TestTaskLifecycle:
    """Tests core task creation, execution, pause, resume, and cancellation."""

    @pytest.mark.asyncio
    async def test_task_creation_and_idempotency(self, clean_orchestrator: TaskOrchestrator) -> None:
        task1 = clean_orchestrator.create_task(
            query="Scaffold python project demo-proj",
            device_id="device-ios-01",
            request_id="req-unique-01",
        )
        assert task1.task_id.startswith("task_")
        assert task1.status == TaskStatus.QUEUED
        assert task1.request_id == "req-unique-01"

        # Duplicate submission with same request_id returns existing task
        task2 = clean_orchestrator.create_task(
            query="Scaffold python project demo-proj",
            device_id="device-ios-01",
            request_id="req-unique-01",
        )
        assert task2.task_id == task1.task_id

    @pytest.mark.asyncio
    async def test_task_plan_and_execution_success(
        self, clean_orchestrator: TaskOrchestrator, temp_workspace: Path
    ) -> None:
        task = clean_orchestrator.create_task(
            query="Create a python library called my-pkg with src/ and tests/",
            device_id="device-ios-01",
        )
        result = await clean_orchestrator.execute_task(task.task_id)

        assert result.status == TaskStatus.COMPLETED
        assert result.steps_completed >= 3
        assert result.verification == "passed"
        assert (temp_workspace / "my-pkg" / "src").is_dir()
        assert (temp_workspace / "my-pkg" / "README.md").is_file()

        # Verify durable state update
        persisted = clean_orchestrator.store.get_task(task.task_id)
        assert persisted is not None
        assert persisted.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_task_cancellation_during_execution(
        self, clean_orchestrator: TaskOrchestrator
    ) -> None:
        task = clean_orchestrator.create_task(
            query="Create a demo project called cancel-test",
            device_id="device-ios-01",
        )
        # Mark cancellation requested before loop proceeds
        clean_orchestrator.cancel_task(task.task_id, reason="User test cancellation")

        result = await clean_orchestrator.execute_task(task.task_id)
        assert result.status == TaskStatus.CANCELLED
        assert result.verification == "cancelled"

        persisted = clean_orchestrator.store.get_task(task.task_id)
        assert persisted.status == TaskStatus.CANCELLED
        assert persisted.cancellation_requested is True

    @pytest.mark.asyncio
    async def test_task_pause_and_resume_lifecycle(
        self, clean_orchestrator: TaskOrchestrator
    ) -> None:
        task = clean_orchestrator.create_task(
            query="Create demo project called pause-test",
            device_id="device-ios-01",
        )
        # Manually set executing and pause
        task.status = TaskStatus.EXECUTING
        clean_orchestrator.store.save_task(task)

        paused = clean_orchestrator.pause_task(task.task_id, reason="User inspection")
        assert paused is True
        assert clean_orchestrator.store.get_task(task.task_id).status == TaskStatus.PAUSED

        resumed = clean_orchestrator.resume_task(task.task_id)
        assert resumed is True
        assert clean_orchestrator.store.get_task(task.task_id).status == TaskStatus.EXECUTING


class TestPlanValidationAndIntegrity:
    """Tests plan validation rules, DAG cycle detection, and cryptographic integrity."""

    def test_plan_validation_rejects_unknown_tool(self, temp_workspace: Path) -> None:
        planner = WorkflowPlanner(workspace_root=temp_workspace)
        invalid_plan = Plan(
            plan_id="plan_bad_tool",
            goal="Test unknown tool",
            workspace_root=str(temp_workspace),
            steps=[
                PlanStep(
                    step_id=1,
                    description="Run unknown capability",
                    tool="nonexistent_tool_xyz",
                    args={},
                    target=str(temp_workspace),
                )
            ],
        )
        with pytest.raises(ValidationError) as exc:
            planner.validate_plan(invalid_plan)
        assert "specifies unknown/unregistered tool" in str(exc.value)

    def test_plan_validation_rejects_cycles(self, temp_workspace: Path) -> None:
        planner = WorkflowPlanner(workspace_root=temp_workspace)
        cyclic_plan = Plan(
            plan_id="plan_cyclic",
            goal="Cyclic dependency test",
            workspace_root=str(temp_workspace),
            steps=[
                PlanStep(
                    step_id=1,
                    description="Step 1",
                    tool="create_directory",
                    args={"directory_path": str(temp_workspace / "dir1")},
                    target=str(temp_workspace / "dir1"),
                    dependencies=[2],
                ),
                PlanStep(
                    step_id=2,
                    description="Step 2",
                    tool="create_directory",
                    args={"directory_path": str(temp_workspace / "dir2")},
                    target=str(temp_workspace / "dir2"),
                    dependencies=[1],
                ),
            ],
        )
        with pytest.raises(ValidationError) as exc:
            planner.validate_plan(cyclic_plan)
        assert "Circular dependency detected" in str(exc.value)

    @pytest.mark.asyncio
    async def test_plan_drift_detection_raises(
        self, clean_orchestrator: TaskOrchestrator, temp_workspace: Path
    ) -> None:
        task = clean_orchestrator.create_task(
            query="Create demo project called drift-test",
            device_id="device-ios-01",
        )
        plan = await clean_orchestrator.plan_task(task)
        legit_hash = plan.plan_hash

        # Tamper with plan step arguments after validation
        plan.steps[0].args["directory_path"] = str(temp_workspace / "tampered")
        clean_orchestrator.store.save_task(task)

        # Executing with original approved_hash should immediately detect drift
        with pytest.raises(PlanDriftError) as exc:
            await clean_orchestrator.execute_task(task.task_id, approved_hash=legit_hash)
        assert "Plan drift detected" in str(exc.value)


class TestRetriesAndLoopProtection:
    """Tests bounded retries and loop detection guards."""

    def test_loop_detector_flags_identical_repeated_calls(self) -> None:
        detector = LoopDetector(max_repeated_identical_calls=3)
        args = {"url": "https://example.com"}

        detector.record_step("browser_navigate", args, state_signature="error", success=False)
        blocked, _ = detector.check_loop()
        assert not blocked

        detector.record_step("browser_navigate", args, state_signature="error", success=False)
        blocked, _ = detector.check_loop()
        assert not blocked

        detector.record_step("browser_navigate", args, state_signature="error", success=False)
        blocked, reason = detector.check_loop()
        assert blocked is True
        assert "Repeated execution without progress" in reason

    def test_loop_detector_flags_oscillating_states(self) -> None:
        detector = LoopDetector()
        # Pattern A -> B -> A -> B
        detector.record_step("open_window", {"app": "calc"}, state_signature="open", success=True)
        detector.record_step("close_window", {"app": "calc"}, state_signature="closed", success=True)
        detector.record_step("open_window", {"app": "calc"}, state_signature="open", success=True)
        detector.record_step("close_window", {"app": "calc"}, state_signature="closed", success=True)

        blocked, reason = detector.check_loop()
        assert blocked is True
        assert "oscillating execution cycle detected" in reason

    @pytest.mark.asyncio
    async def test_bounded_retries_halts_on_persistent_failure(
        self, clean_orchestrator: TaskOrchestrator, temp_workspace: Path
    ) -> None:
        # Register a mock tool that always fails
        reg = clean_orchestrator.registry
        fail_tool_meta = ToolMetadata(
            name="mock_failing_tool",
            description="Fails for testing retries",
            category=ToolCategory.UTILITY,
            risk_level=ToolRiskLevel.LOW,
            mutates_state=False,
        )


        call_count = 0

        def mock_failing_handler(**kwargs):
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Simulated persistent network timeout")

        reg.register(fail_tool_meta, handler=mock_failing_handler)

        plan = Plan(
            plan_id="plan_retry_test",
            goal="Test bounded retries",
            workspace_root=str(temp_workspace),
            steps=[
                PlanStep(
                    step_id=1,
                    description="Run failing tool",
                    tool="mock_failing_tool",
                    args={},
                    target=str(temp_workspace),
                    max_retries=2,
                )
            ],
        )

        task = clean_orchestrator.create_task(query="Run retry test", device_id="ios-dev")
        task.plan = plan
        clean_orchestrator.store.save_task(task)

        result = await clean_orchestrator.execute_task(task.task_id)
        assert result.status in (TaskStatus.FAILED, TaskStatus.ROLLED_BACK)
        # Should have called initial (1) + retries (2) = 3 times
        assert call_count == 3
        persisted = clean_orchestrator.store.get_task(task.task_id)
        assert len(persisted.retry_history) == 3


class TestRiskEscalationAndApprovals:
    """Tests dynamic risk evaluation and human-in-the-loop approval gates."""

    @pytest.mark.asyncio
    async def test_approval_flow_and_resumption(
        self, clean_orchestrator: TaskOrchestrator, temp_workspace: Path
    ) -> None:
        # Create a plan with a step requiring approval
        plan = Plan(
            plan_id="plan_appr_test",
            goal="Approval gate test",
            workspace_root=str(temp_workspace),
            steps=[
                PlanStep(
                    step_id=1,
                    description="Create test dir",
                    tool="create_directory",
                    args={"directory_path": str(temp_workspace / "appr_dir")},
                    target=str(temp_workspace / "appr_dir"),
                    expected_postcondition={"exists": True, "type": "dir"},
                    risk_level=ToolRiskLevel.HIGH,
                    requires_approval=True,  # Explicitly requires approval
                )
            ],
            risk_ceiling=ToolRiskLevel.LOW,  # Step risk exceeds ceiling!
        )
        plan.plan_hash = plan.compute_plan_hash()

        task = clean_orchestrator.create_task(query="Test approval", device_id="ios-dev")
        task.plan = plan
        clean_orchestrator.store.save_task(task)

        # Launch execution as background task
        exec_handle = asyncio.create_task(clean_orchestrator.execute_task(task.task_id))

        # Allow execution loop to reach the approval gate
        await asyncio.sleep(0.1)

        t_current = clean_orchestrator.store.get_task(task.task_id)
        assert t_current.status == TaskStatus.AWAITING_APPROVAL
        assert t_current.pending_approval is not None
        assert t_current.pending_approval.step_id == 1

        # Approve step via orchestrator
        clean_orchestrator.approve_step(task.task_id, step_id=1, approved=True)

        # Wait for execution to finish
        result = await exec_handle
        assert result.status == TaskStatus.COMPLETED
        assert (temp_workspace / "appr_dir").is_dir()

    @pytest.mark.asyncio
    async def test_approval_denied_halts_task(
        self, clean_orchestrator: TaskOrchestrator, temp_workspace: Path
    ) -> None:
        plan = Plan(
            plan_id="plan_deny_test",
            goal="Approval denial test",
            workspace_root=str(temp_workspace),
            steps=[
                PlanStep(
                    step_id=1,
                    description="Denied operation",
                    tool="create_directory",
                    args={"directory_path": str(temp_workspace / "denied_dir")},
                    target=str(temp_workspace / "denied_dir"),
                    requires_approval=True,
                )
            ],
        )
        plan.plan_hash = plan.compute_plan_hash()

        task = clean_orchestrator.create_task(query="Test denial", device_id="ios-dev")

        task.plan = plan
        clean_orchestrator.store.save_task(task)

        exec_handle = asyncio.create_task(clean_orchestrator.execute_task(task.task_id))
        await asyncio.sleep(0.1)

        # Deny step
        clean_orchestrator.approve_step(task.task_id, step_id=1, approved=False)

        result = await exec_handle
        assert result.status in (TaskStatus.FAILED, TaskStatus.ROLLED_BACK)
        assert not (temp_workspace / "denied_dir").exists()


class TestRestartRecoveryAndPersistence:
    """Tests Section 42 safety invariant: Host restarts pause rather than blindly replaying."""

    def test_restart_recovery_pauses_interrupted_tasks(self, temp_workspace: Path) -> None:
        store_dir = temp_workspace / ".nova" / "tasks"
        store = TaskStore(storage_dir=store_dir)

        # Persist a task that was left EXECUTING
        task = OrchestratedTask(
            task_id="task_crashed_01",
            request_id="req_crash",
            device_id="ios-dev",
            query="Simulate crash during execution",
            status=TaskStatus.EXECUTING,
        )
        store.save_task(task)

        # Simulate host reboot by initializing a fresh store and orchestrator
        fresh_store = TaskStore(storage_dir=store_dir)
        recovered_count = fresh_store.recover_interrupted_tasks()

        assert recovered_count == 1
        recovered_task = fresh_store.get_task("task_crashed_01")
        assert recovered_task.status == TaskStatus.PAUSED
        assert "Host restarted" in recovered_task.pause_reason
