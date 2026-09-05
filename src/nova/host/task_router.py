"""REST route handlers for NOVA Phase 09 Agentic Task Orchestration API."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from nova.config.settings import NovaSettings
from nova.errors import AuthenticationError, DeviceRevokedError
from nova.host.auth import DeviceRegistry, TokenManager
from nova.host.websocket import WebSocketHub
from nova.orchestration.engine import TaskOrchestrator
from nova.orchestration.metrics import get_task_metrics
from nova.orchestration.models import OrchestratedTask
from nova.protocol.errors import ProtocolErrorCode, format_error_payload
from nova.protocol.models import (
    PROTOCOL_VERSION,
    StepApprovalRemoteRequest,
    StepApprovalRemoteResponse,
    TaskActionRequest,
    TaskActionResponse,
    TaskCreateRequest,
    TaskDetailResponse,
    TaskMetricsResponse,
    TaskStatus,
    TaskStepResponse,
    TaskStepsListResponse,
)

logger = logging.getLogger("nova.host.task_router")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_task_detail(task: OrchestratedTask) -> TaskDetailResponse:
    plan = task.plan
    total_steps = len(plan.steps) if plan else 0
    artifacts_data = [a.model_dump() for a in task.artifacts]

    pending_app_data = None
    if task.pending_approval:
        pending_app_data = task.pending_approval.model_dump()

    return TaskDetailResponse(
        task_id=task.task_id,
        request_id=task.request_id,
        device_id=task.device_id,
        query=task.query,
        status=task.status,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        current_step_index=task.current_step_index,
        total_steps=total_steps,
        completed_steps=task.progress.completed_steps,
        progress_percent=task.progress.percent,
        current_step_description=task.progress.current_step_description,
        risk_level=task.risk_level.value,
        approval_state=task.approval_state.value,
        pending_approval=pending_app_data,
        response_text=task.result.summary if task.result else None,
        error=task.error,
        artifacts=artifacts_data,
        duration_seconds=task.result.duration_seconds if task.result else 0.0,
        protocol_version=PROTOCOL_VERSION,
    )


class TaskRouter:
    """Encapsulates HTTP endpoints for multi-step agentic task orchestration."""

    def __init__(
        self,
        *,
        settings: NovaSettings,
        device_registry: DeviceRegistry,
        token_manager: TokenManager,
        orchestrator: TaskOrchestrator | None = None,
        websocket_hub: WebSocketHub | None = None,
    ) -> None:
        self.settings = settings
        self.device_registry = device_registry
        self.token_manager = token_manager
        self.orchestrator = orchestrator or TaskOrchestrator(settings=settings)
        self.websocket_hub = websocket_hub or WebSocketHub()

    def authenticate_request(self, request: Request) -> Any:
        """Extract and validate the Bearer token."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise AuthenticationError("Missing Authorization header.")

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise AuthenticationError("Invalid Authorization format. Expected 'Bearer <token>'.")

        token = parts[1]
        return self.token_manager.authenticate_device(token, self.device_registry)

    async def handle_create_task(self, request: Request) -> Response:
        """POST /api/v1/tasks - Create and begin execution of an orchestrated task."""
        try:
            device = self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        try:
            body = await request.json()
            req = TaskCreateRequest(**body)
        except Exception as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.MALFORMED_REQUEST, str(ex)), status_code=400)

        # Prohibit arbitrary shell execution attempts
        query_lower = req.query.lower()
        if any(bad in query_lower for bad in ["run_command", "powershell", "cmd.exe", "exec bash", "rmdir /s"]):
            return JSONResponse(
                format_error_payload(
                    ProtocolErrorCode.REMOTE_EXECUTION_DENIED,
                    "Remote shell command execution is strictly forbidden by host security policy.",
                ),
                status_code=403,
            )

        task = self.orchestrator.create_task(
            query=req.query,
            device_id=device.device_id,
            request_id=req.request_id,
            require_approval=req.require_approval,
            risk_ceiling=req.risk_ceiling,
        )

        # Spawn asynchronous execution
        async def _run() -> None:
            try:
                await self.orchestrator.execute_task(
                    task.task_id,
                    event_sink=self.websocket_hub.broadcast,
                )
            except Exception as e:
                logger.error("Async execution of task %s failed: %s", task.task_id, e)

        exec_task = asyncio.create_task(_run())
        self.orchestrator._async_handles[task.task_id] = exec_task

        resp = _format_task_detail(task)
        return JSONResponse(resp.model_dump(), status_code=202)

    async def handle_list_tasks(self, request: Request) -> Response:
        """GET /api/v1/tasks - Enumerate recent tasks with status filter."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        status_param = request.query_params.get("status")
        status_filter = TaskStatus(status_param) if status_param in TaskStatus._value2member_map_ else None
        limit = int(request.query_params.get("limit", 50))

        tasks = self.orchestrator.store.list_tasks(status=status_filter, limit=limit)
        results = [_format_task_detail(t).model_dump() for t in tasks]
        return JSONResponse(results, status_code=200)

    async def handle_get_task(self, request: Request) -> Response:
        """GET /api/v1/tasks/{task_id} - Inspect comprehensive task details."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        task_id = request.path_params.get("task_id")
        task = self.orchestrator.store.get_task(task_id) if task_id else None
        if not task:
            return JSONResponse(format_error_payload(ProtocolErrorCode.TASK_NOT_FOUND, f"Task '{task_id}' not found."), status_code=404)

        resp = _format_task_detail(task)
        return JSONResponse(resp.model_dump(), status_code=200)

    async def handle_pause_task(self, request: Request) -> Response:
        """POST /api/v1/tasks/{task_id}/pause - Safely pause an active task."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        task_id = request.path_params.get("task_id", "")
        success = self.orchestrator.pause_task(task_id, reason="User paused via API")
        task = self.orchestrator.store.get_task(task_id)

        if not success or not task:
            return JSONResponse(format_error_payload(ProtocolErrorCode.TASK_NOT_FOUND, f"Task '{task_id}' cannot be paused."), status_code=400)

        resp = TaskActionResponse(
            task_id=task_id,
            status=task.status,
            success=True,
            message="Task paused safely.",
        )
        return JSONResponse(resp.model_dump(), status_code=200)

    async def handle_resume_task(self, request: Request) -> Response:
        """POST /api/v1/tasks/{task_id}/resume - Resume execution of a paused task."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        task_id = request.path_params.get("task_id", "")
        success = self.orchestrator.resume_task(task_id)
        task = self.orchestrator.store.get_task(task_id)

        if not success or not task:
            return JSONResponse(format_error_payload(ProtocolErrorCode.TASK_NOT_FOUND, f"Task '{task_id}' cannot be resumed."), status_code=400)

        resp = TaskActionResponse(
            task_id=task_id,
            status=task.status,
            success=True,
            message="Task resumed successfully.",
        )
        return JSONResponse(resp.model_dump(), status_code=200)

    async def handle_cancel_task(self, request: Request) -> Response:
        """POST /api/v1/tasks/{task_id}/cancel - Abort in-flight task."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        task_id = request.path_params.get("task_id", "")
        success = self.orchestrator.cancel_task(task_id, reason="User cancelled via API")
        task = self.orchestrator.store.get_task(task_id)

        if not success or not task:
            return JSONResponse(format_error_payload(ProtocolErrorCode.TASK_NOT_FOUND, f"Task '{task_id}' not found or already finished."), status_code=404)

        resp = TaskActionResponse(
            task_id=task_id,
            status=task.status,
            success=True,
            message="Task has been cancelled.",
        )
        return JSONResponse(resp.model_dump(), status_code=200)

    async def handle_get_task_steps(self, request: Request) -> Response:
        """GET /api/v1/tasks/{task_id}/steps - List plan steps with status and verification."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        task_id = request.path_params.get("task_id", "")
        task = self.orchestrator.store.get_task(task_id)
        if not task:
            return JSONResponse(format_error_payload(ProtocolErrorCode.TASK_NOT_FOUND, f"Task '{task_id}' not found."), status_code=404)

        steps_data: list[TaskStepResponse] = []
        if task.plan:
            for s in task.plan.steps:
                steps_data.append(
                    TaskStepResponse(
                        step_id=s.step_id,
                        description=s.description,
                        tool=s.tool,
                        status=s.status.value,
                        risk_level=s.risk_level.value,
                        attempt_count=s.attempt_count,
                        requires_approval=s.requires_approval,
                        domain=s.domain,
                        reversibility=s.reversibility,
                        error=s.last_error,
                    )
                )

        resp = TaskStepsListResponse(task_id=task_id, steps=steps_data, total=len(steps_data))
        return JSONResponse(resp.model_dump(), status_code=200)

    async def handle_approve_step(self, request: Request) -> Response:
        """POST /api/v1/tasks/{task_id}/approve - Approve pending step."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        task_id = request.path_params.get("task_id", "")
        try:
            body = await request.json()
            step_id = body.get("step_id", 1)
        except Exception:
            step_id = 1

        success = self.orchestrator.approve_step(task_id, step_id=step_id, approved=True)
        task = self.orchestrator.store.get_task(task_id)

        if not success or not task:
            return JSONResponse(format_error_payload(ProtocolErrorCode.TASK_NOT_FOUND, "No pending approval for this step."), status_code=400)

        resp = StepApprovalRemoteResponse(
            task_id=task_id,
            step_id=step_id,
            approved=True,
            status=task.status,
            message="Step approval granted. Resuming execution.",
        )
        return JSONResponse(resp.model_dump(), status_code=200)

    async def handle_deny_step(self, request: Request) -> Response:
        """POST /api/v1/tasks/{task_id}/deny - Deny pending step."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        task_id = request.path_params.get("task_id", "")
        try:
            body = await request.json()
            step_id = body.get("step_id", 1)
        except Exception:
            step_id = 1

        success = self.orchestrator.approve_step(task_id, step_id=step_id, approved=False)
        task = self.orchestrator.store.get_task(task_id)

        if not success or not task:
            return JSONResponse(format_error_payload(ProtocolErrorCode.TASK_NOT_FOUND, "No pending approval for this step."), status_code=400)

        resp = StepApprovalRemoteResponse(
            task_id=task_id,
            step_id=step_id,
            approved=False,
            status=task.status,
            message="Step approval denied. Halting execution safely.",
        )
        return JSONResponse(resp.model_dump(), status_code=200)

    async def handle_task_metrics(self, request: Request) -> Response:
        """GET /api/v1/tasks/metrics - Operational telemetry counters."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        metrics = get_task_metrics()
        resp = TaskMetricsResponse(**metrics.to_dict())
        return JSONResponse(resp.model_dump(), status_code=200)
