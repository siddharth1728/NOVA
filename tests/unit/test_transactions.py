"""Unit tests for transaction management, snapshots, and LIFO rollback."""

from pathlib import Path
import pytest

from nova.errors import RollbackFailedError
from nova.transactions.manager import (
    TransactionManager,
    atomic_write,
    compute_file_hash,
)
from nova.transactions.models import (
    OperationRecord,
    OperationType,
    TransactionStatus,
)


def test_atomic_write_creates_file_and_hash(temp_workspace: Path) -> None:
    target = temp_workspace / "atomic_test.txt"
    content = "Atomic Write Test Payload"
    f_hash, f_size = atomic_write(target, content)

    assert target.exists()
    assert target.read_text(encoding="utf-8") == content
    assert f_hash == compute_file_hash(target)
    assert f_size == len(content.encode("utf-8"))

    # Verify no temp files left behind
    temp_files = list(temp_workspace.glob(".tmp_*"))
    assert len(temp_files) == 0


def test_transaction_lifecycle_and_snapshots(temp_workspace: Path, temp_data_dir: Path) -> None:
    tx_mgr = TransactionManager(backup_dir=temp_data_dir / "backups")
    tx = tx_mgr.begin(description="Test Transaction")
    assert tx.status == TransactionStatus.STARTED

    # Create snapshot of existing file
    existing = temp_workspace / "hello.txt"
    snapshot = tx_mgr.create_snapshot(tx.transaction_id, existing)
    assert snapshot is not None
    assert snapshot.exists()
    assert snapshot.read_text(encoding="utf-8") == existing.read_text(encoding="utf-8")

    tx_mgr.commit(tx.transaction_id)
    assert tx.status == TransactionStatus.COMMITTED
    assert tx.completed_at is not None


def test_lifo_rollback_reversal_order(temp_workspace: Path, temp_data_dir: Path) -> None:
    tx_mgr = TransactionManager(backup_dir=temp_data_dir / "backups")
    tx = tx_mgr.begin(description="Multi-mutation Rollback")

    # Op 1: Create directory
    test_dir = temp_workspace / "lifo_dir"
    test_dir.mkdir()
    op1 = OperationRecord(
        operation_id="op_1",
        op_type=OperationType.CREATE_DIRECTORY,
        target_path=test_dir,
        created_new=True,
    )
    tx_mgr.record_operation(tx.transaction_id, op1)

    # Op 2: Create file inside directory
    test_file = test_dir / "lifo_file.txt"
    atomic_write(test_file, "Payload")
    op2 = OperationRecord(
        operation_id="op_2",
        op_type=OperationType.CREATE_FILE,
        target_path=test_file,
        created_new=True,
    )
    tx_mgr.record_operation(tx.transaction_id, op2)

    # Op 3: Edit existing hello.txt
    hello_file = temp_workspace / "hello.txt"
    original_hello_hash = compute_file_hash(hello_file)
    snap = tx_mgr.create_snapshot(tx.transaction_id, hello_file)
    atomic_write(hello_file, "Modified Content")
    op3 = OperationRecord(
        operation_id="op_3",
        op_type=OperationType.EDIT_FILE,
        target_path=hello_file,
        backup_path=snap,
        pre_hash=original_hello_hash,
        post_hash=compute_file_hash(hello_file),
    )
    tx_mgr.record_operation(tx.transaction_id, op3)

    assert test_file.exists()
    assert test_dir.exists()
    assert hello_file.read_text(encoding="utf-8") == "Modified Content"

    # Execute Rollback (LIFO: op3 -> op2 -> op1)
    rolled_tx = tx_mgr.rollback(tx.transaction_id)
    assert rolled_tx.status == TransactionStatus.ROLLED_BACK

    # Op 3 reversed: hello.txt restored to original content
    assert hello_file.read_text(encoding="utf-8") == "Hello NOVA"
    assert compute_file_hash(hello_file) == original_hello_hash

    # Op 2 reversed: test_file removed
    assert not test_file.exists()

    # Op 1 reversed: test_dir removed
    assert not test_dir.exists()


def test_rollback_failure_raises_and_marks_status(temp_workspace: Path, temp_data_dir: Path) -> None:
    tx_mgr = TransactionManager(backup_dir=temp_data_dir / "backups")
    tx = tx_mgr.begin(description="Failure test")

    file_to_edit = temp_workspace / "hello.txt"
    # Point backup to nonexistent path
    op = OperationRecord(
        operation_id="op_corrupt",
        op_type=OperationType.EDIT_FILE,
        target_path=file_to_edit,
        backup_path=Path("C:/nonexistent/invalid_snapshot.bak"),
        pre_hash="dummy_hash",
    )
    tx_mgr.record_operation(tx.transaction_id, op)

    # Rollback must fail and raise RollbackFailedError
    with pytest.raises(RollbackFailedError) as exc_info:
        tx_mgr.rollback(tx.transaction_id)

    assert exc_info.value.transaction_id == tx.transaction_id
    assert tx.status == TransactionStatus.ROLLBACK_FAILED
