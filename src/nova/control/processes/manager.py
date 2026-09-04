"""Windows process inspection and supervised termination."""

from datetime import datetime, timezone
import logging
import os
import psutil

from nova.control.interfaces import ProcessController
from nova.control.processes.models import ProcessFilter, ProcessInfo, ProcessStopResult
from nova.errors import ProcessAccessDeniedError, ProtectedProcessError

logger = logging.getLogger("nova.control.processes.manager")

# Critical Windows OS and NOVA host binaries that must NEVER be terminated by automated agents
PROTECTED_PROCESS_NAMES = frozenset({
    "csrss.exe",
    "lsass.exe",
    "smss.exe",
    "services.exe",
    "svchost.exe",
    "wininit.exe",
    "winlogon.exe",
    "explorer.exe",
    "dwm.exe",
    "taskhostw.exe",
    "runtimebroker.exe",
    "securityhealthservice.exe",
    "msmpeng.exe",
})


class WindowsProcessController(ProcessController):
    """Authoritative Windows process controller with protected process enforcement."""

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._current_pid = os.getpid()

    def list_processes(self, filter_criteria: ProcessFilter | None = None) -> list[ProcessInfo]:
        """Enumerate active processes with resource usage."""
        if self.dry_run:
            return [
                ProcessInfo(
                    pid=1234,
                    name="python.exe",
                    exe=r"C:\KaryaSetu\.venv\Scripts\python.exe",
                    cpu_percent=1.5,
                    memory_percent=0.8,
                    memory_mb=120.5,
                    status="running",
                    parent_pid=100,
                    created_at="2026-09-04T12:00:00Z",
                ),
                ProcessInfo(
                    pid=5678,
                    name="notepad.exe",
                    exe=r"C:\Windows\System32\notepad.exe",
                    cpu_percent=0.0,
                    memory_percent=0.1,
                    memory_mb=25.2,
                    status="running",
                    parent_pid=1234,
                    created_at="2026-09-04T12:01:00Z",
                ),
            ]

        crit = filter_criteria or ProcessFilter()
        results: list[ProcessInfo] = []

        attrs = ["pid", "name", "exe", "cpu_percent", "memory_percent", "memory_info", "status", "ppid", "create_time"]
        for proc in psutil.process_iter(attrs):
            try:
                info = proc.info
                name = info.get("name") or "unknown"
                pid = info.get("pid") or 0

                # Filter by name pattern
                if crit.name_substring and crit.name_substring.lower() not in name.lower():
                    continue

                mem_info = info.get("memory_info")
                mem_mb = round(mem_info.rss / (1024 * 1024), 1) if mem_info else 0.0
                if crit.min_memory_mb and mem_mb < crit.min_memory_mb:
                    continue

                cpu = round(info.get("cpu_percent") or 0.0, 1)
                if crit.min_cpu_percent and cpu < crit.min_cpu_percent:
                    continue

                created_dt = None
                if info.get("create_time"):
                    created_dt = datetime.fromtimestamp(info["create_time"], tz=timezone.utc).isoformat()

                p_info = ProcessInfo(
                    pid=pid,
                    name=name,
                    exe=info.get("exe"),
                    cpu_percent=cpu,
                    memory_percent=round(info.get("memory_percent") or 0.0, 1),
                    memory_mb=mem_mb,
                    status=info.get("status") or "running",
                    parent_pid=info.get("ppid"),
                    created_at=created_dt,
                )
                results.append(p_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort order
        if crit.sort_by == "cpu":
            results.sort(key=lambda p: p.cpu_percent, reverse=True)
        elif crit.sort_by == "name":
            results.sort(key=lambda p: p.name.lower())
        else:
            results.sort(key=lambda p: p.memory_mb, reverse=True)

        return results[: crit.limit]

    def inspect_process(self, pid: int) -> ProcessInfo | None:
        """Inspect detailed telemetry for a single process."""
        if self.dry_run:
            return ProcessInfo(
                pid=pid,
                name="mock_proc.exe",
                exe=r"C:\Mock\mock_proc.exe",
                cpu_percent=0.5,
                memory_percent=0.2,
                memory_mb=50.0,
                status="running",
                parent_pid=1,
            )

        try:
            p = psutil.Process(pid)
            mem_mb = round(p.memory_info().rss / (1024 * 1024), 1)
            created_dt = datetime.fromtimestamp(p.create_time(), tz=timezone.utc).isoformat()
            return ProcessInfo(
                pid=pid,
                name=p.name(),
                exe=p.exe() if hasattr(p, "exe") else None,
                cpu_percent=round(p.cpu_percent(interval=None), 1),
                memory_percent=round(p.memory_percent(), 1),
                memory_mb=mem_mb,
                status=p.status(),
                parent_pid=p.ppid(),
                created_at=created_dt,
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def stop_process(self, pid: int, force: bool = False) -> ProcessStopResult:
        """Terminate a process, enforcing protected process guards."""
        # 1. Guard against self-termination of NOVA Host
        if pid == self._current_pid:
            raise ProtectedProcessError(
                f"Refusing to terminate current host process (PID {pid})",
                details={"pid": pid, "reason": "Self-preservation guard"},
            )

        if pid in (0, 4):
            raise ProtectedProcessError(
                f"Process with PID {pid} is a protected Windows core process and cannot be terminated",
                details={"pid": pid},
            )

        name = "unknown"
        proc_obj = None
        try:
            proc_obj = psutil.Process(pid)
            name = proc_obj.name()
        except psutil.NoSuchProcess:
            if not self.dry_run:
                return ProcessStopResult(pid=pid, name="unknown", success=True, message="Process was already absent.")
        except psutil.AccessDenied as ex:
            if not self.dry_run:
                raise ProcessAccessDeniedError(f"Access denied inspecting PID {pid}: {ex}", details={"pid": pid}) from ex

        # 2. Guard against critical OS processes
        if name.lower() in PROTECTED_PROCESS_NAMES:
            raise ProtectedProcessError(
                f"Process '{name}' (PID {pid}) is protected by Windows system policy and cannot be terminated",
                details={"pid": pid, "name": name},
            )

        if self.dry_run:
            return ProcessStopResult(pid=pid, name=name if name != "unknown" else "mock_proc.exe", success=True, message="Process terminated (dry-run).")

        p = proc_obj
        if p is None:
            return ProcessStopResult(pid=pid, name="unknown", success=True, message="Process was already absent.")

        # 3. Terminate process
        try:
            if force:
                p.kill()
            else:
                p.terminate()

            # Empirical verification: wait up to 2 seconds for process to exit
            gone, _ = psutil.wait_procs([p], timeout=2.0)
            if p in gone:
                return ProcessStopResult(
                    pid=pid,
                    name=name,
                    success=True,
                    message=f"Process '{name}' (PID {pid}) successfully terminated.",
                )
            else:
                # Force kill if graceful termination timed out
                p.kill()
                gone, _ = psutil.wait_procs([p], timeout=1.0)
                return ProcessStopResult(
                    pid=pid,
                    name=name,
                    success=(p in gone),
                    message=f"Process '{name}' force-killed (exit verified: {p in gone}).",
                )
        except psutil.NoSuchProcess:
            return ProcessStopResult(pid=pid, name=name, success=True, message="Process exited successfully.")
        except psutil.AccessDenied as ex:
            raise ProcessAccessDeniedError(f"Access denied terminating '{name}' (PID {pid}): {ex}", details={"pid": pid}) from ex
