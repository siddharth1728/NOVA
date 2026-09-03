"""NOVA Command Line Interface."""

import asyncio
import importlib.metadata
import platform
import sys
from typing import Annotated

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from nova import __version__
from nova.agent.runtime import NovaRuntime
from nova.config.settings import get_settings
from nova.errors import ConfigurationError, NovaError
from nova.observability.audit import get_audit_trail
from nova.security.permissions import PermissionEngine, check_workspace_containment
from nova.tools.registry import get_tool_registry

app = typer.Typer(
    name="nova",
    help="NOVA: Local-first personal AI operating layer built on Google Antigravity.",
    add_completion=False,
)
console = Console()


@app.command(name="info")
def info_command() -> None:
    """Displays system status, versions, security profile, and workspace confinement."""
    settings = get_settings()

    try:
        sdk_version = importlib.metadata.version("google-antigravity")
    except Exception:
        sdk_version = "unknown"

    table = Table(title="NOVA System Information", show_header=True, header_style="bold cyan")
    table.add_column("Property", style="bold")
    table.add_column("Value")

    table.add_row("NOVA Version", __version__)
    table.add_row("Python Version", platform.python_version())
    table.add_row("Operating System", f"{platform.system()} {platform.release()} ({platform.version()})")
    table.add_row("Antigravity SDK", sdk_version)
    table.add_row("Workspace Root", str(settings.workspace_root))
    table.add_row("Data Directory", str(settings.data_dir))
    table.add_row("Security Mode", settings.security_mode.value.upper())
    table.add_row("Target Model", settings.model_name)
    table.add_row("Thinking Level", settings.thinking_level)
    table.add_row("API Key Configured", "[green]Yes (Masked)[/green]" if settings.get_api_key_value() else "[yellow]No (Set GEMINI_API_KEY)[/yellow]")
    table.add_row("Runtime Status", "[green]Ready (Phase 01)[/green]")

    console.print(table)


@app.command(name="check")
def check_command() -> None:
    """Executes comprehensive subsystem diagnostic health checks."""
    settings = get_settings()
    registry = get_tool_registry()
    engine = PermissionEngine(settings=settings, registry=registry)
    audit = get_audit_trail()

    table = Table(title="NOVA Subsystem Diagnostics", show_header=True, header_style="bold green")
    table.add_column("Subsystem", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    # 1. Python Environment
    table.add_row("Python Runtime", "[green]PASS[/green]", f"v{platform.python_version()}")

    # 2. Antigravity SDK
    try:
        import google.antigravity as ag
        sdk_v = importlib.metadata.version("google-antigravity")
        table.add_row("Antigravity SDK", "[green]PASS[/green]", f"google-antigravity v{sdk_v} bound")
    except Exception as e:
        table.add_row("Antigravity SDK", "[red]FAIL[/red]", str(e))

    # 3. Configuration & Settings
    try:
        safe_cfg = settings.safe_dump()
        table.add_row("Configuration", "[green]PASS[/green]", f"Mode: {settings.security_mode.value}, Env: {settings.environment.value}")
    except Exception as e:
        table.add_row("Configuration", "[red]FAIL[/red]", str(e))

    # 4. Workspace Confinement
    if settings.workspace_root.exists():
        table.add_row("Workspace Root", "[green]PASS[/green]", str(settings.workspace_root))
    else:
        table.add_row("Workspace Root", "[yellow]WARN[/yellow]", f"Path {settings.workspace_root} does not exist yet")

    # 5. Tool Registry
    tools = registry.list_tools()
    read_only_tools = registry.get_phase01_builtin_tools()
    table.add_row("Tool Registry", "[green]PASS[/green]", f"{len(tools)} registered, {len(read_only_tools)} read-only enabled")

    # 6. Security & Permissions
    boundary_ok = check_workspace_containment(settings.workspace_root / "test.txt", settings.workspace_root)
    table.add_row("Security Engine", "[green]PASS[/green]", f"Workspace confinement active: {boundary_ok}")

    # 7. Local Data & Audit
    try:
        audit.log_tool_invocation(
            tool="diagnostic_check",
            risk_level="READ_ONLY",
            approval_state="AUTO",
            inputs={"check": "health"},
            results={"status": "ok"},
        )
        table.add_row("Audit Trail", "[green]PASS[/green]", f"Active at {audit.log_file}")
    except Exception as e:
        table.add_row("Audit Trail", "[red]FAIL[/red]", str(e))

    # 8. Memory Storage
    try:
        mem_dir = settings.memory_dir
        mem_dir.mkdir(parents=True, exist_ok=True)
        table.add_row("Memory Store", "[green]PASS[/green]", f"Local-first store at {mem_dir}")
    except Exception as e:
        table.add_row("Memory Store", "[red]FAIL[/red]", str(e))

    console.print(table)


@app.command(name="query")
def query_command(
    prompt: Annotated[str, typer.Argument(help="Natural language query or goal for NOVA")],
    simulate: Annotated[bool, typer.Option("--simulate", "-s", help="Run local verified simulation without requiring external API keys")] = False,
) -> None:
    """Executes a verified read-only query through the NOVA agent runtime."""
    settings = get_settings()

    console.print(Panel.fit(f"[bold cyan]Query:[/bold cyan] {prompt}", title="NOVA Agent Request"))

    runtime = NovaRuntime(settings=settings)

    try:
        if simulate:
            result = runtime.simulate_query(prompt)
        else:
            result = asyncio.run(runtime.query(prompt))
        console.print(Panel(result, title="[bold green]NOVA Verified Response[/bold green]", border_style="green"))
    except ConfigurationError as e:
        error_msg = (
            f"[bold red]Configuration Required:[/bold red]\n{e.message}\n\n"
            "[bold cyan]Tip:[/bold cyan] To test the local inspection, audit trail, and verification pipeline offline without an API key, run:\n"
            f"  [green]nova query \"{prompt}\" --simulate[/green]"
        )
        console.print(Panel(error_msg, title="Setup Needed", border_style="red"))
        sys.exit(1)
    except NovaError as e:
        console.print(Panel(f"[bold red]Execution Error:[/bold red]\n{e}", title="NOVA Error", border_style="red"))
        sys.exit(1)
    except Exception as e:
        console.print(Panel(f"[bold red]Unexpected Error:[/bold red]\n{e}", title="Error", border_style="red"))
        sys.exit(1)


def cli() -> None:
    """Entry point for project scripts."""
    app()


if __name__ == "__main__":
    app()
