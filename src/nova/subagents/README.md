# NOVA Subagent Architecture

NOVA envisions a multi-agent hierarchy orchestrated by a parent agent session. In **Phase 01**, the architecture establishes strongly-typed specifications (`SubagentBlueprint`) and role models, but keeps subagent execution disabled until the core parent agent is proven stable and reliable.

## Future Subagent Roles

1. **Planner**: Milestone decomposition and structured planning.
2. **Researcher**: Information gathering across documents and authorized web sources.
3. **Coder**: Deterministic code editing, testing, and debugging.
4. **Browser Operator**: Web automation and testing.
5. **Computer Operator**: Desktop GUI control with explicit human confirmation.
6. **Verifier**: Post-condition verification and result validation.
7. **Security Reviewer**: Privilege escalation checks and policy audits.
8. **Document Specialist**: Documentation extraction and synthesis.

## Integration Model

Subagent blueprints map directly to Google Antigravity's native `SubagentConfig` via `to_antigravity_config()`, ensuring seamless activation in subsequent phases.
