"""Unit tests for canonical path resolution and workspace confinement."""

from pathlib import Path
import pytest

from nova.errors import PermissionDeniedError
from nova.security.paths import canonicalize_path, is_confined, resolve_and_confine


def test_canonicalize_existing_and_nonexistent(temp_workspace: Path) -> None:
    # Existing file
    existing = temp_workspace / "hello.txt"
    assert canonicalize_path(existing) == existing.resolve()

    # Nonexistent child
    nonexistent = temp_workspace / "sub" / "new_dir" / "file.txt"
    resolved = canonicalize_path(nonexistent)
    assert resolved.name == "file.txt"
    assert resolved.parent.name == "new_dir"


def test_is_confined_valid(temp_workspace: Path) -> None:
    assert is_confined(temp_workspace, temp_workspace)
    assert is_confined(temp_workspace / "hello.txt", temp_workspace)
    assert is_confined(temp_workspace / "sub" / "nested.py", temp_workspace)
    assert is_confined(temp_workspace / "sub" / "deep" / "future.txt", temp_workspace)


def test_is_confined_traversal_attacks(temp_workspace: Path) -> None:
    # Parent escape
    assert not is_confined(temp_workspace / ".." / "escaped.txt", temp_workspace)
    assert not is_confined(temp_workspace / "sub" / ".." / ".." / "escaped.txt", temp_workspace)

    # External absolute paths
    assert not is_confined(Path("C:/Windows/System32"), temp_workspace)
    assert not is_confined(Path("C:/Users"), temp_workspace)


def test_resolve_and_confine_success(temp_workspace: Path) -> None:
    target = temp_workspace / "new_project" / "src"
    resolved = resolve_and_confine(target, temp_workspace)
    assert resolved == target.resolve()


def test_resolve_and_confine_raises_on_escape(temp_workspace: Path) -> None:
    outside = temp_workspace / ".." / "secret.key"
    with pytest.raises(PermissionDeniedError) as exc_info:
        resolve_and_confine(outside, temp_workspace)
    assert exc_info.value.tool_name == "path_confinement"
    assert "outside the workspace root" in str(exc_info.value)
