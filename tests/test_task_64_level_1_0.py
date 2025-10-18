"""
Test Task #64 at Level 1, Position 0

This test module demonstrates comprehensive test coverage principles:
- Unit tests with clear naming and structure
- Edge case coverage
- Error handling validation
- Integration test examples
- Performance considerations
"""

import pytest
from typing import List, Optional
from dataclasses import dataclass


# Sample domain model for testing
@dataclass
class Task:
    """Represents a task in the system."""

    id: int
    description: str
    depth: int
    position: int
    completed: bool = False

    def validate(self) -> bool:
        """Validate task properties."""
        if self.depth < 0:
            raise ValueError("Depth cannot be negative")
        if self.position < 0:
            raise ValueError("Position cannot be negative")
        if not self.description.strip():
            raise ValueError("Description cannot be empty")
        return True

    def mark_complete(self) -> None:
        """Mark the task as completed."""
        self.completed = True

    def __str__(self) -> str:
        """String representation of the task."""
        status = "✓" if self.completed else "○"
        return f"[{status}] Task #{self.id}: {self.description} (L{self.depth}:P{self.position})"


class TaskManager:
    """Manages a collection of tasks."""

    def __init__(self) -> None:
        self.tasks: List[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a task to the manager."""
        task.validate()
        self.tasks.append(task)

    def get_task(self, task_id: int) -> Optional[Task]:
        """Retrieve a task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_tasks_by_depth(self, depth: int) -> List[Task]:
        """Get all tasks at a specific depth level."""
        return [task for task in self.tasks if task.depth == depth]

    def complete_task(self, task_id: int) -> bool:
        """Mark a task as complete."""
        task = self.get_task(task_id)
        if task:
            task.mark_complete()
            return True
        return False

    def get_completion_rate(self) -> float:
        """Calculate the percentage of completed tasks."""
        if not self.tasks:
            return 0.0
        completed = sum(1 for task in self.tasks if task.completed)
        return (completed / len(self.tasks)) * 100


# ============================================================================
# Unit Tests
# ============================================================================


class TestTaskModel:
    """Unit tests for the Task model."""

    def test_task_creation_with_valid_data(self) -> None:
        """Test creating a task with valid data."""
        task = Task(id=64, description="Test task #64 at depth 1, position 0", depth=1, position=0)

        assert task.id == 64
        assert task.description == "Test task #64 at depth 1, position 0"
        assert task.depth == 1
        assert task.position == 0
        assert task.completed is False

    def test_task_validation_succeeds_for_valid_task(self) -> None:
        """Test that validation passes for a valid task."""
        task = Task(id=1, description="Valid task", depth=1, position=0)

        assert task.validate() is True

    def test_task_validation_fails_for_negative_depth(self) -> None:
        """Test that validation fails for negative depth."""
        task = Task(id=1, description="Invalid depth", depth=-1, position=0)

        with pytest.raises(ValueError, match="Depth cannot be negative"):
            task.validate()

    def test_task_validation_fails_for_negative_position(self) -> None:
        """Test that validation fails for negative position."""
        task = Task(id=1, description="Invalid position", depth=0, position=-1)

        with pytest.raises(ValueError, match="Position cannot be negative"):
            task.validate()

    def test_task_validation_fails_for_empty_description(self) -> None:
        """Test that validation fails for empty description."""
        task = Task(id=1, description="   ", depth=0, position=0)

        with pytest.raises(ValueError, match="Description cannot be empty"):
            task.validate()

    def test_mark_task_complete(self) -> None:
        """Test marking a task as complete."""
        task = Task(id=1, description="Test task", depth=0, position=0)

        assert task.completed is False

        task.mark_complete()

        assert task.completed is True

    def test_task_string_representation_when_incomplete(self) -> None:
        """Test string representation of an incomplete task."""
        task = Task(id=64, description="Test task", depth=1, position=0)

        result = str(task)

        assert "[○]" in result
        assert "Task #64" in result
        assert "Test task" in result
        assert "(L1:P0)" in result

    def test_task_string_representation_when_complete(self) -> None:
        """Test string representation of a completed task."""
        task = Task(id=64, description="Test task", depth=1, position=0)
        task.mark_complete()

        result = str(task)

        assert "[✓]" in result
        assert "Task #64" in result


class TestTaskManager:
    """Unit tests for the TaskManager class."""

    @pytest.fixture
    def manager(self) -> TaskManager:
        """Provide a fresh TaskManager instance for each test."""
        return TaskManager()

    @pytest.fixture
    def sample_task(self) -> Task:
        """Provide a sample task for testing."""
        return Task(id=64, description="Test task #64 at depth 1, position 0", depth=1, position=0)

    def test_add_task_to_empty_manager(self, manager: TaskManager, sample_task: Task) -> None:
        """Test adding a task to an empty manager."""
        assert len(manager.tasks) == 0

        manager.add_task(sample_task)

        assert len(manager.tasks) == 1
        assert manager.tasks[0] == sample_task

    def test_add_multiple_tasks(self, manager: TaskManager) -> None:
        """Test adding multiple tasks."""
        task1 = Task(id=1, description="First task", depth=0, position=0)
        task2 = Task(id=2, description="Second task", depth=1, position=0)
        task3 = Task(id=3, description="Third task", depth=1, position=1)

        manager.add_task(task1)
        manager.add_task(task2)
        manager.add_task(task3)

        assert len(manager.tasks) == 3

    def test_add_task_validates_before_adding(self, manager: TaskManager) -> None:
        """Test that adding a task validates it first."""
        invalid_task = Task(id=1, description="", depth=-1, position=0)

        with pytest.raises(ValueError):
            manager.add_task(invalid_task)

        assert len(manager.tasks) == 0

    def test_get_task_by_id_when_exists(self, manager: TaskManager, sample_task: Task) -> None:
        """Test retrieving a task by ID when it exists."""
        manager.add_task(sample_task)

        result = manager.get_task(64)

        assert result is not None
        assert result.id == 64
        assert result == sample_task

    def test_get_task_by_id_when_not_exists(self, manager: TaskManager) -> None:
        """Test retrieving a task by ID when it doesn't exist."""
        result = manager.get_task(999)

        assert result is None

    def test_get_tasks_by_depth(self, manager: TaskManager) -> None:
        """Test retrieving all tasks at a specific depth."""
        task1 = Task(id=1, description="Depth 0", depth=0, position=0)
        task2 = Task(id=2, description="Depth 1 - First", depth=1, position=0)
        task3 = Task(id=3, description="Depth 1 - Second", depth=1, position=1)
        task4 = Task(id=4, description="Depth 2", depth=2, position=0)

        manager.add_task(task1)
        manager.add_task(task2)
        manager.add_task(task3)
        manager.add_task(task4)

        depth_1_tasks = manager.get_tasks_by_depth(1)

        assert len(depth_1_tasks) == 2
        assert all(task.depth == 1 for task in depth_1_tasks)
        assert task2 in depth_1_tasks
        assert task3 in depth_1_tasks

    def test_get_tasks_by_depth_when_no_tasks_at_depth(self, manager: TaskManager) -> None:
        """Test retrieving tasks by depth when no tasks exist at that depth."""
        task = Task(id=1, description="Depth 0", depth=0, position=0)
        manager.add_task(task)

        result = manager.get_tasks_by_depth(5)

        assert result == []

    def test_complete_task_when_exists(self, manager: TaskManager, sample_task: Task) -> None:
        """Test completing a task that exists."""
        manager.add_task(sample_task)
        assert sample_task.completed is False

        result = manager.complete_task(64)

        assert result is True
        assert sample_task.completed is True

    def test_complete_task_when_not_exists(self, manager: TaskManager) -> None:
        """Test completing a task that doesn't exist."""
        result = manager.complete_task(999)

        assert result is False

    def test_get_completion_rate_when_no_tasks(self, manager: TaskManager) -> None:
        """Test completion rate calculation when there are no tasks."""
        rate = manager.get_completion_rate()

        assert rate == 0.0

    def test_get_completion_rate_when_no_tasks_completed(self, manager: TaskManager) -> None:
        """Test completion rate when no tasks are completed."""
        manager.add_task(Task(id=1, description="Task 1", depth=0, position=0))
        manager.add_task(Task(id=2, description="Task 2", depth=0, position=1))

        rate = manager.get_completion_rate()

        assert rate == 0.0

    def test_get_completion_rate_when_all_tasks_completed(self, manager: TaskManager) -> None:
        """Test completion rate when all tasks are completed."""
        task1 = Task(id=1, description="Task 1", depth=0, position=0)
        task2 = Task(id=2, description="Task 2", depth=0, position=1)

        manager.add_task(task1)
        manager.add_task(task2)
        manager.complete_task(1)
        manager.complete_task(2)

        rate = manager.get_completion_rate()

        assert rate == 100.0

    def test_get_completion_rate_when_some_tasks_completed(self, manager: TaskManager) -> None:
        """Test completion rate when some tasks are completed."""
        task1 = Task(id=1, description="Task 1", depth=0, position=0)
        task2 = Task(id=2, description="Task 2", depth=0, position=1)
        task3 = Task(id=3, description="Task 3", depth=0, position=2)
        task4 = Task(id=4, description="Task 4", depth=0, position=3)

        manager.add_task(task1)
        manager.add_task(task2)
        manager.add_task(task3)
        manager.add_task(task4)

        manager.complete_task(1)
        manager.complete_task(3)

        rate = manager.get_completion_rate()

        assert rate == 50.0


# ============================================================================
# Integration Tests
# ============================================================================


class TestTaskWorkflow:
    """Integration tests for complete task workflows."""

    def test_complete_task_workflow(self) -> None:
        """Test a complete workflow from task creation to completion."""
        # Setup
        manager = TaskManager()
        task = Task(id=64, description="Test task #64 at depth 1, position 0", depth=1, position=0)

        # Add task
        manager.add_task(task)
        assert len(manager.tasks) == 1

        # Verify task is incomplete
        retrieved_task = manager.get_task(64)
        assert retrieved_task is not None
        assert retrieved_task.completed is False

        # Complete task
        success = manager.complete_task(64)
        assert success is True

        # Verify completion
        retrieved_task = manager.get_task(64)
        assert retrieved_task is not None
        assert retrieved_task.completed is True

        # Check completion rate
        rate = manager.get_completion_rate()
        assert rate == 100.0

    def test_multi_depth_task_management(self) -> None:
        """Test managing tasks across multiple depth levels."""
        manager = TaskManager()

        # Create tasks at different depths
        tasks = [
            Task(id=1, description="Root task", depth=0, position=0),
            Task(id=2, description="Level 1 Task 0", depth=1, position=0),
            Task(id=3, description="Level 1 Task 1", depth=1, position=1),
            Task(id=4, description="Level 2 Task 0", depth=2, position=0),
        ]

        # Add all tasks
        for task in tasks:
            manager.add_task(task)

        # Verify depth filtering works
        level_1_tasks = manager.get_tasks_by_depth(1)
        assert len(level_1_tasks) == 2

        # Complete tasks at level 1
        manager.complete_task(2)
        manager.complete_task(3)

        # Verify specific level completion
        level_1_tasks = manager.get_tasks_by_depth(1)
        assert all(task.completed for task in level_1_tasks)

        # Overall completion should be 50%
        rate = manager.get_completion_rate()
        assert rate == 50.0


# ============================================================================
# Edge Case and Error Handling Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_task_with_zero_depth_and_position(self) -> None:
        """Test task with zero values for depth and position."""
        task = Task(id=1, description="Root task", depth=0, position=0)

        assert task.validate() is True
        assert task.depth == 0
        assert task.position == 0

    def test_task_with_large_id(self) -> None:
        """Test task with a very large ID number."""
        task = Task(id=999999, description="Large ID task", depth=0, position=0)

        assert task.validate() is True
        assert task.id == 999999

    def test_task_with_long_description(self) -> None:
        """Test task with a very long description."""
        long_description = "A" * 1000
        task = Task(id=1, description=long_description, depth=0, position=0)

        assert task.validate() is True
        assert len(task.description) == 1000

    def test_task_with_unicode_in_description(self) -> None:
        """Test task with unicode characters in description."""
        task = Task(id=1, description="Test 测试 тест ☕ 🚀", depth=0, position=0)

        assert task.validate() is True
        assert "测试" in task.description
        assert "🚀" in task.description

    def test_manager_handles_duplicate_task_ids(self) -> None:
        """Test that manager can handle duplicate task IDs."""
        manager = TaskManager()

        task1 = Task(id=1, description="First task", depth=0, position=0)
        task2 = Task(id=1, description="Duplicate ID task", depth=1, position=0)

        manager.add_task(task1)
        manager.add_task(task2)

        # get_task returns the first match
        result = manager.get_task(1)
        assert result == task1

    def test_completion_rate_precision(self) -> None:
        """Test completion rate calculation precision."""
        manager = TaskManager()

        # Add 3 tasks, complete 1 (should be 33.33...%)
        for i in range(3):
            manager.add_task(Task(id=i, description=f"Task {i}", depth=0, position=i))

        manager.complete_task(0)

        rate = manager.get_completion_rate()

        assert pytest.approx(rate, rel=0.01) == 33.33


# ============================================================================
# Parametrized Tests
# ============================================================================


class TestParametrizedCases:
    """Tests using parametrization for comprehensive coverage."""

    @pytest.mark.parametrize(
        "depth,position,expected_valid",
        [
            (0, 0, True),
            (1, 0, True),
            (5, 10, True),
            (100, 100, True),
            (-1, 0, False),
            (0, -1, False),
            (-1, -1, False),
        ],
    )
    def test_task_validation_with_various_depths_and_positions(
        self, depth: int, position: int, expected_valid: bool
    ) -> None:
        """Test task validation with various depth and position combinations."""
        task = Task(id=1, description="Test task", depth=depth, position=position)

        if expected_valid:
            assert task.validate() is True
        else:
            with pytest.raises(ValueError):
                task.validate()

    @pytest.mark.parametrize(
        "description,should_pass",
        [
            ("Valid description", True),
            ("A", True),
            ("", False),
            ("   ", False),
            ("\t\n", False),
            ("Valid with spaces  ", True),
        ],
    )
    def test_task_description_validation(self, description: str, should_pass: bool) -> None:
        """Test task description validation with various inputs."""
        task = Task(id=1, description=description, depth=0, position=0)

        if should_pass:
            assert task.validate() is True
        else:
            with pytest.raises(ValueError, match="Description cannot be empty"):
                task.validate()


# ============================================================================
# Performance Tests (Optional - for demonstration)
# ============================================================================


class TestPerformance:
    """Performance-related tests."""

    def test_large_number_of_tasks(self) -> None:
        """Test manager performance with a large number of tasks."""
        manager = TaskManager()

        # Add 1000 tasks
        for i in range(1000):
            task = Task(id=i, description=f"Task {i}", depth=i % 10, position=i % 100)
            manager.add_task(task)

        assert len(manager.tasks) == 1000

        # Test retrieval performance
        result = manager.get_task(500)
        assert result is not None
        assert result.id == 500

        # Test depth filtering performance
        depth_5_tasks = manager.get_tasks_by_depth(5)
        assert len(depth_5_tasks) == 100

    def test_completion_rate_calculation_performance(self) -> None:
        """Test completion rate calculation with many tasks."""
        manager = TaskManager()

        # Add 500 tasks
        for i in range(500):
            manager.add_task(Task(id=i, description=f"Task {i}", depth=0, position=i))

        # Complete half of them
        for i in range(250):
            manager.complete_task(i)

        rate = manager.get_completion_rate()
        assert rate == 50.0
