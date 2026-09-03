"""Builds native Google Antigravity configuration objects from NOVA settings."""

from pathlib import Path

from google.antigravity import LocalAgentConfig
from google.antigravity.types import AgentBehavior, CapabilitiesConfig

from nova.agent.prompts import NOVA_IDENTITY_PROMPT
from nova.config.settings import NovaSettings, get_settings
from nova.security.approvals import ApprovalHandler, ConsoleApprovalHandler
from nova.security.policies import build_antigravity_policies
from nova.tools.registry import get_tool_registry


def build_agent_config(
    settings: NovaSettings | None = None,
    approval_handler: ApprovalHandler | None = None,
    skills_dir: Path | None = None,
) -> LocalAgentConfig:
    """Constructs a production LocalAgentConfig tailored for NOVA Phase 01.

    Enforces read-only capabilities and workspace confinement.

    Args:
        settings: Active NOVA settings.
        approval_handler: Human approval handler.
        skills_dir: Optional path to skills directory.

    Returns:
        Configured LocalAgentConfig instance.
    """
    cfg = settings or get_settings()
    app_handler = approval_handler or ConsoleApprovalHandler()
    registry = get_tool_registry()

    # Determine permitted tools for Phase 01 (Strictly Read-Only)
    enabled_tools = registry.get_phase01_builtin_tools()

    capabilities = CapabilitiesConfig(
        enabled_tools=enabled_tools,
        enable_subagents=False,
        agent_behavior=AgentBehavior.AUTONOMOUS,
    )

    policies = build_antigravity_policies(cfg, app_handler)

    # Session storage directory
    session_save_dir = cfg.data_dir / "sessions"
    session_save_dir.mkdir(parents=True, exist_ok=True)

    skills_paths: list[str] = []
    if skills_dir and skills_dir.exists():
        skills_paths.append(str(skills_dir))
    else:
        pkg_skills = Path(__file__).parent.parent / "skills"
        if pkg_skills.exists():
            skills_paths.append(str(pkg_skills))

    return LocalAgentConfig(
        system_instructions=NOVA_IDENTITY_PROMPT,
        capabilities=capabilities,
        policies=policies,
        workspaces=[str(cfg.workspace_root)],
        model=cfg.model_name,
        api_key=cfg.get_api_key_value(),
        save_dir=str(session_save_dir),
        skills_paths=skills_paths if skills_paths else None,
    )
