"""Models for UI Automation and Vision Fallback targeting."""

from typing import Any
from pydantic import BaseModel, Field

from nova.control.windows.models import WindowBounds


class UIElementInfo(BaseModel):
    """Semantic properties of a Windows UI Automation element."""

    name: str = Field(description="Accessible name / label of element")
    automation_id: str = Field(default="", description="Developer automation identifier")
    control_type: str = Field(description="UIA ControlType (Button, Edit, Text, MenuItem, etc.)")
    class_name: str = Field(default="", description="Underlying Win32 or WPF class name")
    bounds: WindowBounds | None = Field(default=None, description="Screen bounding rectangle")
    is_enabled: bool = Field(default=True, description="Whether element is interactive")
    is_visible: bool = Field(default=True, description="Whether element is visible")
    value: str | None = Field(default=None, description="Current text or numeric value")
    has_focus: bool = Field(default=False, description="Whether element holds active input focus")


class UIElementTarget(BaseModel):
    """Query criteria for locating a specific UI Automation control."""

    name: str | None = Field(default=None, description="Element accessible name to match")
    automation_id: str | None = Field(default=None, description="Exact AutomationId")
    control_type: str | None = Field(default=None, description="ControlType filter (e.g. Button, Edit)")


class VisionTarget(BaseModel):
    """Target candidate proposed by computer vision analysis."""

    screen_id: str = Field(description="Unique observation ID of analyzed frame")
    capture_timestamp: str = Field(description="ISO-8601 timestamp when frame was grabbed")
    x: int = Field(description="Center X coordinate")
    y: int = Field(description="Center Y coordinate")
    width: int = Field(description="Candidate width")
    height: int = Field(description="Candidate height")
    confidence: float = Field(description="Model confidence score between 0.0 and 1.0")
    description: str = Field(description="Visual description of identified element")


class TargetingResult(BaseModel):
    """Resolved targeting output through the deterministic cascade."""

    method: str = Field(description="Resolution method: WIN32_API, UI_AUTOMATION, or VISION")
    success: bool = Field(default=True)
    hwnd: int | None = Field(default=None)
    element: UIElementInfo | None = Field(default=None)
    coordinates: tuple[int, int] | None = Field(default=None)
    confidence: float = Field(default=1.0)
    fallback_reason: str | None = Field(default=None)
