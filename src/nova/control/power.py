"""Workstation power and lock controls for Windows."""

import ctypes
import platform
import logging

from nova.protocol.models import EmergencyActionResponse

logger = logging.getLogger("nova.control.power")


class PowerControlProvider:
    """Manages secure workstation state changes such as remote desktop lock."""

    def lock_workstation(self, *, dry_run: bool = False) -> EmergencyActionResponse:
        """Lock the local Windows workstation immediately."""
        if dry_run:
            logger.info("Dry-run requested: workstation lock simulated.")
            return EmergencyActionResponse(
                action="LOCK_WORKSTATION",
                success=True,
                message="Workstation lock simulated (dry run).",
            )

        if platform.system() != "Windows":
            return EmergencyActionResponse(
                action="LOCK_WORKSTATION",
                success=False,
                message=f"Workstation lock unsupported on platform {platform.system()}.",
            )

        try:
            # Win32 user32 LockWorkStation API
            result = ctypes.windll.user32.LockWorkStation()
            if result != 0:
                return EmergencyActionResponse(
                    action="LOCK_WORKSTATION",
                    success=True,
                    message="Windows workstation locked successfully.",
                )
            else:
                return EmergencyActionResponse(
                    action="LOCK_WORKSTATION",
                    success=False,
                    message="Win32 LockWorkStation call returned 0 (failed).",
                )
        except Exception as ex:
            logger.error("Failed to execute LockWorkStation: %s", ex)
            return EmergencyActionResponse(
                action="LOCK_WORKSTATION",
                success=False,
                message=f"Failed to lock workstation: {ex}",
            )
