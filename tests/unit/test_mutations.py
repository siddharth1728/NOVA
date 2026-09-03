"""Unit tests for the six workspace mutation tools and collision handling."""

from pathlib import Path
import pytest

from nova.config.settings import Environment, NovaSettings
from nova.errors import ConflictError, PermissionDeniedError
from nova.tools.mutations import (
    copy_file,
    create_directory,
    create_file,
    edit_file,
    move_file,
    rename_file,
)
from nova.transactions.manager import compute_file_hash


@pytest.fixture(autouse=True)
def configure_test_workspace(temp_workspace: Path, temp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
    )
    import nova.config.settings
    monkeypatch.setattr(nova.config.settings, "_settings_instance", settings)


def test_create_directory(temp_workspace: Path) -> None:
    target_dir = temp_workspace / "new_folder" / "nested"
    res = create_directory(str(target_dir))
    assert res["status"] == "success"
    assert target_dir.exists()
    assert target_dir.is_dir()
    assert res["created_new"] is True

    # Calling again should succeed with created_new=False
    res2 = create_directory(str(target_dir))
    assert res2["created_new"] is False


def test_create_directory_collision_with_file(temp_workspace: Path) -> None:
    existing_file = temp_workspace / "hello.txt"
    with pytest.raises(ConflictError) as exc_info:
        create_directory(str(existing_file))
    assert exc_info.value.conflict_type == "PATH_CONFLICT"


def test_create_file(temp_workspace: Path) -> None:
    target = temp_workspace / "created.txt"
    content = "New file content 123"
    res = create_file(str(target), content)

    assert res["status"] == "success"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == content
    assert res["size"] == len(content)
    assert res["hash"] == compute_file_hash(target)


def test_create_file_collision_without_overwrite(temp_workspace: Path) -> None:
    target = temp_workspace / "hello.txt"
    with pytest.raises(ConflictError) as exc_info:
        create_file(str(target), "Overwriting?", overwrite=False)
    assert exc_info.value.conflict_type == "TARGET_EXISTS"


def test_edit_file_success_and_stale_detection(temp_workspace: Path) -> None:
    target = temp_workspace / "hello.txt"
    original_hash = compute_file_hash(target)

    # 1. Stale-file conflict: expected_hash doesn't match
    with pytest.raises(ConflictError) as exc_info:
        edit_file(str(target), "New Text", expected_hash="mismatched_stale_hash")
    assert exc_info.value.conflict_type == "FILE_CHANGED_SINCE_PLAN"

    # 2. Valid edit with correct expected_hash
    res = edit_file(str(target), "Updated Text", expected_hash=original_hash)
    assert res["status"] == "success"
    assert target.read_text(encoding="utf-8") == "Updated Text"
    assert res["post_hash"] == compute_file_hash(target)


def test_rename_file(temp_workspace: Path) -> None:
    source = temp_workspace / "hello.txt"
    new_name = "renamed.txt"
    dest = temp_workspace / new_name

    res = rename_file(str(source), new_name)
    assert res["status"] == "success"
    assert not source.exists()
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == "Hello NOVA"


def test_move_file(temp_workspace: Path) -> None:
    source = temp_workspace / "hello.txt"
    dest_dir = temp_workspace / "sub"
    dest_file = dest_dir / "hello.txt"

    res = move_file(str(source), str(dest_dir))
    assert res["status"] == "success"
    assert not source.exists()
    assert dest_file.exists()
    assert dest_file.read_text(encoding="utf-8") == "Hello NOVA"


def test_copy_file(temp_workspace: Path) -> None:
    source = temp_workspace / "hello.txt"
    dest = temp_workspace / "hello_copy.txt"

    res = copy_file(str(source), str(dest))
    assert res["status"] == "success"
    assert source.exists()
    assert dest.exists()
    assert compute_file_hash(source) == compute_file_hash(dest)


def test_mutations_reject_out_of_workspace_targets(temp_workspace: Path) -> None:
    outside = temp_workspace / ".." / "evil.txt"

    with pytest.raises(PermissionDeniedError):
        create_file(str(outside), "hacked")

    with pytest.raises(PermissionDeniedError):
        create_directory(str(temp_workspace / ".." / "evil_dir"))

    with pytest.raises(PermissionDeniedError):
        edit_file(str(outside), "hacked")

    with pytest.raises(PermissionDeniedError):
        rename_file(str(temp_workspace / "hello.txt"), str(outside))

    with pytest.raises(PermissionDeniedError):
        copy_file(str(temp_workspace / "hello.txt"), str(outside))
