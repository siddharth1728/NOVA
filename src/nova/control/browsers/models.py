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

    tab_id: str = Field(description="Unique NOVA tab identifier")
    title: str = Field(description="Tab title")
    url: str | None = Field(default=None, description="Navigated URL if inspectable")
    is_active: bool = Field(default=True)
    loading: bool = Field(default=False, description="Whether the tab is currently loading")


class DOMElement(BaseModel):
    """Structured representation of an interactive or meaningful page element."""

    ref: str = Field(description="Stable internal reference ID (e.g. el_104)")
    role: str = Field(description="Semantic role (e.g. button, link, textbox)")
    name: str = Field(description="Accessible name or visible text")
    tag: str = Field(description="HTML tag name")
    visible: bool = Field(default=True, description="Whether element is currently visible")
    enabled: bool = Field(default=True, description="Whether element is interactable")
    selector_strategy: str = Field(description="Strategy used to identify (e.g. semantic, xpath, css)")
    confidence: float = Field(default=1.0, description="Confidence in reference stability")
    is_sensitive: bool = Field(default=False, description="Whether input is likely sensitive (password, cc)")


class BrowserActionRequest(BaseModel):
    """Request to perform an action on a browser tab/element."""

    tab_id: str | None = Field(default=None, description="Target tab ID")
    action: str = Field(description="Action to perform (click, fill, select, hover, extract)")
    target_ref: str | None = Field(default=None, description="Target element reference (e.g. el_104)")
    value: str | None = Field(default=None, description="Value for fill or select actions")


class BrowserActionResult(BaseModel):
    """Result of a browser automation action."""

    success: bool = Field(description="Whether the action succeeded")
    error: str | None = Field(default=None, description="Error message if failed")
    state_changed: bool = Field(default=False, description="Whether a DOM or navigation change was detected")
    navigation_occurred: bool = Field(default=False, description="Whether a new page load started")
