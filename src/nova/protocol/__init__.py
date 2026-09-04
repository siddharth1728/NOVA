"""NOVA Remote Protocol package."""

from nova.protocol.errors import ProtocolErrorCode, format_error_payload
from nova.protocol.models import (
    AgentStatus,
    CapabilitiesMatrix,
    CapabilityInfo,
    DeviceInfo,
    DeviceRole,
    DeviceStatus,
    EmergencyActionRequest,
    EmergencyActionResponse,
    PairingRequest,
    PairingResponse,
    RemoteQueryRequest,
    RemoteQueryResponse,
    ScreenCaptureRequest,
    ScreenCaptureResponse,
    SystemMetrics,
    SystemStatus,
    WebSocketEvent,
)

__all__ = [
    "AgentStatus",
    "CapabilitiesMatrix",
    "CapabilityInfo",
    "DeviceInfo",
    "DeviceRole",
    "DeviceStatus",
    "EmergencyActionRequest",
    "EmergencyActionResponse",
    "PairingRequest",
    "PairingResponse",
    "ProtocolErrorCode",
    "RemoteQueryRequest",
    "RemoteQueryResponse",
    "ScreenCaptureRequest",
    "ScreenCaptureResponse",
    "SystemMetrics",
    "SystemStatus",
    "WebSocketEvent",
    "format_error_payload",
]
