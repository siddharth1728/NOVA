"""Authoritative NOVA Task Orchestration Engine (Phase 09).

Decomposes natural language goals into verifiable execution plans, governs step execution
through strict policy and risk evaluation, enforces empirical observation and verification,
manages pause/resume/cancellation/rollback, and prevents infinite execution loops.
"""

import asyncio
from datetime import datetime, timezone
import inspect
import logging
from pathlib import Path
import time
from typing import Any
import uuid

from nova.config.settings import NovaSettings, get_settings
from nova.errors import (
    ConflictError,
    PermissionDeniedError,
    PlanDriftError,
    RollbackFailedError,
    ValidationError,
    VerificationError,
)
from nova.memory.interface import MemoryStore
from nova.memory.models import ExecutionRecord
from nova.memory.store import LocalFileMemoryStore
from nova.observability.audit import AuditTrail, get_audit_trail
from nova.orchestration.loop_detector import LoopDetector
from nova.orchestration.metrics import TaskMetricsTracker, get_task_metrics
from nova.orchestration.models import (
    FailureClassification,
    Observation,
    ObservationDomain,
    OrchestratedTask,
    ReversibilityType,
    StepApprovalRequest,
    StepRetryRecord,
    TaskApprovalState,
    TaskArtifact,
    TaskProgress,
    TaskResult,
)
from nova.orchestration.observations import ObservationCollector
from nova.orchestration.planner import WorkflowPlanner
from nova.orchestration.store import TaskStore
from nova.orchestration.verifier import MultiDomainVerifier
from nova.planning.models import Plan, PlanStatus, PlanStep, PlanStepStatus
from nova.protocol.models import TaskStatus, WebSocketEvent
from nova.security.permissions import PermissionDecision, PermissionEngine
from nova.tools.metadata import ToolRiskLevel
from nova.tools.registry import ToolRegistry, get_tool_registry
from nova.transactions.manager import TransactionManager, get_transaction_manager

logger = logging.getLogger("nova.orchestration.engine")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskOrchestrator:
    """Production orchestrator executing multi-step workflows with strict safety and verification."""

    def __init__(
        self,
        settings: NovaSettings | None = None,
        registry: ToolRegistry | None = None,
        store: TaskStore | None = None,
        planner: WorkflowPlanner | None = None,
        verifier: MultiDomainVerifier | None = None,
        observer: ObservationCollector | None = None,
        tx_mgr: TransactionManager | None = None,
        permission_engine: PermissionEngine | None = None,
        audit_trail: AuditTrail | None = None,
        memory_store: MemoryStore | None = None,
        metrics: TaskMetricsTracker | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.registry = registry or get_tool_registry()
        self.store = store or TaskStore()
        self.observer = observer or ObservationCollector()
        self.verifier = verifier or MultiDomainVerifier(observer=self.observer)
        self.planner = planner or WorkflowPlanner(workspace_root=self.settings.workspace_root, registry=self.registry)
        self.tx_mgr = tx_mgr or get_transaction_manager()
        self.permission_engine = permission_engine or PermissionEngine(settings=self.settings, registry=self.registry)
        self.audit = audit_trail or get_audit_trail()
        self.memory = memory_store or LocalFileMemoryStore()
        self.metrics = metrics or get_task_metrics()
        self.approval_timeout: float = 30.0

        # In-memory execution handles and pause/approval events
        self._async_handles: dict[str, asyncio.Task[Any]] = {}
        self._resume_events: dict[str, asyncio.Event] = {}
        self._approval_events: dict[str, asyncio.Event] = {}

        # Recover any interrupted tasks from previous host sessions
        recovered = self.store.recover_interrupted_tasks()
        if recovered:
            logger.info("TaskOrchestrator initialized: safely recovered %d interrupted tasks.", recovered)

    # =========================================================================
    # Task Lifecycle Management
    # =========================================================================

    def create_task(
        self,
        query: str,
        device_id: str,
        request_id: str | None = None,
        require_approval: bool = False,
        risk_ceiling: str = "MEDIUM",
    ) -> OrchestratedTask:
        """Initializes a new OrchestratedTask or returns cached task if idempotent request_id matches."""
        req_id = request_id or str(uuid.uuid4())

        # Idempotency check
        existing = self.store.get_task_by_request_id(req_id)
        active_or_completed = (
            TaskStatus.QUEUED,
            TaskStatus.PLANNING,
            TaskStatus.AWAITING_APPROVAL,
            TaskStatus.EXECUTING,
            TaskStatus.PAUSED,
            TaskStatus.VERIFYING,
            TaskStatus.COMPLETED,
        )
        if existing and existing.status in active_or_completed:
            logger.info("Idempotent hit for request_id: %s (task: %s)", req_id, existing.task_id)
            return existing


        task_id = f"task_{uuid.uuid4().hex[:12]}"
        now = _utc_now_iso()

        task = OrchestratedTask(
            task_id=task_id,
            request_id=req_id,
            device_id=device_id,
            query=query,
            status=TaskStatus.QUEUED,
            created_at=now,
            actor=device_id,
        )

        self.store.save_task(task)
        self.metrics.record_task_started()
        logger.info("Created OrchestratedTask [%s] for query: %s", task_id, query)
        return task

    async def plan_task(
        self,
        task: OrchestratedTask,
        event_sink: Any | None = None,
    ) -> Plan:
        """Decompose query into plan, evaluate initial risk, and validate integrity."""
        task.status = TaskStatus.PLANNING
        self.store.save_task(task)

        if event_sink:
            await event_sink(
                WebSocketEvent(
                    event_type="task.planning",
                    data={"task_id": task.task_id, "query": task.query},
                )
            )

        try:
            plan = self.planner.plan_for_goal(task.query)
            task.plan = plan
            task.progress = TaskProgress(
                total_steps=len(plan.steps),
                completed_steps=0,
                current_step_id=plan.steps[0].step_id if plan.steps else None,
                current_step_description=plan.steps[0].description if plan.steps else None,
                percent=0.0,
            )
            self.store.save_task(task)
            return plan
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = f"Planning failed: {e}"
            self.store.save_task(task)
            self.metrics.record_task_failed()
            logger.error("Planning failed for task %s: %s", task.task_id, e)
            raise

    # =========================================================================
    # Task Execution Loop
    # =========================================================================

    async def execute_task(
        self,
        task_id: str,
        event_sink: Any | None = None,
        approved_hash: str | None = None,
    ) -> TaskResult:
        """Executes the multi-step plan through the authoritative execution loop."""
        task = self.store.get_task(task_id)
        if not task:
            raise ValidationError(f"Task '{task_id}' not found.")

        if not task.plan:
            await self.plan_task(task, event_sink=event_sink)

        plan = task.plan
        if not plan:
            raise ValidationError(f"Task '{task_id}' has no plan to execute.")

        # Plan Integrity Check
        current_hash = plan.compute_plan_hash()
        if not plan.plan_hash:
            plan.plan_hash = current_hash
        target_approved_hash = approved_hash or plan.plan_hash
        if current_hash != target_approved_hash:
            raise PlanDriftError(
                f"Plan drift detected for task {task_id}: current hash {current_hash} != approved {target_approved_hash}",
                plan_id=plan.plan_id,
                expected_hash=target_approved_hash,
                observed_hash=current_hash,
                drift_reason="Plan step parameters modified after validation/approval.",
            )


        # Initialize loop detector and execution context
        loop_detector = LoopDetector()
        start_time = time.perf_counter()
        task.status = TaskStatus.EXECUTING
        task.started_at = _utc_now_iso()
        self.store.save_task(task)

        # Begin atomic transaction for any potential filesystem mutations
        self.tx_mgr.begin(tx_id=task.task_id, description=task.query)

        if event_sink:
            await event_sink(
                WebSocketEvent(
                    event_type="task.step.started",
                    data={
                        "task_id": task.task_id,
                        "status": "EXECUTING",
                        "total_steps": len(plan.steps),
                    },
                )
            )

        completed_steps = 0
        total_steps = len(plan.steps)
        warnings: list[str] = []
        sources: list[str] = []

        try:
            for step_idx, step in enumerate(plan.steps):
                task.current_step_index = step_idx
                task.progress.current_step_id = step.step_id
                task.progress.current_step_description = step.description
                task.progress.percent = round((completed_steps / total_steps) * 100.0, 1)
                self.store.save_task(task)

                # 1. Check for cancellation request
                if task.cancellation_requested:
                    logger.warning("Task %s cancellation detected prior to step %d", task.task_id, step.step_id)
                    await self._handle_cancellation(task, event_sink)
                    return self._build_result(task, completed_steps, total_steps, start_time, warnings, sources)

                # 2. Check for pause state
                if task.status == TaskStatus.PAUSED:
                    logger.info("Task %s is paused. Waiting for resume signal...", task.task_id)
                    resume_evt = self._get_resume_event(task.task_id)
                    await resume_evt.wait()
                    resume_evt.clear()
                    task.status = TaskStatus.EXECUTING
                    self.store.save_task(task)

                # 3. State-Aware Pre-Execution Check
                pre_ok, pre_reason = await self._check_preconditions(step)
                if not pre_ok:
                    logger.warning("Step %d precondition failed: %s. Attempting adaptive recovery...", step.step_id, pre_reason)
                    recovered = await self._attempt_adaptive_recovery(step, pre_reason)
                    if not recovered:
                        raise RuntimeError(f"Precondition failure at step {step.step_id}: {pre_reason}")

                # 4. Loop Detection Check
                is_blocked, loop_reason = loop_detector.check_loop()
                if is_blocked:
                    logger.error("Task %s blocked by LoopDetector: %s", task.task_id, loop_reason)
                    raise RuntimeError(f"TASK BLOCKED: {loop_reason}")

                # 5. Dynamic Risk Re-evaluation & Policy Enforcement
                decision, reason = self.permission_engine.evaluate(step.tool, step.args)
                step_risk = self.permission_engine.risk_evaluator.evaluate_tool(step.tool, step.args)

                # Check if approval is required dynamically
                requires_approval = (
                    step.requires_approval
                    or step_risk > plan.risk_ceiling
                    or (decision == PermissionDecision.ASK and getattr(task, "require_approval", False))
                )

                if requires_approval and task.approval_state != TaskApprovalState.APPROVED:
                    task.status = TaskStatus.AWAITING_APPROVAL
                    task.approval_state = TaskApprovalState.PENDING
                    app_req = StepApprovalRequest(
                        task_id=task.task_id,
                        step_id=step.step_id,
                        tool=step.tool,
                        args=step.args,
                        target=step.target,
                        risk_level=step_risk,
                        reason=reason or f"Operation requires approval ({step_risk.value})",
                        expires_at=datetime.fromtimestamp(time.time() + 300, timezone.utc).isoformat(),
                    )
                    task.pending_approval = app_req
                    self.store.save_task(task)
                    self.metrics.record_approval_request()

                    if event_sink:
                        await event_sink(
                            WebSocketEvent(
                                event_type="task.approval_required",
                                data={
                                    "task_id": task.task_id,
                                    "step_id": step.step_id,
                                    "tool": step.tool,
                                    "risk_level": step_risk.value,
                                    "reason": app_req.reason,
                                },
                            )
                        )

                    # Await user approval event with timeout
                    app_evt = self._get_approval_event(task.task_id)
                    try:
                        await asyncio.wait_for(app_evt.wait(), timeout=self.approval_timeout)
                    except asyncio.TimeoutError:
                        task.status = TaskStatus.FAILED
                        task.error = f"Step {step.step_id} approval request timed out."
                        self.store.save_task(task)
                        raise TimeoutError(task.error)
                    finally:
                        app_evt.clear()

                    task = self.store.get_task(task.task_id) or task
                    if task.approval_state != TaskApprovalState.APPROVED:

                        self.metrics.record_approval_denied()
                        raise PermissionDeniedError(
                            f"Step {step.step_id} ({step.tool}) approval was denied by user.",
                            tool_name=step.tool,
                            risk_level=step_risk.value,
                        )

                    task.status = TaskStatus.EXECUTING
                    task.pending_approval = None
                    self.store.save_task(task)

                # 6. Execute step with Bounded Retries
                step.status = PlanStepStatus.RUNNING
                tool_result, obs = await self._execute_step_with_retries(
                    task=task,
                    step=step,
                    loop_detector=loop_detector,
                    event_sink=event_sink,
                )

                # 7. Record verified artifacts
                self._record_artifacts_from_step(task, step, tool_result, obs)

                step.status = PlanStepStatus.COMPLETED
                completed_steps += 1
                self.metrics.record_step_executed()

                task.progress.completed_steps = completed_steps
                task.progress.percent = round((completed_steps / total_steps) * 100.0, 1)
                self.store.save_task(task)

                # Compact context summary
                self._compact_context(task, step, obs)

                if event_sink:
                    await event_sink(
                        WebSocketEvent(
                            event_type="task.step.completed",
                            data={
                                "task_id": task.task_id,
                                "step_id": step.step_id,
                                "description": step.description,
                                "progress_percent": task.progress.percent,
                            },
                        )
                    )

            # 8. Holistic Final Plan Verification
            task.status = TaskStatus.VERIFYING
            self.store.save_task(task)
            final_ok, final_reason = await self.verifier.verify_final_plan(plan)
            if not final_ok:
                self.metrics.record_verification_failure()
                raise VerificationError(f"Holistic task verification failed: {final_reason}")

            # 9. Commit transaction
            self.tx_mgr.commit(task.task_id)

            # 10. Record outcome in persistent memory
            duration = time.perf_counter() - start_time
            task.status = TaskStatus.COMPLETED
            task.completed_at = _utc_now_iso()
            self.metrics.record_task_completed(duration)

            summary = f"Task completed successfully: executed and verified all {completed_steps} steps in {round(duration, 2)}s."
            result = TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                summary=summary,
                steps_completed=completed_steps,
                steps_failed=0,
                artifacts=task.artifacts,
                sources=sources,
                warnings=warnings,
                verification="passed",
                duration_seconds=round(duration, 3),
            )
            task.result = result
            self.store.save_task(task)

            # Record in execution memory
            self.memory.record_execution(
                ExecutionRecord(
                    record_id=f"exec_{task.task_id}",
                    task_id=task.task_id,
                    tool="task_orchestrator",
                    args_summary=task.query[:200],
                    outcome=summary[:200],
                    success=True,
                    verified=True,
                )
            )

            if event_sink:
                await event_sink(
                    WebSocketEvent(
                        event_type="task.completed",
                        data={
                            "task_id": task.task_id,
                            "status": "COMPLETED",
                            "summary": summary,
                            "duration_seconds": round(duration, 2),
                        },
                    )
                )

            return result

        except Exception as ex:
            duration = time.perf_counter() - start_time
            logger.error("Task execution failed for %s: %s. Initiating LIFO rollback...", task.task_id, ex)
            task.status = TaskStatus.FAILED
            task.error = str(ex)
            self.metrics.record_task_failed()

            # Execute transactional rollback for reversible mutations
            try:
                rolled_tx = self.tx_mgr.rollback(task.task_id)
                task.status = TaskStatus.ROLLED_BACK
                for s in plan.steps:
                    if s.status == PlanStepStatus.COMPLETED:
                        s.status = PlanStepStatus.ROLLED_BACK
                logger.info("Rollback completed cleanly for task %s", task.task_id)
            except Exception as rbe:
                logger.critical("Rollback failed for task %s: %s", task.task_id, rbe)

            res = TaskResult(
                task_id=task.task_id,
                status=task.status,
                summary=f"Execution failed at step {completed_steps + 1}: {ex}",
                steps_completed=completed_steps,
                steps_failed=total_steps - completed_steps,
                artifacts=task.artifacts,
                sources=sources,
                warnings=warnings,
                verification="failed",
                duration_seconds=round(duration, 3),
            )
            task.result = res
            self.store.save_task(task)

            if event_sink:
                await event_sink(
                    WebSocketEvent(
                        event_type="task.failed",
                        data={"task_id": task.task_id, "error": str(ex), "status": task.status.value},
                    )
                )

            return res

    # =========================================================================
    # Step Execution, Retries & Adaptive Recovery
    # =========================================================================

    async def _execute_step_with_retries(
        self,
        task: OrchestratedTask,
        step: PlanStep,
        loop_detector: LoopDetector,
        event_sink: Any | None = None,
    ) -> tuple[Any, Observation | None]:
        """Executes a single step with finite bounded retries and empirical verification."""
        max_attempts = getattr(step, "max_retries", 2)
        tool_entry = self.registry.get(step.tool)
        if not tool_entry or not tool_entry.handler:
            raise RuntimeError(f"Tool handler '{step.tool}' not found.")

        last_error: Exception | None = None

        while step.attempt_count <= max_attempts:
            step.attempt_count += 1
            try:
                # Prepare args with transaction id if needed
                args = dict(step.args)
                if getattr(tool_entry.metadata, "mutates_state", False):
                    args["tx_id"] = task.task_id

                # Tool invocation
                if inspect.iscoroutinefunction(tool_entry.handler):
                    tool_result = await tool_entry.handler(**args)
                else:
                    tool_result = tool_entry(**args)

                # Empirical verification
                ok, reason, obs = await self.verifier.verify_step(step, tool_result=tool_result)
                state_sig = obs.state if obs else "none"
                loop_detector.record_step(step.tool, step.args, state_signature=state_sig, success=ok)

                if not ok:
                    self.metrics.record_verification_failure()
                    raise VerificationError(
                        f"Empirical postcondition verification failed: {reason}",
                        expected=step.expected_postcondition,
                        observed=tool_result,
                    )

                return tool_result, obs

            except Exception as e:
                last_error = e
                step.last_error = str(e)
                self.metrics.record_step_retried()

                # Record retry attempt telemetry
                retry_rec = StepRetryRecord(
                    step_id=step.step_id,
                    attempt=step.attempt_count,
                    error=str(e),
                    recovered=False,
                )
                task.retry_history.append(retry_rec)
                self.store.save_task(task)

                # Classify failure
                classification = self._classify_failure(e)
                if classification != FailureClassification.RECOVERABLE or step.attempt_count > max_attempts:
                    logger.error("Step %d execution halted: %s (attempts: %d/%d)", step.step_id, e, step.attempt_count, max_attempts)
                    raise

                # Controlled backoff delay
                backoff_s = min(0.5 * (2 ** (step.attempt_count - 1)), 2.0)
                logger.warning(
                    "Step %d failed (%s). Retrying (attempt %d/%d) after %0.2fs backoff...",
                    step.step_id,
                    e,
                    step.attempt_count,
                    max_attempts,
                    backoff_s,
                )

                if event_sink:
                    await event_sink(
                        WebSocketEvent(
                            event_type="task.retrying",
                            data={
                                "task_id": task.task_id,
                                "step_id": step.step_id,
                                "attempt": step.attempt_count,
                                "error": str(e),
                            },
                        )
                    )

                await asyncio.sleep(backoff_s)

        raise last_error or RuntimeError(f"Step {step.step_id} failed after {max_attempts} attempts.")

    def _classify_failure(self, error: Exception) -> FailureClassification:
        """Classify failures into Recoverable vs Non-recoverable."""
        err_msg = str(error).lower()
        if isinstance(error, (PermissionDeniedError, PlanDriftError, RollbackFailedError, ConflictError)):
            return FailureClassification.NON_RECOVERABLE

        if any(term in err_msg for term in ["escapes", "boundary", "conflict", "denied", "forbidden", "unauthorized", "security violation"]):
            return FailureClassification.NON_RECOVERABLE

        # Transient, recoverable errors
        if any(term in err_msg for term in ["timeout", "closed", "not found", "stale", "focus", "temporary", "busy", "verification"]):
            return FailureClassification.RECOVERABLE

        return FailureClassification.RECOVERABLE


    async def _check_preconditions(self, step: PlanStep) -> tuple[bool, str]:
        """State-aware check verifying environmental assumptions hold before step execution."""
        # If step assumes a window or tab, verify it is still open
        if step.domain == "WINDOWS" and "hwnd" in step.args:
            hwnd = step.args["hwnd"]
            # Check via window controller if available
            if hasattr(self.observer, "win_ctrl") and hasattr(self.observer.win_ctrl, "get_foreground_window"):
                fg = self.observer.win_ctrl.get_foreground_window()
                if fg and fg.hwnd == hwnd:
                    return True, "Preconditions satisfied."
            import ctypes
            try:
                if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32") and not ctypes.windll.user32.IsWindow(hwnd):
                    return False, f"Target window HWND:{hwnd} was closed unexpectedly."
            except Exception:
                pass

        return True, "Preconditions satisfied."

    async def _attempt_adaptive_recovery(self, step: PlanStep, reason: str) -> bool:
        """Attempt controlled recovery from transient state drift."""
        # If window closed, see if we can re-acquire or re-launch
        if "closed unexpectedly" in reason and "app_name" in step.args:
            logger.info("Adaptive recovery: re-launching target application '%s'", step.args["app_name"])
            tool_entry = self.registry.get("computer.launch_application")
            if tool_entry:
                tool_entry(app_name_or_path=step.args["app_name"], wait_for_window=True)
                return True
        return False

    # =========================================================================
    # Control Actions: Pause, Resume, Cancel, Approval
    # =========================================================================

    def pause_task(self, task_id: str, reason: str = "User initiated pause") -> bool:
        """Safely pause active execution."""
        task = self.store.get_task(task_id)
        pausable = (TaskStatus.QUEUED, TaskStatus.EXECUTING, TaskStatus.PLANNING, TaskStatus.AWAITING_APPROVAL)
        if not task or task.status not in pausable:
            return False

        task.status = TaskStatus.PAUSED
        task.pause_reason = reason
        self.store.save_task(task)
        logger.info("Paused task %s: %s", task_id, reason)
        return True

    def resume_task(self, task_id: str) -> bool:
        """Resume paused task execution from validated state."""
        task = self.store.get_task(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return False

        task.status = TaskStatus.EXECUTING
        task.pause_reason = None
        self.store.save_task(task)

        # Trigger resume event
        if task_id in self._resume_events:
            self._resume_events[task_id].set()

        logger.info("Resumed task %s", task_id)
        return True

    def cancel_task(self, task_id: str, reason: str = "User initiated cancellation") -> bool:
        """Cancel an in-flight or pending task and stop execution safely."""
        task = self.store.get_task(task_id)
        if not task:
            return False

        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return False

        task.cancellation_requested = True
        task.cancellation_reason = reason
        task.status = TaskStatus.CANCELLED

        # Cancel active asyncio handle if bound
        handle = self._async_handles.pop(task_id, None)
        if handle and not handle.done():
            handle.cancel()

        self.store.save_task(task)
        self.metrics.record_task_cancelled()
        logger.info("Directly marked task %s for cancellation: %s", task_id, reason)
        return True

    def approve_step(self, task_id: str, step_id: int, approved: bool, reason: str | None = None) -> bool:
        """Submit approval decision for a pending high-risk step."""
        task = self.store.get_task(task_id)
        if not task or task.status != TaskStatus.AWAITING_APPROVAL:
            return False

        if task.pending_approval and task.pending_approval.step_id == step_id:
            task.approval_state = TaskApprovalState.APPROVED if approved else TaskApprovalState.REJECTED
            task.pending_approval.approved_by = "user"
            if approved:
                task.status = TaskStatus.EXECUTING
            self.store.save_task(task)

            # Fire approval event
            if task_id in self._approval_events:
                self._approval_events[task_id].set()

            logger.info("Step %d approval decision (%s) recorded for task %s", step_id, approved, task_id)
            return True

        return False

    # =========================================================================
    # Helpers
    # =========================================================================

    def _get_resume_event(self, task_id: str) -> asyncio.Event:
        if task_id not in self._resume_events:
            self._resume_events[task_id] = asyncio.Event()
        return self._resume_events[task_id]

    def _get_approval_event(self, task_id: str) -> asyncio.Event:
        if task_id not in self._approval_events:
            self._approval_events[task_id] = asyncio.Event()
        return self._approval_events[task_id]

    async def _handle_cancellation(self, task: OrchestratedTask, event_sink: Any | None) -> None:
        """Safely rolls back state and finalizes task cancellation."""
        self.tx_mgr.rollback(task.task_id)
        task.status = TaskStatus.CANCELLED
        task.completed_at = _utc_now_iso()
        self.store.save_task(task)

        if event_sink:
            await event_sink(
                WebSocketEvent(
                    event_type="task.cancelled",
                    data={"task_id": task.task_id, "reason": task.cancellation_reason},
                )
            )

    def _record_artifacts_from_step(
        self,
        task: OrchestratedTask,
        step: PlanStep,
        tool_result: Any,
        obs: Observation | None,
    ) -> None:
        """Extract and record verifiable task output artifacts."""
        if step.tool in ("create_file", "edit_file"):
            file_path = step.target or step.args.get("file_path")
            if file_path:
                art = TaskArtifact(
                    artifact_id=f"art_{uuid.uuid4().hex[:8]}",
                    type="file",
                    path=str(file_path),
                    source=step.tool,
                    task_id=task.task_id,
                    verification_state="verified" if obs and obs.state == "exists" else "unverified",
                    metadata={"size_bytes": obs.relevant_attributes.get("size_bytes", 0) if obs else 0},
                )
                task.artifacts.append(art)

        elif step.tool == "browser_extract":
            art = TaskArtifact(
                artifact_id=f"art_{uuid.uuid4().hex[:8]}",
                type="browser_result",
                path=None,
                source="browser_extract",
                task_id=task.task_id,
                verification_state="verified",
                metadata={"url": step.target},
            )
            task.artifacts.append(art)

        elif step.tool == "computer.screenshot":
            art = TaskArtifact(
                artifact_id=f"art_{uuid.uuid4().hex[:8]}",
                type="screenshot",
                path=None,
                source="computer.screenshot",
                task_id=task.task_id,
                verification_state="verified",
                metadata={"timestamp": _utc_now_iso()},
            )
            task.artifacts.append(art)

    def _compact_context(self, task: OrchestratedTask, step: PlanStep, obs: Observation | None) -> None:
        """Appends bounded operational step summaries, discarding raw unbounded payloads."""
        obs_state = obs.state if obs else "completed"
        summary = f"Step {step.step_id} ({step.tool}): {obs_state}"
        task.context_summary.append(summary)
        # Keep maximum 15 context summary items
        if len(task.context_summary) > 15:
            task.context_summary = task.context_summary[-15:]

    def _build_result(
        self,
        task: OrchestratedTask,
        completed_steps: int,
        total_steps: int,
        start_time: float,
        warnings: list[str],
        sources: list[str],
    ) -> TaskResult:
        duration = time.perf_counter() - start_time
        return TaskResult(
            task_id=task.task_id,
            status=task.status,
            summary=f"Task cancelled by user ({completed_steps}/{total_steps} steps completed).",
            steps_completed=completed_steps,
            steps_failed=0,
            artifacts=task.artifacts,
            sources=sources,
            warnings=warnings,
            verification="cancelled",
            duration_seconds=round(duration, 3),
        )
