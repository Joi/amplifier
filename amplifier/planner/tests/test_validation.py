"""Tests for project validation including circular dependency detection."""

from amplifier.planner.models import Project
from amplifier.planner.models import Task


class TestCircularDependencyDetection:
    """Test circular dependency detection in task graphs."""

    def test_no_cycles_in_linear_chain(self) -> None:
        """Test that linear chains have no cycles."""
        project = Project(id="test", name="Test")

        t1 = Task(id="t1", title="Task 1")
        t2 = Task(id="t2", title="Task 2", depends_on=["t1"])
        t3 = Task(id="t3", title="Task 3", depends_on=["t2"])

        project.add_task(t1)
        project.add_task(t2)
        project.add_task(t3)

        cycles = project.detect_dependency_cycles()
        assert cycles == []

    def test_detects_simple_two_task_cycle(self) -> None:
        """Test detection of A -> B -> A cycle."""
        project = Project(id="test", name="Test")

        t1 = Task(id="t1", title="Task 1", depends_on=["t2"])
        t2 = Task(id="t2", title="Task 2", depends_on=["t1"])

        project.add_task(t1)
        project.add_task(t2)

        cycles = project.detect_dependency_cycles()
        assert len(cycles) == 1
        # Cycle should contain both tasks
        assert set(cycles[0]) == {"t1", "t2"}

    def test_detects_self_dependency(self) -> None:
        """Test detection of task depending on itself."""
        project = Project(id="test", name="Test")

        t1 = Task(id="t1", title="Task 1", depends_on=["t1"])

        project.add_task(t1)

        cycles = project.detect_dependency_cycles()
        assert len(cycles) == 1
        assert cycles[0] == ["t1"]

    def test_detects_three_task_cycle(self) -> None:
        """Test detection of A -> B -> C -> A cycle."""
        project = Project(id="test", name="Test")

        t1 = Task(id="t1", title="Task 1", depends_on=["t3"])
        t2 = Task(id="t2", title="Task 2", depends_on=["t1"])
        t3 = Task(id="t3", title="Task 3", depends_on=["t2"])

        project.add_task(t1)
        project.add_task(t2)
        project.add_task(t3)

        cycles = project.detect_dependency_cycles()
        assert len(cycles) == 1
        assert set(cycles[0]) == {"t1", "t2", "t3"}

    def test_detects_multiple_separate_cycles(self) -> None:
        """Test detection of multiple independent cycles."""
        project = Project(id="test", name="Test")

        # First cycle: t1 <-> t2
        t1 = Task(id="t1", title="Task 1", depends_on=["t2"])
        t2 = Task(id="t2", title="Task 2", depends_on=["t1"])

        # Second cycle: t3 <-> t4
        t3 = Task(id="t3", title="Task 3", depends_on=["t4"])
        t4 = Task(id="t4", title="Task 4", depends_on=["t3"])

        # Independent task
        t5 = Task(id="t5", title="Task 5")

        for task in [t1, t2, t3, t4, t5]:
            project.add_task(task)

        cycles = project.detect_dependency_cycles()
        assert len(cycles) == 2

    def test_no_cycles_in_diamond_pattern(self) -> None:
        """Test that diamond dependency pattern has no cycles."""
        project = Project(id="test", name="Test")

        t1 = Task(id="t1", title="Start")
        t2 = Task(id="t2", title="Branch A", depends_on=["t1"])
        t3 = Task(id="t3", title="Branch B", depends_on=["t1"])
        t4 = Task(id="t4", title="Merge", depends_on=["t2", "t3"])

        for task in [t1, t2, t3, t4]:
            project.add_task(task)

        cycles = project.detect_dependency_cycles()
        assert cycles == []

    def test_detects_cycle_in_complex_graph(self) -> None:
        """Test cycle detection in complex graph with valid and invalid dependencies."""
        project = Project(id="test", name="Test")

        t1 = Task(id="t1", title="Task 1")
        t2 = Task(id="t2", title="Task 2", depends_on=["t1"])
        t3 = Task(id="t3", title="Task 3", depends_on=["t2"])
        t4 = Task(id="t4", title="Task 4", depends_on=["t3"])
        # Create cycle by making t2 also depend on t4
        t2.depends_on.append("t4")

        for task in [t1, t2, t3, t4]:
            project.add_task(task)

        cycles = project.detect_dependency_cycles()
        assert len(cycles) == 1
        # Cycle should include t2, t3, t4
        assert set(cycles[0]) == {"t2", "t3", "t4"}


class TestDependencyValidation:
    """Test comprehensive dependency validation."""

    def test_validate_valid_project(self) -> None:
        """Test that valid project passes validation."""
        project = Project(id="test", name="Test")

        t1 = Task(id="t1", title="Task 1")
        t2 = Task(id="t2", title="Task 2", depends_on=["t1"])

        project.add_task(t1)
        project.add_task(t2)

        is_valid, errors = project.validate_dependencies()
        assert is_valid
        assert errors == []

    def test_validate_detects_circular_dependencies(self) -> None:
        """Test that validation catches circular dependencies."""
        project = Project(id="test", name="Test")

        t1 = Task(id="t1", title="Task 1", depends_on=["t2"])
        t2 = Task(id="t2", title="Task 2", depends_on=["t1"])

        project.add_task(t1)
        project.add_task(t2)

        is_valid, errors = project.validate_dependencies()
        assert not is_valid
        assert len(errors) == 1
        assert "Circular dependency detected" in errors[0]

    def test_validate_detects_missing_dependencies(self) -> None:
        """Test that validation catches references to non-existent tasks."""
        project = Project(id="test", name="Test")

        t1 = Task(id="t1", title="Task 1", depends_on=["t2"])  # t2 doesn't exist

        project.add_task(t1)

        is_valid, errors = project.validate_dependencies()
        assert not is_valid
        assert len(errors) == 1
        assert "non-existent task" in errors[0]
        assert "t2" in errors[0]

    def test_validate_detects_multiple_errors(self) -> None:
        """Test that validation catches all error types."""
        project = Project(id="test", name="Test")

        t1 = Task(id="t1", title="Task 1", depends_on=["t2", "t_missing"])  # Circular + missing
        t2 = Task(id="t2", title="Task 2", depends_on=["t1"])

        project.add_task(t1)
        project.add_task(t2)

        is_valid, errors = project.validate_dependencies()
        assert not is_valid
        assert len(errors) == 2  # One for cycle, one for missing
        error_text = " ".join(errors)
        assert "Circular dependency" in error_text
        assert "non-existent task" in error_text

    def test_validate_empty_project(self) -> None:
        """Test that empty project is valid."""
        project = Project(id="test", name="Test")

        is_valid, errors = project.validate_dependencies()
        assert is_valid
        assert errors == []
