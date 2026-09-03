"""Unit tests for the empirical verification engine."""

from pathlib import Path

from nova.planning.models import PlanStep
from nova.tools.metadata import ToolRiskLevel
from nova.transactions.manager import compute_file_hash
from nova.transactions.models import (
    OperationRecord,
    OperationType,
    TransactionRecord,
    TransactionStatus,
)
from nova.verification.engine import VerificationEngine


def test_verify_step_positive(temp_workspace: Path) -> None:
    verifier = VerificationEngine()
    test_file = temp_workspace / "hello.txt"
    f_hash = compute_file_hash(test_file)

    step = PlanStep(
        step_id=1,
        description="Check hello",
        tool="create_file",
        target=str(test_file),
        expected_postcondition={"exists": True, "type": "file", "hash": f_hash},
    )

    valid, reason = verifier.verify_step(step)
    assert valid is True
    assert "empirically verified" in reason


def test_verify_step_target_missing(temp_workspace: Path) -> None:
    verifier = VerificationEngine()
    missing = temp_workspace / "nonexistent.txt"

    step = PlanStep(
        step_id=1,
        description="Check missing",
        tool="create_file",
        target=str(missing),
        expected_postcondition={"exists": True},
    )

    valid, reason = verifier.verify_step(step)
    assert valid is False
    assert "not found" in reason


def test_verify_step_hash_mismatch(temp_workspace: Path) -> None:
    verifier = VerificationEngine()
    test_file = temp_workspace / "hello.txt"

    step = PlanStep(
        step_id=1,
        description="Check hash mismatch",
        tool="create_file",
        target=str(test_file),
        expected_postcondition={"exists": True, "hash": "corrupt_fake_hash"},
    )

    valid, reason = verifier.verify_step(step)
    assert valid is False
    assert "hash mismatch" in reason


def test_verify_step_wrong_type(temp_workspace: Path) -> None:
    verifier = VerificationEngine()
    test_dir = temp_workspace / "sub"

    step = PlanStep(
        step_id=1,
        description="Check wrong type",
        tool="create_file",
        target=str(test_dir),
        expected_postcondition={"exists": True, "type": "file"},
    )

    valid, reason = verifier.verify_step(step)
    assert valid is False
    assert "Expected target" in reason and "regular file" in reason


def test_verify_rollback_positive(temp_workspace: Path) -> None:
    verifier = VerificationEngine()
    removed_file = temp_workspace / "newly_created.txt"

    tx = TransactionRecord(
        transaction_id="tx_test",
        status=TransactionStatus.ROLLED_BACK,
        operations=[
            OperationRecord(
                operation_id="op_1",
                op_type=OperationType.CREATE_FILE,
                target_path=removed_file,
                created_new=True,
                rolled_back=True,
            )
        ],
    )

    # File does not exist -> rollback verified
    valid, reason = verifier.verify_rollback(tx)
    assert valid is True
    assert "workspace cleanly restored" in reason
