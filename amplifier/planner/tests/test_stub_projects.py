"""Tests using stub projects to validate super-planner functionality."""

import pytest

from amplifier.planner import Project
from amplifier.planner import TaskState
from amplifier.planner import orchestrate_execution

from .test_helpers import count_ready_tasks
from .test_helpers import create_complex_graph
from .test_helpers import create_diamond_dependency
from .test_helpers import create_linear_chain
from .test_helpers import create_parallel_batches
from .test_helpers import create_stub_project
from .test_helpers import get_execution_wave
from .test_helpers import mark_task_completed
from .test_helpers import simulate_execution
from .test_helpers import validate_project_structure


class TestStubProjectGeneration:
    def test_flat_sequential_project(self):
        project = create_stub_project(depth=0, breadth=5, dependency_type="sequential")

        assert len(project.tasks) == 5

        result = validate_project_structure(project)
        assert result["is_valid"]
        assert result["metrics"]["total_tasks"] == 5
        assert result["metrics"]["root_tasks"] == 5

        assert count_ready_tasks(project) == 1

    def test_two_level_hierarchy(self):
        project = create_stub_project(depth=1, breadth=3, dependency_type="sequential")

        assert len(project.tasks) == 6

        result = validate_project_structure(project)
        assert result["is_valid"]
        assert result["metrics"]["total_tasks"] == 6
        assert result["metrics"]["root_tasks"] == 3

    def test_independent_tasks(self):
        project = create_stub_project(depth=0, breadth=10, add_dependencies=False)

        assert len(project.tasks) == 10

        ready_count = count_ready_tasks(project)
        assert ready_count == 10

    def test_linear_chain(self):
        project = create_linear_chain(length=5)

        assert len(project.tasks) == 5

        for i in range(4):
            task = project.tasks[f"t{i + 1}"]
            assert task.depends_on == [f"t{i}"]

        assert count_ready_tasks(project) == 1

    def test_diamond_dependency(self):
        project = create_diamond_dependency()

        assert len(project.tasks) == 4

        result = validate_project_structure(project)
        assert result["is_valid"]

        wave1 = get_execution_wave(project)
        assert wave1 == ["t1"]

        mark_task_completed(project, "t1")
        wave2 = get_execution_wave(project)
        assert set(wave2) == {"t2", "t3"}

        mark_task_completed(project, "t2")
        mark_task_completed(project, "t3")
        wave3 = get_execution_wave(project)
        assert wave3 == ["t4"]

    def test_parallel_batches(self):
        project = create_parallel_batches(num_batches=3, batch_size=4)

        assert len(project.tasks) == 12

        result = validate_project_structure(project)
        assert result["is_valid"]

        stats = simulate_execution(project)
        assert stats["total_waves"] == 3
        assert stats["max_parallel"] == 4

    def test_complex_graph_structure(self):
        project = create_complex_graph(num_levels=4, tasks_per_level=5, interconnect_ratio=0.5)

        assert len(project.tasks) == 20

        result = validate_project_structure(project)
        assert result["is_valid"]


class TestDependencyResolution:
    def test_sequential_execution_order(self):
        project = create_linear_chain(length=5)

        stats = simulate_execution(project)

        assert stats["total_waves"] == 5
        assert stats["max_parallel"] == 1

        all_completed = all(t.state == TaskState.COMPLETED for t in project.tasks.values())
        assert all_completed

    def test_parallel_execution_waves(self):
        project = create_diamond_dependency()

        stats = simulate_execution(project)

        assert stats["total_waves"] == 3
        assert stats["max_parallel"] == 2

    def test_dependencies_block_execution(self):
        project = create_linear_chain(length=3)

        wave1 = get_execution_wave(project)
        assert wave1 == ["t0"]

        wave_before_completion = get_execution_wave(project)
        assert wave_before_completion == ["t0"]

        mark_task_completed(project, "t0")

        wave2 = get_execution_wave(project)
        assert wave2 == ["t1"]

    def test_multi_dependency_task(self):
        project = Project(id="test", name="Multi-dep")
        from amplifier.planner import Task

        t1 = Task(id="t1", title="Task 1", description="")
        t2 = Task(id="t2", title="Task 2", description="")
        t3 = Task(id="t3", title="Task 3", description="", depends_on=["t1", "t2"])

        project.add_task(t1)
        project.add_task(t2)
        project.add_task(t3)

        wave1 = get_execution_wave(project)
        assert set(wave1) == {"t1", "t2"}

        mark_task_completed(project, "t1")
        wave2 = get_execution_wave(project)
        assert wave2 == ["t2"]

        mark_task_completed(project, "t2")
        wave3 = get_execution_wave(project)
        assert wave3 == ["t3"]


@pytest.mark.asyncio
class TestOrchestrationWithStubs:
    async def test_empty_project_execution(self):
        project = Project(id="empty", name="Empty")

        results = await orchestrate_execution(project)

        assert results.status == "completed"
        assert results.total_tasks == 0
        assert results.completed_tasks == 0

    async def test_small_stub_execution(self):
        project = create_stub_project(depth=1, breadth=3, dependency_type="independent")

        results = await orchestrate_execution(project, max_parallel=5)

        assert results.status == "completed"
        assert results.completed_tasks == len(project.tasks)
        assert results.failed_tasks == 0

    async def test_sequential_stub_execution(self):
        project = create_linear_chain(length=5)

        results = await orchestrate_execution(project)

        assert results.status == "completed"
        assert results.completed_tasks == 5

        for task in project.tasks.values():
            assert task.state == TaskState.COMPLETED

    async def test_diamond_stub_execution(self):
        project = create_diamond_dependency()

        results = await orchestrate_execution(project, max_parallel=2)

        assert results.status == "completed"
        assert results.completed_tasks == 4

        task1_result = results.task_results["t1"]
        task2_result = results.task_results["t2"]
        task3_result = results.task_results["t3"]
        task4_result = results.task_results["t4"]

        assert task1_result.completed_at is not None
        assert task2_result.completed_at is not None
        assert task3_result.completed_at is not None
        assert task4_result.completed_at is not None

        assert task1_result.completed_at < task2_result.started_at
        assert task1_result.completed_at < task3_result.started_at
        assert task2_result.completed_at < task4_result.started_at
        assert task3_result.completed_at < task4_result.started_at

    async def test_large_parallel_batches(self):
        project = create_parallel_batches(num_batches=5, batch_size=10)

        results = await orchestrate_execution(project, max_parallel=10)

        assert results.status == "completed"
        assert results.completed_tasks == 50
        assert results.failed_tasks == 0


class TestProjectValidation:
    def test_valid_project_structure(self):
        project = create_stub_project(depth=2, breadth=3)

        result = validate_project_structure(project)

        assert result["is_valid"]
        assert len(result["errors"]) == 0

    def test_invalid_parent_reference(self):
        project = create_stub_project(depth=1, breadth=2)
        from amplifier.planner import Task

        invalid_task = Task(id="bad", title="Bad Task", description="", parent_id="nonexistent")
        project.add_task(invalid_task)

        result = validate_project_structure(project)

        assert not result["is_valid"]
        assert any("invalid parent_id" in error for error in result["errors"])

    def test_invalid_dependency_reference(self):
        project = create_stub_project(depth=1, breadth=2)
        from amplifier.planner import Task

        invalid_task = Task(id="bad", title="Bad Task", description="", depends_on=["nonexistent"])
        project.add_task(invalid_task)

        result = validate_project_structure(project)

        assert not result["is_valid"]
        assert any("invalid dependency" in error for error in result["errors"])

    def test_project_metrics_calculation(self):
        project = create_stub_project(depth=2, breadth=3)

        result = validate_project_structure(project)

        metrics = result["metrics"]
        assert metrics["total_tasks"] == 9
        assert metrics["root_tasks"] > 0
        assert metrics["max_depth"] >= 0


class TestExecutionWaves:
    def test_single_wave_independent_tasks(self):
        project = create_stub_project(depth=0, breadth=5, add_dependencies=False)

        wave = get_execution_wave(project)

        assert len(wave) == 5

    def test_multiple_waves_sequential(self):
        project = create_linear_chain(length=5)

        waves_executed = []

        while True:
            wave = get_execution_wave(project)
            if not wave:
                break

            waves_executed.append(len(wave))

            for task_id in wave:
                mark_task_completed(project, task_id)

        assert waves_executed == [1, 1, 1, 1, 1]

    def test_parallel_waves_diamond(self):
        project = create_diamond_dependency()

        waves_executed = []

        while True:
            wave = get_execution_wave(project)
            if not wave:
                break

            waves_executed.append(len(wave))

            for task_id in wave:
                mark_task_completed(project, task_id)

        assert waves_executed == [1, 2, 1]
