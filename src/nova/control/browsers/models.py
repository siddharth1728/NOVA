"""Models for browser automation abstractions."""

from pydantic import BaseModel, Field


class BrowserInfo(BaseModel):
    """Information regarding an installed web browser."""

    name: str = Field(description="Browser brand name (e.g. Edge, Chrome)")
    executable: str = Field(description="Executable filename")
    path: str | None = Field(default=None, description="Filesystem binary path")
    is_running: bool = Field(default=False)
    window_count: int = Field(default=0)


class BrowserTab(BaseModel):
    """Metadata describing a browser tab or document."""

    title: str = Field(description="Tab title")
    url: str | None = Field(default=None, description="Navigated URL if inspectable")
    is_active: bool = Field(default=True)
