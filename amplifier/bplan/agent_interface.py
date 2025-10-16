"""Agent Interface - CLI and API for Evidence System

This module provides universal access to the evidence validation system
for all agents and tools. It offers both CLI commands and Python API.

Philosophy:
- Simple, direct interfaces (no complex frameworks)
- Accessible to all agents
- Clear error messages
- Minimal abstractions
"""

import sys
from pathlib import Path
from typing import Any

import click

from amplifier.bplan.evidence_system import EvidenceStore
from amplifier.bplan.three_agent_workflow import WorkflowOrchestrator
from amplifier.bplan.todowrite_integration import BlockingEnforcer
from amplifier.bplan.todowrite_integration import CompletionValidator
from amplifier.bplan.todowrite_integration import EvidenceRequiredTodo
from amplifier.bplan.todowrite_integration import EvidenceStore as TodoWriteEvidenceStore

# Default evidence directory
DEFAULT_EVIDENCE_DIR = Path(".beads/evidence")


class AgentAPI:
    """Python API for agents to interact with evidence system"""

    def __init__(self, evidence_dir: Path | None = None):
        """
        Initialize agent API.

        Args:
            evidence_dir: Directory for evidence storage (default: .beads/evidence)
        """
        self.evidence_dir = evidence_dir or DEFAULT_EVIDENCE_DIR
        self.evidence_store = EvidenceStore(base_dir=self.evidence_dir)
        # Use TodoWrite evidence store wrapper for validation (has retrieve_evidence method)
        todowrite_store = TodoWriteEvidenceStore(base_path=self.evidence_dir)
        self.validator = CompletionValidator(todowrite_store)
        self.enforcer = BlockingEnforcer(self.validator)

    def validate_code(
        self,
        task: str,
        code_path: Path | None = None,
        test_path: Path | None = None,
    ) -> dict[str, Any]:
        """
        Validate code using 3-agent workflow.

        Args:
            task: Task description
            code_path: Path to code file (optional - will be generated)
            test_path: Path to test file (optional - will be generated)

        Returns:
            dict with keys: passed (bool), evidence_id (str), message (str)
        """
        orchestrator = WorkflowOrchestrator()

        try:
            result = orchestrator.execute_workflow(task, self.evidence_store)

            # Extract evidence from workflow result
            evidence_id = None
            if hasattr(result, "evidence") and result.evidence:
                evidence_id = result.evidence.get("id") if isinstance(result.evidence, dict) else None

            return {
                "passed": result.success,
                "evidence_id": evidence_id,
                "message": result.error if result.error else "Validation successful",
                "cheating_detected": False,  # Would be in validation_result if detected
            }
        except Exception as e:
            return {
                "passed": False,
                "evidence_id": None,
                "message": f"Validation failed: {e!s}",
                "cheating_detected": False,
            }

    def check_evidence(self, evidence_id: str) -> dict[str, Any]:
        """
        Check if evidence exists and is valid.

        Args:
            evidence_id: Evidence ID to check

        Returns:
            dict with keys: exists (bool), valid (bool), details (str)
        """
        try:
            evidence = self.evidence_store.get_evidence(evidence_id)

            if not evidence:
                return {
                    "exists": False,
                    "valid": False,
                    "details": f"Evidence not found: {evidence_id}",
                }

            return {
                "exists": True,
                "valid": True,
                "details": f"Evidence type: {evidence.type}, created: {evidence.timestamp}",
                "type": evidence.type,
                "timestamp": evidence.timestamp.isoformat(),
            }
        except (FileNotFoundError, KeyError):
            return {
                "exists": False,
                "valid": False,
                "details": f"Evidence not found: {evidence_id}",
            }

    def validate_todo_completion(
        self,
        content: str,
        evidence_ids: list[str],
        requires_evidence: bool = True,
    ) -> dict[str, Any]:
        """
        Validate todo can be completed with provided evidence.

        Args:
            content: Todo content/description
            evidence_ids: List of evidence IDs
            requires_evidence: Whether evidence is required

        Returns:
            dict with keys: can_complete (bool), reason (str), evidence_status (dict)
        """
        todo = EvidenceRequiredTodo(
            content=content,
            status="in_progress",
            activeForm=f"Working on {content}",
            evidence_ids=evidence_ids,
            requires_evidence=requires_evidence,
        )

        # Build evidence status
        evidence_status = {
            "has_evidence": bool(evidence_ids),
            "evidence_count": len(evidence_ids),
            "all_valid": False,
            "invalid_ids": [],
        }

        # Check each evidence ID
        for evidence_id in evidence_ids:
            try:
                evidence = self.evidence_store.get_evidence(evidence_id)
                if not evidence:
                    evidence_status["invalid_ids"].append(evidence_id)
            except (FileNotFoundError, KeyError):
                evidence_status["invalid_ids"].append(evidence_id)

        evidence_status["all_valid"] = len(evidence_status["invalid_ids"]) == 0 and len(evidence_ids) > 0

        try:
            can_complete = self.validator.validate_completion(todo)
            return {
                "can_complete": can_complete,
                "reason": "Evidence validated successfully",
                "evidence_status": evidence_status,
            }
        except Exception as e:
            return {
                "can_complete": False,
                "reason": str(e),
                "evidence_status": evidence_status,
            }


# CLI Implementation
@click.group()
def cli():
    """Evidence System - Universal validation interface for all agents"""
    pass


@cli.command()
@click.argument("task")
@click.option("--code-path", type=click.Path(path_type=Path), help="Path to code file")
@click.option("--test-path", type=click.Path(path_type=Path), help="Path to test file")
@click.option(
    "--evidence-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_EVIDENCE_DIR,
    help="Evidence directory",
)
def validate_code(task: str, code_path: Path | None, test_path: Path | None, evidence_dir: Path):
    """Validate code using 3-agent workflow"""
    api = AgentAPI(evidence_dir=evidence_dir)
    result = api.validate_code(task, code_path, test_path)

    if result["passed"]:
        click.echo("✅ Code validation PASSED")
        click.echo(f"Evidence ID: {result['evidence_id']}")
        click.echo(f"Details: {result['message']}")
        sys.exit(0)
    else:
        click.echo("❌ Code validation FAILED")
        click.echo(f"Reason: {result['message']}")
        if result["cheating_detected"]:
            click.echo("⚠️  CHEATING DETECTED")
        sys.exit(1)


@cli.command()
@click.argument("evidence_id")
@click.option(
    "--evidence-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_EVIDENCE_DIR,
    help="Evidence directory",
)
def check_evidence(evidence_id: str, evidence_dir: Path):
    """Check if evidence exists and is valid"""
    api = AgentAPI(evidence_dir=evidence_dir)
    result = api.check_evidence(evidence_id)

    if result["exists"]:
        click.echo(f"✅ Evidence found: {evidence_id}")
        click.echo(f"Type: {result.get('type', 'unknown')}")
        click.echo(f"Created: {result.get('timestamp', 'unknown')}")
        sys.exit(0)
    else:
        click.echo(f"❌ Evidence not found: {evidence_id}")
        sys.exit(1)


@cli.command()
@click.argument("content")
@click.option("--evidence-ids", multiple=True, help="Evidence IDs (can specify multiple)")
@click.option("--no-evidence-required", is_flag=True, help="Evidence not required for this todo")
@click.option(
    "--evidence-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_EVIDENCE_DIR,
    help="Evidence directory",
)
def validate_todo(content: str, evidence_ids: tuple[str], no_evidence_required: bool, evidence_dir: Path):
    """Validate todo can be completed with provided evidence"""
    api = AgentAPI(evidence_dir=evidence_dir)
    result = api.validate_todo_completion(
        content=content,
        evidence_ids=list(evidence_ids),
        requires_evidence=not no_evidence_required,
    )

    if result["can_complete"]:
        click.echo("✅ Todo can be completed")
        click.echo(f"Reason: {result['reason']}")
        sys.exit(0)
    else:
        click.echo("❌ Todo cannot be completed")
        click.echo(f"Reason: {result['reason']}")
        sys.exit(1)


@cli.command()
@click.option(
    "--evidence-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_EVIDENCE_DIR,
    help="Evidence directory",
)
def list_evidence(evidence_dir: Path):
    """List all evidence in the store"""
    store = EvidenceStore(base_dir=evidence_dir)
    all_evidence = store.list_evidence()

    if not all_evidence:
        click.echo("No evidence found")
        return

    click.echo(f"Found {len(all_evidence)} evidence items:\n")
    for evidence in all_evidence:
        click.echo(f"ID: {evidence.id}")
        click.echo(f"  Type: {evidence.type}")
        click.echo(f"  Created: {evidence.timestamp}")
        click.echo(f"  Validator: {evidence.validator_id}")
        click.echo()


if __name__ == "__main__":
    cli()
