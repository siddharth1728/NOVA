"""Models for Windows application discovery and launching."""

from pydantic import BaseModel, Field


class AppInfo(BaseModel):
    """Information regarding an installed or discoverable application."""

    name: str = Field(description="Display or executable name of the application")
    executable: str = Field(description="Binary executable name (e.g. notepad.exe)")
    path: str = Field(description="Full filesystem path or system command string")
    publisher: str | None = Field(default=None, description="Software vendor or publisher")
    is_running: bool = Field(default=False, description="Whether an instance is currently active")
    category: str = Field(default="general", description="Application category (editor, browser, etc.)")


class LaunchRequest(BaseModel):
    """Request payload to launch an application."""

    app_name_or_path: str = Field(description="Name or path of target application")
    arguments: list[str] = Field(default_factory=list, description="Optional command-line arguments")
    timeout_seconds: float = Field(default=10.0, description="Max seconds to wait for window appearance")
    wait_for_window: bool = Field(default=True, description="Whether to block until a top-level window appears")


class LaunchResult(BaseModel):
    """Outcome of an application launch attempt."""

    success: bool
    app_name: str
    pid: int | None = None
    hwnd: int | None = None
    window_title: str | None = None
    message: str | None = None
    window_detected: bool = False

