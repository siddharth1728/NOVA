"""NOVA Windows Control Layer package."""

from nova.control.capabilities import CapabilityRegistry
from nova.control.power import PowerControlProvider
from nova.control.screen import ScreenCaptureProvider
from nova.control.system import SystemMetricsProvider

__all__ = [
    "CapabilityRegistry",
    "PowerControlProvider",
    "ScreenCaptureProvider",
    "SystemMetricsProvider",
]
