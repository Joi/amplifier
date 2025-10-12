"""Tests for hierarchical/recursive orchestration functionality."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from amplifier.planner.models import Project
from amplifier.planner.models import Task
from amplifier.planner.models import TaskState
from amplifier.planner.orchestrator import orchestrate_execution


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for test projects."""
    data_dir = tmp_path / "data" / "planner" / "projects"
    data_dir.mkdir(parents=True)

    # Patch the _load_project function to use our temp directory
    original_load_project = None

    def setup():
        nonlocal original_load_project
        from amplifier.planner import orchestrator

        original_load_project = orchestrator._load_project

        def patched_load_project(project_id):
            """Load from temp directory instead of standard location."""
            project_file = data_dir / f"{project_id}.json"
            if not project_file.exists():
                raise FileNotFoundError(f"Sub-project not found: {project_id}")

            with open(project_file) as f:
                data = json.load(f)

            project = Project(
                id=data["id"],
                name=data["name"],
                created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
                updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            )

            for task_data in data.get("tasks", {}).values():
                task = Task(
                    id=task_data["id"],
                    title=task_data["title"],
                    description=task_data.get("description", ""),
                    state=TaskState[task_data.get("state", "PENDING").upper()],
                    parent_id=task_data.get("parent_id"),
                    depends_on=task_data.get("depends_on", []),
                    assigned_to=task_data.get("assigned_to"),
                    created_at=datetime.fromisoformat(task_data.get("created_at", datetime.now().isoformat())),
                    updated_at=datetime.fromisoformat(task_data.get("updated_at", datetime.now().isoformat())),
                    test_command=task_data.get("test_command"),
                    test_file=task_data.get("test_file"),
                    requires_testing=task_data.get("requires_testing", True),
                    is_parent=task_data.get("is_parent", False),
                    sub_project_id=task_data.get("sub_project_id"),
                )
                project.tasks[task.id] = task

            return project

        orchestrator._load_project = patched_load_project

    def teardown():
        if original_load_project:
            from amplifier.planner import orchestrator

            orchestrator._load_project = original_load_project

    setup()
    yield data_dir
    teardown()


def save_project(project: Project, data_dir: Path):
    """Save project to JSON file for testing."""
    project_data = {
        "id": project.id,
        "name": project.name,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "tasks": {},
    }

    for task_id, task in project.tasks.items():
        project_data["tasks"][task_id] = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "state": task.state.value,
            "parent_id": task.parent_id,
            "depends_on": task.depends_on,
            "assigned_to": task.assigned_to,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "test_command": task.test_command,
            "test_file": task.test_file,
            "requires_testing": task.requires_testing,
            "is_parent": task.is_parent,
            "sub_project_id": task.sub_project_id,
        }

    project_file = data_dir / f"{project.id}.json"
    with open(project_file, "w") as f:
        json.dump(project_data, f, indent=2)


@pytest.mark.asyncio
async def test_hierarchical_orchestration_basic(temp_data_dir):
    """Test basic hierarchical orchestration with parent and sub-projects."""
    # Create sub-project
    sub_project = Project(id="sub-proj-1", name="Sub Project 1")
    sub_project.add_task(
        Task(id="sub-task-1", title="Sub Task 1", description="First sub task", requires_testing=False)
    )
    sub_project.add_task(
        Task(
            id="sub-task-2",
            title="Sub Task 2",
            description="Second sub task",
            depends_on=["sub-task-1"],
            requires_testing=False,
        )
    )
    save_project(sub_project, temp_data_dir)

    # Create main project with parent task
    main_project = Project(id="main-proj", name="Main Project")
    main_project.add_task(
        Task(
            id="parent-task",
            title="Parent Task",
            description="Task with sub-project",
            is_parent=True,
            sub_project_id="sub-proj-1",
            requires_testing=False,
        )
    )
    main_project.add_task(
        Task(
            id="leaf-task",
            title="Leaf Task",
            description="Regular task",
            depends_on=["parent-task"],
            requires_testing=False,
        )
    )

    # Run orchestration
    results = await orchestrate_execution(main_project, max_parallel=2, max_retries=1)

    # Verify results
    assert results.status == "completed"
    assert results.completed_tasks == 2
    assert results.failed_tasks == 0

    # Check parent task completed
    assert "parent-task" in results.task_results
    assert results.task_results["parent-task"].status == "success"
    assert "Sub-project completed" in results.task_results["parent-task"].output

    # Check leaf task completed after parent
    assert "leaf-task" in results.task_results
    assert results.task_results["leaf-task"].status == "success"


@pytest.mark.asyncio
async def test_hierarchical_orchestration_with_failures(temp_data_dir):
    """Test hierarchical orchestration when sub-project tasks fail."""
    # Create sub-project with a task that will fail
    sub_project = Project(id="sub-proj-fail", name="Failing Sub Project")
    sub_project.add_task(
        Task(
            id="fail-task",
            title="Failing Task",
            description="Task that fails",
            requires_testing=True,
            test_command="exit 1",  # This will fail
        )
    )
    save_project(sub_project, temp_data_dir)

    # Create main project
    main_project = Project(id="main-fail", name="Main Project with Failures")
    main_project.add_task(
        Task(
            id="parent-fail",
            title="Parent with Failing Sub",
            is_parent=True,
            sub_project_id="sub-proj-fail",
            requires_testing=False,
        )
    )
    main_project.add_task(
        Task(id="dependent-task", title="Dependent Task", depends_on=["parent-fail"], requires_testing=False)
    )

    # Run orchestration
    results = await orchestrate_execution(main_project, max_parallel=2, max_retries=1)

    # Parent task should be marked as failed but IN_PROGRESS (not BLOCKED)
    assert "parent-fail" in results.task_results
    assert results.task_results["parent-fail"].status == "failed"
    error = results.task_results["parent-fail"].error
    assert error is not None
    assert "Sub-project incomplete" in error

    # The parent task should remain IN_PROGRESS in the project
    assert main_project.tasks["parent-fail"].state == TaskState.IN_PROGRESS

    # Dependent task should be skipped
    assert "dependent-task" in results.task_results
    assert results.task_results["dependent-task"].status == "skipped"


@pytest.mark.asyncio
async def test_hierarchical_depth_limit():
    """Test that recursion depth limit is enforced."""
    # Create a simple project
    project = Project(id="depth-test", name="Depth Test")
    project.add_task(Task(id="task1", title="Task 1", requires_testing=False))

    # Try to orchestrate with depth exceeding limit
    with pytest.raises(RecursionError) as exc_info:
        await orchestrate_execution(project, depth=4)  # max_depth is 3

    assert "exceeds maximum depth 3" in str(exc_info.value)


@pytest.mark.asyncio
async def test_nested_hierarchical_projects(temp_data_dir):
    """Test multi-level hierarchical projects (3 levels deep)."""
    # Level 3: Leaf sub-project
    leaf_project = Project(id="leaf-proj", name="Leaf Project")
    leaf_project.add_task(Task(id="leaf-1", title="Leaf Task 1", requires_testing=False))
    save_project(leaf_project, temp_data_dir)

    # Level 2: Middle sub-project with parent task
    middle_project = Project(id="middle-proj", name="Middle Project")
    middle_project.add_task(
        Task(
            id="middle-parent",
            title="Middle Parent",
            is_parent=True,
            sub_project_id="leaf-proj",
            requires_testing=False,
        )
    )
    save_project(middle_project, temp_data_dir)

    # Level 1: Main project
    main_project = Project(id="main-nested", name="Main Nested")
    main_project.add_task(
        Task(
            id="main-parent", title="Main Parent", is_parent=True, sub_project_id="middle-proj", requires_testing=False
        )
    )

    # Run orchestration - should succeed (3 levels deep)
    results = await orchestrate_execution(main_project, max_parallel=2)

    assert results.status == "completed"
    assert results.completed_tasks == 1
    assert "main-parent" in results.task_results
    assert results.task_results["main-parent"].status == "success"


@pytest.mark.asyncio
async def test_parallel_parent_tasks(temp_data_dir):
    """Test multiple parent tasks running in parallel."""
    # Create two sub-projects
    for i in range(1, 3):
        sub_project = Project(id=f"sub-parallel-{i}", name=f"Sub Parallel {i}")
        for j in range(1, 3):
            sub_project.add_task(Task(id=f"sub-{i}-task-{j}", title=f"Sub {i} Task {j}", requires_testing=False))
        save_project(sub_project, temp_data_dir)

    # Create main project with two independent parent tasks
    main_project = Project(id="main-parallel", name="Main Parallel")
    main_project.add_task(
        Task(id="parent-1", title="Parent 1", is_parent=True, sub_project_id="sub-parallel-1", requires_testing=False)
    )
    main_project.add_task(
        Task(id="parent-2", title="Parent 2", is_parent=True, sub_project_id="sub-parallel-2", requires_testing=False)
    )

    # Run orchestration with parallelism
    results = await orchestrate_execution(main_project, max_parallel=2)

    # Both parent tasks should complete
    assert results.status == "completed"
    assert results.completed_tasks == 2
    assert all(results.task_results[f"parent-{i}"].status == "success" for i in range(1, 3))


@pytest.mark.asyncio
async def test_mixed_parent_and_leaf_tasks(temp_data_dir):
    """Test project with mix of parent and leaf tasks."""
    # Create sub-project
    sub_project = Project(id="sub-mixed", name="Sub Mixed")
    sub_project.add_task(Task(id="sub-task", title="Sub Task", requires_testing=False))
    save_project(sub_project, temp_data_dir)

    # Create main project with mixed task types
    main_project = Project(id="main-mixed", name="Main Mixed")

    # Leaf task 1
    main_project.add_task(Task(id="leaf-1", title="Leaf 1", requires_testing=False))

    # Parent task (depends on leaf-1)
    main_project.add_task(
        Task(
            id="parent",
            title="Parent",
            depends_on=["leaf-1"],
            is_parent=True,
            sub_project_id="sub-mixed",
            requires_testing=False,
        )
    )

    # Leaf task 2 (depends on parent)
    main_project.add_task(Task(id="leaf-2", title="Leaf 2", depends_on=["parent"], requires_testing=False))

    # Run orchestration
    results = await orchestrate_execution(main_project, max_parallel=3)

    # All tasks should complete in order
    assert results.status == "completed"
    assert results.completed_tasks == 3

    # Verify all tasks completed
    for task_id in ["leaf-1", "parent", "leaf-2"]:
        assert results.task_results[task_id].status == "success"
