"""Unit tests for multi-step planning, dependency validation, and deterministic plan hashing."""

from pathlib import Path
import pytest

from nova.errors import ValidationError
from nova.planning.models import Plan, PlanStep
from nova.planning.planner import TaskPlanner
from nova.tools.metadata import ToolRiskLevel


def test_plan_generation_and_dependencies(temp_workspace: Path) -> None:
    planner = TaskPlanner(workspace_root=temp_workspace)
    plan = planner.create_plan_for_goal("Create a demo Java backend project called demo-api with README.md")

    assert plan.goal == "Create a demo Java backend project called demo-api with README.md"
    assert len(plan.steps) >= 4
    assert plan.plan_hash != ""

    # Step 1 should be project root directory
    step1 = plan.steps[0]
    assert step1.tool == "create_directory"
    assert step1.dependencies == []

    # Subsequent steps must depend on parent steps
    step2 = plan.steps[1]
    assert 1 in step2.dependencies


def test_circular_dependency_detection(temp_workspace: Path) -> None:
    planner = TaskPlanner(workspace_root=temp_workspace)
    plan = Plan(
        plan_id="plan_cycle",
        goal="Circular test",
        workspace_root=str(temp_workspace),
        steps=[
            PlanStep(
                step_id=1,
                description="Step 1",
                tool="create_directory",
                args={"directory_path": str(temp_workspace / "a")},
                target=str(temp_workspace / "a"),
                dependencies=[2],  # Depends on 2
            ),
            PlanStep(
                step_id=2,
                description="Step 2",
                tool="create_directory",
                args={"directory_path": str(temp_workspace / "b")},
                target=str(temp_workspace / "b"),
                dependencies=[1],  # Depends on 1 -> Cycle!
            ),
        ],
    )

    with pytest.raises(ValidationError) as exc_info:
        planner.validate_plan(plan)
    assert "Circular dependency" in str(exc_info.value)


def test_self_dependency_detection(temp_workspace: Path) -> None:
    planner = TaskPlanner(workspace_root=temp_workspace)
    plan = Plan(
        plan_id="plan_self",
        goal="Self dep test",
        workspace_root=str(temp_workspace),
        steps=[
            PlanStep(
                step_id=1,
                description="Step 1",
                tool="create_directory",
                args={"directory_path": str(temp_workspace / "a")},
                target=str(temp_workspace / "a"),
                dependencies=[1],  # Depends on itself
            )
        ],
    )

    with pytest.raises(ValidationError) as exc_info:
        planner.validate_plan(plan)
    assert "cannot depend on itself" in str(exc_info.value)


def test_deterministic_plan_hashing(temp_workspace: Path) -> None:
    planner = TaskPlanner(workspace_root=temp_workspace)
    plan1 = planner.create_plan_for_goal("Create a python library called my-pkg with src/ and tests/")
    plan2 = planner.create_plan_for_goal("Create a python library called my-pkg with src/ and tests/")

    # Even though plan_ids differ, the content hash must be deterministic
    assert plan1.compute_plan_hash() == plan2.compute_plan_hash()

    # Tampering with a step argument must change the plan hash
    plan1.steps[0].args["directory_path"] = str(temp_workspace / "tampered")
    assert plan1.compute_plan_hash() != plan2.compute_plan_hash()
