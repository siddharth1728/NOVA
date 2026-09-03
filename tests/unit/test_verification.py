"""Unit tests for post-action outcome verification."""

from nova.agent.runtime import NovaRuntime
from nova.config.settings import Environment, NovaSettings
from nova.observability.audit import AuditTrail


def test_verification_rejects_empty_response(temp_workspace, temp_data_dir) -> None:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
    )
    runtime = NovaRuntime(settings=settings)

    valid, reason = runtime.verify_outcome("What files exist?", "")
    assert not valid
    assert "empty" in reason.lower()


def test_verification_positive(temp_workspace, temp_data_dir) -> None:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
    )
    audit = AuditTrail(audit_dir=temp_data_dir / "audit")
    # Simulate a logged filesystem tool call
    audit.log_tool_invocation(
        tool="list_directory",
        risk_level="READ_ONLY",
        approval_state="APPROVED",
        inputs={"path": "."},
        results={"files": ["hello.txt"]},
    )

    runtime = NovaRuntime(settings=settings, audit_trail=audit)
    valid, reason = runtime.verify_outcome(
        "What files are available?",
        "[OBSERVED] The workspace contains hello.txt and sub/.",
    )
    assert valid
    assert "Verification successful" in reason
