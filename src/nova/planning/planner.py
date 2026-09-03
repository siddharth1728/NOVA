"""Multi-step planner with dependency validation and deterministic plan hashing."""

from pathlib import Path
import re
import time
from typing import Any
from uuid import uuid4

from nova.config.settings import get_settings
from nova.errors import ValidationError
from nova.planning.models import Plan, PlanStatus, PlanStep, PlanStepStatus
from nova.security.paths import resolve_and_confine
from nova.tools.metadata import ToolRiskLevel
from nova.tools.registry import get_tool_registry


class TaskPlanner:
    """Decomposes goals into dependency-ordered, verifiable execution plans."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = (workspace_root or get_settings().workspace_root).resolve()
        self.registry = get_tool_registry()

    def create_plan_for_goal(self, goal: str) -> Plan:
        """Constructs a validated multi-step plan for a natural language goal."""
        plan_id = f"plan_{int(time.time()*1000)}_{uuid4().hex[:6]}"
        steps: list[PlanStep] = []

        # Parse project structure requests (e.g. "Create a Java backend project structure called demo-api")
        project_match = re.search(r"(?:create|build|scaffold)\s+(?:a\s+)?([a-zA-Z0-9_-]+(?:\s+project|\s+structure)?)", goal, re.IGNORECASE)
        name_match = re.search(r"(?:called|named)\s+([a-zA-Z0-9_-]+)", goal, re.IGNORECASE)
        project_name = name_match.group(1) if name_match else (project_match.group(1).split()[0] if project_match else "project")

        goal_lower = goal.lower()
        step_counter = 1

        # Check for standard project components in user prompt
        base_dir = self.workspace_root / project_name
        steps.append(
            PlanStep(
                step_id=step_counter,
                description=f"Create project root directory '{project_name}'",
                tool="create_directory",
                args={"directory_path": str(base_dir)},
                target=str(base_dir),
                dependencies=[],
                expected_postcondition={"exists": True, "type": "dir"},
                risk_level=ToolRiskLevel.MEDIUM,
            )
        )
        root_step_id = step_counter
        step_counter += 1

        # Check for subdirectories requested
        if "java" in goal_lower:
            subdirs = ["src/main/java", "src/test/java"]
        elif "python" in goal_lower or "src" in goal_lower or "tests" in goal_lower:
            subdirs = ["src", "tests"]
        else:
            # Look for mentioned paths like "notes/", "docs/"
            found_paths = re.findall(r"([a-zA-Z0-9_/-]+)/", goal)
            subdirs = [p for p in found_paths if p != project_name] or ["src"]

        dir_step_map: dict[str, int] = {}
        for sub in subdirs:
            full_sub = base_dir / sub
            steps.append(
                PlanStep(
                    step_id=step_counter,
                    description=f"Create subdirectory '{sub}'",
                    tool="create_directory",
                    args={"directory_path": str(full_sub)},
                    target=str(full_sub),
                    dependencies=[root_step_id],
                    expected_postcondition={"exists": True, "type": "dir"},
                    risk_level=ToolRiskLevel.MEDIUM,
                )
            )
            dir_step_map[sub] = step_counter
            step_counter += 1

        # Check for files requested (e.g. README.md, pom.xml, etc.)
        files_to_create: list[tuple[str, str, int]] = []
        if "readme" in goal_lower or True:  # Default to README
            readme_path = base_dir / "README.md"
            readme_content = f"# {project_name.title()}\n\nProject initialized by NOVA.\n"
            files_to_create.append((str(readme_path), readme_content, root_step_id))

        for file_path_str, content, dep_id in files_to_create:
            steps.append(
                PlanStep(
                    step_id=step_counter,
                    description=f"Create file '{Path(file_path_str).name}'",
                    tool="create_file",
                    args={"file_path": file_path_str, "content": content, "overwrite": False},
                    target=file_path_str,
                    dependencies=[dep_id],
                    expected_postcondition={"exists": True, "type": "file"},
                    risk_level=ToolRiskLevel.MEDIUM,
                )
            )
            step_counter += 1

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
        """Validates tool existence, path confinement, and dependency graph integrity."""
        if not plan.steps:
            raise ValidationError("Plan must contain at least one step.")

        step_ids = {s.step_id for s in plan.steps}
        if len(step_ids) != len(plan.steps):
            raise ValidationError("Plan contains duplicate step IDs.")

        # Dependency graph validation & cycle detection
        adj: dict[int, list[int]] = {s.step_id: [] for s in plan.steps}
        in_degree: dict[int, int] = {s.step_id: 0 for s in plan.steps}

        for step in plan.steps:
            # 1. Validate tool exists
            meta = self.registry.get_metadata(step.tool)
            if not meta:
                raise ValidationError(f"Step {step.step_id} specifies unknown tool '{step.tool}'.")

            # 2. Validate target confinement
            resolve_and_confine(step.target, self.workspace_root)

            # 3. Check dependencies
            for dep in step.dependencies:
                if dep not in step_ids:
                    raise ValidationError(f"Step {step.step_id} references non-existent dependency step {dep}.")
                if dep == step.step_id:
                    raise ValidationError(f"Step {step.step_id} cannot depend on itself.")
                adj[dep].append(step.step_id)
                in_degree[step.step_id] += 1

        # Topological sort (Kahn's algorithm) to detect circular dependencies
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

        plan.plan_hash = plan.compute_plan_hash()
        plan.status = PlanStatus.VALIDATED
