"""Models for clipboard management."""

from enum import Enum
from pydantic import BaseModel, Field


class ClipboardType(str, Enum):
    """Identified data type resident in system clipboard."""

    EMPTY = "EMPTY"
    TEXT = "TEXT"
    BITMAP = "BITMAP"
    FILES = "FILES"
    OTHER = "OTHER"


class ClipboardContent(BaseModel):
    """Metadata describing clipboard contents without leaking raw secret payload."""

    content_type: ClipboardType = Field(default=ClipboardType.EMPTY)
    has_text: bool = Field(default=False)
    text_length: int = Field(default=0)
    hash_sha256: str | None = Field(default=None, description="SHA-256 hash of text payload for change detection")
    text_preview: str | None = Field(default=None, description="Truncated preview of text content if non-sensitive")
