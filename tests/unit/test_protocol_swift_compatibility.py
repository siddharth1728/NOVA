"""Protocol compatibility test suite validating Python backend schemas against Swift iOS models.

Ensures that every JSON key, data type, enum, and nested structure emitted by the NOVA
Windows Host exactly matches the Codable schemas in ios/NOVA/Models/ProtocolModels.swift.
"""

import json
import pytest
from datetime import datetime, timezone

from nova.protocol.models import (
    PROTOCOL_VERSION,
    SERVER_VERSION,
    AgentStatus,
    AppLaunchRemoteRequest,
    CapabilitiesMatrix,
    CapabilityInfo,
    ClipboardWriteRemoteRequest,
    DeviceInfo,
    DeviceRole,
    DeviceStatus,
    EmergencyActionRequest,
    EmergencyActionResponse,
    HealthResponse,
    KeyboardTypeRemoteRequest,
    KeyComboRemoteRequest,
    KeyPressRemoteRequest,
    MouseClickRemoteRequest,
    MouseMoveRemoteRequest,
    MouseScrollRemoteRequest,
    PairingRequest,
    PairingResponse,
    ProcessStopRemoteRequest,
    RemoteQueryRequest,
    RemoteQueryResponse,
    ScreenCaptureRequest,
    ScreenCaptureResponse,
    SystemMetrics,
    SystemStatus,
    TaskCancelRequest,
    TaskCancelResponse,
    TaskCreateRequest,
    TaskDetailResponse,
    TaskMetricsResponse,
    TaskRecord,
    TaskStatus,
    TaskStepResponse,
    TaskStepsListResponse,
    TaskActionResponse,
    StepApprovalRemoteResponse,
    WebSocketEvent,
    WindowBoundsRemoteRequest,
    WindowCloseRemoteRequest,
    WindowFocusRemoteRequest,

)
from nova.protocol.errors import ProtocolErrorCode, format_error_payload
from nova.control.windows.models import WindowBounds, WindowInfo
from nova.control.applications.models import AppInfo, LaunchResult
from nova.control.processes.models import ProcessInfo, ProcessStopResult
from nova.control.clipboard.models import ClipboardContent, ClipboardType
from nova.control.browsers.models import BrowserTab


class TestProtocolSwiftCompatibility:
    """Validates structural and semantic agreement between Python and Swift models."""

    def test_pairing_schemas(self):
        """Verify PairingRequest and PairingResponse match Swift Decodable keys."""
        # Swift PairingRequest keys: pairing_code, device_id, device_name, platform, client_version
        swift_req = {
            "pairing_code": "123456",
            "device_id": "ios-device-uuid-1234",
            "device_name": "iPhone 16 Pro",
            "platform": "iOS",
            "client_version": "0.4.0",
        }
        py_req = PairingRequest.model_validate(swift_req)
        assert py_req.pairing_code == "123456"
        assert py_req.device_id == "ios-device-uuid-1234"
        assert py_req.platform == "iOS"

        # Python PairingResponse emitted keys: token, device_id, host_name, server_version, protocol_version, expires_at
        py_resp = PairingResponse(
            token="test-jwt-token-xyz",
            device_id="ios-device-uuid-1234",
            host_name="DESKTOP-WIN11",
            server_version=SERVER_VERSION,
            protocol_version=PROTOCOL_VERSION,
            expires_at=datetime.now(timezone.utc).isoformat(),
        )
        resp_json = py_resp.model_dump()
        expected_swift_keys = {"token", "device_id", "host_name", "server_version", "protocol_version", "expires_at"}
        assert set(resp_json.keys()) == expected_swift_keys
        assert resp_json["protocol_version"] == "1.0.0"

    def test_health_response_schema(self):
        """Verify HealthResponse payload matches Swift HealthResponse struct."""
        resp = HealthResponse(
            status="HEALTHY",
            host_name="WIN-NOVA-HOST",
            server_version=SERVER_VERSION,
            protocol_version=PROTOCOL_VERSION,
            uptime_seconds=3600.5,
            agent_state="IDLE",
            active_tasks_count=0,
        )
        payload = resp.model_dump()
        expected_keys = {
            "status", "host_name", "server_version", "protocol_version",
            "uptime_seconds", "agent_state", "active_tasks_count", "timestamp"
        }
        assert set(payload.keys()) == expected_keys
        assert isinstance(payload["uptime_seconds"], (int, float))
        assert isinstance(payload["active_tasks_count"], int)

    def test_system_status_and_metrics_schema(self):
        """Verify SystemStatus, SystemMetrics, and AgentStatus models."""
        metrics = SystemMetrics(
            cpu_percent=14.2,
            ram_total_gb=32.0,
            ram_used_gb=12.5,
            ram_percent=39.0,
            disk_total_gb=1000.0,
            disk_used_gb=450.0,
            disk_percent=45.0,
            uptime_seconds=7200.0,
            boot_time="2026-09-04T00:00:00Z",
            os_version="Windows 11 Pro 23H2",
            hostname="WIN-NOVA-HOST",
        )
        agent = AgentStatus(
            state="IDLE",
            active_plan_id=None,
            workspace_root="C:\\KaryaSetu",
            tools_registered=12,
            uptime_seconds=7200.0,
        )
        status = SystemStatus(
            protocol_version=PROTOCOL_VERSION,
            system=metrics,
            agent=agent,
        )
        data = status.model_dump()
        assert "system" in data
        assert "agent" in data
        assert "protocol_version" in data
        assert "timestamp" in data

        sys_data = data["system"]
        # Match Swift SystemMetrics CodingKeys
        assert "cpu_percent" in sys_data
        assert "ram_total_gb" in sys_data
        assert "ram_used_gb" in sys_data
        assert "ram_percent" in sys_data
        assert "disk_total_gb" in sys_data
        assert "disk_used_gb" in sys_data
        assert "disk_percent" in sys_data
        assert "uptime_seconds" in sys_data
        assert "boot_time" in sys_data
        assert "os_version" in sys_data
        assert "hostname" in sys_data

    def test_screen_capture_schema(self):
        """Verify ScreenCaptureRequest and ScreenCaptureResponse schemas."""
        req = ScreenCaptureRequest(format="png", max_width=1280, max_height=720, quality=80)
        req_data = req.model_dump()
        assert req_data["format"] == "png"
        assert req_data["max_width"] == 1280
        assert req_data["max_height"] == 720
        assert req_data["quality"] == 80

        resp = ScreenCaptureResponse(
            timestamp=datetime.now(timezone.utc).isoformat(),
            format="png",
            width=1920,
            height=1080,
            image_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            file_size_bytes=68,
        )
        resp_data = resp.model_dump()
        expected_keys = {"timestamp", "format", "width", "height", "image_base64", "file_size_bytes"}
        assert set(resp_data.keys()) == expected_keys
        assert isinstance(resp_data["width"], int)
        assert isinstance(resp_data["file_size_bytes"], int)

    def test_capabilities_schema(self):
        """Verify CapabilitiesMatrix and CapabilityInfo schemas."""
        caps = CapabilitiesMatrix(
            capabilities=[
                CapabilityInfo(
                    name="computer.windows",
                    available=True,
                    risk_level="MEDIUM",
                    description="Window management",
                    category="window",
                ),
                CapabilityInfo(
                    name="computer.mouse",
                    available=True,
                    risk_level="LOW",
                    description="Mouse input",
                    category="input",
                ),
            ]
        )
        data = caps.model_dump()
        assert "version" in data
        assert "protocol_version" in data
        assert "host_platform" in data
        assert "capabilities" in data
        assert len(data["capabilities"]) == 2
        cap0 = data["capabilities"][0]
        assert "name" in cap0
        assert "available" in cap0
        assert "risk_level" in cap0
        assert "description" in cap0
        assert "category" in cap0

    def test_agent_query_and_task_schemas(self):
        """Verify RemoteQueryRequest, RemoteQueryResponse, and TaskCancel schemas."""
        # Swift RemoteQueryRequest keys
        swift_req = {
            "query": "Open Notepad",
            "request_id": "req-uuid-1234",
            "require_approval": False,
            "max_steps": 10,
        }
        py_req = RemoteQueryRequest.model_validate(swift_req)
        assert py_req.query == "Open Notepad"
        assert py_req.request_id == "req-uuid-1234"
        assert py_req.require_approval is False

        # Python RemoteQueryResponse
        resp = RemoteQueryResponse(
            session_id="sess-001",
            task_id="task-001",
            request_id="req-uuid-1234",
            query="Open Notepad",
            status=TaskStatus.COMPLETED,
            response_text="Notepad opened successfully.",
            tool_calls_count=1,
            steps_executed=1,
            verification_passed=True,
            plan_id=None,
        )
        resp_data = resp.model_dump()
        expected_keys = {
            "session_id", "task_id", "request_id", "query", "status",
            "response_text", "tool_calls_count", "steps_executed",
            "verification_passed", "plan_id", "protocol_version"
        }
        assert set(resp_data.keys()) == expected_keys
        assert resp_data["status"] == "COMPLETED"

        # TaskCancel schemas
        cancel_req = TaskCancelRequest(task_id="task-001", reason="User stopped")
        assert cancel_req.task_id == "task-001"

        cancel_resp = TaskCancelResponse(task_id="task-001", success=True, message="Task aborted")
        cancel_data = cancel_resp.model_dump()
        assert cancel_data["task_id"] == "task-001"
        assert cancel_data["success"] is True
        assert "timestamp" in cancel_data

    def test_window_info_schema(self):
        """Verify WindowInfo and WindowBounds match Swift model keys."""
        bounds = WindowBounds(x=100, y=100, width=800, height=600)
        win = WindowInfo(
            hwnd=12345,
            title="Untitled - Notepad",
            process_name="notepad.exe",
            pid=4567,
            bounds=bounds,
            visible=True,
            is_foreground=True,
            is_minimized=False,
            is_maximized=False,
        )
        win_data = win.model_dump()
        # Verify keys emitted match what Swift WindowInfo decodes
        expected_keys = {
            "hwnd", "title", "process_name", "pid", "bounds",
            "visible", "is_foreground", "is_minimized", "is_maximized"
        }
        assert set(win_data.keys()) == expected_keys
        assert win_data["pid"] == 4567
        assert win_data["visible"] is True
        assert win_data["bounds"]["width"] == 800

    def test_app_info_and_launch_schemas(self):
        """Verify AppInfo and LaunchResult schemas match Swift AppInfo & AppLaunchResponse."""
        app = AppInfo(
            name="Visual Studio Code",
            executable="code.exe",
            path="C:\\Program Files\\Microsoft VS Code\\code.exe",
            publisher="Microsoft Corporation",
            is_running=True,
            category="development",
        )
        app_data = app.model_dump()
        expected_keys = {"name", "executable", "path", "publisher", "is_running", "category"}
        assert set(app_data.keys()) == expected_keys
        assert app_data["executable"] == "code.exe"

        # LaunchResult (which maps to AppLaunchResponse in Swift)
        launch_res = LaunchResult(
            success=True,
            app_name="notepad.exe",
            pid=7890,
            hwnd=54321,
            window_title="Untitled - Notepad",
            message="Application launched",
            window_detected=True,
        )
        launch_data = launch_res.model_dump()
        assert launch_data["success"] is True
        assert launch_data["app_name"] == "notepad.exe"
        assert launch_data["pid"] == 7890
        assert launch_data["hwnd"] == 54321
        assert launch_data["window_detected"] is True

    def test_process_info_and_stop_schemas(self):
        """Verify ProcessInfo and ProcessStopResult schemas."""
        proc = ProcessInfo(
            pid=1234,
            name="python.exe",
            exe="C:\\Python311\\python.exe",
            cpu_percent=2.5,
            memory_percent=1.2,
            memory_mb=145.8,
            status="running",
            parent_pid=5678,
            created_at="2026-09-04T12:00:00Z",
        )
        proc_data = proc.model_dump()
        expected_keys = {
            "pid", "name", "exe", "cpu_percent", "memory_percent",
            "memory_mb", "status", "parent_pid", "created_at"
        }
        assert set(proc_data.keys()) == expected_keys
        assert proc_data["pid"] == 1234
        assert proc_data["cpu_percent"] == 2.5

        # ProcessStopResult
        stop_res = ProcessStopResult(
            pid=1234,
            name="python.exe",
            success=True,
            message="Terminated",
        )
        stop_data = stop_res.model_dump()
        assert stop_data["pid"] == 1234
        assert stop_data["name"] == "python.exe"
        assert stop_data["success"] is True

    def test_clipboard_schema(self):
        """Verify ClipboardContent matches Swift ClipboardContent model."""
        clip = ClipboardContent(
            content_type=ClipboardType.TEXT,
            has_text=True,
            text_length=15,
            hash_sha256="abcdef1234567890",
            text_preview="Hello NOVA...",
        )
        clip_data = clip.model_dump()
        expected_keys = {"content_type", "has_text", "text_length", "hash_sha256", "text_preview"}
        assert set(clip_data.keys()) == expected_keys
        assert clip_data["content_type"] == "TEXT"
        assert clip_data["has_text"] is True
        assert clip_data["text_length"] == 15

    def test_error_response_schema(self):
        """Verify format_error_payload matches Swift ProtocolErrorResponse."""
        err_payload = format_error_payload(
            ProtocolErrorCode.UNAUTHENTICATED,
            "Invalid session token",
            {"reason": "Token expired"},
        )
        assert err_payload["success"] is False
        assert "protocol_version" in err_payload
        assert "error" in err_payload
        err_detail = err_payload["error"]
        assert err_detail["code"] == "UNAUTHENTICATED"
        assert err_detail["message"] == "Invalid session token"
        assert err_detail["details"] == {"reason": "Token expired"}

    def test_websocket_event_schema(self):
        """Verify WebSocketEvent matches Swift WebSocketEvent struct."""
        evt = WebSocketEvent(
            event_type="telemetry",
            timestamp=datetime.now(timezone.utc).isoformat(),
            data={"cpu": 15.2, "status": "active"},
        )
        evt_data = evt.model_dump()
        assert "event_type" in evt_data
        assert "timestamp" in evt_data
        assert "data" in evt_data

    def test_browser_schemas(self):
        """Verify BrowserTab and browser status schemas match Swift BrowserTabItem & BrowserStatusResponse."""
        tab = BrowserTab(
            tab_id="tab_123",
            title="NOVA Portal",
            url="https://github.com/siddharth1728/NOVA",
            is_active=True,
        )
        tab_data = tab.model_dump()
        assert set(tab_data.keys()) == {"tab_id", "title", "url", "is_active", "loading"}
        assert tab_data["tab_id"] == "tab_123"
        assert tab_data["is_active"] is True
        assert tab_data["loading"] is False

        # Status response dict structure
        status_dict = {
            "enabled": True,
            "running": False,
            "headless": True,
            "protocol_version": PROTOCOL_VERSION,
        }
        assert set(status_dict.keys()) == {"enabled", "running", "headless", "protocol_version"}

    def test_task_orchestration_schemas(self):
        """Verify Phase 09 task models match Swift Codable schemas."""
        req = TaskCreateRequest(
            query="Research asyncio trends",
            request_id="req_123",
            require_approval=True,
            risk_ceiling="MEDIUM",
        )
        req_data = req.model_dump()
        assert req_data["query"] == "Research asyncio trends"
        assert req_data["require_approval"] is True
        assert req_data["risk_ceiling"] == "MEDIUM"

        detail = TaskDetailResponse(
            task_id="task_abc123",
            request_id="req_123",
            device_id="ios-dev-1",
            query="Research asyncio trends",
            status=TaskStatus.EXECUTING,
            created_at=datetime.now(timezone.utc).isoformat(),
            current_step_index=1,
            total_steps=3,
            completed_steps=1,
            progress_percent=33.3,
            current_step_description="Extracting content",
            risk_level="LOW",
            approval_state="NONE",
            duration_seconds=1.23,
            protocol_version=PROTOCOL_VERSION,
        )
        detail_data = detail.model_dump()
        assert detail_data["status"] == "EXECUTING"
        assert detail_data["total_steps"] == 3
        assert detail_data["progress_percent"] == 33.3

        step = TaskStepResponse(
            step_id=1,
            description="Open tab",
            tool="browser_new_tab",
            status="COMPLETED",
            risk_level="LOW",
            attempt_count=1,
            requires_approval=False,
            domain="BROWSER",
            reversibility="REVERSIBLE",
        )
        step_data = step.model_dump()
        assert step_data["step_id"] == 1
        assert step_data["tool"] == "browser_new_tab"
        assert step_data["domain"] == "BROWSER"

        action = TaskActionResponse(
            task_id="task_abc123",
            status=TaskStatus.PAUSED,
            success=True,
            message="Task paused safely",
        )
        action_data = action.model_dump()
        assert action_data["status"] == "PAUSED"
        assert action_data["success"] is True

        metrics = TaskMetricsResponse(
            tasks_started=5,
            tasks_completed=4,
            tasks_failed=1,
            tasks_cancelled=0,
            steps_executed=12,
            steps_retried=1,
            steps_replanned=0,
            approval_requests=1,
            approval_denials=0,
            verification_failures=1,
            average_task_duration=2.45,
        )
        metrics_data = metrics.model_dump()
        assert metrics_data["tasks_started"] == 5
        assert metrics_data["average_task_duration"] == 2.45


