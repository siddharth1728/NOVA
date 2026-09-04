"""Deterministic window targeting and resolution engine."""

import logging
import re
from typing import Sequence

from nova.control.windows.enumeration import enumerate_windows, get_window_info
from nova.control.windows.models import WindowInfo, WindowTarget
from nova.errors import AmbiguousTargetError, WindowNotFoundError

logger = logging.getLogger("nova.control.windows.targeting")


def resolve_target_window(
    target: WindowTarget,
    windows: Sequence[WindowInfo] | None = None,
) -> WindowInfo:
    """Deterministically resolve targeting criteria into a single verified WindowInfo.

    Raises:
        WindowNotFoundError: When no windows match the criteria.
        AmbiguousTargetError: When multiple candidates match without unique disambiguation.
    """
    # 1. Direct HWND lookup (fastest and most deterministic)
    if target.hwnd is not None:
        if windows is not None:
            for w in windows:
                if w.hwnd == target.hwnd:
                    return w
        info = get_window_info(target.hwnd)
        if not info:
            raise WindowNotFoundError(f"Window with HWND {target.hwnd} does not exist", details={"hwnd": target.hwnd})
        return info


    candidates = list(windows) if windows is not None else enumerate_windows(visible_only=True)

    # 2. Exact title match
    if target.exact_title is not None:
        matched = [w for w in candidates if w.title.strip() == target.exact_title.strip()]
        if len(matched) == 1:
            return matched[0]
        if len(matched) > 1:
            raise AmbiguousTargetError(
                f"Multiple windows ({len(matched)}) match exact title '{target.exact_title}'",
                details={"candidates": [w.model_dump() for w in matched]},
            )
        raise WindowNotFoundError(
            f"No visible windows found with exact title '{target.exact_title}'",
            details={"exact_title": target.exact_title},
        )

    # 3. PID filtering
    if target.pid is not None:
        candidates = [w for w in candidates if w.pid == target.pid]
        if not candidates:
            raise WindowNotFoundError(f"No visible windows found for PID {target.pid}", details={"pid": target.pid})
        if len(candidates) == 1:
            return candidates[0]

    # 4. App Name / Executable filtering
    if target.app_name is not None:
        app_q = target.app_name.lower().strip()
        if not app_q.endswith(".exe"):
            app_q_exe = app_q + ".exe"
        else:
            app_q_exe = app_q

        candidates = [
            w for w in candidates
            if w.process_name.lower() == app_q_exe or app_q in w.process_name.lower()
        ]
        if not candidates:
            raise WindowNotFoundError(
                f"No visible windows found for application '{target.app_name}'",
                details={"app_name": target.app_name},
            )
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1 and target.title_pattern is None:
            fg_matched = [w for w in candidates if w.is_foreground]
            if len(fg_matched) == 1:
                return fg_matched[0]
            raise AmbiguousTargetError(
                f"Ambiguous window target: {len(candidates)} windows match application '{target.app_name}'",
                details={"candidates": [w.model_dump() for w in candidates]},
            )


    # 5. Title pattern match
    if target.title_pattern is not None:
        pattern = target.title_pattern.strip()
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            matched = [w for w in candidates if regex.search(w.title)]
        except re.error:
            # Fallback to simple substring
            pat_lower = pattern.lower()
            matched = [w for w in candidates if pat_lower in w.title.lower()]

        if len(matched) == 1:
            return matched[0]
        if len(matched) > 1:
            # If one is foreground, check if user intended foreground
            fg_matched = [w for w in matched if w.is_foreground]
            if len(fg_matched) == 1:
                logger.info("Disambiguated candidate by active foreground state: %s", fg_matched[0].title)
                return fg_matched[0]

            raise AmbiguousTargetError(
                f"Ambiguous window target: {len(matched)} windows match pattern '{pattern}'",
                details={
                    "pattern": pattern,
                    "candidates": [{"hwnd": w.hwnd, "title": w.title, "pid": w.pid} for w in matched],
                },
            )
        raise WindowNotFoundError(
            f"No visible windows match pattern '{pattern}'",
            details={"pattern": pattern},
        )

    if not candidates:
        raise WindowNotFoundError("No windows found matching targeting criteria", details=target.model_dump())

    if len(candidates) == 1:
        return candidates[0]

    raise AmbiguousTargetError(
        f"Target criteria '{target}' is ambiguous across {len(candidates)} windows",
        details={"candidates": [{"hwnd": w.hwnd, "title": w.title, "pid": w.pid} for w in candidates]},
    )
