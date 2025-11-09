#!/usr/bin/env python3
"""Execute the vi-rewrite project using the super-planner orchestrator."""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.insert(0, "/workspaces/amplifier")

from amplifier.planner.models import Project
from amplifier.planner.models import Task
from amplifier.planner.models import TaskState
from amplifier.planner.orchestrator import orchestrate_execution

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_project(project_file: Path) -> Project:
    """Load project from JSON file."""
    with open(project_file) as f:
        data = json.load(f)

    project = Project(
        id=data["id"],
        name=data["name"],
        created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
        updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
    )

    # Load tasks
    for task_data in data.get("tasks", {}).values():
        # Map subproject field correctly
        sub_project_id = task_data.get("subproject")
        is_parent = bool(sub_project_id)

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
            is_parent=is_parent,
            sub_project_id=sub_project_id,
        )
        project.tasks[task.id] = task

    return project


def save_project(project: Project, project_file: Path):
    """Save project to JSON file."""
    data = {
        "id": project.id,
        "name": project.name,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "tasks": {},
    }

    for task in project.tasks.values():
        task_data = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "state": task.state.name.lower(),
            "parent_id": task.parent_id,
            "depends_on": task.depends_on,
            "assigned_to": task.assigned_to,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }

        # Add subproject if it's a parent task
        if task.is_parent and task.sub_project_id:
            task_data["subproject"] = task.sub_project_id

        data["tasks"][task.id] = task_data

    with open(project_file, "w") as f:
        json.dump(data, f, indent=2)


async def main():
    """Execute the vi-rewrite project."""
    project_file = Path("/workspaces/amplifier/data/planner/projects/vi-rewrite.json")

    logger.info("Loading vi-rewrite project...")
    project = load_project(project_file)

    logger.info(f"Project loaded: {project.name}")
    logger.info(f"Total tasks: {len(project.tasks)}")

    # Print initial task status
    for task in project.tasks.values():
        logger.info(f"  - {task.id}: {task.title} [{task.state.name}]")

    logger.info("\nStarting orchestration...")

    # Execute the project with the vi-editor directory as working directory
    results = await orchestrate_execution(
        project=project, project_dir="/workspaces/amplifier/vi-editor", max_parallel=3, max_retries=2
    )

    # Print results
    logger.info("\n" + "=" * 60)
    logger.info("ORCHESTRATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Status: {results.status}")
    logger.info(f"Completed: {results.completed_tasks}/{results.total_tasks}")
    logger.info(f"Failed: {results.failed_tasks}")
    logger.info(f"Skipped: {results.skipped_tasks}")

    # Print task results
    logger.info("\nTask Results:")
    for task_id, result in results.task_results.items():
        status_icon = "✓" if result.status == "success" else "✗"
        logger.info(f"  {status_icon} {task_id}: {result.status}")
        if result.error:
            logger.error(f"    Error: {result.error}")

    # Save updated project state
    logger.info("\nSaving project state...")
    save_project(project, project_file)

    # Return appropriate exit code
    if results.status == "completed":
        logger.info("\n✓ VI EDITOR PROJECT COMPLETED SUCCESSFULLY!")
        return 0
    logger.warning(f"\n⚠ Project execution incomplete: {results.status}")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
