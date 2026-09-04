"""Windows application discovery provider.

Scans Start Menu directories, Windows Registry App Paths, and running processes
to build a structured catalog of available applications.
"""

import logging
import os
from pathlib import Path
import psutil
import winreg

from nova.control.applications.models import AppInfo

logger = logging.getLogger("nova.control.applications.discovery")


COMMON_SYSTEM_APPS = [
    {"name": "Notepad", "executable": "notepad.exe", "path": "notepad.exe", "category": "editor"},
    {"name": "Calculator", "executable": "calc.exe", "path": "calc.exe", "category": "utility"},
    {"name": "File Explorer", "executable": "explorer.exe", "path": "explorer.exe", "category": "system"},
    {"name": "Windows Terminal", "executable": "wt.exe", "path": "wt.exe", "category": "developer"},
    {"name": "Microsoft Edge", "executable": "msedge.exe", "path": "msedge.exe", "category": "browser"},
    {"name": "Google Chrome", "executable": "chrome.exe", "path": "chrome.exe", "category": "browser"},
    {"name": "Visual Studio Code", "executable": "Code.exe", "path": "code", "category": "developer"},
    {"name": "Task Manager", "executable": "taskmgr.exe", "path": "taskmgr.exe", "category": "system"},
]


class WindowsAppDiscovery:
    """Discovers installed, registered, and running Windows applications."""

    def __init__(self) -> None:
        self._cache: list[AppInfo] | None = None

    def list_applications(self, search: str | None = None, force_refresh: bool = False) -> list[AppInfo]:
        """Returns discovered applications, optionally filtered by keyword."""
        if self._cache is None or force_refresh:
            self._cache = self._discover()

        apps = self._cache
        if search:
            q = search.lower().strip()
            apps = [a for a in apps if q in a.name.lower() or q in a.executable.lower()]
        return apps

    def find_application(self, name_or_path: str) -> AppInfo | None:
        """Find a specific application by exact or partial match."""
        apps = self.list_applications()
        q = name_or_path.lower().strip()
        # 1. Exact match on executable or name
        for a in apps:
            if a.executable.lower() == q or a.name.lower() == q:
                return a
        # 2. Substring match
        for a in apps:
            if q in a.executable.lower() or q in a.name.lower():
                return a
        return None

    def is_running(self, app_name: str) -> bool:
        """Check whether any process matches the application name or executable."""
        target = app_name.lower().strip()
        if not target.endswith(".exe"):
            target_exe = target + ".exe"
        else:
            target_exe = target

        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info.get("name") or ""
                if name.lower() == target_exe or name.lower() == target:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    def _discover(self) -> list[AppInfo]:
        """Aggregate discovery from common apps, registry, and running processes."""
        discovered: dict[str, AppInfo] = {}

        # 1. Base system apps
        for item in COMMON_SYSTEM_APPS:
            discovered[item["executable"].lower()] = AppInfo(
                name=item["name"],
                executable=item["executable"],
                path=item["path"],
                category=item["category"],
            )

        # 2. Registry App Paths
        self._scan_registry_app_paths(discovered)

        # 3. Start Menu shortcuts
        self._scan_start_menu_dirs(discovered)

        # 4. Check running states
        running_names = set()
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info.get("name")
                if name:
                    running_names.add(name.lower())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        for app in discovered.values():
            if app.executable.lower() in running_names:
                app.is_running = True

        return list(discovered.values())

    def _scan_registry_app_paths(self, discovered: dict[str, AppInfo]) -> None:
        """Scan HKLM and HKCU App Paths for registered executables."""
        subkeys = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        ]
        for root_key, subkey_path in subkeys:
            try:
                with winreg.OpenKey(root_key, subkey_path) as key:
                    num_subkeys = winreg.QueryInfoKey(key)[0]
                    for i in range(num_subkeys):
                        try:
                            app_exe = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, app_exe) as app_key:
                                try:
                                    path_val, _ = winreg.QueryValueEx(app_key, "")
                                    if path_val and os.path.exists(path_val):
                                        stem = Path(app_exe).stem
                                        name = stem.replace("_", " ").title()
                                        exe_lower = app_exe.lower()
                                        if exe_lower not in discovered:
                                            discovered[exe_lower] = AppInfo(
                                                name=name,
                                                executable=app_exe,
                                                path=str(path_val),
                                                category="application",
                                            )
                                except OSError:
                                    pass
                        except OSError:
                            pass
            except OSError:
                pass

    def _scan_start_menu_dirs(self, discovered: dict[str, AppInfo]) -> None:
        """Scan Start Menu folders for application shortcuts."""
        paths_to_scan: list[Path] = []
        program_data = os.environ.get("ProgramData")
        if program_data:
            paths_to_scan.append(Path(program_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        app_data = os.environ.get("APPDATA")
        if app_data:
            paths_to_scan.append(Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

        for base_dir in paths_to_scan:
            if not base_dir.exists():
                continue
            for root, _, files in os.walk(base_dir):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        name = f[:-4]
                        key = name.lower() + ".exe"
                        if key not in discovered:
                            discovered[key] = AppInfo(
                                name=name,
                                executable=name + ".exe",
                                path=str(Path(root) / f),
                                category="start_menu",
                            )
