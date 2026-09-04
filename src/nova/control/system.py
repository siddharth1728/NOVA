"""Host system telemetry and resource provider for Windows."""

from datetime import datetime, timezone
import os
import platform
import socket
import psutil

from nova.protocol.models import SystemMetrics


class SystemMetricsProvider:
    """Collects real-time hardware, operating system, and uptime metrics."""

    def __init__(self, workspace_root: str | None = None) -> None:
        self.workspace_root = workspace_root or os.getcwd()

    def get_metrics(self) -> SystemMetrics:
        """Gather real-time CPU, RAM, disk, OS version, and boot metrics."""
        # CPU
        cpu_pct = psutil.cpu_percent(interval=None)

        # Virtual memory
        vm = psutil.virtual_memory()
        ram_total_gb = round(vm.total / (1024**3), 2)
        ram_used_gb = round(vm.used / (1024**3), 2)
        ram_pct = vm.percent

        # Disk usage for workspace partition or primary C: drive
        target_path = self.workspace_root if os.path.exists(self.workspace_root) else "C:\\"
        try:
            disk = psutil.disk_usage(target_path)
        except Exception:
            disk = psutil.disk_usage("C:\\")

        disk_total_gb = round(disk.total / (1024**3), 2)
        disk_used_gb = round(disk.used / (1024**3), 2)
        disk_pct = disk.percent

        # Boot time & uptime
        boot_timestamp = psutil.boot_time()
        boot_dt = datetime.fromtimestamp(boot_timestamp, tz=timezone.utc)
        uptime_secs = round(datetime.now(timezone.utc).timestamp() - boot_timestamp, 1)

        # OS and hostname
        os_ver = f"{platform.system()} {platform.release()} ({platform.version()})"
        host = socket.gethostname()

        return SystemMetrics(
            cpu_percent=cpu_pct,
            ram_total_gb=ram_total_gb,
            ram_used_gb=ram_used_gb,
            ram_percent=ram_pct,
            disk_total_gb=disk_total_gb,
            disk_used_gb=disk_used_gb,
            disk_percent=disk_pct,
            uptime_seconds=uptime_secs,
            boot_time=boot_dt.isoformat(),
            os_version=os_ver,
            hostname=host,
        )
