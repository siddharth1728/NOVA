"""Typed specifications and blueprints for future specialized subagents."""

from enum import Enum
from typing import Any

from google.antigravity.types import CapabilitiesConfig, SubagentConfig
from pydantic import BaseModel, Field

from nova.tools.metadata import ToolRiskLevel


class SubagentRole(str, Enum):
    """Specialized subagent functional roles."""

    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    BROWSER_OPERATOR = "browser_operator"
    COMPUTER_OPERATOR = "computer_operator"
    VERIFIER = "verifier"
    SECURITY_REVIEWER = "security_reviewer"
    DOCUMENT_SPECIALIST = "document_specialist"


class SubagentBlueprint(BaseModel):
    """Specification defining a specialized subagent's role, tools, and safety constraints."""

    role: SubagentRole
    name: str
    description: str
    system_instructions: str
    allowed_tools: list[str] = Field(default_factory=list)
    max_risk_level: ToolRiskLevel = ToolRiskLevel.READ_ONLY
    requires_human_approval: bool = False

    def to_antigravity_config(self) -> SubagentConfig:
        """Converts the blueprint into native Antigravity SubagentConfig."""
        caps = CapabilitiesConfig(
            enabled_tools=self.allowed_tools if self.allowed_tools else None,
            enable_subagents=False,
        )
        return SubagentConfig(
            name=self.name,
            description=self.description,
            system_instructions=self.system_instructions,
            capabilities=caps,
        )


# Blueprint Registry of defined subagents for future phases
SUBAGENT_BLUEPRINTS: dict[SubagentRole, SubagentBlueprint] = {
    SubagentRole.PLANNER: SubagentBlueprint(
        role=SubagentRole.PLANNER,
        name="planner",
        description="Breaks complex user goals into structured, dependency-ordered milestones and steps.",
        system_instructions="You are a master planning agent. Analyze objectives, identify prerequisites, and design safe execution plans.",
        allowed_tools=["list_directory", "view_file"],
        max_risk_level=ToolRiskLevel.READ_ONLY,
    ),
    SubagentRole.RESEARCHER: SubagentBlueprint(
        role=SubagentRole.RESEARCHER,
        name="researcher",
        description="Gathers information from documents, codebases, and authorized web sources.",
        system_instructions="You are a research agent. Synthesize facts, cite sources, and structure findings.",
        allowed_tools=["search_directory", "view_file", "search_web", "read_url_content"],
        max_risk_level=ToolRiskLevel.LOW,
    ),
    SubagentRole.CODER: SubagentBlueprint(
        role=SubagentRole.CODER,
        name="coder",
        description="Writes, edits, and refactors software with strict adherence to architectural standards.",
        system_instructions="You are a senior software engineer. Write clean, modular, tested, and robust code.",
        allowed_tools=["view_file", "create_file", "edit_file", "search_directory"],
        max_risk_level=ToolRiskLevel.MEDIUM,
    ),
    SubagentRole.BROWSER_OPERATOR: SubagentBlueprint(
        role=SubagentRole.BROWSER_OPERATOR,
        name="browser_operator",
        description="Interacts with web applications deterministically via structured browser automation.",
        system_instructions="You are a browser automation specialist. Navigate, extract data, and test web UIs safely.",
        allowed_tools=[],
        max_risk_level=ToolRiskLevel.MEDIUM,
        requires_human_approval=True,
    ),
    SubagentRole.COMPUTER_OPERATOR: SubagentBlueprint(
        role=SubagentRole.COMPUTER_OPERATOR,
        name="computer_operator",
        description="Interacts with desktop applications and system windows with verified human approval.",
        system_instructions="You are a desktop operator. Perform UI actions with caution and confirm destructive steps.",
        allowed_tools=[],
        max_risk_level=ToolRiskLevel.HIGH,
        requires_human_approval=True,
    ),
    SubagentRole.VERIFIER: SubagentBlueprint(
        role=SubagentRole.VERIFIER,
        name="verifier",
        description="Rigorously tests outcomes, verifies post-conditions, and confirms task success.",
        system_instructions="You are a verification specialist. Assume nothing. Prove that results match expected outcomes.",
        allowed_tools=["view_file", "list_directory"],
        max_risk_level=ToolRiskLevel.READ_ONLY,
    ),
    SubagentRole.SECURITY_REVIEWER: SubagentBlueprint(
        role=SubagentRole.SECURITY_REVIEWER,
        name="security_reviewer",
        description="Audits plans, code, and proposed actions for privilege escalation, secret leaks, and security risks.",
        system_instructions="You are an autonomous security auditor. Deny risky operations and identify potential vulnerabilities.",
        allowed_tools=["view_file", "search_directory"],
        max_risk_level=ToolRiskLevel.READ_ONLY,
    ),
    SubagentRole.DOCUMENT_SPECIALIST: SubagentBlueprint(
        role=SubagentRole.DOCUMENT_SPECIALIST,
        name="document_specialist",
        description="Parses, indexes, and summarizes documentation, PDFs, markdown, and architecture decision records.",
        system_instructions="You are a technical documentation specialist. Extract schemas, summarize specs, and maintain guides.",
        allowed_tools=["view_file", "search_directory"],
        max_risk_level=ToolRiskLevel.READ_ONLY,
    ),
}
