"""Structured logging setup and secret redaction filters."""

import logging
import re
from typing import Any

# Patterns and key names associated with confidential secrets
SENSITIVE_KEY_PATTERN = re.compile(
    r"(api[_-]?key|secret|token|password|auth|credential|bearer|private[_-]?key)",
    re.IGNORECASE,
)

# Regex matching probable raw API tokens (e.g. AIzaSy..., Bearer ..., sk-...)
SECRET_VALUE_PATTERN = re.compile(
    r"(AIza[0-9A-Za-z\-_]{30,45}|Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*|sk-[A-Za-z0-9]{20,})",
    re.IGNORECASE,
)


def redact_sensitive_data(data: Any) -> Any:
    """Recursively scrub sensitive keys and token values from payloads.

    Args:
        data: Arbitrary data structure (dict, list, str, primitive).

    Returns:
        Scrubbed copy with secrets masked by '[REDACTED]'.
    """
    if isinstance(data, dict):
        cleaned: dict[str, Any] = {}
        for k, v in data.items():
            if SENSITIVE_KEY_PATTERN.search(str(k)):
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_sensitive_data(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    elif isinstance(data, str):
        return SECRET_VALUE_PATTERN.sub("[REDACTED]", data)
    return data


class SecretRedactionFilter(logging.Filter):
    """Logging filter that ensures raw secrets are scrubbed before reaching any handler."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = SECRET_VALUE_PATTERN.sub("[REDACTED]", record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = redact_sensitive_data(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(redact_sensitive_data(a) for a in record.args)
        return True


def configure_logging(level_name: str = "INFO") -> None:
    """Configures application-wide logging with redaction filters."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    logger = logging.getLogger("nova")
    logger.setLevel(level)

    # Avoid duplicate handlers if reconfigured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [NOVA] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SecretRedactionFilter())
        logger.addHandler(handler)
