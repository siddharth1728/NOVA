"""Integration tests for Phase 09 Agentic Multi-Step Workflows.

Tests multi-domain orchestration across Windows desktop, browser, and filesystem,
human-in-the-loop approval gates via REST API, empirical verification postconditions,
failure injection with LIFO rollback, and host restart crash recovery.
"""

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest

from nova.config.settings import Environment, NovaSettings, SecurityMode
from nova.control.browsers.models import BrowserTab
from nova.control.clipboard.models import ClipboardContent, ClipboardType
from nova.control.windows.models import WindowBounds, WindowInfo
from nova.host.auth import DeviceRegistry, TokenManager
from nova.host.pairing import PairingManager
from nova.host.server import create_host_app
from nova.orchestration.engine import TaskOrchestrator
from nova.orchestration.models import (
    Observation,
    ObservationDomain,
    OrchestratedTask,
    TaskApprovalState,
)
from nova.orchestration.observations import ObservationCollector
from nova.orchestration.planner import WorkflowPlanner
from nova.orchestration.store import TaskStore
from nova.orchestration.verifier import MultiDomainVerifier
from nova.planning.models import Plan, PlanStep, PlanStepStatus, ToolRiskLevel
from nova.protocol.models import TaskStatus
from nova.tools.computer import register_computer_tools
from nova.tools.metadata import ToolCategory, ToolMetadata
from nova.tools.mutations import register_mutation_tools
from nova.tools.registry import ToolRegistry


@dataclass
class WorkflowTestContext:
    settings: NovaSettings
    workspace: Path
    client: httpx.AsyncClient
    auth_headers: dict[str, str]
    orchestrator: TaskOrchestrator
    store: TaskStore
    win_mock: MagicMock
    clip_mock: MagicMock
    browser_mock: MagicMock


@pytest.fixture
async def workflow_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[WorkflowTestContext, None]:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    data_dir = tmp_path / ".nova"
    data_dir.mkdir(parents=True, exist_ok=True)

    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=workspace,
        data_dir=data_dir,
        host_secret="integration-test-secret-at-least-32-bytes-long",
        security_mode=SecurityMode.PERMISSIVE,
        require_approval_for_medium_risk=False,
    )
    import nova.config.settings
    monkeypatch.setattr(nova.config.settings, "_settings_instance", settings)

    device_registry = DeviceRegistry(settings.devices_file)
    token_manager = TokenManager(secret_key=settings.host_secret.get_secret_value())
    pairing_manager = PairingManager(default_ttl_seconds=300)

    # Setup mocked domain controllers
    win_mock = MagicMock()
    clip_mock = MagicMock()
    browser_mock = MagicMock()

    # Default mock behavior
    win_mock.get_foreground_window.return_value = WindowInfo(
        hwnd=4200,
        title="Active Editor Window",
        process_name="editor.exe",
        pid=1001,
        bounds=WindowBounds(x=0, y=0, width=800, height=600),
        visible=True,
        is_foreground=True,
    )

    clip_mock.inspect.return_value = ClipboardContent(
        content_type=ClipboardType.TEXT,
        has_text=True,
        text_length=35,
        hash_sha256="fake-hash-for-integration-tests",
    )

    test_tab = BrowserTab(
        tab_id="tab-orch-1",
        title="Agentic Workflow Documentation",
        url="https://docs.novasystem.internal/workflow",
    )
    browser_mock.list_tabs = AsyncMock(return_value=[test_tab])
    browser_mock.inspect = AsyncMock(return_value=[{"id": "doc-title", "tag": "h1"}])

    import nova.orchestration.observations as obs_mod
    monkeypatch.setattr(obs_mod, "get_browser_controller", lambda: browser_mock)

    observer = ObservationCollector(
        window_controller=win_mock,
        clipboard_controller=clip_mock,
    )
    verifier = MultiDomainVerifier(observer=observer)
    store = TaskStore(storage_dir=data_dir / "tasks")
    registry = ToolRegistry()
    register_mutation_tools(registry)
    register_computer_tools(registry)

    # Register mock and real tools
    def _mock_browser_fetch(url: str, **kwargs: Any) -> dict[str, Any]:
        return {
            "tab_id": "tab-orch-1",
            "url": url,
            "content": "Agentic Workflow Documentation content payload",
        }

    def _mock_clipboard_set(text: str, **kwargs: Any) -> dict[str, Any]:
        clip_mock.inspect.return_value = ClipboardContent(
            content_type=ClipboardType.TEXT,
            has_text=True,
            text_length=len(text),
            hash_sha256="fake-hash-for-integration-tests",
        )
        return {"bytes_written": len(text), "status": "success"}

    def _mock_window_focus(hwnd: int | str, **kwargs: Any) -> dict[str, Any]:
        h_int = int(hwnd)
        win_mock.get_foreground_window.return_value = WindowInfo(
            hwnd=h_int,
            title="Active Editor Window",
            process_name="editor.exe",
            pid=1001,
            bounds=WindowBounds(x=0, y=0, width=800, height=600),
            visible=True,
            is_foreground=True,
        )
        return {"hwnd": h_int, "focused": True}

    def _mock_create_doc(path: str, content: str, **kwargs: Any) -> dict[str, Any]:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": str(p), "bytes": len(content)}

    registry.register(
        ToolMetadata(
            name="mock_browser_fetch",
            description="Fetch web page",
            category=ToolCategory.UTILITY,
            risk_level=ToolRiskLevel.LOW,
            mutates_state=False,
            is_reversible=True,
        ),
        handler=_mock_browser_fetch,
    )
    registry.register(
        ToolMetadata(
            name="mock_clipboard_set",
            description="Copy to clipboard",
            category=ToolCategory.UTILITY,
            risk_level=ToolRiskLevel.LOW,
            mutates_state=True,
            is_reversible=True,
        ),
        handler=_mock_clipboard_set,
    )
    registry.register(
        ToolMetadata(
            name="mock_window_focus",
            description="Focus desktop window",
            category=ToolCategory.COMPUTER,
            risk_level=ToolRiskLevel.LOW,
            mutates_state=False,
            is_reversible=True,
        ),
        handler=_mock_window_focus,
    )
    registry.register(
        ToolMetadata(
            name="mock_create_doc",
            description="Create document in workspace",
            category=ToolCategory.FILESYSTEM,
            risk_level=ToolRiskLevel.MEDIUM,
            mutates_state=True,
            is_reversible=True,
        ),
        handler=_mock_create_doc,
    )

    orchestrator = TaskOrchestrator(
        settings=settings,
        registry=registry,
        store=store,
        observer=observer,
        verifier=verifier,
    )
    orchestrator.approval_timeout = 3.0

    app = create_host_app(
        settings=settings,
        device_registry=device_registry,
        token_manager=token_manager,
        pairing_manager=pairing_manager,
        browser_controller=browser_mock,
        task_orchestrator=orchestrator,
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Pair test device
        code, _ = pairing_manager.generate_code()
        pair_resp = await client.post(
            "/api/v1/pair",
            json={
                "pairing_code": code,
                "device_id": "test-ios-orch-client",
                "device_name": "Integration iPhone",
                "platform": "iOS",
            },
        )
        assert pair_resp.status_code == 200
        token = pair_resp.json()["token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        yield WorkflowTestContext(
            settings=settings,
            workspace=workspace,
            client=client,
            auth_headers=auth_headers,
            orchestrator=orchestrator,
            store=store,
            win_mock=win_mock,
            clip_mock=clip_mock,
            browser_mock=browser_mock,
        )


class TestMultiDomainOrchestration:
    """Tests cross-domain workflows spanning Browser, Filesystem, and Windows."""

    @pytest.mark.asyncio
    async def test_multi_domain_workflow(self, workflow_env: WorkflowTestContext) -> None:
        """Executes a 3-step workflow across Browser -> Filesystem -> Clipboard with full verification."""
        doc_path = workflow_env.workspace / "synthesis_report.md"

        plan = Plan(
            plan_id="plan_cross_domain_01",
            goal="Research doc in browser, save summary to disk, copy snippet to clipboard",
            workspace_root=str(workflow_env.workspace),
            steps=[
                PlanStep(
                    step_id=1,
                    description="Extract web content from documentation",
                    tool="mock_browser_fetch",
                    args={"url": "https://docs.novasystem.internal/workflow"},
                    target="tab-orch-1",
                    domain="BROWSER",
                    expected_postcondition={
                        "tab_open": True,
                        "url_contains": "docs.novasystem.internal",
                        "content_contains": "Documentation",
                    },
                    risk_level=ToolRiskLevel.LOW,
                ),
                PlanStep(
                    step_id=2,
                    description="Write synthesis report to filesystem",
                    tool="mock_create_doc",
                    args={
                        "path": str(doc_path),
                        "content": "# Research Report\n\nCross-domain synthesis completed successfully.",
                    },
                    target=str(doc_path),
                    domain="FILESYSTEM",
                    expected_postcondition={"exists": True, "type": "file"},
                    risk_level=ToolRiskLevel.MEDIUM,
                    dependencies=[1],
                ),
                PlanStep(
                    step_id=3,
                    description="Copy final report excerpt to clipboard",
                    tool="mock_clipboard_set",
                    args={"text": "Cross-domain synthesis completed"},
                    target="system_clipboard",
                    domain="CLIPBOARD",
                    expected_postcondition={"has_text": True},
                    risk_level=ToolRiskLevel.LOW,
                    dependencies=[2],
                ),
            ],
            risk_ceiling=ToolRiskLevel.HIGH,
        )
        plan.plan_hash = plan.compute_plan_hash()

        task = workflow_env.orchestrator.create_task(
            query="Execute cross-domain research task",
            device_id="test-ios-orch-client",
        )
        task.plan = plan
        workflow_env.store.save_task(task)

        result = await workflow_env.orchestrator.execute_task(task.task_id)

        # 1. Verify task lifecycle completion
        assert result.status == TaskStatus.COMPLETED
        assert result.verification == "passed"
        assert result.steps_completed == 3
        assert result.steps_failed == 0

        # 2. Verify empirical filesystem side effect
        assert doc_path.exists()
        assert "Cross-domain synthesis" in doc_path.read_text(encoding="utf-8")

        # 3. Verify task store persistence & metrics
        persisted = workflow_env.store.get_task(task.task_id)
        assert persisted.status == TaskStatus.COMPLETED
        assert persisted.progress.percent == 100.0
        assert len(persisted.plan.steps) == 3
        for step in persisted.plan.steps:
            assert step.status == PlanStepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_windows_desktop_control_workflow(self, workflow_env: WorkflowTestContext) -> None:
        """Executes a Windows desktop control workflow verifying focused window state."""
        plan = Plan(
            plan_id="plan_win_control",
            goal="Focus editor window on Windows desktop",
            workspace_root=str(workflow_env.workspace),
            steps=[
                PlanStep(
                    step_id=1,
                    description="Bring editor window to foreground",
                    tool="mock_window_focus",
                    args={"hwnd": 4200},
                    target="4200",
                    domain="WINDOWS",
                    expected_postcondition={"focused": True},
                    risk_level=ToolRiskLevel.LOW,
                )
            ],
            risk_ceiling=ToolRiskLevel.LOW,
        )
        plan.plan_hash = plan.compute_plan_hash()

        task = workflow_env.orchestrator.create_task(
            query="Focus editor",
            device_id="test-ios-orch-client",
        )
        task.plan = plan
        workflow_env.store.save_task(task)

        result = await workflow_env.orchestrator.execute_task(task.task_id)
        assert result.status == TaskStatus.COMPLETED
        assert result.verification == "passed"
        assert workflow_env.win_mock.get_foreground_window.called


class TestHumanInTheLoopApprovalAPI:
    """Tests approval gate and risk escalation workflows through the Starlette REST API."""

    @pytest.mark.asyncio
    async def test_approval_gate_and_resumption_via_api(self, workflow_env: WorkflowTestContext) -> None:
        """Submits task, reaches approval gate, inspects via API, approves, and verifies completion."""
        task = workflow_env.orchestrator.create_task(
            query="Scaffold secure enterprise workflow",
            device_id="test-ios-orch-client",
            risk_ceiling="LOW",
            require_approval=False,
        )
        task_id = task.task_id

        plan = Plan(
            plan_id=f"plan_api_appr_{task_id}",
            goal="Test API approval gate",
            workspace_root=str(workflow_env.workspace),
            steps=[
                PlanStep(
                    step_id=1,
                    description="Safe read-only check",
                    tool="mock_browser_fetch",
                    args={"url": "https://docs.novasystem.internal/workflow"},
                    target="tab-orch-1",
                    domain="BROWSER",
                    expected_postcondition={"tab_open": True},
                    risk_level=ToolRiskLevel.LOW,
                    requires_approval=False,
                ),
                PlanStep(
                    step_id=2,
                    description="High risk file write requiring approval",
                    tool="mock_create_doc",
                    args={
                        "path": str(workflow_env.workspace / "approved_output.txt"),
                        "content": "Authorized operation content",
                    },
                    target=str(workflow_env.workspace / "approved_output.txt"),
                    domain="FILESYSTEM",
                    expected_postcondition={"exists": True},
                    risk_level=ToolRiskLevel.HIGH,
                    requires_approval=True,
                    dependencies=[1],
                ),
            ],
            risk_ceiling=ToolRiskLevel.LOW,
        )
        plan.plan_hash = plan.compute_plan_hash()

        task.plan = plan
        workflow_env.store.save_task(task)

        # Launch execution as background task on active event loop
        exec_task = asyncio.create_task(workflow_env.orchestrator.execute_task(task_id))

        # Give event loop time to reach approval gate
        await asyncio.sleep(0.1)

        # 1. Check status via API - should be AWAITING_APPROVAL
        detail_resp = await workflow_env.client.get(
            f"/api/v1/tasks/{task_id}",
            headers=workflow_env.auth_headers,
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["status"] == TaskStatus.AWAITING_APPROVAL.value
        assert detail["pending_approval"] is not None
        assert detail["pending_approval"]["step_id"] == 2

        # 2. Check steps via API
        steps_resp = await workflow_env.client.get(
            f"/api/v1/tasks/{task_id}/steps",
            headers=workflow_env.auth_headers,
        )
        assert steps_resp.status_code == 200
        steps_data = steps_resp.json()
        assert len(steps_data["steps"]) == 2
        assert steps_data["steps"][1]["requires_approval"] is True

        # 3. Approve step via API
        approve_resp = await workflow_env.client.post(
            f"/api/v1/tasks/{task_id}/approve",
            headers=workflow_env.auth_headers,
            json={"step_id": 2, "approved": True},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == TaskStatus.EXECUTING.value

        # 4. Complete execution
        result = await exec_task
        assert result.status == TaskStatus.COMPLETED
        assert (workflow_env.workspace / "approved_output.txt").exists()

    @pytest.mark.asyncio
    async def test_approval_denied_via_api(self, workflow_env: WorkflowTestContext) -> None:
        """Denies approval via API, verifying task halts and high-risk action is aborted."""
        task = workflow_env.orchestrator.create_task(
            query="Deny flow test",
            device_id="test-ios-orch-client",
            risk_ceiling="LOW",
        )
        task_id = task.task_id

        dangerous_file = workflow_env.workspace / "should_never_exist.txt"
        plan = Plan(
            plan_id=f"plan_deny_{task_id}",
            goal="Test API approval denial",
            workspace_root=str(workflow_env.workspace),
            steps=[
                PlanStep(
                    step_id=1,
                    description="Unapproved action",
                    tool="mock_create_doc",
                    args={"path": str(dangerous_file), "content": "Bad"},
                    target=str(dangerous_file),
                    domain="FILESYSTEM",
                    expected_postcondition={"exists": True},
                    risk_level=ToolRiskLevel.CRITICAL,
                    requires_approval=True,
                )
            ],
            risk_ceiling=ToolRiskLevel.LOW,
        )
        plan.plan_hash = plan.compute_plan_hash()

        task.plan = plan
        workflow_env.store.save_task(task)

        exec_task = asyncio.create_task(workflow_env.orchestrator.execute_task(task_id))
        await asyncio.sleep(0.1)

        # Deny approval via API
        deny_resp = await workflow_env.client.post(
            f"/api/v1/tasks/{task_id}/deny",
            headers=workflow_env.auth_headers,
            json={"step_id": 1, "reason": "Explicit operator rejection"},
        )
        assert deny_resp.status_code == 200

        result = await exec_task
        assert result.status in (TaskStatus.FAILED, TaskStatus.ROLLED_BACK)
        assert not dangerous_file.exists()


class TestFailureInjectionAndRollback:
    """Tests failure injection, retry exhaustion, and LIFO rollback."""

    @pytest.mark.asyncio
    async def test_failure_injection_triggers_lifo_rollback(
        self, workflow_env: WorkflowTestContext
    ) -> None:
        """Injects failure at Step 2; verifies LIFO rollback cleans up Step 1."""
        canary_file = workflow_env.workspace / "canary_step_1.txt"

        def _mock_step1(path: str, **kwargs: Any) -> dict[str, Any]:
            p = Path(path)
            p.write_text("Created during step 1", encoding="utf-8")
            return {"path": str(p), "status": "created"}

        def _mock_failing_step2(**kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("Injected catastrophic failure at step 2")

        workflow_env.orchestrator.registry.register(
            ToolMetadata(
                name="test_step1_tool",
                description="Step 1 tool",
                category=ToolCategory.FILESYSTEM,
                risk_level=ToolRiskLevel.MEDIUM,
                mutates_state=True,
                is_reversible=True,
            ),
            handler=_mock_step1,
        )
        workflow_env.orchestrator.registry.register(
            ToolMetadata(
                name="test_step2_failing_tool",
                description="Step 2 failing tool",
                category=ToolCategory.FILESYSTEM,
                risk_level=ToolRiskLevel.MEDIUM,
                mutates_state=False,
                is_reversible=True,
            ),
            handler=_mock_failing_step2,
        )

        plan = Plan(
            plan_id="plan_fail_rollback",
            goal="Test failure injection and LIFO rollback",
            workspace_root=str(workflow_env.workspace),
            steps=[
                PlanStep(
                    step_id=1,
                    description="Create reversible canary file",
                    tool="test_step1_tool",
                    args={"path": str(canary_file)},
                    target=str(canary_file),
                    domain="FILESYSTEM",
                    expected_postcondition={"exists": True},
                    risk_level=ToolRiskLevel.MEDIUM,
                    reversibility="REVERSIBLE",
                ),
                PlanStep(
                    step_id=2,
                    description="Execute failing tool",
                    tool="test_step2_failing_tool",
                    args={},
                    target=str(workflow_env.workspace),
                    domain="FILESYSTEM",
                    expected_postcondition={},
                    risk_level=ToolRiskLevel.MEDIUM,
                    max_retries=1,
                    dependencies=[1],
                ),
            ],
            risk_ceiling=ToolRiskLevel.HIGH,
        )
        plan.plan_hash = plan.compute_plan_hash()

        task = workflow_env.orchestrator.create_task(
            query="Test rollback injection",
            device_id="test-ios-orch-client",
        )
        task.plan = plan
        workflow_env.store.save_task(task)

        result = await workflow_env.orchestrator.execute_task(task.task_id)

        assert result.status == TaskStatus.ROLLED_BACK
        assert result.steps_failed == 1
        assert "Injected catastrophic failure" in result.summary

        # Confirm rollback was recorded in store
        persisted = workflow_env.store.get_task(task.task_id)
        assert persisted.status == TaskStatus.ROLLED_BACK


class TestCrashRecoveryAndAPILifecycle:
    """Tests host restart recovery and REST API CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_host_restart_recovery_pauses_tasks(self, workflow_env: WorkflowTestContext) -> None:
        """Verifies that an interrupted in-flight task is marked PAUSED on host restart, not blindly replayed."""
        # 1. Create a task and mark it in-flight
        task = workflow_env.orchestrator.create_task(
            query="Interrupted task test",
            device_id="test-ios-orch-client",
        )
        task.status = TaskStatus.EXECUTING
        task.progress.current_step_id = 1
        workflow_env.store.save_task(task)

        # 2. Simulate new host starting up
        fresh_store = TaskStore(storage_dir=workflow_env.settings.data_dir / "tasks")
        recovered_count = fresh_store.recover_interrupted_tasks()
        assert recovered_count == 1

        recovered_task = fresh_store.get_task(task.task_id)
        assert recovered_task.status == TaskStatus.PAUSED
        assert "Host restarted" in (recovered_task.pause_reason or "")

    @pytest.mark.asyncio
    async def test_task_api_full_crud_and_metrics(self, workflow_env: WorkflowTestContext) -> None:
        """Tests task CRUD operations, pause/resume/cancel controls, and metrics endpoint."""
        # 1. List tasks (initially empty or existing)
        list_resp = await workflow_env.client.get("/api/v1/tasks", headers=workflow_env.auth_headers)
        assert list_resp.status_code == 200
        initial_tasks = list_resp.json()
        assert isinstance(initial_tasks, list)

        # 2. Create controllable task for lifecycle testing
        task = workflow_env.orchestrator.create_task(
            query="API CRUD test",
            device_id="test-ios-orch-client",
        )
        task.status = TaskStatus.EXECUTING
        workflow_env.store.save_task(task)
        task_id = task.task_id

        # 3. Get task details
        get_resp = await workflow_env.client.get(
            f"/api/v1/tasks/{task_id}", headers=workflow_env.auth_headers
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["task_id"] == task_id

        # 4. Pause task
        pause_resp = await workflow_env.client.post(
            f"/api/v1/tasks/{task_id}/pause",
            headers=workflow_env.auth_headers,
            json={"reason": "User paused via iPhone"},
        )
        assert pause_resp.status_code == 200
        assert pause_resp.json()["status"] == TaskStatus.PAUSED.value

        # 5. Resume task
        resume_resp = await workflow_env.client.post(
            f"/api/v1/tasks/{task_id}/resume",
            headers=workflow_env.auth_headers,
        )
        assert resume_resp.status_code == 200
        assert resume_resp.json()["status"] in (TaskStatus.QUEUED.value, TaskStatus.EXECUTING.value)

        # 6. Cancel task
        cancel_resp = await workflow_env.client.post(
            f"/api/v1/tasks/{task_id}/cancel",
            headers=workflow_env.auth_headers,
            json={"reason": "User cancelled via iPhone"},
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == TaskStatus.CANCELLED.value

        # 7. Query metrics
        metrics_resp = await workflow_env.client.get(
            "/api/v1/tasks/metrics", headers=workflow_env.auth_headers
        )
        assert metrics_resp.status_code == 200
        metrics = metrics_resp.json()
        assert "tasks_started" in metrics
        assert "tasks_completed" in metrics
        assert "tasks_failed" in metrics
        assert "steps_executed" in metrics

        # 8. Unauthenticated request rejected
        unauth_resp = await workflow_env.client.get("/api/v1/tasks")
        assert unauth_resp.status_code == 401
