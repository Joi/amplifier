"""Test helpers for super-planner testing.

Provides utilities for generating stub projects with configurable complexity,
mocking task execution, and validating test results.
"""

import uuid
from collections.abc import Callable
from typing import Any

from amplifier.planner import Project
from amplifier.planner import Task
from amplifier.planner import TaskState


def create_stub_project(
    depth: int,
    breadth: int,
    add_dependencies: bool = True,
    dependency_type: str = "sequential",
    name_prefix: str = "Stub",
) -> Project:
    """Generate a stub project for testing.

    Args:
        depth: Number of hierarchy levels (0 = flat, 1+ = nested)
        breadth: Number of tasks per level
        add_dependencies: Whether to add dependencies between tasks
        dependency_type: Type of dependencies to create:
            - "sequential": Each task depends on previous (t1 -> t2 -> t3)
            - "fan_out": Root task fans out to all children (t1 -> t2,t3,t4)
            - "fan_in": All children converge to one task (t2,t3,t4 -> t5)
            - "diamond": Diamond pattern (t1 -> t2,t3 -> t4)
            - "independent": No dependencies (max parallelism)
        name_prefix: Prefix for project name

    Returns:
        Project with generated task hierarchy

    Examples:
        >>> # Simple flat project with 5 sequential tasks
        >>> project = create_stub_project(depth=0, breadth=5)
        >>> len(project.tasks)
        5

        >>> # Two-level hierarchy with 3 tasks per level
        >>> project = create_stub_project(depth=2, breadth=3)
        >>> len(project.tasks)
        12  # 3 + 9

        >>> # Independent tasks (max parallelism)
        >>> project = create_stub_project(depth=1, breadth=10, dependency_type="independent")
        >>> ready = [t for t in project.tasks.values() if t.can_start(set())]
        >>> len(ready)
        10
    """
    project_id = str(uuid.uuid4())
    project = Project(id=project_id, name=f"{name_prefix} Project {depth}x{breadth}")

    all_tasks = []
    task_counter = [0]

    def create_level(level: int, parent_id: str | None = None) -> list[Task]:
        """Recursively create tasks at each level."""
        if level > depth:
            return []

        level_tasks = []
        previous_task_id = None

        for i in range(breadth):
            task_num = task_counter[0]
            task_counter[0] += 1

            task_id = f"L{level}-T{i}"
            task = Task(
                id=task_id,
                title=f"Level {level} Task {i}",
                description=f"Test task #{task_num} at depth {level}, position {i}",
                state=TaskState.PENDING,
                parent_id=parent_id,
                depends_on=[],
            )

            if add_dependencies and previous_task_id and dependency_type == "sequential":
                task.depends_on = [previous_task_id]

            level_tasks.append(task)
            all_tasks.append(task)

            if level < depth:
                children = create_level(level + 1, task_id)
                level_tasks.extend(children)

                if add_dependencies and dependency_type == "fan_in" and children:
                    last_child_id = children[0].id if children else None
                    if last_child_id:
                        for child in children[1:]:
                            if last_child_id not in child.depends_on:
                                child.depends_on.append(last_child_id)

            if add_dependencies:
                previous_task_id = task_id

        return level_tasks

    create_level(0)

    if add_dependencies and dependency_type == "diamond" and len(all_tasks) >= 4:
        root = all_tasks[0]
        branch_a = all_tasks[1]
        branch_b = all_tasks[2]
        join = all_tasks[3]

        branch_a.depends_on = [root.id]
        branch_b.depends_on = [root.id]
        join.depends_on = [branch_a.id, branch_b.id]

    for task in all_tasks:
        project.add_task(task)

    return project


def create_linear_chain(length: int, name: str = "Linear Chain") -> Project:
    """Create project with linear task chain.

    Creates: t1 -> t2 -> t3 -> ... -> tN

    Args:
        length: Number of tasks in chain
        name: Project name

    Returns:
        Project with linear dependency chain

    Example:
        >>> project = create_linear_chain(5)
        >>> len(project.tasks)
        5
        >>> project.tasks["t4"].depends_on
        ['t3']
    """
    project = Project(id=str(uuid.uuid4()), name=name)
    previous_id = None

    for i in range(length):
        task = Task(
            id=f"t{i}",
            title=f"Task {i}",
            description=f"Step {i} in linear chain",
            depends_on=[previous_id] if previous_id else [],
        )
        project.add_task(task)
        previous_id = task.id

    return project


def create_diamond_dependency(name: str = "Diamond Dependency") -> Project:
    """Create diamond-shaped dependency graph.

    Creates:
        t1
       /  \
      t2  t3
       \\  /
        t4

    Args:
        name: Project name

    Returns:
        Project with diamond dependency pattern

    Example:
        >>> project = create_diamond_dependency()
        >>> project.tasks["t4"].depends_on
        ['t2', 't3']
    """
    project = Project(id=str(uuid.uuid4()), name=name)

    t1 = Task(id="t1", title="Root Task", description="Starting point")
    t2 = Task(id="t2", title="Branch A", description="Left branch", depends_on=["t1"])
    t3 = Task(id="t3", title="Branch B", description="Right branch", depends_on=["t1"])
    t4 = Task(id="t4", title="Join Task", description="Convergence point", depends_on=["t2", "t3"])

    for task in [t1, t2, t3, t4]:
        project.add_task(task)

    return project


def create_parallel_batches(num_batches: int, batch_size: int, name: str = "Parallel Batches") -> Project:
    """Create project with parallel batches of tasks.

    Each batch runs in parallel, but batches are sequential.

    Creates:
        Batch 0: t0, t1, t2 (parallel)
        Batch 1: t3, t4, t5 (depends on all of batch 0)
        Batch 2: t6, t7, t8 (depends on all of batch 1)

    Args:
        num_batches: Number of sequential batches
        batch_size: Number of parallel tasks per batch
        name: Project name

    Returns:
        Project with parallel batch structure

    Example:
        >>> project = create_parallel_batches(3, 4)
        >>> len(project.tasks)
        12
        >>> # Batch 1 depends on all of batch 0
        >>> project.tasks["t4"].depends_on
        ['t0', 't1', 't2', 't3']
    """
    project = Project(id=str(uuid.uuid4()), name=name)
    task_counter = 0
    previous_batch = []

    for batch_num in range(num_batches):
        current_batch = []

        for i in range(batch_size):
            task_id = f"t{task_counter}"
            task = Task(
                id=task_id,
                title=f"Batch {batch_num} Task {i}",
                description=f"Task {i} in batch {batch_num}",
                depends_on=previous_batch.copy() if previous_batch else [],
            )
            project.add_task(task)
            current_batch.append(task_id)
            task_counter += 1

        previous_batch = current_batch

    return project


def create_complex_graph(
    num_levels: int, tasks_per_level: int, interconnect_ratio: float = 0.3, name: str = "Complex Graph"
) -> Project:
    """Create complex dependency graph with cross-level dependencies.

    Args:
        num_levels: Number of levels in graph
        tasks_per_level: Tasks at each level
        interconnect_ratio: Ratio of cross-level dependencies (0.0 to 1.0)
        name: Project name

    Returns:
        Project with complex dependency structure

    Example:
        >>> project = create_complex_graph(4, 5, interconnect_ratio=0.5)
        >>> len(project.tasks)
        20
    """
    import random

    project = Project(id=str(uuid.uuid4()), name=name)
    levels = []

    for level in range(num_levels):
        level_tasks = []

        for i in range(tasks_per_level):
            task_id = f"L{level}T{i}"
            task = Task(
                id=task_id,
                title=f"Level {level} Task {i}",
                description=f"Complex task at level {level}",
                depends_on=[],
            )

            if level > 0:
                previous_level = levels[level - 1]
                num_deps = max(1, int(len(previous_level) * interconnect_ratio))
                dependencies = random.sample(previous_level, min(num_deps, len(previous_level)))
                task.depends_on = [t.id for t in dependencies]

            project.add_task(task)
            level_tasks.append(task)

        levels.append(level_tasks)

    return project


def count_ready_tasks(project: Project) -> int:
    """Count tasks ready to execute (dependencies met, state pending).

    Args:
        project: Project to analyze

    Returns:
        Number of tasks ready to start

    Example:
        >>> project = create_linear_chain(5)
        >>> count_ready_tasks(project)
        1  # Only first task is ready
    """
    completed_ids = {tid for tid, task in project.tasks.items() if task.state == TaskState.COMPLETED}

    ready = [
        task for task in project.tasks.values() if task.state == TaskState.PENDING and task.can_start(completed_ids)
    ]

    return len(ready)


def mark_task_completed(project: Project, task_id: str) -> None:
    """Mark a task as completed and update its timestamp.

    Args:
        project: Project containing the task
        task_id: ID of task to mark completed

    Example:
        >>> project = create_linear_chain(3)
        >>> mark_task_completed(project, "t0")
        >>> project.tasks["t0"].state
        <TaskState.COMPLETED: 'completed'>
        >>> count_ready_tasks(project)
        1  # t1 is now ready
    """
    from datetime import datetime

    task = project.tasks[task_id]
    task.state = TaskState.COMPLETED
    task.updated_at = datetime.now()


def get_execution_wave(project: Project) -> list[str]:
    """Get the next wave of tasks that can execute in parallel.

    Returns task IDs that have all dependencies met.

    Args:
        project: Project to analyze

    Returns:
        List of task IDs ready to execute

    Example:
        >>> project = create_diamond_dependency()
        >>> wave1 = get_execution_wave(project)
        >>> wave1
        ['t1']
        >>> mark_task_completed(project, 't1')
        >>> wave2 = get_execution_wave(project)
        >>> set(wave2)
        {'t2', 't3'}
    """
    completed_ids = {tid for tid, task in project.tasks.items() if task.state == TaskState.COMPLETED}

    ready = [
        task.id for task in project.tasks.values() if task.state == TaskState.PENDING and task.can_start(completed_ids)
    ]

    return ready


def simulate_execution(project: Project, task_modifier: Callable[[Task], None] | None = None) -> dict[str, int]:
    """Simulate complete execution of project, tracking execution waves.

    Args:
        project: Project to simulate
        task_modifier: Optional function called on each task before marking completed

    Returns:
        Dictionary with execution statistics:
            - total_waves: Number of execution waves
            - max_parallel: Maximum tasks in any single wave
            - total_tasks: Total tasks executed

    Example:
        >>> project = create_diamond_dependency()
        >>> stats = simulate_execution(project)
        >>> stats['total_waves']
        3  # Wave 1: t1, Wave 2: t2+t3, Wave 3: t4
        >>> stats['max_parallel']
        2  # t2 and t3 in parallel
    """
    waves = []
    wave_num = 0

    while True:
        ready = get_execution_wave(project)

        if not ready:
            break

        waves.append(len(ready))

        for task_id in ready:
            task = project.tasks[task_id]
            if task_modifier:
                task_modifier(task)
            mark_task_completed(project, task_id)

        wave_num += 1

    return {
        "total_waves": wave_num,
        "max_parallel": max(waves) if waves else 0,
        "total_tasks": len(project.tasks),
    }


def validate_project_structure(project: Project) -> dict[str, Any]:
    """Validate project structure and return metrics.

    Args:
        project: Project to validate

    Returns:
        Dictionary with validation results:
            - is_valid: Whether structure is valid
            - errors: List of validation errors
            - metrics: Project metrics

    Example:
        >>> project = create_stub_project(2, 3)
        >>> result = validate_project_structure(project)
        >>> result['is_valid']
        True
        >>> result['metrics']['total_tasks']
        12
    """
    errors = []

    for task_id, task in project.tasks.items():
        if task.parent_id and task.parent_id not in project.tasks:
            errors.append(f"Task {task_id} has invalid parent_id: {task.parent_id}")

        for dep_id in task.depends_on:
            if dep_id not in project.tasks:
                errors.append(f"Task {task_id} has invalid dependency: {dep_id}")

    has_cycles = _detect_cycles(project)
    if has_cycles:
        errors.append("Project has circular dependencies")

    roots = project.get_roots()
    leaves = [t for t in project.tasks.values() if not project.get_children(t.id)]

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "metrics": {
            "total_tasks": len(project.tasks),
            "root_tasks": len(roots),
            "leaf_tasks": len(leaves),
            "max_depth": _calculate_max_depth(project),
            "avg_dependencies": sum(len(t.depends_on) for t in project.tasks.values()) / len(project.tasks)
            if project.tasks
            else 0,
        },
    }


def _detect_cycles(project: Project) -> bool:
    """Detect circular dependencies using DFS."""
    visited = set()
    rec_stack = set()

    def has_cycle(task_id: str) -> bool:
        visited.add(task_id)
        rec_stack.add(task_id)

        task = project.tasks.get(task_id)
        if not task:
            return False

        for dep_id in task.depends_on:
            if dep_id not in visited:
                if has_cycle(dep_id):
                    return True
            elif dep_id in rec_stack:
                return True

        rec_stack.remove(task_id)
        return False

    return any(task_id not in visited and has_cycle(task_id) for task_id in project.tasks)


def _calculate_max_depth(project: Project) -> int:
    """Calculate maximum depth of task hierarchy."""

    def get_depth(task_id: str, memo: dict) -> int:
        if task_id in memo:
            return memo[task_id]

        task = project.tasks.get(task_id)
        if not task:
            return 0

        children = project.get_children(task_id)
        if not children:
            depth = 0
        else:
            depth = 1 + max(get_depth(child.id, memo) for child in children)

        memo[task_id] = depth
        return depth

    if not project.tasks:
        return 0

    memo = {}
    roots = project.get_roots()
    return max(get_depth(root.id, memo) for root in roots) if roots else 0
