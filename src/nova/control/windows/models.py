"""Models for Windows window enumeration, targeting, and management."""

from pydantic import BaseModel, Field


class WindowBounds(BaseModel):
    """Bounding rectangle dimensions for a window."""

    x: int = Field(description="Left coordinate")
    y: int = Field(description="Top coordinate")
    width: int = Field(description="Width in pixels")
    height: int = Field(description="Height in pixels")

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


class WindowInfo(BaseModel):
    """Structured information describing a top-level Windows application window."""

    hwnd: int = Field(description="Native Win32 window handle")
    title: str = Field(description="Window title text")
    process_name: str = Field(description="Owning executable filename (e.g. notepad.exe)")
    pid: int = Field(description="Owning Process ID")
    bounds: WindowBounds = Field(description="Window rectangular bounds on desktop")
    visible: bool = Field(default=True, description="Whether window is currently visible")
    is_foreground: bool = Field(default=False, description="Whether window has active input focus")
    is_minimized: bool = Field(default=False, description="Whether window is iconified/minimized")
    is_maximized: bool = Field(default=False, description="Whether window is maximized")


class WindowTarget(BaseModel):
    """Targeting criteria used to resolve an application window."""

    hwnd: int | None = Field(default=None, description="Exact HWND if known")
    pid: int | None = Field(default=None, description="Owning Process ID")
    app_name: str | None = Field(default=None, description="Process executable or app name")
    title_pattern: str | None = Field(default=None, description="Case-insensitive title substring or pattern")
    exact_title: str | None = Field(default=None, description="Exact window title match")
