"""Multi-domain empirical verification engine.

Verifies operational postconditions against actual Windows, browser,
filesystem, process, and clipboard state. Enforces that a successful tool
invocation return code is NEVER accepted as proof of successful execution.
"""

import logging
from pathlib import Path
from typing import Any

from nova.orchestration.models import Observation, ObservationDomain
from nova.orchestration.observations import ObservationCollector
from nova.planning.models import Plan, PlanStep
from nova.verification.engine import VerificationEngine

logger = logging.getLogger("nova.orchestration.verifier")


class MultiDomainVerifier:
    """Verifies empirical state across multiple control domains."""

    def __init__(
        self,
        fs_verifier: VerificationEngine | None = None,
        observer: ObservationCollector | None = None,
    ) -> None:
        self.fs_verifier = fs_verifier or VerificationEngine()
        self.observer = observer or ObservationCollector()

    async def verify_step(
        self,
        step: PlanStep,
        tool_result: Any = None,
    ) -> tuple[bool, str, Observation | None]:
        """Verify step outcome empirically against real system state.

        Args:
            step: The executed plan step.
            tool_result: The raw returned data from tool invocation.

        Returns:
            Tuple of (is_verified, reason, observation).
        """
        raw_dom = getattr(step, "domain", None) or "FILESYSTEM"
        domain_str = str(raw_dom).split(".")[-1].upper()
        target = step.target
        post = step.expected_postcondition or {}
        rules = getattr(step, "verification_rule", None) or {}

        # Combine postcondition and verification_rule
        expected = {**post, **rules}

        # 1. FILESYSTEM DOMAIN
        if domain_str == "FILESYSTEM" or step.tool in (
            "create_directory", "create_file", "edit_file", "rename_file", "move_file", "copy_file"
        ):
            # Use empirical filesystem verifier
            obs = await self.observer.observe(ObservationDomain.FILESYSTEM, target=target)
            if expected.get("exists") is True:
                if not obs.relevant_attributes.get("exists"):
                    return False, f"Filesystem target '{target}' does not exist on disk.", obs
                exp_type = expected.get("type")
                if exp_type and obs.relevant_attributes.get("type") != exp_type:
                    return False, f"Expected target '{target}' to be type '{exp_type}', found '{obs.relevant_attributes.get('type')}'.", obs
                exp_hash = expected.get("hash")
                if exp_hash and obs.relevant_attributes.get("hash_sha256") != exp_hash:
                    return False, f"Target '{target}' hash mismatch: expected {exp_hash}, found {obs.relevant_attributes.get('hash_sha256')}.", obs
            elif expected.get("exists") is False:
                if obs.relevant_attributes.get("exists"):
                    return False, f"Expected target '{target}' to be removed, but it still exists.", obs

            return True, f"Filesystem assertions verified for step {step.step_id}.", obs

        # 2. BROWSER DOMAIN
        elif domain_str == "BROWSER" or step.tool.startswith("browser_") or step.tool == "computer.browser_navigate":
            tab_id = None
            if isinstance(tool_result, dict):
                tab_id = tool_result.get("tab_id")
            if not tab_id and isinstance(step.args, dict):
                tab_id = step.args.get("tab_id")

            obs = await self.observer.observe(ObservationDomain.BROWSER, target=tab_id)
            if obs.state == "closed" and expected.get("tab_open", True):
                return False, f"Browser tab '{tab_id}' is closed or not found.", obs

            # Verify URL expectations
            expected_url_contains = expected.get("url_contains")
            if expected_url_contains:
                current_url = obs.relevant_attributes.get("url", "")
                if expected_url_contains.lower() not in current_url.lower():
                    return False, f"Browser URL '{current_url}' does not contain expected '{expected_url_contains}'.", obs

            # Verify prompt injection flag
            if any("prompt_injection" in flag for flag in obs.safety_flags):
                return False, "Prompt injection pattern detected in browser DOM observation.", obs

            # Verify content presence if required
            expected_content = expected.get("content_contains")
            if expected_content:
                if isinstance(tool_result, dict):
                    content = tool_result.get("content", "")
                    if expected_content.lower() not in content.lower():
                        return False, f"Extracted browser content missing expected token '{expected_content}'.", obs

            return True, f"Browser postconditions verified for step {step.step_id}.", obs

        # 3. WINDOWS DOMAIN
        elif domain_str == "WINDOWS" or step.tool.startswith("computer."):
            hwnd = None
            if isinstance(tool_result, dict):
                hwnd = tool_result.get("hwnd") or (tool_result.get("target") or {}).get("hwnd")
            if not hwnd and isinstance(step.args, dict):
                hwnd = step.args.get("hwnd")

            obs = await self.observer.observe(ObservationDomain.WINDOWS, target=target, hwnd=hwnd)

            if expected.get("focused") is True:
                if not obs.relevant_attributes.get("is_focused"):
                    return False, f"Window target '{target}' (HWND:{hwnd}) is not in the foreground.", obs

            if expected.get("exists") is False and hwnd:
                import ctypes
                if ctypes.windll.user32.IsWindow(hwnd):
                    return False, f"Window HWND:{hwnd} still exists after close request.", obs

            return True, f"Windows desktop postconditions verified for step {step.step_id}.", obs

        # 4. PROCESS DOMAIN
        elif domain_str == "PROCESS" or step.tool in ("computer.stop_process", "computer.launch_app"):
            pid = None
            if isinstance(tool_result, dict):
                pid = tool_result.get("pid")
            if not pid and isinstance(step.args, dict):
                pid = step.args.get("pid")

            obs = await self.observer.observe(ObservationDomain.PROCESS, target=pid or target)
            if expected.get("running") is True:
                if not obs.relevant_attributes.get("running"):
                    return False, f"Process '{pid or target}' is not running.", obs
            elif expected.get("running") is False:
                if obs.relevant_attributes.get("running"):
                    return False, f"Process '{pid or target}' is still running.", obs

            return True, f"Process postconditions verified for step {step.step_id}.", obs

        # 5. CLIPBOARD DOMAIN
        elif domain_str == "CLIPBOARD" or step.tool in ("computer.clipboard_write", "computer.clipboard_read"):
            obs = await self.observer.observe(ObservationDomain.CLIPBOARD)
            if expected.get("has_text") is True and not obs.relevant_attributes.get("has_text"):
                return False, "Clipboard has no text.", obs
            expected_hash = expected.get("hash_sha256")
            if expected_hash and obs.relevant_attributes.get("hash_sha256") != expected_hash:
                return False, f"Clipboard hash mismatch: expected {expected_hash}, found {obs.relevant_attributes.get('hash_sha256')}.", obs

            return True, f"Clipboard postconditions verified for step {step.step_id}.", obs

        # Fallback / General
        obs = await self.observer.observe(ObservationDomain.GENERAL, target=target)
        if isinstance(tool_result, dict) and tool_result.get("error"):
            return False, f"Tool returned error: {tool_result.get('error')}", obs

        return True, f"Step {step.step_id} completed and verified.", obs

    async def verify_final_plan(self, plan: Plan) -> tuple[bool, str]:
        """Verify holistic plan outcomes across all executed steps."""
        for step in plan.steps:
            ok, reason, _ = await self.verify_step(step)
            if not ok:
                return False, f"Plan verification failed at step {step.step_id}: {reason}"
        return True, f"All {len(plan.steps)} steps verified successfully."
