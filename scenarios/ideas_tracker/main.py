#!/usr/bin/env python3
"""
Ideas Tracker - Main CLI and orchestrator

Manages ideas and projects across amplifier branches with auto-syncing data repository.
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from pydantic import BaseModel
from pydantic_ai import Agent

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


class CommandIntent(BaseModel):
    """Structured representation of user intent."""

    action: str  # search, create, update, list, show, etc.
    target: str | None = None  # project name if specified
    query: str | None = None  # search text or content
    metadata: dict[str, Any] = {}  # additional context


class SessionContext(BaseModel):
    """Current session context for smart operations."""

    branch: str | None = None
    repo: str | None = None
    working_directory: str = ""
    recent_commands: list[str] = []
    session_summary: str | None = None


class NaturalLanguageProcessor:
    """Processes natural language commands using LLM."""

    def __init__(self):
        self.agent = None
        self._try_init_agent()

    def _try_init_agent(self):
        """Try to initialize the AI agent, fall back gracefully if no API key."""
        try:
            self.agent = Agent(
                "claude-3-5-haiku-20241022",
                output_type=CommandIntent,
                system_prompt="""You are an intelligent command interpreter for an ideas tracker.

Users can give natural language commands like:
- "show me anything related to authentication" -> search for "authentication"
- "make a note of what I'm working on" -> create a new idea about current session
- "mark the login feature as done" -> update/complete a task
- "what was I thinking about mobile apps?" -> search for "mobile apps"

Your job is to interpret the intent and return a structured CommandIntent:
- action: search, create, update, list, show, complete
- target: project name if mentioned or inferrable
- query: search terms or content to create
- metadata: any additional context like completion status

Be flexible with language and infer intent from context.""",
            )
        except Exception as e:
            logger.debug(f"Could not initialize AI agent: {e}")
            self.agent = None

    async def process_command(self, user_input: str, context: SessionContext) -> CommandIntent:
        """Process natural language input into structured intent."""
        if self.agent is None:
            logger.debug("No AI agent available, using fallback parsing")
            return self._fallback_parsing(user_input)

        try:
            prompt = f"""
User command: "{user_input}"

Current context:
- Branch: {context.branch or "unknown"}
- Repository: {context.repo or "unknown"}
- Working directory: {context.working_directory}

Parse this command and return the appropriate action.
"""

            result = await self.agent.run(prompt)
            return result.output

        except Exception as e:
            logger.debug(f"AI processing failed, using fallback: {e}")
            return self._fallback_parsing(user_input)

    def _fallback_parsing(self, user_input: str) -> CommandIntent:
        """Simple fallback parsing if LLM fails."""
        lower_input = user_input.lower()

        # Search patterns
        if any(word in lower_input for word in ["show", "find", "search", "related", "about"]):
            # Extract search terms more intelligently
            query = user_input.lower()
            # Remove command words to get search terms
            remove_phrases = [
                "show me anything",
                "show me",
                "find me",
                "search for",
                "anything related to",
                "related to",
                "about",
                "find",
                "search",
                "show",
                "anything",
                "me",
            ]
            for phrase in remove_phrases:
                query = query.replace(phrase, "").strip()

            # Clean up extra whitespace and get meaningful terms
            query = " ".join(query.split())

            return CommandIntent(action="search", query=query if query else user_input)

        # Create patterns
        if any(word in lower_input for word in ["note", "create", "add", "remember"]):
            return CommandIntent(action="create", query=user_input)

        # Complete patterns
        if any(word in lower_input for word in ["done", "complete", "finished", "mark"]):
            return CommandIntent(action="complete", query=user_input)

        # Default to search
        return CommandIntent(action="search", query=user_input)


class IntelligentSearcher:
    """LLM-powered search across all ideas and projects."""

    def __init__(self, data_manager: "IdeasDataManager"):
        self.data_manager = data_manager
        self.agent = None
        self._try_init_agent()

    def _try_init_agent(self):
        """Try to initialize the AI agent, fall back gracefully if no API key."""
        try:
            self.agent = Agent(
                "claude-3-5-haiku-20241022",
                system_prompt="""You are a helpful search assistant for an ideas tracker.

Your job is to analyze ideas and projects to find relevant matches based on user queries.
You'll be given a search query and a collection of projects and ideas, and should return
the most relevant results with explanations of why they match.

Focus on semantic similarity, not just keyword matching. Consider:
- Similar concepts (e.g., "auth" matches "authentication", "login")
- Related technologies (e.g., "React" relates to "frontend", "JavaScript")
- Project goals and themes
- Implementation details

Return results in a clear, organized format.""",
            )
        except Exception as e:
            logger.debug(f"Could not initialize search agent: {e}")
            self.agent = None

    async def search(self, query: str) -> dict[str, Any]:
        """Search all projects and ideas using LLM."""
        # Gather all data
        projects = self.data_manager.list_projects()
        all_data = {}

        for project_name in projects:
            project_data = self.data_manager.load_project(project_name)
            if project_data:
                all_data[project_name] = project_data

        if not all_data:
            return {"results": [], "summary": "No projects found to search."}

        if self.agent is None:
            logger.debug("No search agent available, using fallback search")
            return self._fallback_search(query, all_data)

        try:
            # Prepare search context
            search_context = json.dumps(all_data, indent=2)

            prompt = f"""
Search query: "{query}"

Available projects and ideas:
{search_context}

Find and rank the most relevant projects and ideas that match this query.
Return your analysis as a structured response explaining:
1. Which projects/ideas are most relevant and why
2. Key matching concepts or themes
3. Any related or connected ideas that might be useful

Format your response as clear, actionable information for the user.
"""

            result = await self.agent.run(prompt)
            return {"results": result.output, "query": query}

        except Exception as e:
            logger.debug(f"AI search failed, using fallback: {e}")
            return self._fallback_search(query, all_data)

    def _fallback_search(self, query: str, all_data: dict) -> dict[str, Any]:
        """Simple keyword-based fallback search."""
        results = []
        query_lower = query.lower()

        for project_name, project_data in all_data.items():
            matches = []

            # Check project name
            if query_lower in project_name.lower():
                matches.append(f"Project name contains '{query}'")

            # Check ideas
            for idea in project_data.get("ideas", []):
                if query_lower in idea["text"].lower():
                    matches.append(f"Idea: {idea['text'][:100]}...")

            if matches:
                results.append({"project": project_name, "matches": matches, "data": project_data})

        return {"results": results, "query": query, "type": "fallback"}


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
            subprocess.run(
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
    """Main ideas tracker functionality with intelligent LLM features."""

    def __init__(self):
        self.data_manager = IdeasDataManager()
        self.context_detector = BranchContextDetector()
        self._nl_processor = None
        self._searcher = None

    @property
    def nl_processor(self) -> NaturalLanguageProcessor:
        """Lazy-load the natural language processor."""
        if self._nl_processor is None:
            self._nl_processor = NaturalLanguageProcessor()
        return self._nl_processor

    @property
    def searcher(self) -> IntelligentSearcher:
        """Lazy-load the intelligent searcher."""
        if self._searcher is None:
            self._searcher = IntelligentSearcher(self.data_manager)
        return self._searcher

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

    def get_session_context(self) -> SessionContext:
        """Get current session context."""
        repo_info = self.context_detector.get_repo_info()
        return SessionContext(
            branch=repo_info.get("branch"),
            repo=repo_info.get("repo_name"),
            working_directory=repo_info.get("working_directory") or "",
        )

    async def process_intelligent_command(self, user_input: str) -> None:
        """Process a natural language command intelligently."""
        context = self.get_session_context()

        try:
            intent = await self.nl_processor.process_command(user_input, context)

            if intent.action == "search":
                await self.intelligent_search(intent.query or user_input)
            elif intent.action == "create":
                await self.smart_create_idea(intent, context)
            elif intent.action == "complete":
                await self.mark_task_complete(intent.query or user_input)
            elif intent.action == "list":
                self.list_projects()
            elif intent.action == "show" and intent.target:
                self.show_project(intent.target)
            else:
                click.echo(f"🤔 I understood you want to {intent.action}, but I need more specific information.")
                if intent.query:
                    await self.intelligent_search(intent.query)

        except Exception as e:
            logger.error(f"Error processing intelligent command: {e}")
            click.echo(f"❌ Sorry, I had trouble understanding that command: {e}")
            click.echo("💡 Try a simpler form like: 'search authentication' or 'create new project mobile-app'")

    async def intelligent_search(self, query: str) -> None:
        """Perform intelligent search across all ideas."""
        click.echo(f"🔍 Searching for: {query}")

        try:
            results = await self.searcher.search(query)

            if isinstance(results.get("results"), str):
                # LLM returned text response
                click.echo(f"\n{results['results']}")
            elif isinstance(results.get("results"), list) and results["results"]:
                # Fallback search results
                click.echo(f"\nFound {len(results['results'])} matching projects:")
                for result in results["results"]:
                    click.echo(f"\n📋 {result['project']}")
                    for match in result["matches"]:
                        click.echo(f"   • {match}")
            else:
                click.echo("No matching ideas found.")

        except Exception as e:
            logger.error(f"Search failed: {e}")
            click.echo(f"❌ Search failed: {e}")

    async def smart_create_idea(self, intent: CommandIntent, context: SessionContext) -> None:
        """Create an idea using session context and intelligent analysis."""
        if intent.target:
            # User specified a project
            project_name = intent.target
        else:
            # Try to infer project from context or ask
            project_name = await self.infer_or_ask_project(context)

        if not project_name:
            click.echo("❌ Please specify a project name or create one first with: /ideas new PROJECT_NAME")
            return

        # Generate intelligent idea content
        query = intent.query or ""
        if "working on" in query.lower() or "current" in query.lower():
            # Session-aware idea creation
            idea_text = f"Working on: {context.branch or 'unknown branch'} - {query}"
        else:
            idea_text = query

        # Create or add to existing project
        if not self.data_manager.load_project(project_name) and self.create_project(project_name):
            click.echo(f"Created new project: {project_name}")

        if self.add_idea(project_name, idea_text):
            click.echo(f"✅ Added idea to {project_name}")

    async def infer_or_ask_project(self, context: SessionContext) -> str | None:
        """Try to infer project name from context or existing projects."""
        projects = self.data_manager.list_projects()

        if not projects:
            return None

        # If there's only one project, use it
        if len(projects) == 1:
            return projects[0]

        # Try to match branch name to project
        if context.branch:
            branch_words = context.branch.lower().replace("-", " ").replace("_", " ").split()
            for project in projects:
                project_words = project.lower().replace("-", " ").replace("_", " ").split()
                if any(word in project_words for word in branch_words):
                    return project

        return None

    async def mark_task_complete(self, query: str) -> None:
        """Find and mark a task/idea as complete."""
        click.echo(f"🎯 Looking for tasks to mark complete: {query}")

        # Search for matching ideas
        try:
            results = await self.searcher.search(query)

            # For now, show what would be marked complete
            # In a full implementation, you'd update the idea status
            click.echo("Found potentially matching tasks:")
            if isinstance(results.get("results"), list):
                for result in results.get("results", []):
                    click.echo(f"📋 {result['project']}")
                    project_data = result.get("data", {})
                    for idea in project_data.get("ideas", []):
                        if query.lower() in idea["text"].lower():
                            click.echo(f"   • {idea['text']}")
                            click.echo("     [Would mark as complete]")

            click.echo("\n💡 Task completion tracking coming soon! For now, this shows what would be marked complete.")

        except Exception as e:
            logger.error(f"Task completion failed: {e}")
            click.echo(f"❌ Failed to find tasks: {e}")


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

    Natural language commands (powered by AI):
    - "show me anything related to authentication"
    - "make a note of what I'm working on"
    - "mark the login feature as done"
    - "what was I thinking about mobile apps?"
    """
    tracker = IdeasTracker()

    # Ensure setup first
    if not tracker.ensure_setup():
        click.echo("❌ Failed to set up ideas tracker")
        sys.exit(1)

    # Detect if this is a natural language command
    full_input = command + " " + " ".join(args) if args else command
    is_natural_language = command not in ["list", "new", "add", "show", "context", "sync"]

    try:
        if is_natural_language:
            # Handle natural language command
            asyncio.run(tracker.process_intelligent_command(full_input))
        elif command == "list":
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
