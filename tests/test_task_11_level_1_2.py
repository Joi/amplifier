"""
Test Task #11 at Level 1, Position 2

This test module demonstrates comprehensive test coverage principles:
- Unit tests with clear naming and structure
- Edge case coverage
- Error handling validation
- Integration test examples
- Performance considerations
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

import pytest


# Sample domain model for testing
@dataclass
class Task:
    """Represents a task in the system."""

    id: int
    description: str
    depth: int
    position: int
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, str] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate task properties."""
        if self.depth < 0:
            raise ValueError("Depth cannot be negative")
        if self.position < 0:
            raise ValueError("Position cannot be negative")
        if not self.description.strip():
            raise ValueError("Description cannot be empty")
        if self.id <= 0:
            raise ValueError("ID must be positive")
        return True

    def mark_complete(self) -> None:
        """Mark the task as completed."""
        self.completed = True

    def add_metadata(self, key: str, value: str) -> None:
        """Add metadata to the task."""
        if not key.strip():
            raise ValueError("Metadata key cannot be empty")
        self.metadata[key] = value

    def get_metadata(self, key: str) -> str | None:
        """Retrieve metadata value by key."""
        return self.metadata.get(key)

    def __str__(self) -> str:
        """String representation of the task."""
        status = "✓" if self.completed else "○"
        return f"[{status}] Task #{self.id}: {self.description} (L{self.depth}:P{self.position})"


class TaskManager:
    """Manages a collection of tasks."""

    def __init__(self) -> None:
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a task to the manager."""
        task.validate()
        self.tasks.append(task)

    def get_task(self, task_id: int) -> Task | None:
        """Retrieve a task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_tasks_by_depth(self, depth: int) -> list[Task]:
        """Get all tasks at a specific depth level."""
        return [task for task in self.tasks if task.depth == depth]

    def get_tasks_by_position(self, position: int) -> list[Task]:
        """Get all tasks at a specific position."""
        return [task for task in self.tasks if task.position == position]

    def get_tasks_by_depth_and_position(self, depth: int, position: int) -> list[Task]:
        """Get all tasks at a specific depth and position."""
        return [task for task in self.tasks if task.depth == depth and task.position == position]

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

    def get_incomplete_tasks(self) -> list[Task]:
        """Get all incomplete tasks."""
        return [task for task in self.tasks if not task.completed]

    def remove_task(self, task_id: int) -> bool:
        """Remove a task by ID."""
        task = self.get_task(task_id)
        if task:
            self.tasks.remove(task)
            return True
        return False


# ============================================================================
# Unit Tests
# ============================================================================


class TestTaskModel:
    """Unit tests for the Task model."""

    def test_task_creation_with_valid_data(self) -> None:
        """Test creating a task with valid data."""
        task = Task(id=11, description="Test task #11 at depth 1, position 2", depth=1, position=2)

        assert task.id == 11
        assert task.description == "Test task #11 at depth 1, position 2"
        assert task.depth == 1
        assert task.position == 2
        assert task.completed is False

    def test_task_creation_with_metadata(self) -> None:
        """Test creating a task with metadata."""
        metadata = {"priority": "high", "assignee": "user1"}
        task = Task(id=11, description="Task with metadata", depth=1, position=2, metadata=metadata)

        assert task.metadata == metadata
        assert task.get_metadata("priority") == "high"
        assert task.get_metadata("assignee") == "user1"

    def test_task_has_created_at_timestamp(self) -> None:
        """Test that task has created_at timestamp."""
        task = Task(id=11, description="Test task", depth=1, position=2)

        assert isinstance(task.created_at, datetime)
        assert task.created_at <= datetime.now()

    def test_task_validation_succeeds_for_valid_task(self) -> None:
        """Test that validation passes for a valid task."""
        task = Task(id=11, description="Valid task", depth=1, position=2)

        assert task.validate() is True

    def test_task_validation_fails_for_negative_depth(self) -> None:
        """Test that validation fails for negative depth."""
        task = Task(id=11, description="Invalid depth", depth=-1, position=2)

        with pytest.raises(ValueError, match="Depth cannot be negative"):
            task.validate()

    def test_task_validation_fails_for_negative_position(self) -> None:
        """Test that validation fails for negative position."""
        task = Task(id=11, description="Invalid position", depth=1, position=-1)

        with pytest.raises(ValueError, match="Position cannot be negative"):
            task.validate()

    def test_task_validation_fails_for_empty_description(self) -> None:
        """Test that validation fails for empty description."""
        task = Task(id=11, description="   ", depth=1, position=2)

        with pytest.raises(ValueError, match="Description cannot be empty"):
            task.validate()

    def test_task_validation_fails_for_zero_id(self) -> None:
        """Test that validation fails for zero ID."""
        task = Task(id=0, description="Zero ID", depth=1, position=2)

        with pytest.raises(ValueError, match="ID must be positive"):
            task.validate()

    def test_task_validation_fails_for_negative_id(self) -> None:
        """Test that validation fails for negative ID."""
        task = Task(id=-1, description="Negative ID", depth=1, position=2)

        with pytest.raises(ValueError, match="ID must be positive"):
            task.validate()

    def test_mark_task_complete(self) -> None:
        """Test marking a task as complete."""
        task = Task(id=11, description="Test task", depth=1, position=2)

        assert task.completed is False

        task.mark_complete()

        assert task.completed is True

    def test_add_metadata_to_task(self) -> None:
        """Test adding metadata to a task."""
        task = Task(id=11, description="Test task", depth=1, position=2)

        task.add_metadata("priority", "high")
        task.add_metadata("status", "in-progress")

        assert task.get_metadata("priority") == "high"
        assert task.get_metadata("status") == "in-progress"

    def test_add_metadata_with_empty_key_fails(self) -> None:
        """Test that adding metadata with empty key fails."""
        task = Task(id=11, description="Test task", depth=1, position=2)

        with pytest.raises(ValueError, match="Metadata key cannot be empty"):
            task.add_metadata("", "value")

    def test_get_nonexistent_metadata_returns_none(self) -> None:
        """Test that getting nonexistent metadata returns None."""
        task = Task(id=11, description="Test task", depth=1, position=2)

        result = task.get_metadata("nonexistent")

        assert result is None

    def test_task_string_representation_when_incomplete(self) -> None:
        """Test string representation of an incomplete task."""
        task = Task(id=11, description="Test task", depth=1, position=2)

        result = str(task)

        assert "[○]" in result
        assert "Task #11" in result
        assert "Test task" in result
        assert "(L1:P2)" in result

    def test_task_string_representation_when_complete(self) -> None:
        """Test string representation of a completed task."""
        task = Task(id=11, description="Test task", depth=1, position=2)
        task.mark_complete()

        result = str(task)

        assert "[✓]" in result
        assert "Task #11" in result


class TestTaskManager:
    """Unit tests for the TaskManager class."""

    @pytest.fixture
    def manager(self) -> TaskManager:
        """Provide a fresh TaskManager instance for each test."""
        return TaskManager()

    @pytest.fixture
    def sample_task(self) -> Task:
        """Provide a sample task for testing."""
        return Task(id=11, description="Test task #11 at depth 1, position 2", depth=1, position=2)

    def test_add_task_to_empty_manager(self, manager: TaskManager, sample_task: Task) -> None:
        """Test adding a task to an empty manager."""
        assert len(manager.tasks) == 0

        manager.add_task(sample_task)

        assert len(manager.tasks) == 1
        assert manager.tasks[0] == sample_task

    def test_add_multiple_tasks(self, manager: TaskManager) -> None:
        """Test adding multiple tasks."""
        task1 = Task(id=1, description="First task", depth=0, position=0)
        task2 = Task(id=2, description="Second task", depth=1, position=1)
        task3 = Task(id=3, description="Third task", depth=1, position=2)

        manager.add_task(task1)
        manager.add_task(task2)
        manager.add_task(task3)

        assert len(manager.tasks) == 3

    def test_add_task_validates_before_adding(self, manager: TaskManager) -> None:
        """Test that adding a task validates it first."""
        invalid_task = Task(id=-1, description="", depth=-1, position=2)

        with pytest.raises(ValueError):
            manager.add_task(invalid_task)

        assert len(manager.tasks) == 0

    def test_get_task_by_id_when_exists(self, manager: TaskManager, sample_task: Task) -> None:
        """Test retrieving a task by ID when it exists."""
        manager.add_task(sample_task)

        result = manager.get_task(11)

        assert result is not None
        assert result.id == 11
        assert result == sample_task

    def test_get_task_by_id_when_not_exists(self, manager: TaskManager) -> None:
        """Test retrieving a task by ID when it doesn't exist."""
        result = manager.get_task(999)

        assert result is None

    def test_get_tasks_by_depth(self, manager: TaskManager) -> None:
        """Test retrieving all tasks at a specific depth."""
        task1 = Task(id=1, description="Depth 0", depth=0, position=0)
        task2 = Task(id=2, description="Depth 1 - First", depth=1, position=0)
        task3 = Task(id=3, description="Depth 1 - Second", depth=1, position=2)
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

    def test_get_tasks_by_position(self, manager: TaskManager) -> None:
        """Test retrieving all tasks at a specific position."""
        task1 = Task(id=1, description="Position 0", depth=0, position=0)
        task2 = Task(id=2, description="Position 2 - First", depth=1, position=2)
        task3 = Task(id=3, description="Position 2 - Second", depth=2, position=2)

        manager.add_task(task1)
        manager.add_task(task2)
        manager.add_task(task3)

        position_2_tasks = manager.get_tasks_by_position(2)

        assert len(position_2_tasks) == 2
        assert all(task.position == 2 for task in position_2_tasks)
        assert task2 in position_2_tasks
        assert task3 in position_2_tasks

    def test_get_tasks_by_depth_and_position(self, manager: TaskManager) -> None:
        """Test retrieving tasks by both depth and position."""
        task1 = Task(id=1, description="D0P0", depth=0, position=0)
        task2 = Task(id=2, description="D1P2 - Target", depth=1, position=2)
        task3 = Task(id=3, description="D1P1", depth=1, position=1)
        task4 = Task(id=4, description="D2P2", depth=2, position=2)

        manager.add_task(task1)
        manager.add_task(task2)
        manager.add_task(task3)
        manager.add_task(task4)

        results = manager.get_tasks_by_depth_and_position(1, 2)

        assert len(results) == 1
        assert results[0] == task2

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

        result = manager.complete_task(11)

        assert result is True
        assert sample_task.completed is True

    def test_complete_task_when_not_exists(self, manager: TaskManager) -> None:
        """Test completing a task that doesn't exist."""
        result = manager.complete_task(999)

        assert result is False

    def test_get_incomplete_tasks(self, manager: TaskManager) -> None:
        """Test retrieving incomplete tasks."""
        task1 = Task(id=1, description="Task 1", depth=1, position=0)
        task2 = Task(id=2, description="Task 2", depth=1, position=1)
        task3 = Task(id=3, description="Task 3", depth=1, position=2)

        manager.add_task(task1)
        manager.add_task(task2)
        manager.add_task(task3)

        manager.complete_task(1)

        incomplete = manager.get_incomplete_tasks()

        assert len(incomplete) == 2
        assert task2 in incomplete
        assert task3 in incomplete
        assert task1 not in incomplete

    def test_remove_task_when_exists(self, manager: TaskManager, sample_task: Task) -> None:
        """Test removing a task that exists."""
        manager.add_task(sample_task)
        assert len(manager.tasks) == 1

        result = manager.remove_task(11)

        assert result is True
        assert len(manager.tasks) == 0

    def test_remove_task_when_not_exists(self, manager: TaskManager) -> None:
        """Test removing a task that doesn't exist."""
        result = manager.remove_task(999)

        assert result is False

    def test_get_completion_rate_when_no_tasks(self, manager: TaskManager) -> None:
        """Test completion rate calculation when there are no tasks."""
        rate = manager.get_completion_rate()

        assert rate == 0.0

    def test_get_completion_rate_when_no_tasks_completed(self, manager: TaskManager) -> None:
        """Test completion rate when no tasks are completed."""
        manager.add_task(Task(id=1, description="Task 1", depth=1, position=0))
        manager.add_task(Task(id=2, description="Task 2", depth=1, position=2))

        rate = manager.get_completion_rate()

        assert rate == 0.0

    def test_get_completion_rate_when_all_tasks_completed(self, manager: TaskManager) -> None:
        """Test completion rate when all tasks are completed."""
        task1 = Task(id=1, description="Task 1", depth=1, position=0)
        task2 = Task(id=2, description="Task 2", depth=1, position=2)

        manager.add_task(task1)
        manager.add_task(task2)
        manager.complete_task(1)
        manager.complete_task(2)

        rate = manager.get_completion_rate()

        assert rate == 100.0

    def test_get_completion_rate_when_some_tasks_completed(self, manager: TaskManager) -> None:
        """Test completion rate when some tasks are completed."""
        task1 = Task(id=1, description="Task 1", depth=1, position=0)
        task2 = Task(id=2, description="Task 2", depth=1, position=1)
        task3 = Task(id=3, description="Task 3", depth=1, position=2)
        task4 = Task(id=4, description="Task 4", depth=1, position=3)

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
        task = Task(id=11, description="Test task #11 at depth 1, position 2", depth=1, position=2)

        # Add task
        manager.add_task(task)
        assert len(manager.tasks) == 1

        # Verify task is incomplete
        retrieved_task = manager.get_task(11)
        assert retrieved_task is not None
        assert retrieved_task.completed is False

        # Add metadata
        retrieved_task.add_metadata("priority", "high")
        retrieved_task.add_metadata("estimated_hours", "5")

        # Complete task
        success = manager.complete_task(11)
        assert success is True

        # Verify completion
        retrieved_task = manager.get_task(11)
        assert retrieved_task is not None
        assert retrieved_task.completed is True

        # Verify metadata persists
        assert retrieved_task.get_metadata("priority") == "high"

        # Check completion rate
        rate = manager.get_completion_rate()
        assert rate == 100.0

    def test_multi_depth_task_management(self) -> None:
        """Test managing tasks across multiple depth levels."""
        manager = TaskManager()

        # Create tasks at different depths with position 2
        tasks = [
            Task(id=1, description="Root task", depth=0, position=0),
            Task(id=2, description="Level 1 Task 0", depth=1, position=0),
            Task(id=3, description="Level 1 Task 2", depth=1, position=2),
            Task(id=4, description="Level 2 Task 2", depth=2, position=2),
        ]

        # Add all tasks
        for task in tasks:
            manager.add_task(task)

        # Verify depth filtering works
        level_1_tasks = manager.get_tasks_by_depth(1)
        assert len(level_1_tasks) == 2

        # Verify position filtering works
        position_2_tasks = manager.get_tasks_by_position(2)
        assert len(position_2_tasks) == 2

        # Complete tasks at position 2
        manager.complete_task(3)
        manager.complete_task(4)

        # Verify specific position completion
        position_2_tasks = manager.get_tasks_by_position(2)
        assert all(task.completed for task in position_2_tasks)

        # Overall completion should be 50%
        rate = manager.get_completion_rate()
        assert rate == 50.0

    def test_task_lifecycle_with_metadata(self) -> None:
        """Test complete task lifecycle including metadata management."""
        manager = TaskManager()
        task = Task(id=11, description="Task with metadata lifecycle", depth=1, position=2)

        # Add task
        manager.add_task(task)

        # Add initial metadata
        task.add_metadata("status", "todo")
        task.add_metadata("assignee", "developer1")

        # Update metadata as task progresses
        task.add_metadata("status", "in-progress")
        assert task.get_metadata("status") == "in-progress"

        # Complete task and update metadata
        manager.complete_task(11)
        task.add_metadata("status", "done")
        task.add_metadata("completed_by", "developer1")

        # Verify final state
        assert task.completed is True
        assert task.get_metadata("status") == "done"
        assert task.get_metadata("completed_by") == "developer1"


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

    def test_task_at_position_2_with_zero_depth(self) -> None:
        """Test task at position 2 with zero depth."""
        task = Task(id=1, description="Root at position 2", depth=0, position=2)

        assert task.validate() is True
        assert task.position == 2

    def test_task_with_large_id(self) -> None:
        """Test task with a very large ID number."""
        task = Task(id=999999, description="Large ID task", depth=1, position=2)

        assert task.validate() is True
        assert task.id == 999999

    def test_task_with_long_description(self) -> None:
        """Test task with a very long description."""
        long_description = "A" * 1000
        task = Task(id=11, description=long_description, depth=1, position=2)

        assert task.validate() is True
        assert len(task.description) == 1000

    def test_task_with_unicode_in_description(self) -> None:
        """Test task with unicode characters in description."""
        task = Task(id=11, description="Test 测试 тест ☕ 🚀", depth=1, position=2)

        assert task.validate() is True
        assert "测试" in task.description
        assert "🚀" in task.description

    def test_task_with_unicode_in_metadata(self) -> None:
        """Test task with unicode characters in metadata."""
        task = Task(id=11, description="Test task", depth=1, position=2)
        task.add_metadata("comment", "需要審查 🔍")

        assert task.get_metadata("comment") == "需要審查 🔍"

    def test_manager_handles_duplicate_task_ids(self) -> None:
        """Test that manager can handle duplicate task IDs."""
        manager = TaskManager()

        task1 = Task(id=11, description="First task", depth=1, position=2)
        task2 = Task(id=11, description="Duplicate ID task", depth=1, position=2)

        manager.add_task(task1)
        manager.add_task(task2)

        # get_task returns the first match
        result = manager.get_task(11)
        assert result == task1

    def test_completion_rate_precision(self) -> None:
        """Test completion rate calculation precision."""
        manager = TaskManager()

        # Add 3 tasks, complete 1 (should be 33.33...%)
        for i in range(1, 4):
            manager.add_task(Task(id=i, description=f"Task {i}", depth=1, position=i))

        manager.complete_task(1)

        rate = manager.get_completion_rate()

        assert pytest.approx(rate, rel=0.01) == 33.33

    def test_empty_metadata_dict_on_new_task(self) -> None:
        """Test that new tasks have empty metadata dict."""
        task = Task(id=11, description="New task", depth=1, position=2)

        assert task.metadata == {}
        assert len(task.metadata) == 0

    def test_metadata_overwrites_existing_key(self) -> None:
        """Test that adding metadata with existing key overwrites the value."""
        task = Task(id=11, description="Test task", depth=1, position=2)

        task.add_metadata("priority", "low")
        assert task.get_metadata("priority") == "low"

        task.add_metadata("priority", "high")
        assert task.get_metadata("priority") == "high"


# ============================================================================
# Parametrized Tests
# ============================================================================


class TestParametrizedCases:
    """Tests using parametrization for comprehensive coverage."""

    @pytest.mark.parametrize(
        "task_id,depth,position,expected_valid",
        [
            (11, 1, 2, True),
            (1, 0, 0, True),
            (100, 5, 10, True),
            (9999, 100, 100, True),
            (0, 1, 2, False),  # zero ID
            (-1, 1, 2, False),  # negative ID
            (11, -1, 2, False),  # negative depth
            (11, 1, -1, False),  # negative position
        ],
    )
    def test_task_validation_with_various_parameters(
        self, task_id: int, depth: int, position: int, expected_valid: bool
    ) -> None:
        """Test task validation with various parameter combinations."""
        task = Task(id=task_id, description="Test task", depth=depth, position=position)

        if expected_valid:
            assert task.validate() is True
        else:
            with pytest.raises(ValueError):
                task.validate()

    @pytest.mark.parametrize(
        "description,should_pass",
        [
            ("Valid description", True),
            ("Test task #11 at depth 1, position 2", True),
            ("A", True),
            ("", False),
            ("   ", False),
            ("\t\n", False),
            ("Valid with spaces  ", True),
            ("Multi\nline\ndescription", True),
        ],
    )
    def test_task_description_validation(self, description: str, should_pass: bool) -> None:
        """Test task description validation with various inputs."""
        task = Task(id=11, description=description, depth=1, position=2)

        if should_pass:
            assert task.validate() is True
        else:
            with pytest.raises(ValueError, match="Description cannot be empty"):
                task.validate()

    @pytest.mark.parametrize(
        "position,expected_count",
        [
            (0, 1),
            (1, 1),
            (2, 2),
            (3, 0),
        ],
    )
    def test_get_tasks_by_position_parametrized(self, position: int, expected_count: int) -> None:
        """Test getting tasks by position with various positions."""
        manager = TaskManager()

        tasks = [
            Task(id=1, description="P0", depth=0, position=0),
            Task(id=2, description="P1", depth=1, position=1),
            Task(id=3, description="P2-1", depth=1, position=2),
            Task(id=4, description="P2-2", depth=2, position=2),
        ]

        for task in tasks:
            manager.add_task(task)

        results = manager.get_tasks_by_position(position)

        assert len(results) == expected_count


# ============================================================================
# Performance Tests (Optional - for demonstration)
# ============================================================================


class TestPerformance:
    """Performance-related tests."""

    def test_large_number_of_tasks(self) -> None:
        """Test manager performance with a large number of tasks."""
        manager = TaskManager()

        # Add 1000 tasks
        for i in range(1, 1001):
            task = Task(id=i, description=f"Task {i}", depth=i % 10, position=i % 100)
            manager.add_task(task)

        assert len(manager.tasks) == 1000

        # Test retrieval performance
        result = manager.get_task(500)
        assert result is not None
        assert result.id == 500

        # Test position filtering performance
        position_2_tasks = manager.get_tasks_by_position(2)
        assert len(position_2_tasks) == 10

    def test_completion_rate_calculation_performance(self) -> None:
        """Test completion rate calculation with many tasks."""
        manager = TaskManager()

        # Add 500 tasks
        for i in range(1, 501):
            manager.add_task(Task(id=i, description=f"Task {i}", depth=1, position=i % 10))

        # Complete half of them
        for i in range(1, 251):
            manager.complete_task(i)

        rate = manager.get_completion_rate()
        assert rate == 50.0

    def test_metadata_operations_performance(self) -> None:
        """Test metadata operations with many keys."""
        task = Task(id=11, description="Task with lots of metadata", depth=1, position=2)

        # Add 100 metadata entries
        for i in range(100):
            task.add_metadata(f"key_{i}", f"value_{i}")

        assert len(task.metadata) == 100

        # Verify retrieval
        for i in range(100):
            assert task.get_metadata(f"key_{i}") == f"value_{i}"

    def test_incomplete_tasks_filtering_performance(self) -> None:
        """Test filtering incomplete tasks with many tasks."""
        manager = TaskManager()

        # Add 1000 tasks
        for i in range(1, 1001):
            manager.add_task(Task(id=i, description=f"Task {i}", depth=1, position=i % 10))

        # Complete 300 tasks
        for i in range(1, 301):
            manager.complete_task(i)

        incomplete = manager.get_incomplete_tasks()

        assert len(incomplete) == 700
        assert all(not task.completed for task in incomplete)
