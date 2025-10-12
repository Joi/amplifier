"""Simple 3-task test project for end-to-end agent integration testing.

This test creates a minimal project with 3 tasks and dependencies to verify:
- Real agent execution via Claude SDK
- Dependency ordering
- Test verification loop
- Basic orchestration flow
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from amplifier.planner.models import Project
from amplifier.planner.models import Task
from amplifier.planner.models import TaskState
from amplifier.planner.orchestrator import orchestrate_execution


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Claude Code CLI and API key - manual testing only")
async def test_simple_3_task_project():
    """Test simple 3-task project with real agent execution."""
    # Create temporary project directory
    with TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create simple Python module structure
        (project_dir / "math_utils.py").touch()
        (project_dir / "tests").mkdir()

        # Task 1: Create add function
        task1 = Task(
            id="task1-add",
            title="Create add function",
            description="Create a simple add(a, b) function in math_utils.py that returns a + b",
            state=TaskState.PENDING,
            requires_testing=False,  # No tests for this simple task
        )

        # Task 2: Create multiply function (depends on task1)
        task2 = Task(
            id="task2-multiply",
            title="Create multiply function",
            description="Create a simple multiply(a, b) function in math_utils.py that returns a * b",
            state=TaskState.PENDING,
            depends_on=["task1-add"],
            requires_testing=False,
        )

        # Task 3: Create tests (depends on task2)
        task3 = Task(
            id="task3-tests",
            title="Create tests for math functions",
            description="""Create tests/test_math_utils.py with pytest tests for add and multiply functions:
            - test_add() should test add(2, 3) == 5
            - test_multiply() should test multiply(3, 4) == 12
            Make sure to import the functions from math_utils module.""",
            state=TaskState.PENDING,
            depends_on=["task2-multiply"],
            test_command="pytest tests/test_math_utils.py -v",
            requires_testing=True,
        )

        # Create project
        project = Project(id="simple-test", name="Simple 3-Task Test")
        project.add_task(task1)
        project.add_task(task2)
        project.add_task(task3)

        # Save project to data directory for sub-project loading
        # (even though this is flat, the orchestrator expects projects in data/)
        data_dir = Path("data/planner/projects")
        data_dir.mkdir(parents=True, exist_ok=True)

        # Save project JSON
        project_file = data_dir / f"{project.id}.json"
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

        with open(project_file, "w") as f:
            json.dump(project_data, f, indent=2)

        # Execute orchestration with real agents
        print(f"\n{'=' * 60}")
        print("Starting simple 3-task project orchestration")
        print(f"Project directory: {project_dir}")
        print(f"{'=' * 60}\n")

        results = await orchestrate_execution(project, project_dir=str(project_dir), max_parallel=1, max_retries=2)

        # Print results
        print(f"\n{'=' * 60}")
        print("Orchestration Results:")
        print(f"Status: {results.status}")
        print(f"Completed: {results.completed_tasks}/{results.total_tasks}")
        print(f"Failed: {results.failed_tasks}")
        print(f"Skipped: {results.skipped_tasks}")
        print(f"{'=' * 60}\n")

        for task_id, result in results.task_results.items():
            print(f"\nTask: {task_id}")
            print(f"  Status: {result.status}")
            print(f"  Attempts: {result.attempts}")
            if result.output:
                print(f"  Output: {result.output[:200]}...")
            if result.error:
                print(f"  Error: {result.error[:200]}...")

        # Cleanup project file
        project_file.unlink()

        # Verify results
        assert results.status == "completed", f"Expected completed, got {results.status}"
        assert results.completed_tasks == 3, f"Expected 3 completed, got {results.completed_tasks}"
        assert results.failed_tasks == 0, f"Expected 0 failed, got {results.failed_tasks}"

        # Verify files were created
        assert (project_dir / "math_utils.py").exists(), "math_utils.py not created"
        assert (project_dir / "tests" / "test_math_utils.py").exists(), "test_math_utils.py not created"

        # Verify math_utils.py has content
        math_utils_content = (project_dir / "math_utils.py").read_text()
        assert "add" in math_utils_content, "add function not found in math_utils.py"
        assert "multiply" in math_utils_content, "multiply function not found in math_utils.py"

        # Verify tests file has content
        tests_content = (project_dir / "tests" / "test_math_utils.py").read_text()
        assert "test_add" in tests_content, "test_add not found in tests"
        assert "test_multiply" in tests_content, "test_multiply not found in tests"

        print("\n✓ All assertions passed!")
        print("\nThis test verified:")
        print("  - Real agent execution via Claude SDK")
        print("  - Dependency ordering (task1 → task2 → task3)")
        print("  - File creation by agents")
        print("  - Test verification loop")
        print("  - Successful orchestration completion")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_simple_3_task_project())
