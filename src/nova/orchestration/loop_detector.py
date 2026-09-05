"""Loop detection and safety guards to prevent autonomous infinite execution."""

from collections import deque
import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger("nova.orchestration.loop_detector")


class LoopDetector:
    """Detects ineffective repeating actions, state oscillations, and failure runaway."""

    def __init__(
        self,
        max_repeated_identical_calls: int = 3,
        max_consecutive_failures: int = 4,
        history_window: int = 12,
    ) -> None:
        self.max_identical = max_repeated_identical_calls
        self.max_consecutive_failures = max_consecutive_failures
        self.history: deque[dict[str, Any]] = deque(maxlen=history_window)
        self.consecutive_failures: int = 0

    def _hash_args(self, args: dict[str, Any]) -> str:
        try:
            canonical = json.dumps(args, sort_keys=True, default=str)
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
        except Exception:
            return str(hash(str(args)))

    def record_step(
        self,
        tool: str,
        args: dict[str, Any],
        state_signature: str | None = None,
        success: bool = True,
    ) -> None:
        """Record an executed step for loop analysis."""
        entry = {
            "tool": tool,
            "args_hash": self._hash_args(args),
            "state_sig": state_signature or "none",
            "success": success,
        }
        self.history.append(entry)

        if not success:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0

    def check_loop(self) -> tuple[bool, str | None]:
        """Evaluate action history to detect loops or stalls.

        Returns:
            Tuple of (is_blocked, reason_if_blocked).
        """
        # 1. Consecutive failure limit check
        if self.consecutive_failures >= self.max_consecutive_failures:
            reason = (
                f"Repeated execution without progress: exceeded {self.max_consecutive_failures} "
                "consecutive step failures."
            )
            logger.warning("Loop detector blocked: %s", reason)
            return True, reason

        if len(self.history) < 3:
            return False, None

        # 2. Identical tool and argument repetition check
        last_entry = self.history[-1]
        identical_count = 0
        for entry in reversed(self.history):
            if (
                entry["tool"] == last_entry["tool"]
                and entry["args_hash"] == last_entry["args_hash"]
            ):
                identical_count += 1
            else:
                break

        if identical_count >= self.max_identical:
            reason = (
                f"Repeated execution without progress: tool '{last_entry['tool']}' invoked "
                f"{identical_count} times consecutively with identical arguments."
            )
            logger.warning("Loop detector blocked: %s", reason)
            return True, reason

        # 3. Oscillating cycle detection (e.g. A -> B -> A -> B)
        # Check cycles of length 2 and 3
        history_list = list(self.history)
        for cycle_len in (2, 3):
            needed = cycle_len * 2
            if len(history_list) >= needed:
                recent = history_list[-needed:]
                part1 = [(e["tool"], e["args_hash"]) for e in recent[:cycle_len]]
                part2 = [(e["tool"], e["args_hash"]) for e in recent[cycle_len:]]
                if part1 == part2:
                    cycle_tools = [p[0] for p in part1]
                    reason = (
                        f"Repeated execution without progress: oscillating execution cycle "
                        f"detected ({' -> '.join(cycle_tools)})."
                    )
                    logger.warning("Loop detector blocked: %s", reason)
                    return True, reason

        return False, None

    def reset(self) -> None:
        """Reset history and failure counters."""
        self.history.clear()
        self.consecutive_failures = 0
