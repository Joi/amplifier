"""Task and Project data models for the Super-Planner system."""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum


class TaskState(Enum):
    """Task states for workflow management."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class Task:
    """Task with hierarchical structure and dependencies."""

    id: str
    title: str
    description: str = ""
    state: TaskState = TaskState.PENDING
    parent_id: str | None = None
    depends_on: list[str] = field(default_factory=list)
    assigned_to: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def can_start(self, completed_ids: set[str]) -> bool:
        """Check if task can start based on dependency completion."""
        if not self.depends_on:
            return True
        return all(dep_id in completed_ids for dep_id in self.depends_on)


@dataclass
class Project:
    """Project container for hierarchical tasks."""

    id: str
    name: str
    tasks: dict[str, Task] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_task(self, task: Task) -> None:
        """Add task to project and update timestamp."""
        self.tasks[task.id] = task
        self.updated_at = datetime.now()

    def get_roots(self) -> list[Task]:
        """Get all root tasks (no parent)."""
        return [task for task in self.tasks.values() if task.parent_id is None]

    def get_children(self, parent_id: str) -> list[Task]:
        """Get direct children of a task."""
        return [task for task in self.tasks.values() if task.parent_id == parent_id]

    def detect_dependency_cycles(self) -> list[list[str]]:
        """Detect circular dependencies in the task graph using DFS.

        Returns:
            List of cycles, where each cycle is a list of task IDs forming a loop.
            Empty list if no cycles detected.
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(task_id: str) -> None:
            """DFS to detect cycles."""
            if task_id not in self.tasks:
                return

            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)

            task = self.tasks[task_id]
            for dep_id in task.depends_on:
                if dep_id not in visited:
                    dfs(dep_id)
                elif dep_id in rec_stack:
                    # Found a cycle - extract it from path
                    cycle_start = path.index(dep_id)
                    cycle = path[cycle_start:] + [dep_id]

                    # Normalize cycle to start with smallest ID (for deduplication)
                    min_id = min(cycle[:-1])  # Exclude last duplicate
                    min_idx = cycle.index(min_id)
                    normalized = cycle[min_idx:-1] + cycle[:min_idx]

                    # Only add if not already found
                    if normalized not in cycles:
                        cycles.append(normalized)

            path.pop()
            rec_stack.remove(task_id)

        # Run DFS from each unvisited node
        for task_id in self.tasks:
            if task_id not in visited:
                dfs(task_id)

        return cycles

    def validate_dependencies(self) -> tuple[bool, list[str]]:
        """Validate that all dependencies are valid.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check for circular dependencies
        cycles = self.detect_dependency_cycles()
        if cycles:
            for cycle in cycles:
                cycle_str = " -> ".join(cycle + [cycle[0]])
                errors.append(f"Circular dependency detected: {cycle_str}")

        # Check for missing dependencies
        for task_id, task in self.tasks.items():
            for dep_id in task.depends_on:
                if dep_id not in self.tasks:
                    errors.append(f"Task '{task_id}' depends on non-existent task '{dep_id}'")

        return (len(errors) == 0, errors)
