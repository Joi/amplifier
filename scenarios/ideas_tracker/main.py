#!/usr/bin/env python3
"""
Ideas Tracker - Main CLI and orchestrator

Manages ideas and projects across amplifier branches with auto-syncing data repository.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


class IdeasDataManager:
    """Manages the ideas data repository and local storage."""

    def __init__(self):
        self.home_dir = Path.home()
        self.data_dir = self.home_dir / "amplifier-ideas-data"
        self.repo_url = "git@github.com:ramparte/amplifier-ideas-data.git"

    def ensure_data_repo(self) -> bool:
        """Ensure the ideas data repository is available locally."""
        if self.data_dir.exists():
            logger.debug(f"Ideas data directory exists at {self.data_dir}")
            return True

        logger.info(f"Ideas data repository not found. Cloning from {self.repo_url}...")
        try:
            result = subprocess.run(
                ["git", "clone", self.repo_url, str(self.data_dir)], capture_output=True, text=True, check=True
            )
            logger.info("Successfully cloned ideas data repository")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone ideas repository: {e.stderr}")
            logger.info(
                "You may need to create the repository first at https://github.com/ramparte/amplifier-ideas-data"
            )
            return False

    def get_projects_dir(self) -> Path:
        """Get the projects directory, creating if needed."""
        projects_dir = self.data_dir / "projects"
        projects_dir.mkdir(exist_ok=True)
        return projects_dir

    def get_project_file(self, project_name: str) -> Path:
        """Get the path to a project's JSON file."""
        return self.get_projects_dir() / f"{project_name}.json"

    def load_project(self, project_name: str) -> dict[str, Any] | None:
        """Load a project's data."""
        project_file = self.get_project_file(project_name)
        if not project_file.exists():
            return None
        try:
            with open(project_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load project {project_name}: {e}")
            return None

    def save_project(self, project_name: str, project_data: dict[str, Any]) -> bool:
        """Save a project's data."""
        project_file = self.get_project_file(project_name)
        try:
            with open(project_file, "w") as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved project {project_name}")
            return True
        except OSError as e:
            logger.error(f"Failed to save project {project_name}: {e}")
            return False

    def list_projects(self) -> list[str]:
        """List all available projects."""
        projects_dir = self.get_projects_dir()
        return [f.stem for f in projects_dir.glob("*.json")]


class BranchContextDetector:
    """Detects current git branch and amplifier project context."""

    def __init__(self):
        self.cwd = Path.cwd()

    def get_current_branch(self) -> str | None:
        """Get the current git branch."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"], capture_output=True, text=True, check=True, cwd=self.cwd
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def get_repo_info(self) -> dict[str, str | None]:
        """Get repository information."""
        try:
            # Get remote origin URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True, cwd=self.cwd
            )
            origin_url = result.stdout.strip()

            # Extract repo name from URL
            repo_name = None
            if origin_url:
                if origin_url.endswith(".git"):
                    origin_url = origin_url[:-4]
                repo_name = origin_url.split("/")[-1]

            return {
                "branch": self.get_current_branch(),
                "origin_url": origin_url,
                "repo_name": repo_name,
                "working_directory": str(self.cwd),
            }
        except subprocess.CalledProcessError:
            return {"branch": None, "origin_url": None, "repo_name": None, "working_directory": str(self.cwd)}


class IdeasTracker:
    """Main ideas tracker functionality."""

    def __init__(self):
        self.data_manager = IdeasDataManager()
        self.context_detector = BranchContextDetector()

    def ensure_setup(self) -> bool:
        """Ensure the ideas tracker is properly set up."""
        return self.data_manager.ensure_data_repo()

    def create_project(self, project_name: str) -> bool:
        """Create a new project."""
        if self.data_manager.load_project(project_name):
            logger.error(f"Project '{project_name}' already exists")
            return False

        context = self.context_detector.get_repo_info()
        project_data = {
            "name": project_name,
            "created_at": datetime.now().isoformat(),
            "created_in_branch": context.get("branch"),
            "created_in_repo": context.get("repo_name"),
            "ideas": [],
            "metadata": {"tags": [], "status": "active"},
        }

        if self.data_manager.save_project(project_name, project_data):
            logger.info(f"Created project '{project_name}'")
            return True
        return False

    def add_idea(self, project_name: str, idea_text: str) -> bool:
        """Add an idea to a project."""
        project_data = self.data_manager.load_project(project_name)
        if not project_data:
            logger.error(f"Project '{project_name}' not found")
            return False

        context = self.context_detector.get_repo_info()
        idea = {
            "text": idea_text,
            "added_at": datetime.now().isoformat(),
            "added_in_branch": context.get("branch"),
            "added_in_repo": context.get("repo_name"),
        }

        project_data["ideas"].append(idea)

        if self.data_manager.save_project(project_name, project_data):
            logger.info(f"Added idea to '{project_name}': {idea_text}")
            return True
        return False

    def list_projects(self) -> None:
        """List all projects and recent ideas."""
        projects = self.data_manager.list_projects()
        if not projects:
            click.echo("No projects found. Create one with: /ideas new PROJECT_NAME")
            return

        click.echo(f"Found {len(projects)} project(s):\n")

        for project_name in sorted(projects):
            project_data = self.data_manager.load_project(project_name)
            if not project_data:
                continue

            ideas_count = len(project_data.get("ideas", []))
            status = project_data.get("metadata", {}).get("status", "active")

            click.echo(f"📋 {project_name}")
            click.echo(f"   Status: {status}")
            click.echo(f"   Ideas: {ideas_count}")

            # Show recent ideas (max 3)
            recent_ideas = project_data.get("ideas", [])[-3:]
            if recent_ideas:
                click.echo("   Recent ideas:")
                for idea in recent_ideas:
                    text = idea["text"]
                    if len(text) > 60:
                        text = text[:57] + "..."
                    click.echo(f"   • {text}")
            click.echo()

    def show_project(self, project_name: str) -> None:
        """Show detailed information about a project."""
        project_data = self.data_manager.load_project(project_name)
        if not project_data:
            click.echo(f"Project '{project_name}' not found")
            return

        click.echo(f"📋 Project: {project_name}")
        click.echo(f"Created: {project_data.get('created_at', 'Unknown')}")

        if project_data.get("created_in_branch"):
            click.echo(f"Created in branch: {project_data['created_in_branch']}")

        ideas = project_data.get("ideas", [])
        click.echo(f"Ideas ({len(ideas)}):")

        if not ideas:
            click.echo('  No ideas yet. Add one with: /ideas add PROJECT_NAME "your idea"')
        else:
            for i, idea in enumerate(ideas, 1):
                click.echo(f"\n  {i}. {idea['text']}")
                click.echo(f"     Added: {idea['added_at']}")
                if idea.get("added_in_branch"):
                    click.echo(f"     Branch: {idea['added_in_branch']}")

    def show_context(self) -> None:
        """Show current branch and project context."""
        context = self.context_detector.get_repo_info()

        click.echo("🔍 Current Context:")
        click.echo(f"Working directory: {context['working_directory']}")
        click.echo(f"Repository: {context.get('repo_name', 'Unknown')}")
        click.echo(f"Branch: {context.get('branch', 'Unknown')}")

        if context.get("origin_url"):
            click.echo(f"Origin URL: {context['origin_url']}")

    def sync_data(self) -> None:
        """Sync changes with the remote repository."""
        if not self.data_manager.data_dir.exists():
            click.echo("Ideas data repository not found. Nothing to sync.")
            return

        try:
            # Add all changes
            subprocess.run(["git", "add", "."], check=True, cwd=self.data_manager.data_dir)

            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=self.data_manager.data_dir
            )

            if not result.stdout.strip():
                click.echo("No changes to sync.")
                return

            # Commit changes
            context = self.context_detector.get_repo_info()
            commit_message = f"Update ideas from {context.get('branch', 'unknown-branch')}"

            subprocess.run(["git", "commit", "-m", commit_message], check=True, cwd=self.data_manager.data_dir)

            # Push changes
            subprocess.run(["git", "push"], check=True, cwd=self.data_manager.data_dir)

            click.echo("✅ Successfully synced changes to GitHub")

        except subprocess.CalledProcessError as e:
            click.echo(f"❌ Failed to sync: {e}")


@click.command()
@click.argument("command", default="list")
@click.argument("args", nargs=-1)
def main(command: str, args: tuple) -> None:
    """Ideas Tracker - Cross-branch project and ideas management.

    Available commands:
    - list: List all projects and recent ideas
    - new PROJECT_NAME: Create a new project
    - add PROJECT_NAME "idea text": Add idea to project
    - show PROJECT_NAME: Show project details
    - context: Show current branch context
    - sync: Sync with GitHub repository
    """
    tracker = IdeasTracker()

    # Ensure setup first
    if not tracker.ensure_setup():
        click.echo("❌ Failed to set up ideas tracker")
        sys.exit(1)

    try:
        if command == "list":
            tracker.list_projects()

        elif command == "new":
            if not args:
                click.echo("Error: Please provide a project name")
                click.echo("Usage: /ideas new PROJECT_NAME")
                sys.exit(1)
            tracker.create_project(args[0])

        elif command == "add":
            if len(args) < 2:
                click.echo("Error: Please provide project name and idea text")
                click.echo('Usage: /ideas add PROJECT_NAME "idea text"')
                sys.exit(1)
            tracker.add_idea(args[0], args[1])

        elif command == "show":
            if not args:
                click.echo("Error: Please provide a project name")
                click.echo("Usage: /ideas show PROJECT_NAME")
                sys.exit(1)
            tracker.show_project(args[0])

        elif command == "context":
            tracker.show_context()

        elif command == "sync":
            tracker.sync_data()

        else:
            click.echo(f"Unknown command: {command}")
            click.echo("Available commands: list, new, add, show, context, sync")
            sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\nOperation cancelled.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        click.echo(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
