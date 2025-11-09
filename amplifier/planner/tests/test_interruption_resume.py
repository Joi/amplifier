"""Tests for interruption and resume scenarios.

These tests validate the critical workflow where:
1. User starts a large project
2. Execution is interrupted (session ends, timeout, etc.)
3. User resumes with "keep going" or compacted context
4. System correctly continues from where it left off
"""

import tempfile
from pathlib import Path

import pytest

from amplifier.planner import TaskState
from amplifier.planner import load_project
from amplifier.planner import orchestrate_execution
from amplifier.planner import save_project

from .test_helpers import create_linear_chain
from .test_helpers import create_parallel_batches
from .test_helpers import create_stub_project


class TestInterruptionAndResume:
    """Test interruption and resume workflows."""

    @pytest.fixture
    def temp_data_dir(self, monkeypatch):
        """Use temporary directory for data storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            def mock_get_path(project_id):
                base = tmpdir_path / "data" / "planner" / "projects"
                base.mkdir(parents=True, exist_ok=True)
                return base / f"{project_id}.json"

            monkeypatch.setattr("amplifier.planner.storage.get_project_path", mock_get_path)
            yield tmpdir_path

    @pytest.mark.asyncio
    async def test_basic_interruption_and_resume(self, temp_data_dir):
        """Test that partial execution can be resumed."""
        project = create_linear_chain(length=5)

        await orchestrate_execution(project, max_parallel=1)

        completed_before = sum(1 for t in project.tasks.values() if t.state == TaskState.COMPLETED)
        assert completed_before == 5

        save_project(project)

        loaded_project = load_project(project.id)
        completed_after_load = sum(1 for t in loaded_project.tasks.values() if t.state == TaskState.COMPLETED)
        assert completed_after_load == 5

    @pytest.mark.asyncio
    async def test_resume_with_partial_completion(self, temp_data_dir):
        """Test resuming when some tasks are completed."""
        project = create_parallel_batches(num_batches=3, batch_size=5)

        task_ids = list(project.tasks.keys())
        first_batch = task_ids[:5]
        for task_id in first_batch:
            project.tasks[task_id].state = TaskState.COMPLETED

        save_project(project)

        loaded_project = load_project(project.id)

        results = await orchestrate_execution(loaded_project)

        assert results.status == "completed"
        assert results.completed_tasks == 10

        all_completed = all(t.state == TaskState.COMPLETED for t in loaded_project.tasks.values())
        assert all_completed

    @pytest.mark.asyncio
    async def test_abandoned_in_progress_tasks(self, temp_data_dir):
        """Test handling of tasks marked IN_PROGRESS but abandoned."""
        project = create_linear_chain(length=3)

        project.tasks["t0"].state = TaskState.IN_PROGRESS

        save_project(project)

        loaded_project = load_project(project.id)

        assert loaded_project.tasks["t0"].state == TaskState.IN_PROGRESS

        loaded_project.tasks["t0"].state = TaskState.PENDING

        results = await orchestrate_execution(loaded_project)

        assert results.status == "completed"
        assert results.completed_tasks == 3

    @pytest.mark.asyncio
    async def test_multiple_resume_cycles(self, temp_data_dir):
        """Test multiple interruption-resume cycles."""
        project = create_stub_project(depth=2, breadth=4)

        total_tasks = len(project.tasks)
        tasks_per_cycle = 3

        completed_count = 0

        for _ in range(5):
            if completed_count >= total_tasks:
                break

            await orchestrate_execution(project, max_parallel=tasks_per_cycle)

            completed_count = sum(1 for t in project.tasks.values() if t.state == TaskState.COMPLETED)

            save_project(project)

            if completed_count < total_tasks:
                project = load_project(project.id)

        assert completed_count == total_tasks

    @pytest.mark.asyncio
    async def test_resume_preserves_completed_tasks(self, temp_data_dir):
        """Test that resume doesn't re-execute completed tasks."""
        project = create_linear_chain(length=5)

        project.tasks["t0"].state = TaskState.COMPLETED
        project.tasks["t1"].state = TaskState.COMPLETED

        save_project(project)

        loaded_project = load_project(project.id)

        results = await orchestrate_execution(loaded_project)

        assert results.completed_tasks == 3

    @pytest.mark.asyncio
    async def test_resume_with_dependency_failures(self, temp_data_dir):
        """Test resume when some dependencies have failed."""
        project = create_stub_project(depth=1, breadth=3, dependency_type="sequential")

        project.tasks["L0-T1"].state = TaskState.BLOCKED

        save_project(project)

        loaded_project = load_project(project.id)

        results = await orchestrate_execution(loaded_project)

        assert results.status == "partial"
        assert results.failed_tasks > 0 or results.skipped_tasks > 0


class TestContextCompaction:
    """Test behavior when resuming with compacted context."""

    @pytest.fixture
    def temp_data_dir(self, monkeypatch):
        """Use temporary directory for data storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            def mock_get_path(project_id):
                base = tmpdir_path / "data" / "planner" / "projects"
                base.mkdir(parents=True, exist_ok=True)
                return base / f"{project_id}.json"

            monkeypatch.setattr("amplifier.planner.storage.get_project_path", mock_get_path)
            yield tmpdir_path

    @pytest.mark.asyncio
    async def test_resume_from_project_id_only(self, temp_data_dir):
        """Test resuming with only project ID (simulating compacted context)."""
        original_project = create_stub_project(depth=1, breadth=5)
        project_id = original_project.id

        for task in list(original_project.tasks.values())[:3]:
            task.state = TaskState.COMPLETED

        save_project(original_project)

        loaded_project = load_project(project_id)

        assert len(loaded_project.tasks) == len(original_project.tasks)

        completed = sum(1 for t in loaded_project.tasks.values() if t.state == TaskState.COMPLETED)
        assert completed == 3

        results = await orchestrate_execution(loaded_project)

        assert results.status == "completed"

    @pytest.mark.asyncio
    async def test_resume_idempotency(self, temp_data_dir):
        """Test that running orchestrate_execution on completed project is safe."""
        project = create_linear_chain(length=3)

        results1 = await orchestrate_execution(project)
        assert results1.status == "completed"

        save_project(project)

        loaded_project = load_project(project.id)

        results2 = await orchestrate_execution(loaded_project)
        assert results2.status == "completed"
        assert results2.completed_tasks == 0
