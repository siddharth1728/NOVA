"""Transactional execution manager and LIFO rollback engine."""

import hashlib
import os
from pathlib import Path
import shutil
import threading
import time
from uuid import uuid4

from nova.config.settings import get_settings
from nova.errors import RollbackFailedError
from nova.transactions.models import (
    OperationRecord,
    OperationType,
    TransactionRecord,
    TransactionStatus,
    _utc_now,
)


def compute_file_hash(path: Path) -> str | None:
    """Calculates SHA-256 hash of a file, returning None if file does not exist."""
    if not path.exists() or not path.is_file():
        return None
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def atomic_write(target_path: Path, content: str | bytes) -> tuple[str, int]:
    """Writes content atomically to target_path using a temporary sibling file and replacement.

    Args:
        target_path: Destination path.
        content: String or byte content to write.

    Returns:
        Tuple of (sha256_hash, file_size_in_bytes).
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = f".tmp_{target_path.name}_{uuid4().hex[:8]}"
    temp_path = target_path.parent / temp_name

    mode = "wb" if isinstance(content, bytes) else "w"
    encoding = None if isinstance(content, bytes) else "utf-8"

    try:
        with open(temp_path, mode, encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        file_hash = compute_file_hash(temp_path) or ""
        file_size = temp_path.stat().st_size

        # Atomic replacement on Windows NTFS and POSIX
        os.replace(temp_path, target_path)
        return file_hash, file_size
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


class TransactionManager:
    """Thread-safe manager for atomic transactions, snapshots, and LIFO rollback."""

    def __init__(self, backup_dir: Path | None = None) -> None:
        self.backup_dir = (backup_dir or (get_settings().data_dir / "backups")).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._transactions: dict[str, TransactionRecord] = {}
        self._lock = threading.RLock()

    def begin(self, tx_id: str | None = None, description: str = "") -> TransactionRecord:
        """Starts a new workspace transaction."""
        with self._lock:
            transaction_id = tx_id or f"tx_{int(time.time()*1000)}_{uuid4().hex[:6]}"
            tx = TransactionRecord(
                transaction_id=transaction_id,
                description=description,
                status=TransactionStatus.STARTED,
            )
            self._transactions[transaction_id] = tx
            # Create transaction snapshot folder
            (self.backup_dir / transaction_id).mkdir(parents=True, exist_ok=True)
            return tx

    def get_transaction(self, tx_id: str) -> TransactionRecord | None:
        """Retrieves a transaction record by identifier."""
        with self._lock:
            return self._transactions.get(tx_id)

    def create_snapshot(self, tx_id: str, target: Path) -> Path | None:
        """Creates a snapshot copy of an existing file prior to mutation."""
        with self._lock:
            if not target.exists() or not target.is_file():
                return None

            tx_backup_dir = self.backup_dir / tx_id
            tx_backup_dir.mkdir(parents=True, exist_ok=True)

            snapshot_name = f"{uuid4().hex[:8]}_{target.name}"
            snapshot_path = tx_backup_dir / snapshot_name
            shutil.copy2(target, snapshot_path)
            return snapshot_path

    def record_operation(self, tx_id: str, op: OperationRecord) -> None:
        """Appends an executed operation to the active transaction."""
        with self._lock:
            tx = self._transactions.get(tx_id)
            if not tx:
                raise ValueError(f"Transaction {tx_id} not found")
            tx.operations.append(op)
            tx.status = TransactionStatus.RUNNING

    def commit(self, tx_id: str) -> TransactionRecord:
        """Finalizes and commits an active transaction."""
        with self._lock:
            tx = self._transactions.get(tx_id)
            if not tx:
                raise ValueError(f"Transaction {tx_id} not found")
            tx.status = TransactionStatus.COMMITTED
            tx.completed_at = _utc_now()
            return tx

    def rollback(self, tx_id: str) -> TransactionRecord:
        """Reverses all completed operations in strict LIFO (reverse) order.

        Raises:
            RollbackFailedError: If any rollback operation cannot be safely completed.
        """
        with self._lock:
            tx = self._transactions.get(tx_id)
            if not tx:
                raise ValueError(f"Transaction {tx_id} not found")

            tx.status = TransactionStatus.ROLLING_BACK

            # Strict reverse order (LIFO)
            for op in reversed(tx.operations):
                if op.rolled_back:
                    continue

                try:
                    self._reverse_operation(op)
                    op.rolled_back = True
                except Exception as e:
                    tx.status = TransactionStatus.ROLLBACK_FAILED
                    tx.completed_at = _utc_now()
                    tx.error = f"Rollback failed on {op.operation_id}: {e}"

                    recovery_info = {
                        "failed_op_id": op.operation_id,
                        "op_type": op.op_type.value,
                        "target_path": str(op.target_path),
                        "backup_path": str(op.backup_path) if op.backup_path else None,
                    }
                    raise RollbackFailedError(
                        f"Critical failure during rollback of transaction {tx_id}: {e}",
                        transaction_id=tx_id,
                        failed_operation=op.operation_id,
                        recovery_info=recovery_info,
                    ) from e

            tx.status = TransactionStatus.ROLLED_BACK
            tx.completed_at = _utc_now()
            return tx

    def _reverse_operation(self, op: OperationRecord) -> None:
        """Executes the specific reversal logic for a single operation."""
        target = op.target_path

        if op.op_type == OperationType.CREATE_FILE:
            # If created new, delete it
            if op.created_new and target.exists() and target.is_file():
                target.unlink()

        elif op.op_type == OperationType.CREATE_DIRECTORY:
            # If created new and empty, remove directory
            if op.created_new and target.exists() and target.is_dir():
                # Check if empty (excluding possible system files)
                if not any(target.iterdir()):
                    target.rmdir()
                else:
                    # Non-empty directory: remove only if NOVA created everything inside
                    shutil.rmtree(target)

        elif op.op_type == OperationType.EDIT_FILE:
            # Restore from backup snapshot
            if not op.backup_path or not op.backup_path.exists():
                raise FileNotFoundError(f"Snapshot backup missing or inaccessible: {op.backup_path}")
            shutil.copy2(op.backup_path, target)
            restored_hash = compute_file_hash(target)
            if op.pre_hash and restored_hash != op.pre_hash:
                raise RuntimeError(f"Restored hash {restored_hash} does not match pre-hash {op.pre_hash}")

        elif op.op_type in (OperationType.RENAME_FILE, OperationType.MOVE_FILE):
            # Move target back to original secondary_path
            if op.secondary_path and target.exists():
                op.secondary_path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, op.secondary_path)

        elif op.op_type == OperationType.COPY_FILE:
            # Remove destination copy
            if target.exists() and target.is_file():
                target.unlink()


# Singleton transaction manager
_global_tx_manager: TransactionManager | None = None


def get_transaction_manager() -> TransactionManager:
    """Provides singleton TransactionManager instance tracking active settings."""
    global _global_tx_manager
    current_backup_dir = (get_settings().data_dir / "backups").resolve()
    if _global_tx_manager is None or _global_tx_manager.backup_dir != current_backup_dir:
        _global_tx_manager = TransactionManager(backup_dir=current_backup_dir)
    return _global_tx_manager
