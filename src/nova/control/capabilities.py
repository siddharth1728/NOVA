"""Host capability matrix and discovery registry."""

import platform
from nova.protocol.models import CapabilitiesMatrix, CapabilityInfo


class CapabilityRegistry:
    """Manages the catalog of host features exposed to remote clients."""

    def __init__(self, *, enable_dangerous: bool = False) -> None:
        self.enable_dangerous = enable_dangerous

    def get_matrix(self) -> CapabilitiesMatrix:
        """Return the current capability matrix for the running host."""
        caps: list[CapabilityInfo] = [
            CapabilityInfo(
                name="desktop_telemetry",
                available=True,
                risk_level="READ_ONLY",
                description="Real-time CPU, RAM, disk, OS version, and boot metrics.",
            ),
            CapabilityInfo(
                name="desktop_screen_capture",
                available=True,
                risk_level="READ_ONLY",
                description="Live desktop screenshot capture and JPEG/PNG streaming.",
            ),
            CapabilityInfo(
                name="agent_query_dispatch",
                available=True,
                risk_level="MUTATION_WORKSPACE",
                description="Dispatch natural language queries to local NOVA agent runtime.",
            ),
            CapabilityInfo(
                name="agent_plan_inspection",
                available=True,
                risk_level="READ_ONLY",
                description="Inspect active multi-step plans and verification status.",
            ),
            CapabilityInfo(
                name="audit_trail_streaming",
                available=True,
                risk_level="READ_ONLY",
                description="Real-time WebSocket streaming of structured audit events.",
            ),
            CapabilityInfo(
                name="workstation_lock",
                available=platform.system() == "Windows",
                risk_level="DANGEROUS_SYSTEM",
                description="Immediate remote workstation lock via Win32 LockWorkStation.",
            ),
            CapabilityInfo(
                name="task_cancellation",
                available=True,
                risk_level="CONTROL_SYSTEM",
                description="Direct abort of in-flight agent tasks via host task controller.",
            ),
            CapabilityInfo(
                name="arbitrary_shell_execution",
                available=False,  # Strictly blocked remotely per NOVA security policy
                risk_level="BLOCKED_DANGEROUS",
                description="Arbitrary shell commands (run_command) are strictly disabled over remote protocol.",
            ),
        ]
        return CapabilitiesMatrix(
            version="1.0.0",
            host_platform=platform.system(),
            capabilities=caps,
        )
