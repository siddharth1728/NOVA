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
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
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
