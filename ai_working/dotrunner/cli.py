"""
Command-line interface for DotRunner

Provides commands for running, listing, and managing workflow sessions.
"""

import asyncio
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ai_working.dotrunner.engine import WorkflowEngine
from ai_working.dotrunner.persistence import list_sessions
from ai_working.dotrunner.persistence import load_state
from ai_working.dotrunner.persistence import load_workflow
from ai_working.dotrunner.workflow import Workflow

console = Console()


@click.group()
@click.version_option(version="0.2.0", prog_name="dotrunner")
def cli():
    """DotRunner - AI-powered workflow automation

    Declarative workflow orchestration using YAML and Claude AI.
    """
    pass


@cli.command()
@click.argument("workflow_file", type=click.Path(exists=True))
@click.option("--context", "-c", help="Override context as JSON string")
@click.option("--no-save", is_flag=True, help="Don't save checkpoints")
def run(workflow_file: str, context: str | None, no_save: bool):
    """Run a workflow from YAML file

    Example:
        dotrunner run workflow.yaml
        dotrunner run workflow.yaml --context '{"file": "main.py"}'
    """
    try:
        # Load workflow
        workflow = Workflow.from_yaml(Path(workflow_file))
        console.print(f"[bold blue]Loading workflow:[/bold blue] {workflow.name}")

        # Override context if provided
        if context:
            try:
                override = json.loads(context)
                workflow.context.update(override)
                console.print("[dim]Context overridden[/dim]")
            except json.JSONDecodeError as e:
                console.print(f"[bold red]Error:[/bold red] Invalid JSON in --context: {e}")
                sys.exit(1)

        # Validate workflow (raises ValueError on errors)
        try:
            workflow.validate()
        except ValueError as e:
            console.print(f"[bold red]Workflow validation failed:[/bold red] {e}")
            sys.exit(1)

        # Execute workflow
        console.print(f"[bold green]Starting workflow:[/bold green] {workflow.name}\n")

        engine = WorkflowEngine(save_checkpoints=not no_save)
        result = asyncio.run(engine.run(workflow))

        # Display results
        console.print()
        if result.status == "completed":
            console.print("[bold green]✓ Workflow completed successfully[/bold green]")
        else:
            console.print(f"[bold red]✗ Workflow failed:[/bold red] {result.error}")

        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  • Total time: {result.total_time:.2f}s")
        console.print(
            f"  • Nodes completed: {len([r for r in result.node_results if r.status == 'success'])}/{len(result.node_results)}"
        )

        if engine.session_id and not no_save:
            console.print(f"  • Session ID: [cyan]{engine.session_id}[/cyan]")

        # Show node details
        console.print("\n[bold]Node Results:[/bold]")
        for node_result in result.node_results:
            status_icon = "✓" if node_result.status == "success" else "✗"
            status_color = "green" if node_result.status == "success" else "red"
            console.print(
                f"  [{status_color}]{status_icon}[/{status_color}] {node_result.node_id} ({node_result.execution_time:.2f}s)"
            )

        # Exit with appropriate code
        sys.exit(0 if result.status == "completed" else 1)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option("--all", "show_all", is_flag=True, help="Show all sessions including completed")
def list(show_all: bool):
    """List workflow sessions

    Shows recent workflow executions with their status.
    """
    try:
        sessions = list_sessions()

        if not show_all:
            sessions = [s for s in sessions if s.status != "completed"]

        if not sessions:
            console.print("[dim]No sessions found[/dim]")
            return

        table = Table(title="Workflow Sessions")
        table.add_column("Session ID", style="cyan")
        table.add_column("Workflow", style="bold")
        table.add_column("Status", style="yellow")
        table.add_column("Progress")
        table.add_column("Updated")

        for session in sessions:
            status_color = {"completed": "green", "failed": "red", "running": "yellow"}.get(session.status, "white")

            table.add_row(
                session.session_id,
                session.workflow_name,
                f"[{status_color}]{session.status}[/{status_color}]",
                f"{session.nodes_completed}/{session.nodes_total}",
                session.updated_at[:19],
            )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("session_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def status(session_id: str, output_json: bool):
    """Show detailed status of a workflow session

    Example:
        dotrunner status my_workflow_20250119_143022_a3f2
    """
    try:
        state = load_state(session_id)

        if output_json:
            import dataclasses

            print(json.dumps(dataclasses.asdict(state), indent=2))
            return

        console.print(f"[bold]Session:[/bold] [cyan]{session_id}[/cyan]")
        console.print(f"[bold]Workflow:[/bold] {state.workflow_id}")
        console.print(f"[bold]Status:[/bold] {state.status}")
        console.print(f"[bold]Current Node:[/bold] {state.current_node or 'None'}")
        console.print(f"[bold]Nodes Completed:[/bold] {len(state.results)}")

        if state.results:
            console.print("\n[bold]Node History:[/bold]")
            for result in state.results:
                status_icon = "✓" if result.status == "success" else "✗"
                console.print(f"  {status_icon} {result.node_id} ({result.execution_time:.2f}s)")
                if result.error:
                    console.print(f"    [red]Error: {result.error}[/red]")

        console.print("\n[bold]Context Variables:[/bold]")
        for key, value in state.context.items():
            value_str = str(value) if len(str(value)) <= 60 else str(value)[:60] + "..."
            console.print(f"  • {key}: {value_str}")

    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] Session not found: {session_id}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("session_id")
def resume(session_id: str):
    """Resume an interrupted workflow

    Loads saved state and continues execution from the last checkpoint.

    Example:
        dotrunner resume my_workflow_20250119_143022_a3f2
    """
    try:
        # Load saved state
        console.print(f"[bold blue]Loading session:[/bold blue] {session_id}")
        state = load_state(session_id)

        if state.status == "completed":
            console.print("[yellow]Workflow already completed[/yellow]")
            sys.exit(0)

        # Load original workflow
        try:
            workflow = load_workflow(session_id)
            console.print(f"[bold blue]Resuming workflow:[/bold blue] {workflow.name}")

            # Create engine and resume execution
            engine = WorkflowEngine(save_checkpoints=True)

            # Restore state and continue execution
            console.print(f"[dim]Resuming from node: {state.current_node or 'start'}[/dim]")
            console.print(f"[dim]Nodes completed: {len(state.results)}[/dim]\n")

            # Resume by running with existing session ID
            result = asyncio.run(engine.run(workflow, session_id=session_id))

            # Display results
            console.print()
            if result.status == "completed":
                console.print("[bold green]✓ Workflow completed successfully[/bold green]")
            else:
                console.print(f"[bold red]✗ Workflow failed:[/bold red] {result.error}")

            console.print("\n[bold]Summary:[/bold]")
            console.print(f"  • Total time: {result.total_time:.2f}s")
            console.print(
                f"  • Nodes completed: {len([r for r in result.node_results if r.status == 'success'])}/{len(result.node_results)}"
            )

            sys.exit(0 if result.status == "completed" else 1)

        except FileNotFoundError:
            console.print("[bold red]Error:[/bold red] Workflow definition not found.")
            console.print("[dim]The workflow was not saved with this session. Unable to resume.[/dim]")
            sys.exit(1)

    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] Session not found: {session_id}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
