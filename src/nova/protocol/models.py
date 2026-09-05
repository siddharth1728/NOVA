"""NOVA Remote Protocol v1 data models and schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

PROTOCOL_VERSION = "1.0.0"
SERVER_VERSION = "0.4.0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DeviceRole(str, Enum):
    """Access level for a paired device."""

    CONTROLLER = "CONTROLLER"
    OBSERVER = "OBSERVER"
    ADMIN = "ADMIN"


class DeviceStatus(str, Enum):
    """Lifecycle status of a device in the host trust registry."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class TaskStatus(str, Enum):
    """Authoritative lifecycle status of a remote agent task."""

    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    PAUSED = "PAUSED"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ROLLED_BACK = "ROLLED_BACK"
    DISCONNECTED = "DISCONNECTED"



class DeviceInfo(BaseModel):
    """Metadata describing an authorized or paired client device."""

    model_config = ConfigDict(frozen=True)

    device_id: str = Field(description="Unique device identifier (UUID or hardware fingerprint)")
    name: str = Field(description="Human-readable device name")
    platform: str = Field(default="iOS", description="Platform/OS name")
    role: DeviceRole = Field(default=DeviceRole.CONTROLLER)
    status: DeviceStatus = Field(default=DeviceStatus.ACTIVE)
    paired_at: str = Field(default_factory=_utc_now_iso)
    last_seen_at: str | None = None


class PairingRequest(BaseModel):
    """Client request to pair with host using a temporary PIN code."""

    pairing_code: str = Field(min_length=6, max_length=6, description="6-digit ephemeral host pairing code")
    device_id: str = Field(min_length=3, description="Client persistent device identifier")
    device_name: str = Field(min_length=1, description="Friendly device name (e.g. 'iPhone 16 Pro')")
    platform: str = Field(default="iOS", description="Client operating platform")
    client_version: str = Field(default="0.4.0", description="Client application version")


class PairingResponse(BaseModel):
    """Host confirmation containing signed session token upon successful pairing."""

    token: str = Field(description="JWT Bearer token for authenticating subsequent requests")
    device_id: str
    host_name: str
    server_version: str = SERVER_VERSION
    protocol_version: str = PROTOCOL_VERSION
    expires_at: str


class HealthResponse(BaseModel):
    """Host service health, operational readiness, and protocol version."""

    status: str = Field(default="HEALTHY", description="HEALTHY or DEGRADED")
    host_name: str
    server_version: str = SERVER_VERSION
    protocol_version: str = PROTOCOL_VERSION
    uptime_seconds: float
    agent_state: str
    active_tasks_count: int = 0
    timestamp: str = Field(default_factory=_utc_now_iso)


class SystemMetrics(BaseModel):
    """Host hardware and operating system telemetry."""

    cpu_percent: float
    ram_total_gb: float
    ram_used_gb: float
    ram_percent: float
    disk_total_gb: float
    disk_used_gb: float
    disk_percent: float
    uptime_seconds: float
    boot_time: str
    os_version: str
    hostname: str


class AgentStatus(BaseModel):
    """Live state of the local NOVA agent runtime."""

    state: str = Field(description="IDLE, PLANNING, EXECUTING, or ERROR")
    active_plan_id: str | None = None
    workspace_root: str
    tools_registered: int
    uptime_seconds: float


class SystemStatus(BaseModel):
    """Comprehensive host telemetry packet."""

    timestamp: str = Field(default_factory=_utc_now_iso)
    protocol_version: str = PROTOCOL_VERSION
    system: SystemMetrics
    agent: AgentStatus


class ScreenCaptureRequest(BaseModel):
    """Parameters for remote screen snapshot."""

    format: str = Field(default="png", description="Image format: png or jpeg")
    max_width: int | None = Field(default=None, description="Optional downscale width")
    max_height: int | None = Field(default=None, description="Optional downscale height")
    quality: int = Field(default=80, ge=10, le=100, description="Compression quality (for jpeg)")


class ScreenCaptureResponse(BaseModel):
    """Desktop screen snapshot payload."""

    timestamp: str = Field(default_factory=_utc_now_iso)
    format: str = "png"
    width: int
    height: int
    image_base64: str = Field(description="Base64 encoded image data")
    file_size_bytes: int


class CapabilityInfo(BaseModel):
    """Specification of an exposed host capability."""

    name: str
    available: bool
    risk_level: str
    description: str
    category: str = "general"


class CapabilitiesMatrix(BaseModel):
    """Matrix of all available host and agent capabilities."""

    version: str = "1.0.0"
    protocol_version: str = PROTOCOL_VERSION
    host_platform: str = "Windows"
    capabilities: list[CapabilityInfo] = Field(default_factory=list)


class RemoteQueryRequest(BaseModel):
    """Query submitted from mobile client for agent execution."""

    query: str = Field(min_length=1, description="Natural language request or task")
    request_id: str | None = Field(default=None, description="Client idempotency key (UUID)")
    require_approval: bool = Field(default=False, description="Whether plan requires approval before execution")
    max_steps: int = Field(default=10, ge=1, le=50)
    context: dict[str, Any] = Field(default_factory=dict)


class RemoteQueryResponse(BaseModel):
    """Result of remote agent query execution."""

    session_id: str
    task_id: str
    request_id: str | None = None
    query: str
    status: TaskStatus
    response_text: str
    tool_calls_count: int
    steps_executed: int
    verification_passed: bool
    plan_id: str | None = None
    protocol_version: str = PROTOCOL_VERSION


class TaskCancelRequest(BaseModel):
    """Mobile request to abort an in-flight agent task."""

    task_id: str = Field(description="Unique task identifier to cancel")
    reason: str = Field(default="User initiated cancellation from mobile client")


class TaskCancelResponse(BaseModel):
    """Outcome of cancellation request."""

    task_id: str
    success: bool
    message: str
    timestamp: str = Field(default_factory=_utc_now_iso)


class TaskRecord(BaseModel):
    """Host execution record for tracking task lifecycle and idempotency."""

    task_id: str
    request_id: str
    device_id: str
    query: str
    status: TaskStatus
    created_at: str = Field(default_factory=_utc_now_iso)
    updated_at: str = Field(default_factory=_utc_now_iso)
    response_text: str | None = None
    error: str | None = None


class EmergencyActionRequest(BaseModel):
    """Emergency control invocation."""

    action: str = Field(description="Lock, cancel, or stop")
    reason: str = Field(default="User initiated from mobile client")


class EmergencyActionResponse(BaseModel):
    """Outcome of emergency control execution."""

    action: str
    success: bool
    message: str
    timestamp: str = Field(default_factory=_utc_now_iso)


class WebSocketEvent(BaseModel):
    """Real-time streaming event over WebSocket connection."""

    event_type: str = Field(description="telemetry, agent_plan, agent_step, task_update, audit, alert")
    timestamp: str = Field(default_factory=_utc_now_iso)
    data: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Phase 09: Agentic Task Execution & Multi-Step Workflow Models
# =============================================================================


class TaskCreateRequest(BaseModel):
    """Client request to initialize and start an orchestrated agentic task."""

    query: str = Field(min_length=1, description="Goal or multi-step prompt")
    request_id: str | None = Field(default=None, description="Client idempotency key")
    require_approval: bool = Field(default=False, description="Require manual approval before executing plan")
    risk_ceiling: str = Field(default="MEDIUM", description="Max risk allowed without manual approval")
    context: dict[str, Any] = Field(default_factory=dict)


class TaskDetailResponse(BaseModel):
    """Comprehensive status and progress report for an orchestrated task."""

    task_id: str
    request_id: str
    device_id: str
    query: str
    status: TaskStatus
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    current_step_index: int = 0
    total_steps: int = 0
    completed_steps: int = 0
    progress_percent: float = 0.0
    current_step_description: str | None = None
    risk_level: str = "LOW"
    approval_state: str = "NONE"
    pending_approval: dict[str, Any] | None = None
    response_text: str | None = None
    error: str | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    duration_seconds: float = 0.0
    protocol_version: str = PROTOCOL_VERSION


class TaskStepResponse(BaseModel):
    """Details of an individual plan step within an orchestrated task."""

    step_id: int
    description: str
    tool: str
    status: str
    risk_level: str
    attempt_count: int
    requires_approval: bool
    domain: str = "FILESYSTEM"
    reversibility: str = "REVERSIBLE"
    error: str | None = None


class TaskStepsListResponse(BaseModel):
    """List of all plan steps for a task."""

    task_id: str
    steps: list[TaskStepResponse]
    total: int


class TaskActionRequest(BaseModel):
    """Generic control action request (pause, resume, etc.)."""

    reason: str = Field(default="User initiated action")


class TaskActionResponse(BaseModel):
    """Outcome of a task control action."""

    task_id: str
    status: TaskStatus
    success: bool
    message: str
    timestamp: str = Field(default_factory=_utc_now_iso)


class StepApprovalRemoteRequest(BaseModel):
    """Human approval decision on a pending step."""

    step_id: int
    approved: bool
    reason: str | None = None


class StepApprovalRemoteResponse(BaseModel):
    """Outcome of step approval submission."""

    task_id: str
    step_id: int
    approved: bool
    status: TaskStatus
    message: str
    timestamp: str = Field(default_factory=_utc_now_iso)


class TaskMetricsResponse(BaseModel):
    """Operational telemetry counters for the task orchestration system."""

    tasks_started: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_cancelled: int = 0
    steps_executed: int = 0
    steps_retried: int = 0
    steps_replanned: int = 0
    approval_requests: int = 0
    approval_denials: int = 0
    verification_failures: int = 0
    average_task_duration: float = 0.0


# =============================================================================
# Phase 05: Remote Computer Control Requests
# =============================================================================



class WindowFocusRemoteRequest(BaseModel):
    hwnd: int


class WindowCloseRemoteRequest(BaseModel):
    hwnd: int


class WindowBoundsRemoteRequest(BaseModel):
    hwnd: int
    x: int
    y: int
    width: int
    height: int


class AppLaunchRemoteRequest(BaseModel):
    app_name_or_path: str
    arguments: list[str] = Field(default_factory=list)
    wait_for_window: bool = True
    timeout_seconds: float = 10.0


class MouseMoveRemoteRequest(BaseModel):
    x: int
    y: int
    delta: bool = False
    relative_to_hwnd: int | None = None


class MouseClickRemoteRequest(BaseModel):
    button: str = "left"  # left, right, middle
    count: int = 1
    x: int | None = None
    y: int | None = None
    relative_to_hwnd: int | None = None


class MouseScrollRemoteRequest(BaseModel):
    clicks: int
    x: int | None = None
    y: int | None = None


class KeyboardTypeRemoteRequest(BaseModel):
    text: str
    target_hwnd: int | None = None


class KeyPressRemoteRequest(BaseModel):
    key: str
    target_hwnd: int | None = None


class KeyComboRemoteRequest(BaseModel):
    keys: list[str]
    target_hwnd: int | None = None


class ClipboardWriteRemoteRequest(BaseModel):
    text: str


class ProcessStopRemoteRequest(BaseModel):
    pid: int
    force: bool = False


class UIElementActionRemoteRequest(BaseModel):
    action: str = "invoke"  # invoke or set_value
    name: str | None = None
    automation_id: str | None = None
    control_type: str | None = None
    value: str | None = None
    hwnd: int | None = None

