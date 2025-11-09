"""
Tests for state persistence and session management.

Tests the persistence module that handles saving/loading workflow state
to/from disk for checkpointing and resumption.
"""

import json
import shutil

import pytest

from ai_working.dotrunner.persistence import SessionInfo
from ai_working.dotrunner.persistence import delete_session
from ai_working.dotrunner.persistence import generate_session_id
from ai_working.dotrunner.persistence import get_session_dir
from ai_working.dotrunner.persistence import get_sessions_dir
from ai_working.dotrunner.persistence import list_sessions
from ai_working.dotrunner.persistence import load_state
from ai_working.dotrunner.persistence import load_workflow
from ai_working.dotrunner.persistence import save_state
from ai_working.dotrunner.persistence import save_workflow
from ai_working.dotrunner.state import NodeResult
from ai_working.dotrunner.state import WorkflowState
from ai_working.dotrunner.workflow import Node
from ai_working.dotrunner.workflow import Workflow


@pytest.fixture
def sample_state():
    """Create a sample workflow state for testing"""
    return WorkflowState(
        workflow_id="test-workflow",
        current_node="node2",
        context={"var1": "value1", "var2": 42},
        results=[
            NodeResult(
                node_id="node1",
                status="success",
                outputs={"output1": "result1"},
                raw_response="AI response here",
                execution_time=1.5,
            )
        ],
        status="running",
        execution_path=["node1"],
    )


@pytest.fixture
def sample_workflow():
    """Create a sample workflow for testing"""
    nodes = [
        Node(id="node1", name="Node 1", prompt="Prompt 1", next="node2"),
        Node(id="node2", name="Node 2", prompt="Prompt 2", type="terminal"),
    ]
    return Workflow(name="test-workflow", description="Test workflow", nodes=nodes)


@pytest.fixture
def temp_sessions_dir(tmp_path, monkeypatch):
    """Override sessions directory to use temp directory"""
    sessions_dir = tmp_path / ".dotrunner" / "sessions"
    sessions_dir.mkdir(parents=True)

    # Patch get_sessions_dir to return our temp directory
    monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

    yield sessions_dir

    # Cleanup
    if sessions_dir.exists():
        shutil.rmtree(sessions_dir.parent)


class TestSessionIdGeneration:
    """Test session ID generation"""

    def test_generate_session_id_format(self):
        """Test that session ID has correct format: {workflow_name}_{timestamp}_{uuid}"""
        session_id = generate_session_id("my-workflow")

        assert session_id.startswith("my-workflow_")
        parts = session_id.split("_")
        assert len(parts) >= 3  # name, date, time (optional), uuid
        # Last part should be 8-char UUID
        assert len(parts[-1]) == 8

    def test_generate_session_id_unique(self):
        """Test that consecutive session IDs are unique"""
        id1 = generate_session_id("workflow")
        id2 = generate_session_id("workflow")

        assert id1 != id2  # Different UUIDs


class TestStatePersistence:
    """Test state saving and loading"""

    def test_save_state_creates_files(self, sample_state, temp_sessions_dir):
        """Test that save_state creates session directory and files"""
        session_id = save_state(sample_state)

        session_dir = get_session_dir(session_id)
        assert session_dir.exists()
        assert (session_dir / "state.json").exists()
        assert (session_dir / "metadata.json").exists()

    def test_save_state_with_explicit_id(self, sample_state, temp_sessions_dir):
        """Test saving state with explicit session ID"""
        session_id = save_state(sample_state, session_id="explicit-id-123")

        assert session_id == "explicit-id-123"
        session_dir = get_session_dir(session_id)
        assert session_dir.exists()

    def test_save_state_json_content(self, sample_state, temp_sessions_dir):
        """Test that saved state.json contains correct data"""
        session_id = save_state(sample_state)

        state_file = get_session_dir(session_id) / "state.json"
        with open(state_file) as f:
            state_dict = json.load(f)

        assert state_dict["workflow_id"] == "test-workflow"
        assert state_dict["current_node"] == "node2"
        assert state_dict["context"] == {"var1": "value1", "var2": 42}
        assert state_dict["status"] == "running"
        assert len(state_dict["results"]) == 1
        assert state_dict["results"][0]["node_id"] == "node1"

    def test_save_state_metadata_content(self, sample_state, temp_sessions_dir):
        """Test that saved metadata.json contains correct data"""
        session_id = save_state(sample_state)

        metadata_file = get_session_dir(session_id) / "metadata.json"
        with open(metadata_file) as f:
            metadata = json.load(f)

        assert metadata["session_id"] == session_id
        assert metadata["workflow_name"] == "test-workflow"
        assert metadata["status"] == "running"
        assert metadata["nodes_completed"] == 1
        assert "started_at" in metadata
        assert "updated_at" in metadata

    def test_save_state_preserves_started_at(self, sample_state, temp_sessions_dir):
        """Test that subsequent saves preserve the original started_at timestamp"""
        # First save
        session_id = save_state(sample_state, session_id="preserve-test")

        metadata_file = get_session_dir(session_id) / "metadata.json"
        with open(metadata_file) as f:
            first_metadata = json.load(f)
        original_started_at = first_metadata["started_at"]

        # Second save (update)
        sample_state.status = "completed"
        save_state(sample_state, session_id=session_id)

        with open(metadata_file) as f:
            second_metadata = json.load(f)

        # started_at should be preserved
        assert second_metadata["started_at"] == original_started_at
        # updated_at should change
        assert second_metadata["updated_at"] != original_started_at

    def test_load_state_success(self, sample_state, temp_sessions_dir):
        """Test loading a previously saved state"""
        session_id = save_state(sample_state)

        loaded_state = load_state(session_id)

        assert loaded_state.workflow_id == sample_state.workflow_id
        assert loaded_state.current_node == sample_state.current_node
        assert loaded_state.context == sample_state.context
        assert loaded_state.status == sample_state.status
        assert len(loaded_state.results) == len(sample_state.results)
        assert loaded_state.results[0].node_id == sample_state.results[0].node_id

    def test_load_state_not_found(self, temp_sessions_dir):
        """Test loading non-existent session raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="Session not found"):
            load_state("nonexistent-session-id")

    def test_load_state_corrupted_json(self, sample_state, temp_sessions_dir):
        """Test loading state with corrupted JSON raises clear error"""
        session_id = save_state(sample_state)

        # Corrupt the state.json file
        state_file = get_session_dir(session_id) / "state.json"
        with open(state_file, "w") as f:
            f.write("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            load_state(session_id)

    def test_load_state_missing_required_fields(self, sample_state, temp_sessions_dir):
        """Test loading state with missing required fields raises error"""
        session_id = save_state(sample_state)

        # Write incomplete state (missing workflow_id)
        state_file = get_session_dir(session_id) / "state.json"
        with open(state_file, "w") as f:
            json.dump(
                {
                    "current_node": "node2",
                    "context": {},
                    "results": [],
                    "status": "running",
                },
                f,
            )

        with pytest.raises(KeyError):
            load_state(session_id)

    def test_load_state_node_result_reconstruction(self, sample_state, temp_sessions_dir):
        """Test that NodeResult objects are properly reconstructed"""
        session_id = save_state(sample_state)

        loaded_state = load_state(session_id)

        result = loaded_state.results[0]
        assert isinstance(result, NodeResult)
        assert result.node_id == "node1"
        assert result.status == "success"
        assert result.outputs == {"output1": "result1"}
        assert result.execution_time == 1.5


class TestSessionManagement:
    """Test session listing and deletion"""

    def test_list_sessions_empty(self, temp_sessions_dir):
        """Test listing sessions when directory is empty"""
        sessions = list_sessions()

        assert sessions == []

    def test_list_sessions_single_session(self, sample_state, temp_sessions_dir):
        """Test listing sessions with one saved session"""
        session_id = save_state(sample_state)

        sessions = list_sessions()

        assert len(sessions) == 1
        assert sessions[0].session_id == session_id
        assert sessions[0].workflow_name == "test-workflow"
        assert sessions[0].status == "running"
        assert sessions[0].nodes_completed == 1

    def test_list_sessions_multiple_sorted(self, sample_state, temp_sessions_dir):
        """Test that sessions are sorted by updated_at (most recent first)"""
        # Save multiple sessions
        id1 = save_state(sample_state, session_id="session-1")
        import time

        time.sleep(0.1)  # Ensure different timestamps
        id2 = save_state(sample_state, session_id="session-2")

        sessions = list_sessions()

        assert len(sessions) == 2
        # Most recent first
        assert sessions[0].session_id == id2
        assert sessions[1].session_id == id1

    def test_list_sessions_skips_corrupted_metadata(self, sample_state, temp_sessions_dir):
        """Test that corrupted metadata files are skipped with warning"""
        # Save valid session
        valid_id = save_state(sample_state, session_id="valid-session")

        # Create corrupted session
        corrupted_dir = get_sessions_dir() / "corrupted-session"
        corrupted_dir.mkdir(exist_ok=True)
        metadata_file = corrupted_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            f.write("{invalid json")

        sessions = list_sessions()

        # Should only return valid session
        assert len(sessions) == 1
        assert sessions[0].session_id == valid_id

    def test_list_sessions_skips_missing_metadata(self, sample_state, temp_sessions_dir):
        """Test that sessions without metadata.json are skipped"""
        # Save valid session
        valid_id = save_state(sample_state, session_id="valid-session")

        # Create session directory without metadata
        incomplete_dir = get_sessions_dir() / "incomplete-session"
        incomplete_dir.mkdir(exist_ok=True)
        # Don't create metadata.json

        sessions = list_sessions()

        # Should only return valid session
        assert len(sessions) == 1
        assert sessions[0].session_id == valid_id

    def test_list_sessions_handles_non_directory_items(self, sample_state, temp_sessions_dir):
        """Test that non-directory items in sessions dir are skipped"""
        # Save valid session
        valid_id = save_state(sample_state, session_id="valid-session")

        # Create a file (not directory) in sessions dir
        file_path = get_sessions_dir() / "not-a-directory.txt"
        file_path.write_text("random file")

        sessions = list_sessions()

        # Should only return valid session
        assert len(sessions) == 1
        assert sessions[0].session_id == valid_id

    def test_delete_session_existing(self, sample_state, temp_sessions_dir):
        """Test deleting an existing session"""
        session_id = save_state(sample_state)

        session_dir = get_session_dir(session_id)
        assert session_dir.exists()

        delete_session(session_id)

        assert not session_dir.exists()

    def test_delete_session_nonexistent(self, temp_sessions_dir):
        """Test deleting non-existent session doesn't raise error"""
        # Should not raise
        delete_session("nonexistent-session")

    def test_delete_session_removes_from_list(self, sample_state, temp_sessions_dir):
        """Test that deleted session no longer appears in list"""
        session_id = save_state(sample_state)

        sessions_before = list_sessions()
        assert len(sessions_before) == 1

        delete_session(session_id)

        sessions_after = list_sessions()
        assert len(sessions_after) == 0


class TestWorkflowPersistence:
    """Test workflow definition saving and loading"""

    def test_save_workflow_creates_yaml(self, sample_workflow, temp_sessions_dir):
        """Test that save_workflow creates workflow.yaml file"""
        session_id = "test-session"
        session_dir = get_session_dir(session_id)
        session_dir.mkdir(parents=True)

        save_workflow(sample_workflow, session_id)

        workflow_file = session_dir / "workflow.yaml"
        assert workflow_file.exists()

    def test_load_workflow_success(self, sample_workflow, temp_sessions_dir):
        """Test loading a previously saved workflow"""
        session_id = "test-session"
        session_dir = get_session_dir(session_id)
        session_dir.mkdir(parents=True)

        save_workflow(sample_workflow, session_id)
        loaded_workflow = load_workflow(session_id)

        assert loaded_workflow.name == sample_workflow.name
        assert loaded_workflow.description == sample_workflow.description
        assert len(loaded_workflow.nodes) == len(sample_workflow.nodes)
        assert loaded_workflow.nodes[0].id == sample_workflow.nodes[0].id

    def test_load_workflow_not_found(self, temp_sessions_dir):
        """Test loading workflow from non-existent session raises error"""
        with pytest.raises(FileNotFoundError, match="Workflow definition not found"):
            load_workflow("nonexistent-session")

    def test_load_workflow_missing_yaml(self, temp_sessions_dir):
        """Test loading workflow when session exists but workflow.yaml doesn't"""
        session_id = "session-without-workflow"
        session_dir = get_session_dir(session_id)
        session_dir.mkdir(parents=True)
        # Don't create workflow.yaml

        with pytest.raises(FileNotFoundError, match="Workflow definition not found"):
            load_workflow(session_id)


class TestAtomicWrites:
    """Test atomic write operations for data integrity"""

    def test_save_state_uses_temp_file(self, sample_state, temp_sessions_dir):
        """Test that save_state uses temporary file for atomic write"""
        session_id = save_state(sample_state)

        # Temp files should be cleaned up
        session_dir = get_session_dir(session_id)
        tmp_files = list(session_dir.glob("*.tmp"))
        assert len(tmp_files) == 0  # All temp files cleaned up

    def test_concurrent_saves_dont_corrupt(self, sample_state, temp_sessions_dir):
        """Test that concurrent saves to same session don't corrupt data"""
        import concurrent.futures

        session_id = "concurrent-test"

        def save_with_different_status(status):
            state = WorkflowState(
                workflow_id="test-workflow",
                current_node="node1",
                context={"status": status},
                results=[],
                status=status,
            )
            save_state(state, session_id=session_id)

        # Try to save concurrently with different statuses
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(save_with_different_status, f"status-{i}") for i in range(10)]
            concurrent.futures.wait(futures)

        # Load final state - should be valid JSON, not corrupted
        final_state = load_state(session_id)
        assert final_state.workflow_id == "test-workflow"
        # Status should be one of the saved values (not corrupted)
        assert final_state.status.startswith("status-")


class TestSessionInfo:
    """Test SessionInfo dataclass"""

    def test_session_info_creation(self):
        """Test creating SessionInfo object"""
        info = SessionInfo(
            session_id="test-id",
            workflow_name="test-workflow",
            status="running",
            started_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:01:00",
            nodes_completed=5,
            nodes_total=10,
        )

        assert info.session_id == "test-id"
        assert info.workflow_name == "test-workflow"
        assert info.status == "running"
        assert info.nodes_completed == 5
        assert info.nodes_total == 10
