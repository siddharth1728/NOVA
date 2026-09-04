"""Host capability matrix and discovery registry."""

import platform
from nova.protocol.models import CapabilitiesMatrix, CapabilityInfo


class CapabilityRegistry:
    """Manages the catalog of host features exposed to remote clients."""

    def __init__(self, *, enable_dangerous: bool = False) -> None:
        self.enable_dangerous = enable_dangerous

    def get_matrix(self) -> CapabilitiesMatrix:
        """Return the current capability matrix for the running host."""
        is_win = platform.system() == "Windows"

        caps: list[CapabilityInfo] = [
            # System Telemetry & Monitor
            CapabilityInfo(
                name="desktop_telemetry",
                available=True,
                risk_level="READ_ONLY",
                description="Real-time CPU, RAM, disk, OS version, and boot metrics.",
                category="system",
            ),
            CapabilityInfo(
                name="desktop_screen_capture",
                available=True,
                risk_level="READ_ONLY",
                description="Live desktop screenshot capture and JPEG/PNG streaming.",
                category="screen",
            ),
            CapabilityInfo(
                name="multi_monitor_detection",
                available=is_win,
                risk_level="READ_ONLY",
                description="Enumerate physical displays, bounds, and virtual desktop coordinates.",
                category="screen",
            ),

            # Computer Control Layer
            CapabilityInfo(
                name="window_management",
                available=is_win,
                risk_level="CONTROL",
                description="Enumerate, focus, minimize, maximize, restore, resize, and close desktop windows.",
                category="computer",
            ),
            CapabilityInfo(
                name="application_launcher",
                available=is_win,
                risk_level="CONTROL",
                description="Discover installed applications and safely launch supervised processes.",
                category="computer",
            ),
            CapabilityInfo(
                name="mouse_control",
                available=is_win,
                risk_level="CONTROL",
                description="Absolute and window-relative cursor movement, click, drag, and wheel scroll.",
                category="computer",
            ),
            CapabilityInfo(
                name="keyboard_control",
                available=is_win,
                risk_level="CONTROL",
                description="Unicode text entry, key strokes, and validated safe chord combinations.",
                category="computer",
            ),
            CapabilityInfo(
                name="clipboard_control",
                available=is_win,
                risk_level="CONTROL",
                description="Read, write, and clear system clipboard with sensitive data protection.",
                category="computer",
            ),
            CapabilityInfo(
                name="process_supervision",
                available=is_win,
                risk_level="CONTROL",
                description="Inspect running processes with CPU/memory telemetry and protected termination.",
                category="computer",
            ),
            CapabilityInfo(
                name="ui_automation",
                available=is_win,
                risk_level="CONTROL",
                description="Inspect semantic UI element tree, invoke accessible controls, and read/write values.",
                category="computer",
            ),
            CapabilityInfo(
                name="vision_fallback",
                available=True,
                risk_level="CONTROL",
                description="Controlled vision coordinate resolution with confidence thresholds and staleness guards.",
                category="computer",
            ),
            CapabilityInfo(
                name="browser_control",
                available=is_win,
                risk_level="CONTROL",
                description="Discover installed web browsers and navigate to URLs.",
                category="computer",
            ),

            # Agent Runtime
            CapabilityInfo(
                name="agent_query_dispatch",
                available=True,
                risk_level="MUTATION_WORKSPACE",
                description="Dispatch natural language queries to local NOVA agent runtime.",
                category="agent",
            ),
            CapabilityInfo(
                name="agent_plan_inspection",
                available=True,
                risk_level="READ_ONLY",
                description="Inspect active multi-step plans and verification status.",
                category="agent",
            ),
            CapabilityInfo(
                name="audit_trail_streaming",
                available=True,
                risk_level="READ_ONLY",
                description="Real-time WebSocket streaming of structured audit events.",
                category="audit",
            ),

            # Security & Emergency
            CapabilityInfo(
                name="workstation_lock",
                available=is_win,
                risk_level="DANGEROUS_SYSTEM",
                description="Immediate remote workstation lock via Win32 LockWorkStation.",
                category="power",
            ),
            CapabilityInfo(
                name="task_cancellation",
                available=True,
                risk_level="CONTROL_SYSTEM",
                description="Direct abort of in-flight agent tasks via host task controller.",
                category="control",
            ),
            CapabilityInfo(
                name="arbitrary_shell_execution",
                available=False,  # Strictly blocked remotely per NOVA security policy
                risk_level="BLOCKED_DANGEROUS",
                description="Arbitrary shell commands (run_command) are strictly disabled over remote protocol.",
                category="terminal",
            ),
        ]
        return CapabilitiesMatrix(
            version="1.0.0",
            host_platform=platform.system(),
            capabilities=caps,
        )
