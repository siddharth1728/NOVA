"""Models and enums for mouse and keyboard input control."""

from enum import Enum
from pydantic import BaseModel, Field


class MouseButton(str, Enum):
    """Mouse button identifiers."""

    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class MouseAction(str, Enum):
    """Types of mouse input actions."""

    MOVE = "move"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    DOWN = "down"
    UP = "up"
    DRAG = "drag"
    SCROLL = "scroll"


class Key(str, Enum):
    """Canonical typed keys supported for keyboard input."""

    ENTER = "ENTER"
    RETURN = "RETURN"
    ESCAPE = "ESCAPE"
    ESC = "ESC"
    TAB = "TAB"
    SPACE = "SPACE"
    BACKSPACE = "BACKSPACE"
    DELETE = "DELETE"
    INSERT = "INSERT"
    HOME = "HOME"
    END = "END"
    PAGE_UP = "PAGE_UP"
    PAGE_DOWN = "PAGE_DOWN"
    ARROW_UP = "UP"
    ARROW_DOWN = "DOWN"
    ARROW_LEFT = "LEFT"
    ARROW_RIGHT = "RIGHT"
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"
    F4 = "F4"
    F5 = "F5"
    F6 = "F6"
    F7 = "F7"
    F8 = "F8"
    F9 = "F9"
    F10 = "F10"
    F11 = "F11"
    F12 = "F12"
    CTRL = "CTRL"
    CONTROL = "CONTROL"
    ALT = "ALT"
    SHIFT = "SHIFT"
    WIN = "WIN"
    WINDOWS = "WINDOWS"


class KeyCombination(BaseModel):
    """Structured representation of a key chord (e.g. Ctrl+Shift+S)."""

    modifiers: list[str] = Field(default_factory=list, description="Modifier keys (CTRL, ALT, SHIFT, WIN)")
    key: str = Field(description="Primary key (letter, number, or special Key enum)")


class InputResult(BaseModel):
    """Outcome of an input injection action."""

    success: bool
    action: str
    target_hwnd: int | None = None
    details: dict[str, str | int | float | bool] = Field(default_factory=dict)
    message: str | None = None
