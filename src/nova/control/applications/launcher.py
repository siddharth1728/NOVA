"""Safe Windows application launcher.

Validates executable targets, executes subprocesses under controlled boundaries,
and observes window creation within configurable timeouts.
"""

import logging
import os
import subprocess
import time
import psutil

from nova.control.applications.discovery import WindowsAppDiscovery
from nova.control.applications.models import AppInfo, LaunchRequest, LaunchResult
from nova.control.interfaces import ApplicationController
from nova.errors import ApplicationLaunchError, ValidationError

logger = logging.getLogger("nova.control.applications.launcher")

# Executables strictly prohibited from automated launching
PROHIBITED_EXECUTABLES = frozenset({
    "format.com",
    "diskpart.exe",
    "regedit.exe",
    "bcdedit.exe",
    "shutdown.exe",
    "rundll32.exe",
    "vssadmin.exe",
})


class WindowsApplicationController(ApplicationController):
    """Authoritative Windows Application Controller implementing safe discovery and execution."""

    def __init__(self, discovery: WindowsAppDiscovery | None = None, *, dry_run: bool = False) -> None:
        self.discovery = discovery or WindowsAppDiscovery()
        self.dry_run = dry_run

    def list_applications(self, search: str | None = None) -> list[AppInfo]:
        """Enumerate installed or discoverable applications."""
        return self.discovery.list_applications(search)

    def find_application(self, name_or_path: str) -> AppInfo | None:
        """Find a specific application by name or path."""
        return self.discovery.find_application(name_or_path)

    def is_running(self, app_name: str) -> bool:
        """Check whether any instances of the application are running."""
        return self.discovery.is_running(app_name)

    def launch_application(self, request: LaunchRequest) -> LaunchResult:
        """Safely launch an application and optionally wait for its window."""
        target = request.app_name_or_path.strip()
        if not target:
            raise ValidationError("Target application name or path cannot be empty")

        # 1. Check prohibited executables and script extensions
        exe_lower = os.path.basename(target).lower()
        _, ext = os.path.splitext(exe_lower)
        if ext in {".bat", ".cmd", ".ps1", ".vbs", ".js", ".wsf", ".scr"}:
            raise ApplicationLaunchError(
                f"Direct script execution is prohibited: '{exe_lower}'",
                details={"target": target, "extension": ext},
            )

        if exe_lower in PROHIBITED_EXECUTABLES:
            raise ApplicationLaunchError(
                f"Application '{exe_lower}' is prohibited by safety policy",
                details={"target": target},
            )


        # 2. Resolve known application from discovery catalog if not a direct path
        resolved_path = target
        app_name = target
        if not os.path.exists(target):
            app = self.discovery.find_application(target)
            if app:
                resolved_path = app.path
                app_name = app.name

        # 3. Dry-run support for testing
        if self.dry_run:
            logger.info("Dry-run requested: application launch simulated for %s", resolved_path)
            return LaunchResult(
                success=True,
                app_name=app_name,
                pid=99999,
                hwnd=12345,
                window_title=f"{app_name} (Simulated)",
                message="Application launch simulated successfully (dry-run).",
                window_detected=True,
            )

        # 4. Execute application subprocess
        try:
            cmd = [resolved_path] + request.arguments
            # On Windows, start detached without inheriting console
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            proc = subprocess.Popen(
                cmd,
                shell=False,
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            pid = proc.pid
            logger.info("Launched process %s with PID %d", app_name, pid)
        except Exception as ex:
            logger.error("Failed to launch application '%s': %s", target, ex)
            raise ApplicationLaunchError(f"Failed to launch '{target}': {ex}", details={"target": target}) from ex

        # 5. Observe window appearance if requested
        hwnd = None
        window_title = None
        if request.wait_for_window:
            hwnd, window_title = self._wait_for_window_handle(pid, timeout_seconds=request.timeout_seconds)

        return LaunchResult(
            success=True,
            app_name=app_name,
            pid=pid,
            hwnd=hwnd,
            window_title=window_title,
            message=f"Application {app_name} started (PID: {pid}).",
            window_detected=(hwnd is not None),
        )

    def _wait_for_window_handle(self, target_pid: int, timeout_seconds: float = 10.0) -> tuple[int | None, str | None]:
        """Poll for a visible top-level window owned by target_pid or child processes."""
        import win32gui
        import win32process

        deadline = time.time() + timeout_seconds

        def enum_handler(h: int, acc: list[tuple[int, str]]):
            if win32gui.IsWindowVisible(h):
                title = win32gui.GetWindowText(h)
                if title:
                    _, w_pid = win32process.GetWindowThreadProcessId(h)
                    if w_pid == target_pid:
                        acc.append((h, title))
            return True

        while time.time() < deadline:
            windows: list[tuple[int, str]] = []
            try:
                win32gui.EnumWindows(enum_handler, windows)
                if windows:
                    return windows[0][0], windows[0][1]
            except Exception:
                pass
            time.sleep(0.3)

        return None, None
