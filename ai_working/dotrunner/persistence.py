"""
State persistence for DotRunner workflows

Manages saving/loading workflow state to/from disk for checkpointing and resumption.
Session files are stored in .dotrunner/sessions/{session_id}/ directories.
"""

import json
import logging
import tempfile
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ai_working.dotrunner.state import NodeResult
from ai_working.dotrunner.state import WorkflowState

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Metadata about a workflow session"""

    session_id: str
    workflow_name: str
    status: str
    started_at: str
    updated_at: str
    nodes_completed: int
    nodes_total: int


def get_sessions_dir() -> Path:
    """Get base sessions directory (.dotrunner/sessions/)"""
    path = Path.cwd() / ".dotrunner" / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_session_id(workflow_name: str) -> str:
    """Generate session ID: {workflow_name}_{timestamp}_{short_uuid}"""
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    short_id = str(uuid.uuid4())[:8]
    return f"{workflow_name}_{timestamp}_{short_id}"


def get_session_dir(session_id: str) -> Path:
    """Get path to specific session directory"""
    return get_sessions_dir() / session_id


def save_state(state: WorkflowState, session_id: str | None = None) -> str:
    """
    Save workflow state to disk atomically.

    Creates session directory if needed, saves state.json and metadata.json.
    Uses atomic write operations to prevent corruption.
    Returns session_id.
    """

    if session_id is None:
        session_id = generate_session_id(state.workflow_id)

    session_dir = get_session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    # Save state.json atomically
    state_dict = asdict(state)
    state_file = session_dir / "state.json"

    # Write to temp file first, then rename atomically
    with tempfile.NamedTemporaryFile(mode="w", dir=session_dir, delete=False, suffix=".tmp") as tmp:
        json.dump(state_dict, tmp, indent=2)
        tmp_path = Path(tmp.name)

    # Atomic rename (on POSIX systems)
    tmp_path.replace(state_file)

    # Save metadata.json atomically
    metadata = {
        "session_id": session_id,
        "workflow_name": state.workflow_id,
        "status": state.status,
        "updated_at": datetime.now(UTC).isoformat(),
        "nodes_completed": len(state.results),
        "nodes_total": len(state.results),  # Will be updated by caller
    }

    metadata_file = session_dir / "metadata.json"
    if metadata_file.exists():
        # Update existing metadata
        with open(metadata_file) as f:
            existing = json.load(f)
        metadata["started_at"] = existing.get("started_at", metadata["updated_at"])
        metadata["nodes_total"] = existing.get("nodes_total", metadata["nodes_total"])
    else:
        metadata["started_at"] = metadata["updated_at"]

    # Atomic write for metadata too
    with tempfile.NamedTemporaryFile(mode="w", dir=session_dir, delete=False, suffix=".tmp") as tmp:
        json.dump(metadata, tmp, indent=2)
        tmp_path = Path(tmp.name)

    tmp_path.replace(metadata_file)

    logger.debug(f"Saved state to {session_dir}")
    return session_id


def load_state(session_id: str) -> WorkflowState:
    """Load workflow state from disk"""
    session_dir = get_session_dir(session_id)
    state_file = session_dir / "state.json"

    if not state_file.exists():
        raise FileNotFoundError(f"Session not found: {session_id}")

    with open(state_file) as f:
        state_dict = json.load(f)

    # Reconstruct NodeResult objects
    results = [NodeResult(**r) for r in state_dict["results"]]

    return WorkflowState(
        workflow_id=state_dict["workflow_id"],
        current_node=state_dict.get("current_node"),
        context=state_dict["context"],
        results=results,
        status=state_dict["status"],
    )


def list_sessions() -> list[SessionInfo]:
    """List all saved sessions"""
    sessions = []
    sessions_dir = get_sessions_dir()

    if not sessions_dir.exists():
        return []

    for session_dir in sessions_dir.iterdir():
        if not session_dir.is_dir():
            continue

        metadata_file = session_dir / "metadata.json"
        if not metadata_file.exists():
            continue

        try:
            with open(metadata_file) as f:
                metadata = json.load(f)

            sessions.append(
                SessionInfo(
                    session_id=metadata["session_id"],
                    workflow_name=metadata["workflow_name"],
                    status=metadata["status"],
                    started_at=metadata["started_at"],
                    updated_at=metadata["updated_at"],
                    nodes_completed=metadata["nodes_completed"],
                    nodes_total=metadata["nodes_total"],
                )
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Skipping invalid session {session_dir.name}: {e}")
            continue

    return sorted(sessions, key=lambda s: s.updated_at, reverse=True)


def delete_session(session_id: str):
    """Delete a session directory"""
    import shutil

    session_dir = get_session_dir(session_id)
    if session_dir.exists():
        shutil.rmtree(session_dir)
        logger.debug(f"Deleted session {session_id}")


def save_workflow(workflow, session_id: str):
    """Save workflow definition to session for later resumption"""
    session_dir = get_session_dir(session_id)
    workflow_file = session_dir / "workflow.yaml"

    # Import here to avoid circular dependency
    from ai_working.dotrunner.workflow import Workflow

    if isinstance(workflow, Workflow):
        workflow_dict = workflow.to_dict()
        import yaml

        with open(workflow_file, "w") as f:
            yaml.dump(workflow_dict, f, default_flow_style=False)


def load_workflow(session_id: str):
    """Load workflow definition from session"""
    session_dir = get_session_dir(session_id)
    workflow_file = session_dir / "workflow.yaml"

    if not workflow_file.exists():
        raise FileNotFoundError(f"Workflow definition not found for session: {session_id}")

    # Import here to avoid circular dependency
    from ai_working.dotrunner.workflow import Workflow

    return Workflow.from_yaml(workflow_file)
