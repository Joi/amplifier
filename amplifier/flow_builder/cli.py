"""
CLI entry point for flow-builder tool.

Phase 1: Simple CLI that asks basic questions and generates a workflow.
NO AI-driven interrogation yet - just direct prompts.
"""

from pathlib import Path

import click

from amplifier.flow_builder.generator import generate_yaml
from amplifier.flow_builder.interrogation import build_minimal_workflow
from amplifier.flow_builder.validation import validate_workflow


@click.command("flow-builder")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output path for workflow YAML (default: ai_flows/<name>.yaml)",
)
def cli(output: Path | None) -> None:
    """
    Interactive tool for creating DotRunner workflows.

    Phase 1: Asks basic questions and generates a single-node workflow.
    Future phases will add AI-driven interrogation and multi-node support.

    Examples:
        $ flow-builder
        $ flow-builder --output my-workflow.yaml
    """
    click.echo("=== Flow Builder ===")
    click.echo()

    # Gather basic workflow information
    name = click.prompt("Workflow name", type=str)

    # Validate name is not empty
    if not name or not name.strip():
        click.echo("Error: Workflow name cannot be empty", err=True)
        raise click.Abort()

    name = name.strip()

    description = click.prompt("Workflow description", type=str)

    click.echo()
    click.echo("--- Node Configuration ---")

    node_name = click.prompt("Node name", type=str)
    node_prompt = click.prompt("Node prompt", type=str)

    # Optional fields
    agent = click.prompt("Agent (optional, press Enter to skip)", type=str, default="", show_default=False)

    agent_mode = click.prompt("Agent mode (optional, press Enter to skip)", type=str, default="", show_default=False)

    outputs_input = click.prompt(
        "Outputs (optional, comma-separated, press Enter to skip)", type=str, default="", show_default=False
    )

    # Parse outputs (comma-separated list)
    outputs = None
    if outputs_input:
        outputs = [o.strip() for o in outputs_input.split(",") if o.strip()]

    # Build workflow spec
    spec = build_minimal_workflow(
        name=name,
        description=description,
        node_name=node_name,
        node_prompt=node_prompt,
        agent=agent if agent else None,
        agent_mode=agent_mode if agent_mode else None,
        outputs=outputs,
    )

    # Validate workflow
    errors = validate_workflow(spec)
    if errors:
        click.echo()
        click.echo("Error: Workflow validation failed:", err=True)
        for error in errors:
            click.echo(f"  - {error}", err=True)
        raise click.Abort()

    # Determine output path
    if output is None:
        # Default: ai_flows/<name>.yaml
        output = Path("ai_flows") / f"{name}.yaml"

    # Generate YAML
    generate_yaml(spec, output)

    click.echo()
    click.echo(f"Success! Workflow created: {output}")
    click.echo()
    click.echo("To execute this workflow:")
    click.echo(f"  dotrunner run {output}")


if __name__ == "__main__":
    cli()
