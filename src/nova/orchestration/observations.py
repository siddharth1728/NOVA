"""Normalized empirical observation collector across NOVA control domains."""

from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
from typing import Any
import psutil

from nova.control.browsers.playwright_manager import get_browser_controller
from nova.control.clipboard.manager import WindowsClipboardController
from nova.control.windows.manager import WindowsWindowController
from nova.orchestration.models import Observation, ObservationDomain
from nova.transactions.manager import compute_file_hash

logger = logging.getLogger("nova.orchestration.observations")

# Maximum string length for attribute summaries to prevent context explosion
MAX_ATTR_STRING_LEN = 500

PROMPT_INJECTION_TRIGGERS = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard all",
    "system prompt",
    "you are now an unrestricted",
    "bypass safety",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_attributes(attrs: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Sanitize attributes to keep them bounded and detect security flags."""
    clean: dict[str, Any] = {}
    safety_flags: list[str] = []

    for k, v in attrs.items():
        if isinstance(v, str):
            lower_v = v.lower()
            for trigger in PROMPT_INJECTION_TRIGGERS:
                if trigger in lower_v:
                    safety_flags.append(f"prompt_injection_pattern_detected:{trigger}")
                    break
            if len(v) > MAX_ATTR_STRING_LEN:
                clean[k] = v[:MAX_ATTR_STRING_LEN] + "…[TRUNCATED]"
            else:
                clean[k] = v
        elif isinstance(v, (int, float, bool, type(None))):
            clean[k] = v
        elif isinstance(v, list):
            clean[k] = v[:20]  # cap list lengths
        elif isinstance(v, dict):
            sub_clean, sub_flags = _sanitize_attributes(v)
            clean[k] = sub_clean
            safety_flags.extend(sub_flags)
        else:
            clean[k] = str(v)[:MAX_ATTR_STRING_LEN]

    return clean, list(set(safety_flags))


class ObservationCollector:
    """Collects bounded, normalized empirical observations from the host environment."""

    def __init__(
        self,
        window_controller: WindowsWindowController | None = None,
        clipboard_controller: WindowsClipboardController | None = None,
    ) -> None:
        self.win_ctrl = window_controller or WindowsWindowController()
        self.clip_ctrl = clipboard_controller or WindowsClipboardController()

    async def observe(
        self,
        domain: ObservationDomain | str,
        target: Any = None,
        **kwargs: Any,
    ) -> Observation:
        if isinstance(domain, ObservationDomain):
            dom = domain
        elif isinstance(domain, str):
            clean = domain.split(".")[-1].upper()
            try:
                dom = ObservationDomain(clean)
            except ValueError:
                dom = ObservationDomain.GENERAL
        else:
            dom = ObservationDomain.GENERAL

        try:
            if dom == ObservationDomain.FILESYSTEM:
                return self._observe_filesystem(target)
            elif dom == ObservationDomain.WINDOWS:
                return self._observe_windows(target, **kwargs)
            elif dom == ObservationDomain.BROWSER:
                return await self._observe_browser(target, **kwargs)
            elif dom == ObservationDomain.PROCESS:
                return self._observe_process(target)
            elif dom == ObservationDomain.CLIPBOARD:
                return self._observe_clipboard()
            else:
                return self._observe_general(target, **kwargs)
        except Exception as ex:
            logger.warning("Observation failed for domain %s (target=%s): %s", dom.value, target, ex)
            return Observation(
                source=dom,
                entity=str(target or "unknown"),
                state="error",
                relevant_attributes={"error": str(ex)},
                confidence=0.0,
                safety_flags=["observation_failure"],
            )

    def _observe_filesystem(self, target: Any) -> Observation:
        path = Path(str(target)) if target else Path(".")
        exists = path.exists()

        attrs: dict[str, Any] = {"exists": exists}
        if exists:
            is_file = path.is_file()
            attrs["type"] = "file" if is_file else ("dir" if path.is_dir() else "other")
            try:
                stat = path.stat()
                attrs["size_bytes"] = stat.st_size
                if is_file and stat.st_size <= 5 * 1024 * 1024:  # Hash only files <= 5MB
                    attrs["hash_sha256"] = compute_file_hash(path)
            except Exception as e:
                attrs["stat_error"] = str(e)

        clean_attrs, flags = _sanitize_attributes(attrs)
        return Observation(
            source=ObservationDomain.FILESYSTEM,
            entity=str(path),
            state="exists" if exists else "missing",
            relevant_attributes=clean_attrs,
            confidence=1.0,
            safety_flags=flags,
        )

    def _observe_windows(self, target: Any, **kwargs: Any) -> Observation:
        hwnd = kwargs.get("hwnd")
        if hwnd is None and isinstance(target, int):
            hwnd = target

        fg = self.win_ctrl.get_foreground_window()
        is_focused = (fg is not None and hwnd is not None and fg.hwnd == hwnd)

        attrs: dict[str, Any] = {
            "foreground_hwnd": fg.hwnd if fg else None,
            "foreground_title": fg.title if fg else None,
            "is_focused": is_focused,
        }

        entity = f"HWND:{hwnd}" if hwnd is not None else (str(target) if target else "desktop")
        state = "focused" if is_focused else ("open" if hwnd else "enumerated")

        clean_attrs, flags = _sanitize_attributes(attrs)
        return Observation(
            source=ObservationDomain.WINDOWS,
            entity=entity,
            state=state,
            relevant_attributes=clean_attrs,
            confidence=1.0,
            safety_flags=flags,
        )

    async def _observe_browser(self, target: Any, **kwargs: Any) -> Observation:
        browser = get_browser_controller()
        tab_id = str(target) if target else kwargs.get("tab_id")

        tabs = await browser.list_tabs()
        matching_tab = next((t for t in tabs if t.tab_id == tab_id), None) if tab_id else (tabs[0] if tabs else None)

        if matching_tab:
            attrs: dict[str, Any] = {
                "tab_id": matching_tab.tab_id,
                "title": matching_tab.title,
                "url": matching_tab.url,
                "total_tabs": len(tabs),
            }
            # Attempt light inspect if tab available
            try:
                elements = await browser.inspect(matching_tab.tab_id)
                attrs["element_count"] = len(elements)
            except Exception:
                pass

            clean_attrs, flags = _sanitize_attributes(attrs)
            return Observation(
                source=ObservationDomain.BROWSER,
                entity=matching_tab.tab_id,
                state="open",
                relevant_attributes=clean_attrs,
                confidence=1.0,
                safety_flags=flags,
            )
        else:
            return Observation(
                source=ObservationDomain.BROWSER,
                entity=str(tab_id or "none"),
                state="closed",
                relevant_attributes={"total_tabs": len(tabs)},
                confidence=1.0,
                safety_flags=[],
            )

    def _observe_process(self, target: Any) -> Observation:
        pid = int(target) if str(target).isdigit() else None
        running = False
        attrs: dict[str, Any] = {}

        if pid is not None:
            running = psutil.pid_exists(pid)
            attrs["pid"] = pid
            attrs["running"] = running
            if running:
                try:
                    p = psutil.Process(pid)
                    attrs["name"] = p.name()
                    attrs["status"] = p.status()
                except Exception:
                    pass
        else:
            name_str = str(target).lower()
            matching = [p.pid for p in psutil.process_iter(["name"]) if name_str in (p.info["name"] or "").lower()]
            running = len(matching) > 0
            attrs["matching_pids"] = matching[:5]
            attrs["running"] = running

        clean_attrs, flags = _sanitize_attributes(attrs)
        return Observation(
            source=ObservationDomain.PROCESS,
            entity=str(target),
            state="running" if running else "terminated",
            relevant_attributes=clean_attrs,
            confidence=1.0,
            safety_flags=flags,
        )

    def _observe_clipboard(self) -> Observation:
        meta = self.clip_ctrl.inspect()
        attrs = {
            "has_text": meta.has_text,
            "text_length": meta.text_length,
            "hash_sha256": meta.hash_sha256,
        }
        clean_attrs, flags = _sanitize_attributes(attrs)
        return Observation(
            source=ObservationDomain.CLIPBOARD,
            entity="system_clipboard",
            state="has_text" if meta.has_text else "empty",
            relevant_attributes=clean_attrs,
            confidence=1.0,
            safety_flags=flags,
        )

    def _observe_general(self, target: Any, **kwargs: Any) -> Observation:
        clean_attrs, flags = _sanitize_attributes(kwargs)
        return Observation(
            source=ObservationDomain.GENERAL,
            entity=str(target or "general"),
            state="observed",
            relevant_attributes=clean_attrs,
            confidence=0.9,
            safety_flags=flags,
        )
