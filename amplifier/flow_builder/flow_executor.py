"""
Flow executor module - Phase 5.

Executes workflows via DotRunner. Thin wrapper, no reimplementation.
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ExecutionResult:
    """Result from workflow execution."""

    status: str  # "completed" or "failed"
    output: str
    error: str | None = None


def list_flows(flows_dir: Path) -> list[Path]:
    """List all workflow YAML files in directory.

    Args:
        flows_dir: Directory containing workflow files

    Returns:
        List of Path objects for YAML files
    """
    if not flows_dir.exists():
        return []

    flows = []
    for yaml_file in flows_dir.glob("*.yaml"):
        if yaml_file.name.startswith("."):
            continue
        flows.append(yaml_file)

    return flows


def execute_workflow(workflow_path: Path, context: dict[str, Any] | None = None) -> ExecutionResult:
    """Execute workflow using DotRunner CLI.

    Args:
        workflow_path: Path to workflow YAML file
        context: Optional context dict to pass to workflow

    Returns:
        ExecutionResult with status and output
    """
    cmd = ["python", "-m", "ai_working.dotrunner", "run", str(workflow_path)]

    if context:
        cmd.extend(["--context", json.dumps(context)])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, check=False
        )

        if result.returncode == 0:
            return ExecutionResult(status="completed", output=result.stdout)
        else:
            return ExecutionResult(
                status="failed", output=result.stdout, error=result.stderr
            )

    except subprocess.TimeoutExpired:
        return ExecutionResult(
            status="failed",
            output="",
            error="Workflow execution timed out after 300 seconds",
        )
