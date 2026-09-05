"""Multi-domain workflow planner decomposing user goals into validated, verifiable execution plans."""

from pathlib import Path
import re
import time
from typing import Any
from uuid import uuid4

from nova.config.settings import get_settings
from nova.errors import ValidationError
from nova.planning.models import Plan, PlanStatus, PlanStep, PlanStepStatus
from nova.planning.planner import TaskPlanner
from nova.security.paths import resolve_and_confine
from nova.security.risk import RiskEvaluator
from nova.tools.categories import ToolCategory
from nova.tools.metadata import ToolRiskLevel
from nova.tools.registry import ToolRegistry, get_tool_registry

# Known tool domains based on prefixes and categories
DOMAIN_MAP = {
    ToolCategory.BROWSER: "BROWSER",
    ToolCategory.COMPUTER: "WINDOWS",
    ToolCategory.FILESYSTEM: "FILESYSTEM",
    ToolCategory.TERMINAL: "PROCESS",
    ToolCategory.UTILITY: "GENERAL",
}


class WorkflowPlanner:
    """Decomposes multi-domain user goals into dependency-tracked, verifiable execution plans."""

    def __init__(
        self,
        workspace_root: Path | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.workspace_root = (workspace_root or get_settings().workspace_root).resolve()
        self.registry = registry or get_tool_registry()
        self.risk_evaluator = RiskEvaluator(self.registry)
        self.fs_planner = TaskPlanner(workspace_root=self.workspace_root)

    def plan_for_goal(self, goal: str) -> Plan:
        """Decompose natural language goal into a validated multi-step plan across domains."""
        goal_lower = goal.lower()
        plan_id = f"plan_{int(time.time()*1000)}_{uuid4().hex[:6]}"

        # Pattern 1: Browser research and file extraction
        # e.g. "Research python asyncio trends and save findings to report.md"
        # e.g. "Open Chrome, research the latest Java backend internship trends, save the useful results into a document"
        if any(term in goal_lower for term in ["research", "search web", "browse", "visit", "http://", "https://"]):
            return self._create_browser_research_plan(plan_id, goal)

        # Pattern 2: Windows application launch and interaction
        # e.g. "Launch notepad, type hello world, and verify window"
        elif any(term in goal_lower for term in ["launch", "open app", "open notepad", "type text", "focus window"]):
            return self._create_windows_control_plan(plan_id, goal)

        # Pattern 3: Filesystem project / code scaffolding (default to TaskPlanner)
        else:
            base_plan = self.fs_planner.create_plan_for_goal(goal)
            self.validate_plan(base_plan)
            return base_plan

    def _create_browser_research_plan(self, plan_id: str, goal: str) -> Plan:
        """Construct multi-domain plan combining Browser intelligence and Filesystem storage."""
        steps: list[PlanStep] = []
        step_id = 1

        # Extract target url if present or default to a research search
        url_match = re.search(r"https?://[^\s]+", goal)
        url = url_match.group(0) if url_match else "https://en.wikipedia.org/wiki/Main_Page"

        # Determine target output file
        file_match = re.search(r"(?:save|write|export|output).*?(?:to|in|into)\s+([a-zA-Z0-9_.-]+\.md|[a-zA-Z0-9_.-]+\.txt)", goal, re.IGNORECASE)
        filename = file_match.group(1) if file_match else "research_notes.md"
        target_file = self.workspace_root / filename

        # Step 1: Open browser tab
        steps.append(
            PlanStep(
                step_id=step_id,
                description=f"Open browser tab to '{url}'",
                tool="browser_new_tab",
                args={"url": url},
                target=url,
                dependencies=[],
                domain="BROWSER",
                expected_postcondition={"tab_open": True},
                verification_rule={"tab_open": True, "url_contains": "http"},
                risk_level=ToolRiskLevel.LOW,
                reversibility="REVERSIBLE",
            )
        )
        tab_step_id = step_id
        step_id += 1

        # Step 2: Extract content from page
        steps.append(
            PlanStep(
                step_id=step_id,
                description="Extract visible research content from browser tab",
                tool="browser_extract",
                args={"tab_id": "current"},
                target=url,
                dependencies=[tab_step_id],
                domain="BROWSER",
                expected_postcondition={"content_extracted": True},
                verification_rule={},
                risk_level=ToolRiskLevel.READ_ONLY,
                reversibility="REVERSIBLE",
            )
        )
        extract_step_id = step_id
        step_id += 1

        # Step 3: Write extracted results to verified file
        steps.append(
            PlanStep(
                step_id=step_id,
                description=f"Save research findings to '{filename}'",
                tool="create_file",
                args={
                    "file_path": str(target_file),
                    "content": f"# Research Findings\n\nGoal: {goal}\nSource: {url}\n\nAutomated extraction completed by NOVA.\n",
                    "overwrite": True,
                },
                target=str(target_file),
                dependencies=[extract_step_id],
                domain="FILESYSTEM",
                expected_postcondition={"exists": True, "type": "file"},
                verification_rule={"exists": True, "type": "file"},
                risk_level=ToolRiskLevel.MEDIUM,
                reversibility="REVERSIBLE",
            )
        )

        plan = Plan(
            plan_id=plan_id,
            goal=goal,
            workspace_root=str(self.workspace_root),
            steps=steps,
            risk_ceiling=ToolRiskLevel.MEDIUM,
        )
        self.validate_plan(plan)
        return plan

    def _create_windows_control_plan(self, plan_id: str, goal: str) -> Plan:
        """Construct Windows application control workflow plan."""
        steps: list[PlanStep] = []
        step_id = 1

        app_name = "notepad.exe"
        if "calc" in goal.lower():
            app_name = "calc.exe"

        # Step 1: Launch application
        steps.append(
            PlanStep(
                step_id=step_id,
                description=f"Launch application '{app_name}'",
                tool="computer.launch_application",
                args={"app_name_or_path": app_name, "wait_for_window": True},
                target=app_name,
                dependencies=[],
                domain="WINDOWS",
                expected_postcondition={"running": True},
                verification_rule={"running": True},
                risk_level=ToolRiskLevel.MEDIUM,
                reversibility="REVERSIBLE",
            )
        )
        launch_id = step_id
        step_id += 1

        # Step 2: Focus application window
        steps.append(
            PlanStep(
                step_id=step_id,
                description=f"Focus '{app_name}' window to accept input",
                tool="computer.focus_window",
                args={"title_pattern": "Notepad" if "notepad" in app_name else "Calculator"},
                target=app_name,
                dependencies=[launch_id],
                domain="WINDOWS",
                expected_postcondition={"focused": True},
                verification_rule={"focused": True},
                risk_level=ToolRiskLevel.LOW,
                reversibility="REVERSIBLE",
            )
        )
        focus_id = step_id
        step_id += 1

        # Step 3: Type sample input if requested
        if "type" in goal.lower() or "input" in goal.lower():
            text_match = re.search(r'type\s+["\']([^"\']+)["\']', goal)
            input_text = text_match.group(1) if text_match else "NOVA verified input"
            steps.append(
                PlanStep(
                    step_id=step_id,
                    description=f"Type text into active application",
                    tool="computer.type_text",
                    args={"text": input_text},
                    target=app_name,
                    dependencies=[focus_id],
                    domain="WINDOWS",
                    expected_postcondition={},
                    verification_rule={},
                    risk_level=ToolRiskLevel.LOW,
                    reversibility="NON_REVERSIBLE",
                )
            )

        plan = Plan(
            plan_id=plan_id,
            goal=goal,
            workspace_root=str(self.workspace_root),
            steps=steps,
            risk_ceiling=ToolRiskLevel.MEDIUM,
        )
        self.validate_plan(plan)
        return plan

    def validate_plan(self, plan: Plan) -> None:
        """Validate that all steps use registered tools, valid args, and cycle-free DAGs."""
        if not plan.steps:
            raise ValidationError("Plan must contain at least one step.")

        step_ids = {s.step_id for s in plan.steps}
        if len(step_ids) != len(plan.steps):
            raise ValidationError("Plan contains duplicate step IDs.")

        adj: dict[int, list[int]] = {s.step_id: [] for s in plan.steps}
        in_degree: dict[int, int] = {s.step_id: 0 for s in plan.steps}

        max_step_risk = ToolRiskLevel.READ_ONLY

        for step in plan.steps:
            # 1. Validate tool is registered in ToolRegistry
            tool_entry = self.registry.get(step.tool)
            if not tool_entry:
                raise ValidationError(f"Plan step {step.step_id} specifies unknown/unregistered tool '{step.tool}'.")

            meta = tool_entry.metadata
            # Set metadata-derived properties
            step.risk_level = meta.risk_level
            step.requires_approval = step.requires_approval or (meta.risk_level >= ToolRiskLevel.HIGH)
            step.reversibility = "REVERSIBLE" if meta.is_reversible else "NON_REVERSIBLE"
            if meta.category in DOMAIN_MAP:
                step.domain = DOMAIN_MAP[meta.category]


            if step.risk_level > max_step_risk:
                max_step_risk = step.risk_level

            # 2. Filesystem target confinement validation
            if step.domain == "FILESYSTEM" or meta.category == ToolCategory.FILESYSTEM:
                if step.target:
                    try:
                        resolve_and_confine(step.target, self.workspace_root)
                    except Exception as e:
                        raise ValidationError(f"Step {step.step_id} filesystem target escapes workspace: {e}")

            # 3. Dependencies check
            for dep in step.dependencies:
                if dep not in step_ids:
                    raise ValidationError(f"Step {step.step_id} references non-existent dependency step {dep}.")
                if dep == step.step_id:
                    raise ValidationError(f"Step {step.step_id} cannot depend on itself.")
                adj[dep].append(step.step_id)
                in_degree[step.step_id] += 1

        # Kahn's algorithm for DAG cycle detection
        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        visited_count = 0
        while queue:
            curr = queue.pop(0)
            visited_count += 1
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(plan.steps):
            raise ValidationError("Circular dependency detected in plan execution graph.")

        plan.risk_ceiling = max_step_risk
        plan.plan_hash = plan.compute_plan_hash()
        plan.status = PlanStatus.VALIDATED
