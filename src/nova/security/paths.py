"""Robust canonical path resolution and workspace boundary confinement."""

import os
from pathlib import Path
import sys

from nova.errors import PermissionDeniedError


def canonicalize_path(path_input: Path | str) -> Path:
    """Resolves an existing or pending path to its canonical, normalized representation.

    Handles nonexistent target files by resolving the nearest existing ancestor.
    """
    raw = str(path_input).strip()
    if raw.startswith("file:///"):
        raw = raw[8:]
    elif raw.startswith("file://"):
        raw = raw[7:]

    p = Path(raw)

    # If the exact path exists, resolve directly
    if p.exists():
        return p.resolve()

    # For nonexistent paths, traverse upward to find the closest existing parent
    curr = p
    tail_parts: list[str] = []
    while not curr.exists() and curr != curr.parent:
        tail_parts.append(curr.name)
        curr = curr.parent

    # Resolve existing ancestor and recombine with child segments
    resolved_ancestor = curr.resolve()
    for segment in reversed(tail_parts):
        resolved_ancestor = resolved_ancestor / segment

    return resolved_ancestor


def is_confined(target_path: Path | str, workspace_root: Path | str) -> bool:
    """Determines whether target_path resides strictly within workspace_root.

    Correctly enforces Windows case-insensitivity, drive boundaries, and directory separators.

    Args:
        target_path: File or directory path to check.
        workspace_root: Allowed confinement root.

    Returns:
        True if target_path is within or equal to workspace_root, False otherwise.
    """
    try:
        canonical_target = canonicalize_path(target_path)
        canonical_root = Path(workspace_root).resolve()

        if sys.platform == "win32":
            target_norm = os.path.normcase(str(canonical_target))
            root_norm = os.path.normcase(str(canonical_root))

            # Must equal root exactly or be in a subfolder with separator
            if target_norm == root_norm:
                return True
            return target_norm.startswith(root_norm + os.sep)
        else:
            try:
                canonical_target.relative_to(canonical_root)
                return True
            except ValueError:
                return False
    except Exception:
        # On any resolution or filesystem anomaly, fail closed
        return False


def resolve_and_confine(target_path: Path | str, workspace_root: Path | str) -> Path:
    """Resolves target_path canonically and guarantees it resides within workspace_root.

    Args:
        target_path: Path to resolve.
        workspace_root: Confinement root.

    Returns:
        Resolved canonical Path.

    Raises:
        PermissionDeniedError: If the target path lies outside the workspace boundary.
    """
    canonical_target = canonicalize_path(target_path)
    canonical_root = Path(workspace_root).resolve()

    if not is_confined(canonical_target, canonical_root):
        raise PermissionDeniedError(
            f"Path '{target_path}' resolves to '{canonical_target}' which lies outside the workspace root '{canonical_root}'",
            tool_name="path_confinement",
            target_path=str(canonical_target),
        )

    return canonical_target
