"""
Tests for workflow state management.

Following test-first philosophy:
- Tests written BEFORE implementation
- Tests use real file I/O (not mocks)
- Tests verify actual behavior
- Antagonistic tests catch shortcuts and cheating
"""

import json
import tempfile
from collections.abc import Generator
from dataclasses import asdict
from pathlib import Path

import pytest

from amplifier.bplan.workflow_state import WorkflowState
from amplifier.bplan.workflow_state import clear_state
from amplifier.bplan.workflow_state import load_state
from amplifier.bplan.workflow_state import save_state


class TestWorkflowState:
    """Test WorkflowState dataclass and serialization."""

    def test_workflow_state_creation(self) -> None:
        """Test creating a WorkflowState instance."""
        state = WorkflowState(
            epic_id="amplifier-100",
            current_stage="planning",
            current_phase="phase-1",
            phases=["phase-1", "phase-2"],
            project_brief="Test project",
            plan_summary="Test plan",
        )

        assert state.epic_id == "amplifier-100"
        assert state.current_stage == "planning"
        assert state.current_phase == "phase-1"
        assert state.phases == ["phase-1", "phase-2"]
        assert state.project_brief == "Test project"
        assert state.plan_summary == "Test plan"

    def test_workflow_state_to_dict(self) -> None:
        """Test converting WorkflowState to dictionary."""
        state = WorkflowState(
            epic_id="amplifier-101",
            current_stage="execution",
            current_phase="phase-2",
            phases=["phase-1", "phase-2", "phase-3"],
            project_brief="Brief",
            plan_summary="Summary",
        )

        data = asdict(state)

        assert data["epic_id"] == "amplifier-101"
        assert data["current_stage"] == "execution"
        assert data["current_phase"] == "phase-2"
        assert data["phases"] == ["phase-1", "phase-2", "phase-3"]
        assert data["project_brief"] == "Brief"
        assert data["plan_summary"] == "Summary"
        assert isinstance(data, dict)

    def test_workflow_state_from_dict(self) -> None:
        """Test creating WorkflowState from dictionary."""
        data = {
            "epic_id": "amplifier-102",
            "current_stage": "validation",
            "current_phase": "phase-3",
            "phases": ["phase-1"],
            "project_brief": "Test brief",
            "plan_summary": "Test summary",
        }

        state = WorkflowState(**data)

        assert state.epic_id == "amplifier-102"
        assert state.current_stage == "validation"
        assert state.current_phase == "phase-3"
        assert state.phases == ["phase-1"]

    def test_workflow_state_round_trip(self) -> None:
        """Test that state survives dict conversion round trip."""
        original = WorkflowState(
            epic_id="amplifier-103",
            current_stage="planning",
            current_phase="phase-1",
            phases=["phase-1", "phase-2"],
            project_brief="Original brief",
            plan_summary="Original summary",
        )

        # Convert to dict and back
        data = asdict(original)
        restored = WorkflowState(**data)

        assert restored.epic_id == original.epic_id
        assert restored.current_stage == original.current_stage
        assert restored.current_phase == original.current_phase
        assert restored.phases == original.phases
        assert restored.project_brief == original.project_brief
        assert restored.plan_summary == original.plan_summary


class TestStatePersistence:
    """Test state persistence to filesystem using real file I/O."""

    @pytest.fixture
    def temp_state_dir(self) -> Generator[Path, None, None]:
        """Create a temporary directory for state files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / ".beads"
            state_dir.mkdir(parents=True, exist_ok=True)
            yield state_dir

    @pytest.fixture
    def state_file(self, temp_state_dir: Path) -> Path:
        """Return the state file path."""
        return temp_state_dir / "bplan_state.json"

    def test_save_workflow_state(self, state_file: Path) -> None:
        """Test saving workflow state to file."""
        state = WorkflowState(
            epic_id="amplifier-200",
            current_stage="planning",
            current_phase="phase-1",
            phases=["phase-1", "phase-2"],
            project_brief="Test project",
            plan_summary="Test plan",
        )

        save_state(state, state_file)

        # Verify file exists
        assert state_file.exists()
        assert state_file.is_file()

        # Verify file content
        with open(state_file) as f:
            data = json.load(f)

        assert data["epic_id"] == "amplifier-200"
        assert data["current_stage"] == "planning"
        assert data["current_phase"] == "phase-1"

    def test_load_workflow_state(self, state_file: Path) -> None:
        """Test loading workflow state from file."""
        # Create state file
        state = WorkflowState(
            epic_id="amplifier-201",
            current_stage="execution",
            current_phase="phase-2",
            phases=["phase-1", "phase-2"],
            project_brief="Load test",
            plan_summary="Load plan",
        )
        save_state(state, state_file)

        # Load state
        loaded = load_state(state_file)

        assert loaded is not None
        assert loaded.epic_id == "amplifier-201"
        assert loaded.current_stage == "execution"
        assert loaded.current_phase == "phase-2"
        assert loaded.phases == ["phase-1", "phase-2"]
        assert loaded.project_brief == "Load test"
        assert loaded.plan_summary == "Load plan"

    def test_save_and_load_round_trip(self, state_file: Path) -> None:
        """Test that state survives save/load round trip with real file I/O."""
        original = WorkflowState(
            epic_id="amplifier-202",
            current_stage="validation",
            current_phase="phase-3",
            phases=["phase-1", "phase-2", "phase-3"],
            project_brief="Round trip test",
            plan_summary="Round trip plan",
        )

        # Save and load
        save_state(original, state_file)
        restored = load_state(state_file)

        # Verify all fields match
        assert restored is not None
        assert restored.epic_id == original.epic_id
        assert restored.current_stage == original.current_stage
        assert restored.current_phase == original.current_phase
        assert restored.phases == original.phases
        assert restored.project_brief == original.project_brief
        assert restored.plan_summary == original.plan_summary

    def test_load_missing_file(self, state_file: Path) -> None:
        """Test loading state when file doesn't exist returns None."""
        # Ensure file doesn't exist
        if state_file.exists():
            state_file.unlink()

        loaded = load_state(state_file)

        assert loaded is None

    def test_load_corrupted_json(self, state_file: Path) -> None:
        """Test loading state with corrupted JSON returns None."""
        # Write invalid JSON
        with open(state_file, "w") as f:
            f.write("{ this is not valid JSON }")

        loaded = load_state(state_file)

        assert loaded is None

    def test_load_incomplete_data(self, state_file: Path) -> None:
        """Test loading state with missing required fields returns None."""
        # Write JSON with missing fields
        incomplete = {"epic_id": "amplifier-203", "current_stage": "planning"}

        with open(state_file, "w") as f:
            json.dump(incomplete, f)

        loaded = load_state(state_file)

        # Should return None due to missing required fields
        assert loaded is None

    def test_clear_state(self, state_file: Path) -> None:
        """Test clearing workflow state removes the file."""
        # Create state
        state = WorkflowState(
            epic_id="amplifier-204",
            current_stage="planning",
            current_phase="phase-1",
            phases=["phase-1"],
            project_brief="Clear test",
            plan_summary="Clear plan",
        )
        save_state(state, state_file)
        assert state_file.exists()

        # Clear state
        clear_state(state_file)

        # Verify file is removed
        assert not state_file.exists()

    def test_clear_state_missing_file(self, state_file: Path) -> None:
        """Test clearing state when file doesn't exist doesn't raise error."""
        # Ensure file doesn't exist
        if state_file.exists():
            state_file.unlink()

        # Should not raise an error
        clear_state(state_file)

        assert not state_file.exists()

    def test_multiple_save_overwrite(self, state_file: Path) -> None:
        """Test that saving multiple times overwrites previous state."""
        # Save first state
        state1 = WorkflowState(
            epic_id="amplifier-205",
            current_stage="planning",
            current_phase="phase-1",
            phases=["phase-1"],
            project_brief="First",
            plan_summary="First plan",
        )
        save_state(state1, state_file)

        # Save second state
        state2 = WorkflowState(
            epic_id="amplifier-206",
            current_stage="execution",
            current_phase="phase-2",
            phases=["phase-1", "phase-2"],
            project_brief="Second",
            plan_summary="Second plan",
        )
        save_state(state2, state_file)

        # Load and verify it's the second state
        loaded = load_state(state_file)

        assert loaded is not None
        assert loaded.epic_id == "amplifier-206"
        assert loaded.current_stage == "execution"
        assert loaded.project_brief == "Second"

    def test_state_file_is_valid_json(self, state_file: Path) -> None:
        """Test that saved state file is valid, readable JSON."""
        state = WorkflowState(
            epic_id="amplifier-207",
            current_stage="planning",
            current_phase="phase-1",
            phases=["phase-1", "phase-2"],
            project_brief="JSON test",
            plan_summary="JSON plan",
        )

        save_state(state, state_file)

        # Read as JSON directly (not through load_state)
        with open(state_file) as f:
            data = json.load(f)

        # Verify it's a dict with expected keys
        assert isinstance(data, dict)
        assert "epic_id" in data
        assert "current_stage" in data
        assert "current_phase" in data
        assert "phases" in data
        assert "project_brief" in data
        assert "plan_summary" in data

    def test_state_tracks_phase_progression(self, state_file: Path) -> None:
        """Test that state can track progression through phases."""
        phases = ["phase-1", "phase-2", "phase-3", "phase-4"]

        # Start at phase-1
        state = WorkflowState(
            epic_id="amplifier-208",
            current_stage="execution",
            current_phase="phase-1",
            phases=phases,
            project_brief="Progression test",
            plan_summary="Progression plan",
        )
        save_state(state, state_file)

        # Move to phase-2
        loaded = load_state(state_file)
        assert loaded is not None
        loaded.current_phase = "phase-2"
        save_state(loaded, state_file)

        # Verify progression
        final = load_state(state_file)
        assert final is not None
        assert final.current_phase == "phase-2"
        assert final.phases == phases

    def test_state_with_empty_strings(self, state_file: Path) -> None:
        """Test state with empty string fields (edge case)."""
        state = WorkflowState(
            epic_id="amplifier-209",
            current_stage="planning",
            current_phase="phase-1",
            phases=["phase-1"],
            project_brief="",  # Empty string
            plan_summary="",  # Empty string
        )

        save_state(state, state_file)
        loaded = load_state(state_file)

        assert loaded is not None
        assert loaded.project_brief == ""
        assert loaded.plan_summary == ""

    def test_state_with_special_characters(self, state_file: Path) -> None:
        """Test state with special characters in fields."""
        state = WorkflowState(
            epic_id="amplifier-210",
            current_stage="planning",
            current_phase="phase-1",
            phases=["phase-1"],
            project_brief="Test with 'quotes' and \"double quotes\"",
            plan_summary="Test with newlines\nand\ttabs",
        )

        save_state(state, state_file)
        loaded = load_state(state_file)

        assert loaded is not None
        assert loaded.project_brief == "Test with 'quotes' and \"double quotes\""
        assert loaded.plan_summary == "Test with newlines\nand\ttabs"

    def test_state_with_unicode(self, state_file: Path) -> None:
        """Test state with unicode characters."""
        state = WorkflowState(
            epic_id="amplifier-211",
            current_stage="planning",
            current_phase="phase-1",
            phases=["phase-1"],
            project_brief="Test with emoji 🚀 and unicode 日本語",
            plan_summary="Unicode test ñ é ü",
        )

        save_state(state, state_file)
        loaded = load_state(state_file)

        assert loaded is not None
        assert "🚀" in loaded.project_brief
        assert "日本語" in loaded.project_brief
        assert "ñ" in loaded.plan_summary


class TestResumeWorkflow:
    """Test workflow resumption scenarios."""

    @pytest.fixture
    def temp_state_dir(self) -> Generator[Path, None, None]:
        """Create a temporary directory for state files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / ".beads"
            state_dir.mkdir(parents=True, exist_ok=True)
            yield state_dir

    @pytest.fixture
    def state_file(self, temp_state_dir: Path) -> Path:
        """Return the state file path."""
        return temp_state_dir / "bplan_state.json"

    def test_resume_after_interruption(self, state_file: Path) -> None:
        """Test that workflow can resume after interruption."""
        # Simulate workflow start
        state = WorkflowState(
            epic_id="amplifier-300",
            current_stage="execution",
            current_phase="phase-2",
            phases=["phase-1", "phase-2", "phase-3"],
            project_brief="Interruption test",
            plan_summary="Test resumption",
        )
        save_state(state, state_file)

        # Simulate interruption (process restart)
        # ... workflow terminates ...

        # Resume workflow
        resumed = load_state(state_file)

        assert resumed is not None
        assert resumed.epic_id == "amplifier-300"
        assert resumed.current_phase == "phase-2"
        # Workflow should continue from phase-2
        assert "phase-3" in resumed.phases

    def test_no_state_on_fresh_start(self, state_file: Path) -> None:
        """Test that fresh start has no state."""
        # Don't create any state file
        if state_file.exists():
            state_file.unlink()

        loaded = load_state(state_file)

        assert loaded is None

    def test_resume_preserves_all_context(self, state_file: Path) -> None:
        """Test that resume preserves all workflow context."""
        original = WorkflowState(
            epic_id="amplifier-301",
            current_stage="execution",
            current_phase="phase-3",
            phases=["phase-1", "phase-2", "phase-3", "phase-4"],
            project_brief="Complex project with detailed requirements",
            plan_summary="Multi-phase execution plan with dependencies",
        )

        save_state(original, state_file)

        # Simulate resume
        resumed = load_state(state_file)

        # All context should be preserved
        assert resumed is not None
        assert resumed.epic_id == original.epic_id
        assert resumed.current_stage == original.current_stage
        assert resumed.current_phase == original.current_phase
        assert resumed.phases == original.phases
        assert resumed.project_brief == original.project_brief
        assert resumed.plan_summary == original.plan_summary
