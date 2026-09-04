"""Windows clipboard controller implementation with sensitive data protection."""

import hashlib
import logging
import win32clipboard
import win32con

from nova.control.clipboard.models import ClipboardContent, ClipboardType
from nova.control.interfaces import ClipboardController
from nova.errors import ClipboardAccessError

logger = logging.getLogger("nova.control.clipboard.manager")


class WindowsClipboardController(ClipboardController):
    """Authoritative Windows clipboard controller with hash tracking and format detection."""

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._mock_text: str = ""

    def read_text(self) -> str | None:
        """Read textual content currently in system clipboard."""
        if self.dry_run:
            return self._mock_text

        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                    data = win32clipboard.GetClipboardData(win32con.CF_TEXT)
                    return data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
                return None
            finally:
                win32clipboard.CloseClipboard()
        except Exception as ex:
            logger.error("Failed to read clipboard: %s", ex)
            raise ClipboardAccessError(f"Failed to read clipboard: {ex}") from ex

    def write_text(self, text: str) -> bool:
        """Write text to system clipboard."""
        if self.dry_run:
            self._mock_text = text
            return True

        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
                return True
            finally:
                win32clipboard.CloseClipboard()
        except Exception as ex:
            logger.error("Failed to write clipboard: %s", ex)
            raise ClipboardAccessError(f"Failed to write clipboard: {ex}") from ex

    def clear(self) -> bool:
        """Empty system clipboard contents."""
        if self.dry_run:
            self._mock_text = ""
            return True

        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                return True
            finally:
                win32clipboard.CloseClipboard()
        except Exception as ex:
            logger.error("Failed to clear clipboard: %s", ex)
            raise ClipboardAccessError(f"Failed to clear clipboard: {ex}") from ex

    def inspect(self) -> ClipboardContent:
        """Inspect clipboard metadata and compute SHA-256 hash without leaking secrets."""
        if self.dry_run:
            has_txt = bool(self._mock_text)
            h = hashlib.sha256(self._mock_text.encode("utf-8")).hexdigest() if has_txt else None
            return ClipboardContent(
                content_type=ClipboardType.TEXT if has_txt else ClipboardType.EMPTY,
                has_text=has_txt,
                text_length=len(self._mock_text),
                hash_sha256=h,
                text_preview=self._mock_text[:30] if has_txt else None,
            )

        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT) or ""
                    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    return ClipboardContent(
                        content_type=ClipboardType.TEXT,
                        has_text=True,
                        text_length=len(text),
                        hash_sha256=h,
                        text_preview=text[:30] if len(text) > 0 else None,
                    )
                elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_BITMAP):
                    return ClipboardContent(content_type=ClipboardType.BITMAP)
                elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                    return ClipboardContent(content_type=ClipboardType.FILES)
                elif win32clipboard.CountClipboardFormats() == 0:
                    return ClipboardContent(content_type=ClipboardType.EMPTY)
                return ClipboardContent(content_type=ClipboardType.OTHER)
            finally:
                win32clipboard.CloseClipboard()
        except Exception as ex:
            logger.warning("Clipboard inspection failed: %s", ex)
            return ClipboardContent(content_type=ClipboardType.EMPTY)
