"""NOVA Remote Protocol v1 data models and schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


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


class PairingResponse(BaseModel):
    """Host confirmation containing signed session token upon successful pairing."""

    token: str = Field(description="JWT Bearer token for authenticating subsequent requests")
    device_id: str
    host_name: str
    server_version: str = "0.1.0"
    expires_at: str


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
    host_platform: str = "Windows"
    capabilities: list[CapabilityInfo] = Field(default_factory=list)


class RemoteQueryRequest(BaseModel):
    """Query submitted from mobile client for agent execution."""

    query: str = Field(min_length=1, description="Natural language request or task")
    require_approval: bool = Field(default=False, description="Whether plan requires approval before execution")
    max_steps: int = Field(default=10, ge=1, le=50)
    context: dict[str, Any] = Field(default_factory=dict)


class RemoteQueryResponse(BaseModel):
    """Result of remote agent query execution."""

    session_id: str
    query: str
    status: str
    response_text: str
    tool_calls_count: int
    steps_executed: int
    verification_passed: bool
    plan_id: str | None = None


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

    event_type: str = Field(description="telemetry, agent_plan, agent_step, audit, alert")
    timestamp: str = Field(default_factory=_utc_now_iso)
    data: dict[str, Any] = Field(default_factory=dict)
