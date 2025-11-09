"""
Interactive test mode - Phase 7.

Simple workflow testing without execution.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TestSession:
    """Manages interactive workflow testing."""

    workflow_name: str
    nodes: list[dict[str, Any]]
    current_index: int = 0
    mock_outputs: dict[str, dict[str, Any]] = None

    def __post_init__(self):
        if self.mock_outputs is None:
            self.mock_outputs = {}

    def is_complete(self) -> bool:
        """Check if all nodes tested."""
        return self.current_index >= len(self.nodes)

    def current_node(self) -> dict[str, Any] | None:
        """Get current node being tested."""
        if self.is_complete():
            return None
        return self.nodes[self.current_index]

    def advance(self, outputs: dict[str, Any]):
        """Record outputs and move to next node."""
        if not self.is_complete():
            node_id = self.nodes[self.current_index]["id"]
            self.mock_outputs[node_id] = outputs
            self.current_index += 1


def start_test_session(workflow_path: Path) -> TestSession:
    """Start interactive test session for workflow."""
    with open(workflow_path) as f:
        data = yaml.safe_load(f)

    workflow = data.get("workflow", {})
    nodes = data.get("nodes", [])

    return TestSession(workflow_name=workflow.get("name", "test"), nodes=nodes)


def save_test_recording(session: TestSession, output_path: Path):
    """Save test session as YAML."""
    data = {"workflow": session.workflow_name, "mock_outputs": session.mock_outputs}

    with open(output_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
