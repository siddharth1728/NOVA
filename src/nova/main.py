"""NOVA Command Line Interface."""

import asyncio
import importlib.metadata
import platform
import sys
from pathlib import Path
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


@app.command(name="plan")
def plan_command(
    prompt: Annotated[str, typer.Argument(help="Goal or project structure request to plan")],
) -> None:
    """Constructs a structured multi-step plan without performing any filesystem mutations (dry-run)."""
    from nova.planning.planner import TaskPlanner

    settings = get_settings()
    planner = TaskPlanner(workspace_root=settings.workspace_root)

    try:
        plan = planner.create_plan_for_goal(prompt)

        table = Table(title=f"NOVA Proposed Plan: {plan.goal}", show_header=True, header_style="bold cyan")
        table.add_column("Step", style="bold", width=6)
        table.add_column("Description", style="white")
        table.add_column("Tool", style="yellow")
        table.add_column("Target", style="cyan")
        table.add_column("Deps", style="magenta")
        table.add_column("Risk", style="red")

        for step in plan.steps:
            deps_str = ", ".join(str(d) for d in step.dependencies) if step.dependencies else "-"
            table.add_row(
                str(step.step_id),
                step.description,
                step.tool,
                Path(step.target).name or step.target,
                deps_str,
                step.risk_level.value,
            )

        console.print(table)
        summary = (
            f"[bold]Plan ID:[/bold] {plan.plan_id}\n"
            f"[bold]Plan Hash:[/bold] {plan.plan_hash}\n"
            f"[bold]Total Operations:[/bold] {len(plan.steps)} planned\n"
            f"[bold]Risk Ceiling:[/bold] {plan.risk_ceiling.value}\n\n"
            "[bold yellow]DRY-RUN MODE: Zero filesystem modifications made.[/bold yellow]\n"
            f"To execute this plan with transactional safety, run:\n"
            f"  [green]nova execute \"{prompt}\"[/green]"
        )
        console.print(Panel(summary, title="[bold green]Plan Summary[/bold green]", border_style="cyan"))

    except Exception as e:
        console.print(Panel(f"[bold red]Planning Error:[/bold red]\n{e}", title="Error", border_style="red"))
        sys.exit(1)


@app.command(name="execute")
def execute_command(
    prompt: Annotated[str, typer.Argument(help="Goal or project structure request to plan and execute")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Automatically approve the plan without prompting")] = False,
) -> None:
    """Plans, prompts for confirmation, and executes mutations inside a verified atomic transaction."""
    from nova.planning.executor import PlanExecutor
    from nova.planning.planner import TaskPlanner

    settings = get_settings()
    planner = TaskPlanner(workspace_root=settings.workspace_root)
    executor = PlanExecutor()

    try:
        # 1. Synthesize Plan
        plan = planner.create_plan_for_goal(prompt)

        table = Table(title=f"Proposed Plan: {plan.goal}", show_header=True, header_style="bold cyan")
        table.add_column("Step", style="bold", width=6)
        table.add_column("Description", style="white")
        table.add_column("Tool", style="yellow")
        table.add_column("Target", style="cyan")
        table.add_column("Risk", style="red")

        for step in plan.steps:
            table.add_row(
                str(step.step_id),
                step.description,
                step.tool,
                Path(step.target).name or step.target,
                step.risk_level.value,
            )

        console.print(table)
        console.print(f"[bold]Plan Hash:[/bold] {plan.plan_hash}")
        console.print(f"[bold]Workspace:[/bold] {settings.workspace_root}")
        console.print(f"[bold]Total Changes:[/bold] {len(plan.steps)} operations proposed (Risk: {plan.risk_ceiling.value})")

        # 2. Approval Gate
        if not yes:
            approved = typer.confirm("Authorize this transaction?", default=False)
            if not approved:
                console.print("[yellow]Execution cancelled by user. Zero changes made.[/yellow]")
                sys.exit(0)

        # 3. Transactional Execution & Verification
        console.print("\n[bold cyan]Starting Transactional Execution...[/bold cyan]")
        result = executor.execute(plan, approved_hash=plan.plan_hash)

        if result.success:
            success_msg = (
                f"[bold green][OK] Transaction Committed Successfully![/bold green]\n\n"
                f"Goal: {plan.goal}\n"
                f"Completed: {result.completed_steps}/{result.total_steps} operations verified.\n"
                f"Transaction ID: {result.transaction_id}\n"
                f"Status: {result.status.value}"
            )
            console.print(Panel(success_msg, title="[bold green]NOVA Transaction Result[/bold green]", border_style="green"))
        else:
            fail_msg = (
                f"[bold red][FAILED] Execution Failed at Step {result.completed_steps + 1}[/bold red]\n"
                f"Error: {result.error}\n\n"
                f"Rollback Status: {'Cleanly Restored (LIFO verified)' if result.rollback_verified else 'ROLLBACK FAILED'}"
            )
            console.print(Panel(fail_msg, title="[bold red]Transaction Rolled Back[/bold red]", border_style="red"))
            sys.exit(1)

    except Exception as e:
        console.print(Panel(f"[bold red]Execution Failure:[/bold red]\n{e}", title="Error", border_style="red"))
        sys.exit(1)


# Host Subcommands (Phase 03)
host_app = typer.Typer(name="host", help="Manage NOVA Windows Host service and mobile device pairing.")
app.add_typer(host_app, name="host")


@host_app.command(name="start")
def host_start_command(
    bind: Annotated[str, typer.Option("--host", "-h", help="Network host/interface to bind")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="TCP port to listen on")] = 8000,
    log_level: Annotated[str, typer.Option("--log-level", "-l", help="Server log level")] = "info",
) -> None:
    """Starts the NOVA Windows Host ASGI service for mobile and remote control."""
    from nova.host.server import create_host_app, run_host_server

    settings = get_settings()
    console.print(
        Panel(
            f"[bold cyan]NOVA Windows Host Service[/bold cyan]\n"
            f"[white]Binding to:[/white] http://{bind}:{port}\n"
            f"[white]WebSocket:[/white] ws://{bind}:{port}/ws/v1/events\n"
            f"[white]Workspace:[/white] {settings.workspace_root}\n"
            f"[white]Device Registry:[/white] {settings.devices_file}\n"
            f"[green]Ready for mobile device connections.[/green]",
            title="[bold green]NOVA Host Online[/bold green]",
            border_style="green",
        )
    )
    app_instance = create_host_app(settings=settings)
    run_host_server(app_instance, host=bind, port=port, log_level=log_level)


@host_app.command(name="pair-code")
def host_pair_code_command(
    ttl: Annotated[int, typer.Option("--ttl", "-t", help="Validity period in seconds")] = 300,
) -> None:
    """Generates an ephemeral 6-digit pairing code to authorize a new mobile device."""
    from nova.host.pairing import PairingManager

    pm = PairingManager(default_ttl_seconds=ttl)
    code, exp = pm.generate_code()

    console.print(
        Panel(
            f"\n[bold yellow]        {code[:3]} {code[3:]}        [/bold yellow]\n\n"
            f"[white]Expires at:[/white] {exp.strftime('%H:%M:%S UTC')}\n"
            f"[white]Enter this code in the NOVA iOS app to link this device.[/white]",
            title="[bold cyan]Device Pairing Code[/bold cyan]",
            border_style="yellow",
        )
    )


@host_app.command(name="devices")
def host_devices_command() -> None:
    """Lists all paired client devices in the host trust registry."""
    from nova.host.auth import DeviceRegistry

    settings = get_settings()
    reg = DeviceRegistry(settings.devices_file)
    devices = reg.list_devices()

    if not devices:
        console.print("[yellow]No devices currently paired. Run 'nova host pair-code' to link a device.[/yellow]")
        return

    table = Table(title="Paired NOVA Client Devices", show_header=True, header_style="bold cyan")
    table.add_column("Device ID", style="bold")
    table.add_column("Name")
    table.add_column("Platform")
    table.add_column("Role")
    table.add_column("Status")
    table.add_column("Last Seen")

    for d in devices:
        status_color = "green" if d.status.value == "ACTIVE" else "red"
        table.add_row(
            d.device_id,
            d.name,
            d.platform,
            d.role.value,
            f"[{status_color}]{d.status.value}[/{status_color}]",
            d.last_seen_at or "Never",
        )

    console.print(table)


@host_app.command(name="revoke")
def host_revoke_command(
    device_id: Annotated[str, typer.Argument(help="ID of the device to revoke access from")],
) -> None:
    """Revokes access for a specified client device immediately."""
    from nova.host.auth import DeviceRegistry

    settings = get_settings()
    reg = DeviceRegistry(settings.devices_file)
    if reg.revoke_device(device_id):
        console.print(f"[bold green]Device '{device_id}' has been REVOKED.[/bold green] All future requests will be denied.")
    else:
        console.print(f"[bold red]Device '{device_id}' not found in registry.[/bold red]")
        sys.exit(1)


def cli() -> None:
    """Entry point for project scripts."""
    app()


if __name__ == "__main__":
    app()
