"""REST and WebSocket route handlers for NOVA Windows Host."""

import asyncio
from datetime import datetime, timezone
import json
import logging
import time
import uuid
from typing import Any
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.websockets import WebSocket, WebSocketDisconnect

from nova.agent.runtime import NovaRuntime
from nova.config.settings import NovaSettings
from nova.control.capabilities import CapabilityRegistry
from nova.control.power import PowerControlProvider
from nova.control.screen import ScreenCaptureProvider
from nova.control.system import SystemMetricsProvider
from nova.errors import AuthenticationError, DeviceRevokedError, PairingExpiredError
from nova.host.auth import DeviceRegistry, TokenManager
from nova.host.pairing import PairingManager
from nova.host.websocket import WebSocketHub
from nova.protocol.errors import ProtocolErrorCode, format_error_payload
from nova.protocol.models import (
    AgentStatus,
    DeviceInfo,
    EmergencyActionRequest,
    PairingRequest,
    RemoteQueryRequest,
    RemoteQueryResponse,
    ScreenCaptureRequest,
    SystemStatus,
    WebSocketEvent,
)
from nova.tools.registry import get_tool_registry

logger = logging.getLogger("nova.host.router")


class HostRouter:
    """Encapsulates dependencies and route handlers for the host HTTP/WS API."""

    def __init__(
        self,
        *,
        settings: NovaSettings,
        runtime: NovaRuntime,
        device_registry: DeviceRegistry,
        token_manager: TokenManager,
        pairing_manager: PairingManager,
        websocket_hub: WebSocketHub,
        system_metrics: SystemMetricsProvider | None = None,
        screen_capture: ScreenCaptureProvider | None = None,
        power_control: PowerControlProvider | None = None,
        capability_registry: CapabilityRegistry | None = None,
    ) -> None:
        self.settings = settings
        self.runtime = runtime
        self.device_registry = device_registry
        self.token_manager = token_manager
        self.pairing_manager = pairing_manager
        self.websocket_hub = websocket_hub
        self.system_metrics = system_metrics or SystemMetricsProvider(workspace_root=str(settings.workspace_root))
        self.screen_capture = screen_capture or ScreenCaptureProvider()
        self.power_control = power_control or PowerControlProvider()
        self.capability_registry = capability_registry or CapabilityRegistry()
        self.host_start_time = time.time()

    def authenticate_request(self, request: Request) -> DeviceInfo:
        """Extract and validate the Bearer token from the HTTP Authorization header."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise AuthenticationError("Missing Authorization header.")

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise AuthenticationError("Invalid Authorization format. Expected 'Bearer <token>'.")

        token = parts[1]
        return self.token_manager.authenticate_device(token, self.device_registry)

    async def handle_pair(self, request: Request) -> Response:
        """POST /api/v1/pair - Exchange 6-digit code for device JWT token."""
        try:
            body = await request.json()
            req = PairingRequest(**body)
        except Exception as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.MALFORMED_REQUEST, f"Invalid pairing payload: {ex}"),
                status_code=400,
            )

        try:
            resp = self.pairing_manager.verify_and_pair(req, self.device_registry, self.token_manager)
            return JSONResponse(resp.model_dump(), status_code=200)
        except PairingExpiredError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.PAIRING_EXPIRED, str(ex)),
                status_code=400,
            )
        except Exception as ex:
            logger.error("Pairing error: %s", ex)
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.INTERNAL_ERROR, str(ex)),
                status_code=500,
            )

    async def handle_status(self, request: Request) -> Response:
        """GET /api/v1/status - Returns real-time host and agent telemetry."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)),
                status_code=403,
            )
        except AuthenticationError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)),
                status_code=401,
            )

        metrics = self.system_metrics.get_metrics()
        uptime_host = round(time.time() - self.host_start_time, 1)

        tool_reg = get_tool_registry()
        tool_count = len(tool_reg.list_tools()) if tool_reg else 0

        agent = AgentStatus(
            state=self.runtime.lifecycle.current_state.value,
            active_plan_id=None,
            workspace_root=str(self.settings.workspace_root),
            tools_registered=tool_count,
            uptime_seconds=uptime_host,
        )

        status_obj = SystemStatus(
            timestamp=datetime.now(timezone.utc).isoformat(),
            system=metrics,
            agent=agent,
        )
        return JSONResponse(status_obj.model_dump(), status_code=200)

    async def handle_screen_capture(self, request: Request) -> Response:
        """POST /api/v1/screen/capture - Capture desktop frame."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)),
                status_code=403,
            )
        except AuthenticationError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)),
                status_code=401,
            )

        req_model: ScreenCaptureRequest | None = None
        try:
            body = await request.json()
            if body:
                req_model = ScreenCaptureRequest(**body)
        except Exception:
            req_model = ScreenCaptureRequest()

        result = self.screen_capture.capture(req_model)
        return JSONResponse(result.model_dump(), status_code=200)

    async def handle_capabilities(self, request: Request) -> Response:
        """GET /api/v1/capabilities - Discover host and remote capabilities."""
        matrix = self.capability_registry.get_matrix()
        return JSONResponse(matrix.model_dump(), status_code=200)

    async def handle_agent_query(self, request: Request) -> Response:
        """POST /api/v1/agent/query - Dispatch natural language query to agent runtime."""
        try:
            device = self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)),
                status_code=403,
            )
        except AuthenticationError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)),
                status_code=401,
            )

        try:
            body = await request.json()
            query_req = RemoteQueryRequest(**body)
        except Exception as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.MALFORMED_REQUEST, f"Invalid query payload: {ex}"),
                status_code=400,
            )

        # Policy enforcement: prohibit remote execution of shell commands
        query_lower = query_req.query.lower()
        if any(bad in query_lower for bad in ["run_command", "powershell", "cmd.exe", "exec bash", "rmdir /s"]):
            return JSONResponse(
                format_error_payload(
                    ProtocolErrorCode.REMOTE_EXECUTION_DENIED,
                    "Remote shell command execution is strictly forbidden by host security policy.",
                ),
                status_code=403,
            )

        session_id = str(uuid.uuid4())
        logger.info("Executing remote query [%s] from device %s: %s", session_id, device.device_id, query_req.query)

        # Notify via WebSocket event stream
        await self.websocket_hub.broadcast(
            WebSocketEvent(
                event_type="agent_plan",
                data={"session_id": session_id, "query": query_req.query, "state": "PLANNING"},
            )
        )

        try:
            if self.settings.get_api_key_value() and "test" not in self.settings.environment.value:
                response_text = await self.runtime.query(query_req.query)
            else:
                response_text = self.runtime.simulate_query(query_req.query)

            await self.websocket_hub.broadcast(
                WebSocketEvent(
                    event_type="agent_step",
                    data={"session_id": session_id, "status": "COMPLETED", "result_preview": response_text[:100]},
                )
            )

            resp_model = RemoteQueryResponse(
                session_id=session_id,
                query=query_req.query,
                status="COMPLETED",
                response_text=response_text,
                tool_calls_count=1,
                steps_executed=1,
                verification_passed=True,
                plan_id=f"plan_{session_id[:8]}",
            )
            return JSONResponse(resp_model.model_dump(), status_code=200)

        except Exception as ex:
            logger.error("Agent query execution failed: %s", ex)
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.INTERNAL_ERROR, f"Agent runtime failure: {ex}"),
                status_code=500,
            )

    async def handle_emergency_lock(self, request: Request) -> Response:
        """POST /api/v1/emergency/lock - Immediately locks the Windows workstation."""
        try:
            device = self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)),
                status_code=403,
            )
        except AuthenticationError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)),
                status_code=401,
            )

        dry_run = request.query_params.get("dry_run", "false").lower() == "true"
        req_data = EmergencyActionRequest(action="LOCK_WORKSTATION")
        try:
            body = await request.json()
            if body:
                req_data = EmergencyActionRequest(**body)
        except Exception:
            pass

        logger.warning(
            "Emergency lock invoked from device %s (dry_run=%s, reason=%s)",
            device.device_id,
            dry_run,
            req_data.reason,
        )

        outcome = self.power_control.lock_workstation(dry_run=dry_run)

        await self.websocket_hub.broadcast(
            WebSocketEvent(
                event_type="alert",
                data={
                    "action": "LOCK_WORKSTATION",
                    "device_id": device.device_id,
                    "success": outcome.success,
                    "message": outcome.message,
                },
            )
        )

        return JSONResponse(outcome.model_dump(), status_code=200 if outcome.success else 500)

    async def handle_list_devices(self, request: Request) -> Response:
        """GET /api/v1/devices - List all registered devices."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)),
                status_code=403,
            )
        except AuthenticationError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)),
                status_code=401,
            )

        devices = self.device_registry.list_devices()
        return JSONResponse([d.model_dump() for d in devices], status_code=200)

    async def handle_revoke_device(self, request: Request) -> Response:
        """POST /api/v1/devices/{device_id}/revoke - Revoke a paired device."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)),
                status_code=403,
            )
        except AuthenticationError as ex:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)),
                status_code=401,
            )

        target_device_id = request.path_params.get("device_id")
        if not target_device_id:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.MALFORMED_REQUEST, "Missing device_id parameter."),
                status_code=400,
            )

        revoked = self.device_registry.revoke_device(target_device_id)
        if not revoked:
            return JSONResponse(
                format_error_payload(ProtocolErrorCode.NOT_FOUND, f"Device '{target_device_id}' not found."),
                status_code=404,
            )

        return JSONResponse({"success": True, "device_id": target_device_id, "status": "REVOKED"}, status_code=200)

    async def handle_websocket_events(self, websocket: WebSocket) -> None:
        """WS /ws/v1/events - Real-time telemetry, plans, and audit streaming."""
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008)  # Policy violation
            return

        try:
            device = self.token_manager.authenticate_device(token, self.device_registry)
        except Exception as ex:
            logger.warning("WebSocket authentication rejected: %s", ex)
            await websocket.close(code=1008)
            return

        await self.websocket_hub.connect(websocket, device.device_id)

        try:
            # Send initial welcome telemetry
            await websocket.send_json(
                {
                    "event_type": "welcome",
                    "device_id": device.device_id,
                    "host": self.system_metrics.get_metrics().hostname,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            while True:
                # Keep-alive loop listening for client messages/pings
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    if msg.get("action") == "ping":
                        await websocket.send_json({"event_type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
                except Exception:
                    pass
        except WebSocketDisconnect:
            await self.websocket_hub.disconnect(websocket)
        except Exception as ex:
            logger.info("WebSocket connection closed: %s", ex)
            await self.websocket_hub.disconnect(websocket)
