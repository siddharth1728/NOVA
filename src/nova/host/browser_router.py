"""REST route handlers for NOVA Windows Host Browser integration."""

import logging
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from nova.config.settings import NovaSettings
from nova.control.browsers.playwright_manager import get_browser_controller
from nova.errors import AuthenticationError, DeviceRevokedError
from nova.host.auth import DeviceRegistry, TokenManager
from nova.protocol.errors import ProtocolErrorCode, format_error_payload
from nova.protocol.models import PROTOCOL_VERSION

logger = logging.getLogger("nova.host.browser_router")


class BrowserRouter:
    """Encapsulates route handlers for the browser HTTP API."""

    def __init__(
        self,
        *,
        settings: NovaSettings,
        device_registry: DeviceRegistry,
        token_manager: TokenManager,
        browser_controller: Any | None = None,
    ) -> None:
        self.settings = settings
        self.device_registry = device_registry
        self.token_manager = token_manager
        self.controller = browser_controller or get_browser_controller()

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

    async def handle_status(self, request: Request) -> Response:
        """GET /api/v1/browser/status - Check browser subsystem health."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        is_running = self.controller.browser is not None
        
        return JSONResponse({
            "enabled": self.settings.browser_enabled,
            "running": is_running,
            "headless": self.settings.browser_headless,
            "protocol_version": PROTOCOL_VERSION,
        }, status_code=200)

    async def handle_list_tabs(self, request: Request) -> Response:
        """GET /api/v1/browser/tabs - List active browser tabs."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        tabs = await self.controller.list_tabs()
        return JSONResponse([t.model_dump() for t in tabs], status_code=200)

    async def handle_new_tab(self, request: Request) -> Response:
        """POST /api/v1/browser/tabs - Open a new tab."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        url = None
        try:
            body = await request.json()
            url = body.get("url")
        except Exception:
            pass

        try:
            tab = await self.controller.new_tab(url)
            return JSONResponse(tab.model_dump(), status_code=200)
        except Exception as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.INTERNAL_ERROR, str(ex)), status_code=500)

    async def handle_close_tab(self, request: Request) -> Response:
        """DELETE /api/v1/browser/tabs/{tab_id} - Close a tab."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        tab_id = request.path_params.get("tab_id")
        if not tab_id:
            return JSONResponse(format_error_payload(ProtocolErrorCode.INVALID_REQUEST, "Missing tab_id"), status_code=400)

        success = await self.controller.close_tab(tab_id)
        return JSONResponse({"success": success, "tab_id": tab_id}, status_code=200 if success else 404)

    async def handle_focus_tab(self, request: Request) -> Response:
        """POST /api/v1/browser/tabs/{tab_id}/focus - Focus a tab."""
        try:
            self.authenticate_request(request)
        except DeviceRevokedError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.REVOKED_DEVICE, str(ex)), status_code=403)
        except AuthenticationError as ex:
            return JSONResponse(format_error_payload(ProtocolErrorCode.UNAUTHENTICATED, str(ex)), status_code=401)

        tab_id = request.path_params.get("tab_id")
        if not tab_id:
            return JSONResponse(format_error_payload(ProtocolErrorCode.INVALID_REQUEST, "Missing tab_id"), status_code=400)

        success = await self.controller.focus_tab(tab_id)
        return JSONResponse({"success": success, "tab_id": tab_id}, status_code=200 if success else 404)
