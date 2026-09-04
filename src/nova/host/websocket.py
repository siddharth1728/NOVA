"""WebSocket connection hub and real-time event broadcaster."""

import asyncio
import logging
from typing import Any
from starlette.websockets import WebSocket, WebSocketState

from nova.protocol.models import WebSocketEvent

logger = logging.getLogger("nova.host.websocket")


class WebSocketHub:
    """Manages active streaming WebSocket connections for remote clients."""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, str] = {}  # socket -> device_id
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket, device_id: str) -> None:
        """Register an authenticated WebSocket client."""
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = device_id
        logger.info("WebSocket connected for device: %s (Total: %d)", device_id, len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a disconnected WebSocket client."""
        async with self._lock:
            device_id = self._connections.pop(websocket, None)
        if device_id:
            logger.info("WebSocket disconnected for device: %s (Remaining: %d)", device_id, len(self._connections))

    async def broadcast(self, event: WebSocketEvent | dict[str, Any]) -> int:
        """Broadcast an event payload to all connected clients."""
        payload = event.model_dump() if isinstance(event, WebSocketEvent) else event
        dead_sockets: list[WebSocket] = []

        async with self._lock:
            active_sockets = list(self._connections.keys())

        delivered = 0
        for ws in active_sockets:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(payload)
                    delivered += 1
                else:
                    dead_sockets.append(ws)
            except Exception as ex:
                logger.warning("Error sending WebSocket event: %s", ex)
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                for ws in dead_sockets:
                    self._connections.pop(ws, None)

        return delivered
