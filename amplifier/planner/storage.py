"""JSON storage operations for Super-Planner."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from amplifier.planner.models import Project
from amplifier.planner.models import Task
from amplifier.planner.models import TaskState
from amplifier.utils.file_io import read_json
from amplifier.utils.file_io import write_json


@dataclass
class ProjectSummary:
    """Summary information about a project."""

    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    pending_tasks: int


def get_project_path(project_id: str) -> Path:
    """Get the storage path for a project."""
    base = Path("data/planner/projects")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{project_id}.json"


def save_project(project: Project) -> None:
    """Save project to JSON file."""
    data = {
        "id": project.id,
        "name": project.name,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "tasks": {
            task_id: {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "state": task.state.value,
                "parent_id": task.parent_id,
                "depends_on": task.depends_on,
                "assigned_to": task.assigned_to,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }
            for task_id, task in project.tasks.items()
        },
    }
    write_json(data, get_project_path(project.id))


def load_project(project_id: str) -> Project:
    """Load project from JSON file."""
    data = read_json(get_project_path(project_id))

    # Reconstruct tasks with proper TaskState enum
    tasks = {}
    for task_id, task_data in data.get("tasks", {}).items():
        tasks[task_id] = Task(
            id=task_data["id"],
            title=task_data["title"],
            description=task_data["description"],
            state=TaskState(task_data["state"]),
            parent_id=task_data["parent_id"],
            depends_on=task_data["depends_on"],
            assigned_to=task_data["assigned_to"],
            created_at=datetime.fromisoformat(task_data["created_at"]),
            updated_at=datetime.fromisoformat(task_data["updated_at"]),
        )

    return Project(
        id=data["id"],
        name=data["name"],
        tasks=tasks,
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )


def list_projects() -> list[ProjectSummary]:
    """List all projects with summary information.

    Returns:
        List of ProjectSummary objects sorted by most recently updated first
    """
    base = Path("data/planner/projects")
    if not base.exists():
        return []

    summaries = []
    for project_file in base.glob("*.json"):
        try:
            data = read_json(project_file)

            # Count tasks by state
            tasks = data.get("tasks", {})
            total_tasks = len(tasks)
            completed = sum(1 for t in tasks.values() if t["state"] == TaskState.COMPLETED.value)
            in_progress = sum(1 for t in tasks.values() if t["state"] == TaskState.IN_PROGRESS.value)
            blocked = sum(1 for t in tasks.values() if t["state"] == TaskState.BLOCKED.value)
            pending = sum(1 for t in tasks.values() if t["state"] == TaskState.PENDING.value)

            summary = ProjectSummary(
                id=data["id"],
                name=data["name"],
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
                total_tasks=total_tasks,
                completed_tasks=completed,
                in_progress_tasks=in_progress,
                blocked_tasks=blocked,
                pending_tasks=pending,
            )
            summaries.append(summary)

        except Exception:
            # Skip invalid/corrupt project files
            continue

    # Sort by most recently updated first
    summaries.sort(key=lambda s: s.updated_at, reverse=True)
    return summaries


def get_most_recent_project() -> str | None:
    """Get the ID of the most recently updated project.

    Returns:
        Project ID of most recent project, or None if no projects exist
    """
    summaries = list_projects()
    return summaries[0].id if summaries else None


def find_project_by_name(name: str, exact: bool = False) -> list[ProjectSummary]:
    """Find projects by name.

    Args:
        name: Project name to search for
        exact: If True, require exact match (case-insensitive). If False, match substring.

    Returns:
        List of matching ProjectSummary objects sorted by most recent first
    """
    summaries = list_projects()
    name_lower = name.lower()

    if exact:
        matches = [s for s in summaries if s.name.lower() == name_lower]
    else:
        matches = [s for s in summaries if name_lower in s.name.lower()]

    return matches
