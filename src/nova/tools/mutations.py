"""Controlled workspace mutation tools with transactional safety and rollback tracking."""

import os
from pathlib import Path
import shutil
import time
from typing import Any
from uuid import uuid4

from nova.config.settings import get_settings
from nova.errors import ConflictError
from nova.observability.audit import get_audit_trail
from nova.security.paths import resolve_and_confine
from nova.tools.categories import ToolCategory
from nova.tools.metadata import ToolRiskLevel
from nova.tools.registry import get_tool_registry, nova_tool
from nova.transactions.manager import (
    atomic_write,
    compute_file_hash,
    get_transaction_manager,
)
from nova.transactions.models import OperationRecord, OperationType


def _record_tool_audit(tool: str, inputs: Any, results: Any, success: bool = True, error: str | None = None) -> None:
    audit = get_audit_trail()
    audit.log_tool_invocation(
        tool=tool,
        risk_level="MEDIUM",
        approval_state="APPROVED",
        inputs=inputs,
        results=results,
        success=success,
        error=error,
    )


def create_directory(directory_path: str, tx_id: str | None = None) -> dict[str, Any]:
    """Creates a new directory inside the workspace.

    Args:
        directory_path: Target directory path.
        tx_id: Optional active transaction ID.

    Returns:
        Structured result dict.
    """
    settings = get_settings()
    canonical_dir = resolve_and_confine(directory_path, settings.workspace_root)

    if canonical_dir.exists():
        if canonical_dir.is_file():
            raise ConflictError(
                f"Cannot create directory '{canonical_dir}': path already exists as a file.",
                conflict_type="PATH_CONFLICT",
                target_path=str(canonical_dir),
            )
        created_new = False
    else:
        canonical_dir.mkdir(parents=True, exist_ok=True)
        created_new = True

    if tx_id:
        tx_mgr = get_transaction_manager()
        op = OperationRecord(
            operation_id=f"op_{int(time.time()*1000)}_{uuid4().hex[:4]}",
            op_type=OperationType.CREATE_DIRECTORY,
            target_path=canonical_dir,
            created_new=created_new,
        )
        tx_mgr.record_operation(tx_id, op)

    result = {
        "status": "success",
        "operation": "create_directory",
        "target": str(canonical_dir),
        "created_new": created_new,
    }
    _record_tool_audit("create_directory", {"path": str(canonical_dir)}, result)
    return result


def create_file(
    file_path: str,
    content: str,
    overwrite: bool = False,
    tx_id: str | None = None,
) -> dict[str, Any]:
    """Creates a new file with specified content atomically within the workspace.

    Args:
        file_path: Target file path.
        content: Text content to write.
        overwrite: Whether to overwrite existing file if present.
        tx_id: Optional active transaction ID.

    Returns:
        Structured result dict with hash and size.
    """
    settings = get_settings()
    canonical_file = resolve_and_confine(file_path, settings.workspace_root)

    if canonical_file.exists() and not overwrite:
        raise ConflictError(
            f"Cannot create file '{canonical_file}': target already exists and overwrite is False.",
            conflict_type="TARGET_EXISTS",
            target_path=str(canonical_file),
        )

    pre_hash = compute_file_hash(canonical_file) if canonical_file.exists() else None
    pre_size = canonical_file.stat().st_size if canonical_file.exists() else None
    created_new = not canonical_file.exists()

    backup_path = None
    if tx_id and canonical_file.exists():
        tx_mgr = get_transaction_manager()
        backup_path = tx_mgr.create_snapshot(tx_id, canonical_file)

    post_hash, post_size = atomic_write(canonical_file, content)

    if tx_id:
        tx_mgr = get_transaction_manager()
        op = OperationRecord(
            operation_id=f"op_{int(time.time()*1000)}_{uuid4().hex[:4]}",
            op_type=OperationType.CREATE_FILE,
            target_path=canonical_file,
            backup_path=backup_path,
            pre_hash=pre_hash,
            post_hash=post_hash,
            pre_size=pre_size,
            post_size=post_size,
            created_new=created_new,
        )
        tx_mgr.record_operation(tx_id, op)

    result = {
        "status": "success",
        "operation": "create_file",
        "target": str(canonical_file),
        "hash": post_hash,
        "size": post_size,
        "created_new": created_new,
    }
    _record_tool_audit("create_file", {"path": str(canonical_file), "size": post_size}, result)
    return result


def edit_file(
    file_path: str,
    replacement_content: str,
    expected_hash: str | None = None,
    target_content: str | None = None,
    tx_id: str | None = None,
) -> dict[str, Any]:
    """Modifies an existing file with stale-state detection and snapshot protection.

    Args:
        file_path: Target file path.
        replacement_content: New text content to write.
        expected_hash: Optional SHA-256 hash expected before applying edit.
        target_content: Optional substring to search and replace if targeted edit.
        tx_id: Optional active transaction ID.

    Returns:
        Structured result dict.
    """
    settings = get_settings()
    canonical_file = resolve_and_confine(file_path, settings.workspace_root)

    if not canonical_file.exists():
        raise ConflictError(
            f"Cannot edit file '{canonical_file}': target does not exist.",
            conflict_type="TARGET_MISSING",
            target_path=str(canonical_file),
        )

    pre_hash = compute_file_hash(canonical_file)
    pre_size = canonical_file.stat().st_size

    # Concurrency / Stale file protection
    if expected_hash and pre_hash != expected_hash:
        raise ConflictError(
            f"File '{canonical_file}' was modified since planning. Expected hash {expected_hash} but found {pre_hash}.",
            conflict_type="FILE_CHANGED_SINCE_PLAN",
            target_path=str(canonical_file),
            details={"expected_hash": expected_hash, "observed_hash": pre_hash},
        )

    backup_path = None
    if tx_id:
        tx_mgr = get_transaction_manager()
        backup_path = tx_mgr.create_snapshot(tx_id, canonical_file)

    if target_content is not None:
        current_text = canonical_file.read_text(encoding="utf-8")
        if target_content not in current_text:
            raise ConflictError(
                f"Target content block not found in '{canonical_file}'.",
                conflict_type="CONTENT_MISMATCH",
                target_path=str(canonical_file),
            )
        new_text = current_text.replace(target_content, replacement_content, 1)
    else:
        new_text = replacement_content

    post_hash, post_size = atomic_write(canonical_file, new_text)

    if tx_id:
        tx_mgr = get_transaction_manager()
        op = OperationRecord(
            operation_id=f"op_{int(time.time()*1000)}_{uuid4().hex[:4]}",
            op_type=OperationType.EDIT_FILE,
            target_path=canonical_file,
            backup_path=backup_path,
            pre_hash=pre_hash,
            post_hash=post_hash,
            pre_size=pre_size,
            post_size=post_size,
            created_new=False,
        )
        tx_mgr.record_operation(tx_id, op)

    result = {
        "status": "success",
        "operation": "edit_file",
        "target": str(canonical_file),
        "pre_hash": pre_hash,
        "post_hash": post_hash,
        "size": post_size,
    }
    _record_tool_audit("edit_file", {"path": str(canonical_file), "post_hash": post_hash}, result)
    return result


def rename_file(source_path: str, new_name_or_path: str, tx_id: str | None = None) -> dict[str, Any]:
    """Renames an existing file or directory within the workspace.

    Args:
        source_path: Existing item path.
        new_name_or_path: New name or relative path.
        tx_id: Optional active transaction ID.

    Returns:
        Structured result dict.
    """
    settings = get_settings()
    canonical_source = resolve_and_confine(source_path, settings.workspace_root)

    if not canonical_source.exists():
        raise ConflictError(
            f"Cannot rename '{canonical_source}': source does not exist.",
            conflict_type="TARGET_MISSING",
            target_path=str(canonical_source),
        )

    # If new_name is just a filename, place in same directory
    if os.sep not in new_name_or_path and "/" not in new_name_or_path:
        dest_candidate = canonical_source.parent / new_name_or_path
    else:
        dest_candidate = Path(new_name_or_path)

    canonical_dest = resolve_and_confine(dest_candidate, settings.workspace_root)

    if canonical_dest.exists():
        raise ConflictError(
            f"Cannot rename to '{canonical_dest}': destination already exists.",
            conflict_type="TARGET_EXISTS",
            target_path=str(canonical_dest),
        )

    file_hash = compute_file_hash(canonical_source) if canonical_source.is_file() else None
    os.replace(canonical_source, canonical_dest)

    if tx_id:
        tx_mgr = get_transaction_manager()
        op = OperationRecord(
            operation_id=f"op_{int(time.time()*1000)}_{uuid4().hex[:4]}",
            op_type=OperationType.RENAME_FILE,
            target_path=canonical_dest,
            secondary_path=canonical_source,
            pre_hash=file_hash,
            post_hash=file_hash,
        )
        tx_mgr.record_operation(tx_id, op)

    result = {
        "status": "success",
        "operation": "rename_file",
        "source": str(canonical_source),
        "destination": str(canonical_dest),
        "hash": file_hash,
    }
    _record_tool_audit("rename_file", {"source": str(canonical_source), "destination": str(canonical_dest)}, result)
    return result


def move_file(source_path: str, destination_path: str, tx_id: str | None = None) -> dict[str, Any]:
    """Moves an existing file or directory to another directory within the workspace.

    Args:
        source_path: Existing item path.
        destination_path: Destination folder or file path.
        tx_id: Optional active transaction ID.

    Returns:
        Structured result dict.
    """
    settings = get_settings()
    canonical_source = resolve_and_confine(source_path, settings.workspace_root)

    if not canonical_source.exists():
        raise ConflictError(
            f"Cannot move '{canonical_source}': source does not exist.",
            conflict_type="TARGET_MISSING",
            target_path=str(canonical_source),
        )

    dest_cand = Path(destination_path)
    if not dest_cand.is_absolute():
        dest_cand = settings.workspace_root / dest_cand

    # If destination exists and is a directory, append source name
    if dest_cand.exists() and dest_cand.is_dir():
        dest_cand = dest_cand / canonical_source.name

    canonical_dest = resolve_and_confine(dest_cand, settings.workspace_root)

    if canonical_dest.exists():
        raise ConflictError(
            f"Cannot move to '{canonical_dest}': destination already exists.",
            conflict_type="TARGET_EXISTS",
            target_path=str(canonical_dest),
        )

    canonical_dest.parent.mkdir(parents=True, exist_ok=True)
    file_hash = compute_file_hash(canonical_source) if canonical_source.is_file() else None
    os.replace(canonical_source, canonical_dest)

    if tx_id:
        tx_mgr = get_transaction_manager()
        op = OperationRecord(
            operation_id=f"op_{int(time.time()*1000)}_{uuid4().hex[:4]}",
            op_type=OperationType.MOVE_FILE,
            target_path=canonical_dest,
            secondary_path=canonical_source,
            pre_hash=file_hash,
            post_hash=file_hash,
        )
        tx_mgr.record_operation(tx_id, op)

    result = {
        "status": "success",
        "operation": "move_file",
        "source": str(canonical_source),
        "destination": str(canonical_dest),
        "hash": file_hash,
    }
    _record_tool_audit("move_file", {"source": str(canonical_source), "destination": str(canonical_dest)}, result)
    return result


def copy_file(
    source_path: str,
    destination_path: str,
    overwrite: bool = False,
    tx_id: str | None = None,
) -> dict[str, Any]:
    """Copies an existing file within the workspace.

    Args:
        source_path: Existing file path.
        destination_path: Destination file path.
        overwrite: Whether to overwrite existing destination.
        tx_id: Optional active transaction ID.

    Returns:
        Structured result dict.
    """
    settings = get_settings()
    canonical_source = resolve_and_confine(source_path, settings.workspace_root)

    if not canonical_source.exists() or not canonical_source.is_file():
        raise ConflictError(
            f"Cannot copy '{canonical_source}': source file does not exist.",
            conflict_type="TARGET_MISSING",
            target_path=str(canonical_source),
        )

    dest_cand = Path(destination_path)
    if not dest_cand.is_absolute():
        dest_cand = settings.workspace_root / dest_cand

    if dest_cand.exists() and dest_cand.is_dir():
        dest_cand = dest_cand / canonical_source.name

    canonical_dest = resolve_and_confine(dest_cand, settings.workspace_root)

    if canonical_dest.exists() and not overwrite:
        raise ConflictError(
            f"Cannot copy to '{canonical_dest}': destination already exists and overwrite is False.",
            conflict_type="TARGET_EXISTS",
            target_path=str(canonical_dest),
        )

    canonical_dest.parent.mkdir(parents=True, exist_ok=True)
    created_new = not canonical_dest.exists()
    shutil.copy2(canonical_source, canonical_dest)
    dest_hash = compute_file_hash(canonical_dest)

    if tx_id:
        tx_mgr = get_transaction_manager()
        op = OperationRecord(
            operation_id=f"op_{int(time.time()*1000)}_{uuid4().hex[:4]}",
            op_type=OperationType.COPY_FILE,
            target_path=canonical_dest,
            secondary_path=canonical_source,
            post_hash=dest_hash,
            created_new=created_new,
        )
        tx_mgr.record_operation(tx_id, op)

    result = {
        "status": "success",
        "operation": "copy_file",
        "source": str(canonical_source),
        "destination": str(canonical_dest),
        "hash": dest_hash,
    }
    _record_tool_audit("copy_file", {"source": str(canonical_source), "destination": str(canonical_dest)}, result)
    return result


def register_mutation_tools() -> None:
    """Registers the six controlled mutation tools into the global ToolRegistry."""
    registry = get_tool_registry()

    tools_to_register = [
        ("create_directory", create_directory, "Create a directory safely inside the workspace root."),
        ("create_file", create_file, "Create a new file with text content atomically inside the workspace."),
        ("edit_file", edit_file, "Edit an existing file with stale-state conflict detection."),
        ("rename_file", rename_file, "Rename a file or folder safely within the workspace."),
        ("move_file", move_file, "Move a file or folder safely within the workspace."),
        ("copy_file", copy_file, "Copy a file safely within the workspace."),
    ]

    for name, fn, desc in tools_to_register:
        nova_tool(
            name=name,
            description=desc,
            category=ToolCategory.FILESYSTEM,
            risk_level=ToolRiskLevel.MEDIUM,
            requires_approval=True,
            mutates_state=True,
            is_reversible=True,
            registry=registry,
        )(fn)


# Register immediately upon module import
register_mutation_tools()
