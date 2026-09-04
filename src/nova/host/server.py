"""ASGI application factory and server entry point for NOVA Windows Host."""

import asyncio
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route, WebSocketRoute
import uvicorn

from nova.agent.runtime import NovaRuntime
from nova.config.settings import NovaSettings, get_settings
from nova.control.capabilities import CapabilityRegistry
from nova.control.power import PowerControlProvider
from nova.control.screen import ScreenCaptureProvider
from nova.control.system import SystemMetricsProvider
from nova.host.auth import DeviceRegistry, TokenManager
from nova.host.pairing import PairingManager
from nova.host.router import HostRouter
from nova.host.tasks import TaskController
from nova.host.websocket import WebSocketHub
from nova.protocol.models import WebSocketEvent

logger = logging.getLogger("nova.host.server")


def create_host_app(
    settings: NovaSettings | None = None,
    runtime: NovaRuntime | None = None,
    device_registry: DeviceRegistry | None = None,
    token_manager: TokenManager | None = None,
    pairing_manager: PairingManager | None = None,
    websocket_hub: WebSocketHub | None = None,
    task_controller: TaskController | None = None,
    system_metrics: SystemMetricsProvider | None = None,
    screen_capture: ScreenCaptureProvider | None = None,
    power_control: PowerControlProvider | None = None,
    capability_registry: CapabilityRegistry | None = None,
    telemetry_interval: float = 3.0,
) -> Starlette:
    """Factory creating the production Starlette ASGI app for the Windows Host."""
    st = settings or get_settings()
    rt = runtime or NovaRuntime(settings=st)
    reg = device_registry or DeviceRegistry(st.devices_file)
    tok = token_manager or TokenManager(
        secret_key=st.host_secret.get_secret_value() if st.host_secret else None,
        key_file=st.data_dir / "host_secret.key",
    )
    pair = pairing_manager or PairingManager(default_ttl_seconds=st.pairing_code_ttl_seconds)
    hub = websocket_hub or WebSocketHub()
    tasks = task_controller or TaskController()
    metrics = system_metrics or SystemMetricsProvider(workspace_root=str(st.workspace_root))
    screen = screen_capture or ScreenCaptureProvider()
    power = power_control or PowerControlProvider()
    caps = capability_registry or CapabilityRegistry()

    router = HostRouter(
        settings=st,
        runtime=rt,
        device_registry=reg,
        token_manager=tok,
        pairing_manager=pair,
        websocket_hub=hub,
        task_controller=tasks,
        system_metrics=metrics,
        screen_capture=screen,
        power_control=power,
        capability_registry=caps,
    )

    # Periodic telemetry background task for connected WebSockets
    async def _telemetry_broadcaster():
        try:
            while True:
                await asyncio.sleep(telemetry_interval)
                if hub.active_count > 0:
                    current_metrics = metrics.get_metrics()
                    await hub.broadcast(
                        WebSocketEvent(
                            event_type="telemetry",
                            data=current_metrics.model_dump(),
                        )
                    )
        except asyncio.CancelledError:
            pass

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncGenerator[None, None]:
        task = asyncio.create_task(_telemetry_broadcaster())
        # Store instances in app state for access
        app.state.router = router
        app.state.pairing_manager = pair
        app.state.device_registry = reg
        app.state.token_manager = tok
        app.state.websocket_hub = hub
        app.state.task_controller = tasks
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    routes = [
        Route("/api/v1/health", router.handle_health, methods=["GET"]),
        Route("/api/v1/pair", router.handle_pair, methods=["POST"]),
        Route("/api/v1/status", router.handle_status, methods=["GET"]),
        Route("/api/v1/screen/capture", router.handle_screen_capture, methods=["POST"]),
        Route("/api/v1/capabilities", router.handle_capabilities, methods=["GET"]),
        Route("/api/v1/agent/query", router.handle_agent_query, methods=["POST"]),
        Route("/api/v1/agent/tasks/{task_id}/cancel", router.handle_cancel_task, methods=["POST"]),
        Route("/api/v1/agent/tasks/{task_id}", router.handle_get_task, methods=["GET"]),
        Route("/api/v1/emergency/lock", router.handle_emergency_lock, methods=["POST"]),
        Route("/api/v1/devices", router.handle_list_devices, methods=["GET"]),
        Route("/api/v1/devices/{device_id}/revoke", router.handle_revoke_device, methods=["POST"]),
        WebSocketRoute("/ws/v1/events", router.handle_websocket_events),
    ]

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    app = Starlette(routes=routes, middleware=middleware, lifespan=lifespan)
    return app


def run_host_server(
    app: Starlette,
    host: str = "127.0.0.1",
    port: int = 8000,
    log_level: str = "info",
) -> None:
    """Run the host ASGI server using uvicorn with graceful lifecycle handling."""
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.run()
