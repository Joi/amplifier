"""
Tests for interactive test mode - Phase 7.

TEST-FIRST: Define contract for workflow testing without execution.
"""

from pathlib import Path

import pytest

from amplifier.flow_builder.test_mode import (
    TestSession,
    save_test_recording,
    start_test_session,
)


class TestSessionInitialization:
    """Test TestSession creation and initialization."""

    def test_test_session_initialization(self):
        """Should initialize test session with nodes."""
        nodes = [
            {"id": "node1", "name": "First", "prompt": "Do something"},
            {"id": "node2", "name": "Second", "prompt": "Do another"},
        ]

        session = TestSession(workflow_name="test-flow", nodes=nodes)

        assert session.workflow_name == "test-flow"
        assert len(session.nodes) == 2
        assert session.current_index == 0
        assert session.mock_outputs == {}

    def test_test_session_with_empty_nodes(self):
        """Should handle workflow with no nodes."""
        session = TestSession(workflow_name="empty", nodes=[])

        assert session.workflow_name == "empty"
        assert len(session.nodes) == 0
        assert session.is_complete()


class TestSessionStateManagement:
    """Test session state tracking."""

    def test_is_complete_false_at_start(self):
        """Should not be complete at start."""
        nodes = [{"id": "node1", "name": "Node1", "prompt": "task"}]
        session = TestSession(workflow_name="test", nodes=nodes)

        assert not session.is_complete()

    def test_is_complete_true_after_all_nodes(self):
        """Should be complete after processing all nodes."""
        nodes = [
            {"id": "node1", "name": "Node1", "prompt": "task1"},
            {"id": "node2", "name": "Node2", "prompt": "task2"},
        ]
        session = TestSession(workflow_name="test", nodes=nodes)

        session.advance({"result": "ok"})
        assert not session.is_complete()

        session.advance({"result": "ok"})
        assert session.is_complete()

    def test_current_node_returns_active_node(self):
        """Should return current node being tested."""
        nodes = [
            {"id": "node1", "name": "Node1", "prompt": "task1"},
            {"id": "node2", "name": "Node2", "prompt": "task2"},
        ]
        session = TestSession(workflow_name="test", nodes=nodes)

        current = session.current_node()
        assert current is not None
        assert current["id"] == "node1"

        session.advance({"result": "ok"})
        current = session.current_node()
        assert current is not None
        assert current["id"] == "node2"

    def test_current_node_returns_none_when_complete(self):
        """Should return None when all nodes processed."""
        nodes = [{"id": "node1", "name": "Node1", "prompt": "task"}]
        session = TestSession(workflow_name="test", nodes=nodes)

        session.advance({"result": "ok"})
        assert session.current_node() is None


class TestSessionAdvancement:
    """Test advancing through nodes."""

    def test_advance_records_outputs(self):
        """Should record outputs for each node."""
        nodes = [
            {"id": "node1", "name": "Node1", "prompt": "task1"},
            {"id": "node2", "name": "Node2", "prompt": "task2"},
        ]
        session = TestSession(workflow_name="test", nodes=nodes)

        session.advance({"result": "success", "data": "value1"})
        assert "node1" in session.mock_outputs
        assert session.mock_outputs["node1"] == {"result": "success", "data": "value1"}

        session.advance({"result": "success", "data": "value2"})
        assert "node2" in session.mock_outputs
        assert session.mock_outputs["node2"] == {"result": "success", "data": "value2"}

    def test_advance_increments_index(self):
        """Should move to next node after advance."""
        nodes = [
            {"id": "node1", "name": "Node1", "prompt": "task1"},
            {"id": "node2", "name": "Node2", "prompt": "task2"},
        ]
        session = TestSession(workflow_name="test", nodes=nodes)

        assert session.current_index == 0
        session.advance({"result": "ok"})
        assert session.current_index == 1

    def test_advance_handles_empty_outputs(self):
        """Should handle empty output dict."""
        nodes = [{"id": "node1", "name": "Node1", "prompt": "task"}]
        session = TestSession(workflow_name="test", nodes=nodes)

        session.advance({})
        assert session.mock_outputs["node1"] == {}


class TestSessionLoading:
    """Test loading session from workflow file."""

    def test_start_test_session_from_yaml(self, tmp_path):
        """Should load session from workflow YAML."""
        workflow = tmp_path / "test.yaml"
        workflow.write_text(
            """workflow:
  name: test-workflow
  description: Test

nodes:
  - id: node1
    name: First Node
    prompt: Do task 1
  - id: node2
    name: Second Node
    prompt: Do task 2
"""
        )

        session = start_test_session(workflow)

        assert session.workflow_name == "test-workflow"
        assert len(session.nodes) == 2
        assert session.nodes[0]["id"] == "node1"

    def test_start_test_session_with_missing_workflow_name(self, tmp_path):
        """Should use default name if workflow name missing."""
        workflow = tmp_path / "unnamed.yaml"
        workflow.write_text(
            """workflow:
  description: Test

nodes:
  - id: node1
    prompt: Task
"""
        )

        session = start_test_session(workflow)

        assert session.workflow_name == "test"  # Default value


class TestSessionSaving:
    """Test saving test recordings."""

    def test_save_test_recording_writes_yaml(self, tmp_path):
        """Should save session as YAML file."""
        nodes = [{"id": "node1", "name": "Node1", "prompt": "task"}]
        session = TestSession(workflow_name="test-flow", nodes=nodes)
        session.advance({"result": "success", "value": 42})

        output_file = tmp_path / "recording.yaml"
        save_test_recording(session, output_file)

        assert output_file.exists()

        import yaml

        with open(output_file) as f:
            data = yaml.safe_load(f)

        assert data["workflow"] == "test-flow"
        assert "node1" in data["mock_outputs"]
        assert data["mock_outputs"]["node1"]["value"] == 42

    def test_save_test_recording_handles_multiple_nodes(self, tmp_path):
        """Should save all node outputs."""
        nodes = [
            {"id": "node1", "name": "Node1", "prompt": "task1"},
            {"id": "node2", "name": "Node2", "prompt": "task2"},
        ]
        session = TestSession(workflow_name="multi-node", nodes=nodes)
        session.advance({"result": "ok1"})
        session.advance({"result": "ok2"})

        output_file = tmp_path / "recording.yaml"
        save_test_recording(session, output_file)

        import yaml

        with open(output_file) as f:
            data = yaml.safe_load(f)

        assert len(data["mock_outputs"]) == 2
        assert data["mock_outputs"]["node1"]["result"] == "ok1"
        assert data["mock_outputs"]["node2"]["result"] == "ok2"
