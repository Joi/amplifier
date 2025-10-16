"""
Workflow state management for /bplan workflow.

Provides state persistence to enable workflow resumption after interruptions.
Uses defensive file I/O with retry logic for cloud sync compatibility.
"""

import logging
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path

from amplifier.utils.file_io import read_json
from amplifier.utils.file_io import write_json

logger = logging.getLogger(__name__)


@dataclass
class WorkflowState:
    """State for /bplan workflow execution.

    Tracks current position in workflow and all context needed to resume.
    """

    epic_id: str
    current_stage: str
    current_phase: str
    phases: list[str]
    project_brief: str
    plan_summary: str


def save_state(state: WorkflowState, state_file: Path | str | None = None) -> None:
    """Save workflow state to file.

    Args:
        state: The workflow state to save
        state_file: Path to state file (defaults to .beads/bplan_state.json)
    """
    if state_file is None:
        state_file = Path.cwd() / ".beads" / "bplan_state.json"
    else:
        state_file = Path(state_file)

    # Convert state to dict and save
    data = asdict(state)
    write_json(data, state_file)
    logger.debug(f"Saved workflow state to {state_file}")


def load_state(state_file: Path | str | None = None) -> WorkflowState | None:
    """Load workflow state from file.

    Args:
        state_file: Path to state file (defaults to .beads/bplan_state.json)

    Returns:
        WorkflowState if file exists and is valid, None otherwise
    """
    if state_file is None:
        state_file = Path.cwd() / ".beads" / "bplan_state.json"
    else:
        state_file = Path(state_file)

    # Check if file exists
    if not state_file.exists():
        logger.debug(f"No state file found at {state_file}")
        return None

    try:
        # Load JSON data
        data = read_json(state_file)

        # Validate that all required fields are present
        required_fields = {
            "epic_id",
            "current_stage",
            "current_phase",
            "phases",
            "project_brief",
            "plan_summary",
        }
        if not all(field in data for field in required_fields):
            logger.warning(f"State file {state_file} missing required fields")
            return None

        # Create WorkflowState from data
        state = WorkflowState(**data)
        logger.debug(f"Loaded workflow state from {state_file}")
        return state

    except (ValueError, TypeError, KeyError) as e:
        logger.warning(f"Failed to load state from {state_file}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading state from {state_file}: {e}")
        return None


def clear_state(state_file: Path | str | None = None) -> None:
    """Clear workflow state by removing the state file.

    Args:
        state_file: Path to state file (defaults to .beads/bplan_state.json)
    """
    if state_file is None:
        state_file = Path.cwd() / ".beads" / "bplan_state.json"
    else:
        state_file = Path(state_file)

    # Remove file if it exists
    if state_file.exists():
        state_file.unlink()
        logger.debug(f"Cleared workflow state from {state_file}")
    else:
        logger.debug(f"No state file to clear at {state_file}")
