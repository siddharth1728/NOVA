"""Integration tests for CLI 'plan' (dry-run) and 'execute' (transactional) commands."""

from pathlib import Path
import pytest
from typer.testing import CliRunner

from nova.config.settings import Environment, NovaSettings
from nova.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def configure_test_environment(temp_workspace: Path, temp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = NovaSettings(
        environment=Environment.TEST,
        workspace_root=temp_workspace,
        data_dir=temp_data_dir,
    )
    import nova.config.settings
    monkeypatch.setattr(nova.config.settings, "_settings_instance", settings)


def test_cli_plan_is_strictly_dry_run(temp_workspace: Path) -> None:
    # Record initial files
    initial_files = list(temp_workspace.rglob("*"))

    result = runner.invoke(app, ["plan", "Create a python library called cli-test with src/ and tests/"])
    assert result.exit_code == 0
    assert "DRY-RUN MODE: Zero filesystem modifications made." in result.stdout
    assert "Plan Hash:" in result.stdout

    # Verify absolutely zero mutations were made to disk
    current_files = list(temp_workspace.rglob("*"))
    assert current_files == initial_files
    assert not (temp_workspace / "cli-test").exists()


def test_cli_execute_with_yes_flag(temp_workspace: Path) -> None:
    result = runner.invoke(app, ["execute", "Create demo-app with README.md and src/", "--yes"])
    assert result.exit_code == 0
    assert "Transaction Committed Successfully!" in result.stdout
    assert "Verified" in result.stdout or "verified" in result.stdout

    # Verify mutations took effect
    project_dir = temp_workspace / "demo-app"
    assert project_dir.exists() and project_dir.is_dir()
    assert (project_dir / "src").exists()
    assert (project_dir / "README.md").exists()
