#!/usr/bin/env python3
"""
GTD Tool for Amplifier - Follows the Amplifier Tool contract.

Provides GTD operations as an Amplifier tool with proper name, description,
input_schema, and execute() interface.

Features:
- Cache freshness tracking on all operations
- Timeout handling with partial results
- Quick mode using cached data
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from amplifier_core.models import ToolResult  # type: ignore[import-not-found]

from .daily_note import DailyNoteGenerator
from .dashboard import GTDDashboard
from .notes_sync import NotesSync, get_notes_cache_info
from .reminders_sync import (
    load_reminders_cache,
    get_cache_info,
)
from amplifier_lib_beads import enrich_reminders_with_links
from .eventkit_sync import (
    sync_reminders_eventkit,
    check_eventkit,
    EVENTKIT_AVAILABLE,
    update_reminder,
    delete_reminder,
    complete_reminder,
)
from . import presentations
from . import reading
from . import repos
from . import withings
from . import email_sync
from . import beads
from . import kimono
from . import inbox_processor


class GTDAmplifierTool:
    """GTD Tool following the Amplifier Tool contract.

    Implements the required interface:
    - name: str property
    - description: str property
    - input_schema: dict property
    - execute(input: dict) -> ToolResult async method
    """

    OPERATIONS = [
        # Morning routine
        "morning_routine",
        "morning_quick",
        # Generation
        "generate_dashboard",
        "generate_daily_note",
        # Sync
        "sync_notes",
        "sync_reminders",
        "sync_single_list",
        # Status
        "notes_status",
        "reminders_status",
        "cache_status",
        # Reminders queries
        "focus",
        "inbox_list",
        "waiting_for",
        "projects_list",
        # Reminders mutations
        "reminder_update",
        "reminder_delete",
        "reminder_complete",
        # Inbox processing
        "process_inbox",
        # Presentations
        "pres_list",
        "pres_add",
        "pres_complete",
        "pres_archive",
        "pres_update",
        "pres_stats",
        # Reading queue
        "read_list",
        "read_add",
        "read_start",
        "read_finish",
        "read_archive",
        "read_stats",
        # Health
        "sync_weight",
        # Projects
        "project_status",
        # Repos
        "repo_sync",
        "repo_scan",
        "repo_check",
        "repo_triage",
        "repo_action",
        "repo_archive",
        "repo_list_archived",
        # Email sync
        "sync_emails",
        "email_sync_status",
        "email_sync_clear",
        "email_done",
        # Beads issue tracking
        "beads_ready",
        "beads_list",
        "beads_feature_backlog",
        "beads_show",
        "beads_create",
        "beads_close",
        "beads_update",
        "beads_dep_add",
        "beads_sync",
        "beads_stats",
        "beads_blocked",
        "beads_search",
        "beads_context",
        # Beads multi-repo aggregation
        "beads_ready_all",
        "beads_stats_all",
        "beads_search_all",
        "beads_list_repos",
        # Beads ↔ Reminders linking
        "beads_link_reminder",
        "beads_unlink_reminder",
        "beads_list_links",
        # Kimono
        "kimono_scan",
    ]

    def __init__(self, config: Optional[dict] = None):
        config = config or {}
        self.vault_path = Path(
            os.path.expanduser(config.get("vault_path", "~/switchboard"))
        )
        self.reminders_cache = self.vault_path / "reminders" / "reminders_cache.json"
        # Optional beads root override - if not set, beads uses .beads discovery
        beads_root = config.get("beads_root")
        self.beads_root = Path(os.path.expanduser(beads_root)) if beads_root else None

    @property
    def name(self) -> str:
        return "gtd"

    @property
    def description(self) -> str:
        return (
            "GTD (Getting Things Done) productivity tools for managing tasks, notes, presentations, and reading.\n\n"
            "MORNING ROUTINE:\n"
            "- morning_routine: Complete startup (~3s) - sync reminders/notes, generate dashboard/daily note\n"
            "- morning_quick: Fast startup using cached data\n\n"
            "GENERATION:\n"
            "- generate_dashboard: Generate GTD Dashboard\n"
            "- generate_daily_note: Generate today's daily note\n\n"
            "SYNC:\n"
            "- sync_reminders: Pull from Apple Reminders (EventKit, fast)\n"
            "- sync_notes: Bidirectional Notes.app ↔ Obsidian\n"
            "- cache_status: Check freshness of all caches\n\n"
            "REMINDERS:\n"
            "- focus: Urgent/overdue/due-today items\n"
            "- inbox_list: Items needing processing\n"
            "- waiting_for: Items you're waiting on\n"
            "- reminder_update: Update reminder (set due date, title, notes, priority)\n"
            "- reminder_delete: Delete a reminder\n"
            "- reminder_complete: Mark reminder as complete\n\n"
            "PRESENTATIONS:\n"
            "- pres_list: List presentations (filter: status, priority)\n"
            "- pres_add: Add presentation (url, title required)\n"
            "- pres_complete: Mark done (id required)\n"
            "- pres_archive: Archive (id required)\n"
            "- pres_stats: Statistics\n\n"
            "READING QUEUE:\n"
            "- read_list: List reading items\n"
            "- read_add: Add URL/PDF (url, title required)\n"
            "- read_start: Start reading (id required)\n"
            "- read_finish: Finish reading (id required)\n"
            "- read_archive: Archive (id required)\n"
            "- read_stats: Statistics\n\n"
            "HEALTH:\n"
            "- sync_weight: Sync weight from Withings (days: number of days to sync)\n\n"
            "PROJECTS:\n"
            "- project_status: View projects with linked repo status\n\n"
            "REPOS:\n"
            "- repo_sync: Fetch and pull all repos (push: bool to also push)\n"
            "- repo_scan: Discover git repos and rebuild repos.json\n"
            "- repo_check: Check sync status without pulling\n"
            "- repo_triage: Get detailed triage info for dirty/unsynced repos\n"
            "- repo_action: Execute action on repo (commit_all, push, pull, stash, discard)\n"
            "- repo_archive: Archive a repo (hide from views)\n"
            "- repo_list_archived: List archived repos\n\n"
            "EMAIL SYNC:\n"
            "- sync_emails: Sync starred Gmail emails to reminders (thread-aware, deduped, optional AI drafts)\n"
            "- email_sync_status: Check email sync state\n"
            "- email_sync_clear: Clear sync state (allow re-importing)\n"
            "- email_done: Complete email reminder AND unstar Gmail (streamlined inbox zero)\n\n"
            "BEADS ISSUE TRACKING:\n"
            "- beads_ready: Get tasks ready to work on (no blockers)\n"
            "- beads_list: List all issues (filter by status, priority, type)\n"
            "- beads_feature_backlog: Get feature backlog (all feature-type issues)\n"
            "- beads_show: Show issue details (id required)\n"
            "- beads_create: Create new issue (title required)\n"
            "- beads_close: Close an issue (id required)\n"
            "- beads_update: Update issue (id required)\n"
            "- beads_dep_add: Add dependency between issues\n"
            "- beads_sync: Sync beads with git\n"
            "- beads_stats: Get project statistics\n"
            "- beads_blocked: Get blocked issues\n"
            "- beads_search: Search issues by text\n"
            "- beads_context: Get current beads context for session awareness\n\n"
            "KIMONO:\n"
            "- kimono_scan: Scan calendar for events requiring kimono (uses explicit #kimono* tags only)"
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": self.OPERATIONS,
                    "description": "The GTD operation to perform",
                },
                "skip_sync": {
                    "type": "boolean",
                    "description": "For morning_routine: skip reminders/notes sync",
                    "default": False,
                },
                "skip_open": {
                    "type": "boolean",
                    "description": "For morning_routine: don't open Obsidian",
                    "default": False,
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max seconds for sync operations (default: 60 for reminders, 120 for notes)",
                },
                "date": {
                    "type": "string",
                    "description": "For generate_daily_note: date in YYYY-MM-DD format",
                },
                "limit": {
                    "type": "integer",
                    "description": "For inbox_list/waiting_for: max items to return",
                    "default": 20,
                },
                "list_name": {
                    "type": "string",
                    "description": "For sync_single_list: name of the list to sync (e.g., 'Inbox')",
                },
                # Presentations parameters
                "url": {
                    "type": "string",
                    "description": "For pres_add/read_add: URL (Google Slides or web page)",
                },
                "title": {
                    "type": "string",
                    "description": "For pres_add/read_add: title (required)",
                },
                "id": {
                    "type": "string",
                    "description": "For pres_complete/archive/update, read_start/finish/archive: item ID",
                },
                "deadline": {
                    "type": "string",
                    "description": "Deadline in YYYY-MM-DD format",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priority level",
                },
                "status": {
                    "type": "string",
                    "description": "For filtering: status (todo/done/archived for pres, to-read/reading/read/archived for read)",
                },
                "notion_url": {
                    "type": "string",
                    "description": "For pres_add: Notion brief URL",
                },
                "slack_url": {
                    "type": "string",
                    "description": "For pres_add: Slack conversation URL",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for the item",
                },
                "notes": {
                    "type": "string",
                    "description": "Notes text",
                },
                "estimated_hours": {
                    "type": "number",
                    "description": "For pres_add: estimated hours",
                },
                "actual_hours": {
                    "type": "number",
                    "description": "For pres_complete: actual hours spent",
                },
                "estimated_minutes": {
                    "type": "integer",
                    "description": "For read_add: estimated reading time in minutes",
                },
                "source": {
                    "type": "string",
                    "description": "For read_add: source (e.g., newsletter, recommendation)",
                },
                "include_archived": {
                    "type": "boolean",
                    "description": "For list operations: include archived items",
                    "default": False,
                },
                # Reminder mutation parameters
                "reminder_id": {
                    "type": "string",
                    "description": "For reminder_update/delete/complete: the reminder's ID (from inbox_list)",
                },
                "title_match": {
                    "type": "string",
                    "description": "For reminder_update/delete/complete: find reminder by exact title match",
                },
                "new_title": {
                    "type": "string",
                    "description": "For reminder_update: new title for the reminder",
                },
                "due_date": {
                    "type": "string",
                    "description": "For reminder_update: due date (YYYY-MM-DD, 'today', or empty to clear)",
                },
                "reminder_priority": {
                    "type": "integer",
                    "description": "For reminder_update: priority (0=none, 1=high, 5=medium, 9=low)",
                },
                "completed": {
                    "type": "boolean",
                    "description": "For reminder_update: set completion status",
                },
                # Email sync parameters
                "create_drafts": {
                    "type": "boolean",
                    "description": "For sync_emails: generate AI draft replies and include links in reminders",
                    "default": False,
                },
                "max_emails": {
                    "type": "integer",
                    "description": "For sync_emails: maximum emails to fetch",
                    "default": 100,
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "For sync_emails: preview without creating",
                    "default": False,
                },
                # Beads parameters
                "issue_id": {
                    "type": "string",
                    "description": "For beads operations: the issue ID (e.g., 'amplifier-bundle-gtd-ke5')",
                },
                "issue_type": {
                    "type": "string",
                    "enum": ["epic", "task", "bug", "feature", "chore"],
                    "description": "For beads_create/list: issue type",
                },
                "issue_priority": {
                    "type": "integer",
                    "description": "For beads_create/update/list: priority 0-4 (0=highest)",
                },
                "description": {
                    "type": "string",
                    "description": "For beads_create: detailed description",
                },
                "parent_id": {
                    "type": "string",
                    "description": "For beads_create/dep_add: parent issue ID",
                },
                "child_id": {
                    "type": "string",
                    "description": "For beads_dep_add: child issue ID",
                },
                "dep_type": {
                    "type": "string",
                    "enum": ["blocks", "related", "parent"],
                    "description": "For beads_dep_add: dependency type",
                },
                "query": {
                    "type": "string",
                    "description": "For beads_search: search query",
                },
                "beads_cwd": {
                    "type": "string",
                    "description": "For beads operations: working directory (uses config beads_root or .beads discovery if not specified)",
                },
                # Kimono parameters
                "days_ahead": {
                    "type": "integer",
                    "description": "For kimono_scan: number of days to look ahead (default 90)",
                    "default": 90,
                },
            },
            "required": ["operation"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        """Execute a GTD operation.

        Args:
            input: Dictionary with 'operation' key and operation-specific parameters

        Returns:
            ToolResult with success status and output data
        """
        operation = input.get("operation")

        try:
            result = await self._dispatch(input)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(
                success=False, error={"message": str(e), "operation": operation}
            )

    async def _dispatch(self, kwargs: dict[str, Any]) -> Any:
        """Dispatch to the appropriate operation handler."""
        operation = kwargs.get("operation")

        if operation == "morning_routine":
            return self._morning_routine(
                skip_sync=kwargs.get("skip_sync", False),
                skip_open=kwargs.get("skip_open", False),
                timeout=kwargs.get("timeout"),
            )
        elif operation == "morning_quick":
            return self._morning_quick(skip_open=kwargs.get("skip_open", False))
        elif operation == "generate_dashboard":
            return self._generate_dashboard()
        elif operation == "generate_daily_note":
            return self._generate_daily_note(kwargs.get("date"))
        elif operation == "sync_notes":
            return self._sync_notes(timeout=kwargs.get("timeout", 120))
        elif operation == "sync_reminders":
            return self._sync_reminders(timeout=kwargs.get("timeout", 60))
        elif operation == "sync_single_list":
            return self._sync_single_list(
                list_name=kwargs.get("list_name"), timeout=kwargs.get("timeout", 120)
            )
        elif operation == "notes_status":
            return self._notes_status()
        elif operation == "reminders_status":
            return self._reminders_status()
        elif operation == "cache_status":
            return self._cache_status()
        elif operation == "focus":
            return self._focus()
        elif operation == "inbox_list":
            return self._inbox_list(kwargs.get("limit", 20))
        elif operation == "waiting_for":
            return self._waiting_for(kwargs.get("limit", 20))
        elif operation == "projects_list":
            return self._projects_list()
        # Reminder mutation operations
        elif operation == "reminder_update":
            return self._reminder_update(
                reminder_id=kwargs.get("reminder_id"),
                title_match=kwargs.get("title_match"),
                list_name=kwargs.get("list_name"),
                new_title=kwargs.get("new_title"),
                due_date=kwargs.get("due_date"),
                notes=kwargs.get("notes"),
                priority=kwargs.get("reminder_priority"),
                completed=kwargs.get("completed"),
            )
        elif operation == "reminder_delete":
            return self._reminder_delete(
                reminder_id=kwargs.get("reminder_id"),
                title_match=kwargs.get("title_match"),
                list_name=kwargs.get("list_name"),
            )
        elif operation == "reminder_complete":
            return self._reminder_complete(
                reminder_id=kwargs.get("reminder_id"),
                title_match=kwargs.get("title_match"),
                list_name=kwargs.get("list_name"),
            )
        elif operation == "process_inbox":
            return self._process_inbox(dry_run=kwargs.get("dry_run", False))
        # Presentations operations
        elif operation == "pres_list":
            return self._pres_list(
                status=kwargs.get("status"),
                priority=kwargs.get("priority"),
                include_archived=kwargs.get("include_archived", False),
            )
        elif operation == "pres_add":
            return self._pres_add(
                url=kwargs.get("url"),
                title=kwargs.get("title"),
                deadline=kwargs.get("deadline"),
                priority=kwargs.get("priority", "medium"),
                notion_url=kwargs.get("notion_url"),
                slack_url=kwargs.get("slack_url"),
                tags=kwargs.get("tags"),
                notes=kwargs.get("notes", ""),
                estimated_hours=kwargs.get("estimated_hours"),
            )
        elif operation == "pres_complete":
            return self._pres_complete(
                pres_id=kwargs.get("id"),
                actual_hours=kwargs.get("actual_hours"),
                notes=kwargs.get("notes"),
            )
        elif operation == "pres_archive":
            return self._pres_archive(kwargs.get("id"))
        elif operation == "pres_update":
            return self._pres_update(kwargs.get("id"), **kwargs)
        elif operation == "pres_stats":
            return self._pres_stats()
        # Reading operations
        elif operation == "read_list":
            return self._read_list(
                status=kwargs.get("status"),
                priority=kwargs.get("priority"),
                include_archived=kwargs.get("include_archived", False),
            )
        elif operation == "read_add":
            return self._read_add(
                url=kwargs.get("url"),
                title=kwargs.get("title"),
                deadline=kwargs.get("deadline"),
                priority=kwargs.get("priority", "medium"),
                source=kwargs.get("source", "manual"),
                tags=kwargs.get("tags"),
                notes=kwargs.get("notes", ""),
                estimated_minutes=kwargs.get("estimated_minutes"),
            )
        elif operation == "read_start":
            return self._read_start(kwargs.get("id"))
        elif operation == "read_finish":
            return self._read_finish(kwargs.get("id"), notes=kwargs.get("notes"))
        elif operation == "read_archive":
            return self._read_archive(kwargs.get("id"))
        elif operation == "read_stats":
            return self._read_stats()
        # Health operations
        elif operation == "sync_weight":
            return withings.sync_weight(days=kwargs.get("days", 1))
        # Project operations
        elif operation == "project_status":
            return self._project_status(
                status=kwargs.get("status"),
                priority=kwargs.get("priority"),
            )
        # Repo operations
        elif operation == "repo_sync":
            return repos.repo_sync(
                self.vault_path,
                push=kwargs.get("push", False),
            )
        elif operation == "repo_scan":
            return repos.repo_scan(self.vault_path)
        elif operation == "repo_check":
            return repos.repo_check(self.vault_path)
        elif operation == "repo_triage":
            return repos.repo_triage(
                self.vault_path,
                repo_name=kwargs.get("repo_name"),
            )
        elif operation == "repo_action":
            return repos.repo_action(
                self.vault_path,
                repo_name=kwargs.get("repo_name", ""),
                action=kwargs.get("action", ""),
                commit_message=kwargs.get("commit_message"),
            )
        elif operation == "repo_archive":
            return repos.repo_archive(
                self.vault_path,
                repo_name=kwargs.get("repo_name", ""),
                archive=kwargs.get("archive", True),
            )
        elif operation == "repo_list_archived":
            return repos.repo_list_archived(self.vault_path)
        # Email sync operations
        elif operation == "sync_emails":
            return self._sync_emails(
                dry_run=kwargs.get("dry_run", False),
                max_emails=kwargs.get("max_emails", 100),
                create_drafts=kwargs.get("create_drafts", False),
            )
        elif operation == "email_sync_status":
            return email_sync.get_sync_status()
        elif operation == "email_sync_clear":
            return email_sync.clear_sync_state()
        elif operation == "email_done":
            return email_sync.email_done(
                reminder_id=kwargs.get("reminder_id"),
                title_match=kwargs.get("title_match"),
                list_name=kwargs.get("list_name", "Email Replies"),
            )
        # Beads operations
        elif operation == "beads_ready":
            return beads.beads_ready(cwd=self._get_beads_cwd(kwargs))
        elif operation == "beads_list":
            return beads.beads_list(
                status=kwargs.get("status"),
                priority=kwargs.get("issue_priority"),
                issue_type=kwargs.get("issue_type"),
                cwd=self._get_beads_cwd(kwargs),
            )
        elif operation == "beads_feature_backlog":
            return beads.beads_feature_backlog(
                status=kwargs.get("status", "open"),
                cwd=self._get_beads_cwd(kwargs),
            )
        elif operation == "beads_show":
            return beads.beads_show(
                issue_id=kwargs.get("issue_id") or kwargs.get("id"),
                cwd=self._get_beads_cwd(kwargs),
            )
        elif operation == "beads_create":
            return beads.beads_create(
                title=kwargs.get("title", ""),
                priority=kwargs.get("issue_priority", 2),
                issue_type=kwargs.get("issue_type", "task"),
                description=kwargs.get("description"),
                parent=kwargs.get("parent_id"),
                cwd=self._get_beads_cwd(kwargs),
            )
        elif operation == "beads_close":
            return beads.beads_close(
                issue_id=kwargs.get("issue_id") or kwargs.get("id"),
                notes=kwargs.get("notes"),
                cwd=self._get_beads_cwd(kwargs),
            )
        elif operation == "beads_update":
            return beads.beads_update(
                issue_id=kwargs.get("issue_id") or kwargs.get("id"),
                status=kwargs.get("status"),
                priority=kwargs.get("issue_priority"),
                title=kwargs.get("title"),
                notes=kwargs.get("notes"),
                cwd=self._get_beads_cwd(kwargs),
            )
        elif operation == "beads_dep_add":
            return beads.beads_dep_add(
                child_id=kwargs.get("child_id"),
                parent_id=kwargs.get("parent_id"),
                dep_type=kwargs.get("dep_type", "blocks"),
                cwd=self._get_beads_cwd(kwargs),
            )
        elif operation == "beads_sync":
            return beads.beads_sync(cwd=self._get_beads_cwd(kwargs))
        elif operation == "beads_stats":
            return beads.beads_stats(cwd=self._get_beads_cwd(kwargs))
        elif operation == "beads_blocked":
            return beads.beads_blocked(cwd=self._get_beads_cwd(kwargs))
        elif operation == "beads_search":
            return beads.beads_search(
                query=kwargs.get("query", ""),
                cwd=self._get_beads_cwd(kwargs),
            )
        elif operation == "beads_context":
            return beads.get_beads_context(cwd=self._get_beads_cwd(kwargs))
        # Beads multi-repo aggregation
        elif operation == "beads_ready_all":
            return beads.beads_ready_all()
        elif operation == "beads_stats_all":
            return beads.beads_stats_all()
        elif operation == "beads_search_all":
            return beads.beads_search_all(query=kwargs.get("query", ""))
        elif operation == "beads_list_repos":
            return beads.beads_list_repos()
        # Beads ↔ Reminders linking
        elif operation == "beads_link_reminder":
            return beads.beads_link_reminder(
                reminder_id=kwargs.get("reminder_id", ""),
                beads_id=kwargs.get("beads_id", ""),
                reminder_title=kwargs.get("reminder_title"),
                beads_title=kwargs.get("beads_title"),
            )
        elif operation == "beads_unlink_reminder":
            return beads.beads_unlink_reminder(
                reminder_id=kwargs.get("reminder_id"),
                beads_id=kwargs.get("beads_id"),
            )
        elif operation == "beads_list_links":
            return beads.beads_list_links()
        # Kimono operations
        elif operation == "kimono_scan":
            return self._kimono_scan(days_ahead=kwargs.get("days_ahead", 90))
        else:
            return {"error": f"Unknown operation: {operation}"}

    def _get_beads_cwd(self, kwargs: dict) -> str | None:
        """Get the working directory for beads operations.

        Priority:
        1. Explicit beads_cwd parameter in kwargs
        2. beads_root from tool config
        3. None (let beads discover .beads from current directory)
        """
        import os

        cwd = kwargs.get("beads_cwd")
        if cwd:
            return os.path.expanduser(cwd)
        if self.beads_root:
            return str(self.beads_root)
        # Let beads discover .beads from current directory
        return None

    def _get_cache_freshness(self) -> dict:
        """Get freshness info for all caches."""
        reminders_info = get_cache_info(self.reminders_cache)
        notes_info = get_notes_cache_info()

        return {
            "reminders": {
                "age_seconds": reminders_info.get("cache_age_seconds"),
                "age_human": reminders_info.get("cache_age_human"),
                "is_stale": reminders_info.get("is_stale", True),
            },
            "notes": {
                "age_seconds": notes_info.get("cache_age_seconds"),
                "age_human": notes_info.get("cache_age_human"),
                "is_stale": notes_info.get("is_stale", True),
            },
        }

    def _morning_routine(
        self,
        skip_sync: bool = False,
        skip_open: bool = False,
        timeout: Optional[int] = None,
    ) -> dict:
        """Run the complete GTD morning routine with timeout handling."""
        import subprocess

        results = {
            "steps": [],
            "dashboard_path": None,
            "daily_note_path": None,
            "errors": [],
            "warnings": [],
            "cache_freshness": None,
        }

        # Step 1: Sync reminders (uses EventKit for speed)
        if not skip_sync:
            try:
                sync_result = self._sync_reminders(timeout=timeout or 60)
                if sync_result.get("partial"):
                    results["warnings"].append(
                        f"Partial reminders sync: {sync_result.get('lists_failed', [])} lists failed"
                    )
                results["steps"].append(
                    f"Synced {sync_result.get('total', 0)} reminders from {sync_result.get('lists', 0)} lists ({sync_result.get('method', 'unknown')})"
                )
            except Exception as e:
                results["errors"].append(f"Reminders sync failed: {e}")

        # Step 2: Sync notes
        if not skip_sync:
            try:
                syncer = NotesSync()
                sync_result = syncer.sync(max_timeout=timeout or 120)
                summary = sync_result["summary"]
                if summary.get("partial"):
                    results["warnings"].append("Partial notes sync (timed out)")
                results["steps"].append(
                    f"Synced Notes.app: {summary['total_created']} created, "
                    f"{summary['total_updated']} updated"
                )
            except Exception as e:
                results["errors"].append(f"Notes sync failed: {e}")

        # Step 3: Generate GTD Dashboard
        try:
            dashboard = GTDDashboard()
            path = dashboard.save()
            results["dashboard_path"] = str(path)
            results["steps"].append("Generated GTD Dashboard")
        except Exception as e:
            results["errors"].append(f"Dashboard generation failed: {e}")

        # Step 4: Generate Daily Note
        try:
            generator = DailyNoteGenerator()
            path = generator.save()
            results["daily_note_path"] = str(path)
            results["steps"].append("Generated daily note")
        except Exception as e:
            results["errors"].append(f"Daily note generation failed: {e}")

        # Step 5: Open Obsidian
        if not skip_open:
            try:
                subprocess.run(
                    ["open", "obsidian://open?vault=switchboard&file=GTD%20Dashboard"],
                    check=True,
                )
                results["steps"].append("Opened GTD Dashboard in Obsidian")
            except Exception as e:
                results["errors"].append(f"Failed to open Obsidian: {e}")

        # Add cache freshness info
        results["cache_freshness"] = self._get_cache_freshness()

        # Add focus snapshot - what needs attention today
        try:
            focus = self._focus()
            # Get inbox count
            inbox = self._inbox_list(limit=5)

            # Count overdue ticklers (items with source: "overdue_tickler")
            overdue_ticklers = [
                item
                for item in focus["items"]["tickled_today"]
                if item.get("source") == "overdue_tickler"
            ]

            # Build top items list (max 5)
            top_items = []
            for item in focus["items"]["past_deadline"][:2]:
                top_items.append(
                    {"title": item["title"], "due": "overdue", "list": item["list"]}
                )
            # Include overdue ticklers as "overdue" items
            for item in overdue_ticklers[:2]:
                if len(top_items) < 5:
                    top_items.append(
                        {"title": item["title"], "due": "overdue", "list": item["list"]}
                    )
            for item in focus["items"]["flagged"][:2]:
                if len(top_items) < 5:
                    top_items.append(
                        {"title": item["title"], "due": "urgent", "list": item["list"]}
                    )
            for item in focus["items"]["deadline_today"][:2]:
                if len(top_items) < 5:
                    top_items.append(
                        {"title": item["title"], "due": "today", "list": item["list"]}
                    )

            results["focus_snapshot"] = {
                # Include both past deadlines AND overdue ticklers in overdue count
                "overdue": focus["past_deadline_count"] + len(overdue_ticklers),
                "urgent": focus["flagged_count"],
                "due_today": focus["deadline_today_count"],
                "inbox_count": inbox["count"],
                "top_items": top_items,
            }
        except Exception as e:
            results["warnings"].append(f"Could not generate focus snapshot: {e}")

        results["success"] = len(results["errors"]) == 0

        return results

    def _morning_quick(self, skip_open: bool = False) -> dict:
        """Quick morning routine using cached data - no sync, just generate."""
        import subprocess

        results = {
            "steps": [],
            "dashboard_path": None,
            "daily_note_path": None,
            "errors": [],
            "warnings": [],
            "cache_freshness": None,
        }

        # Check cache freshness first
        freshness = self._get_cache_freshness()
        results["cache_freshness"] = freshness

        if freshness["reminders"]["is_stale"]:
            results["warnings"].append(
                f"Reminders cache is stale ({freshness['reminders']['age_human']}). "
                "Run morning_routine or sync_reminders for fresh data."
            )

        if freshness["notes"]["is_stale"]:
            results["warnings"].append(
                f"Notes cache is stale ({freshness['notes']['age_human']}). "
                "Run morning_routine or sync_notes for fresh data."
            )

        # Generate GTD Dashboard (uses cached data)
        try:
            dashboard = GTDDashboard()
            path = dashboard.save()
            results["dashboard_path"] = str(path)
            results["steps"].append("Generated GTD Dashboard (from cache)")
        except Exception as e:
            results["errors"].append(f"Dashboard generation failed: {e}")

        # Generate Daily Note
        try:
            generator = DailyNoteGenerator()
            path = generator.save()
            results["daily_note_path"] = str(path)
            results["steps"].append("Generated daily note")
        except Exception as e:
            results["errors"].append(f"Daily note generation failed: {e}")

        # Open Obsidian
        if not skip_open:
            try:
                subprocess.run(
                    ["open", "obsidian://open?vault=switchboard&file=GTD%20Dashboard"],
                    check=True,
                )
                results["steps"].append("Opened GTD Dashboard in Obsidian")
            except Exception as e:
                results["errors"].append(f"Failed to open Obsidian: {e}")

        results["success"] = len(results["errors"]) == 0
        return results

    def _generate_dashboard(self) -> dict:
        """Generate the GTD Dashboard."""
        dashboard = GTDDashboard()
        path = dashboard.save()
        freshness = self._get_cache_freshness()

        return {
            "success": True,
            "path": str(path),
            "message": "GTD Dashboard generated",
            "cache_freshness": freshness,
        }

    def _generate_daily_note(self, date: Optional[str] = None) -> dict:
        """Generate a daily note."""
        target_date = None
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d")

        generator = DailyNoteGenerator()
        path = generator.save(target_date)
        return {
            "success": True,
            "path": str(path),
            "message": f"Daily note generated for {path.stem}",
        }

    def _sync_notes(self, timeout: int = 120) -> dict:
        """Sync Notes.app with Obsidian with timeout handling."""
        syncer = NotesSync()
        result = syncer.sync(max_timeout=timeout)

        return {
            "success": result["summary"]["total_errors"] == 0
            and not result["summary"].get("partial"),
            "partial": result["summary"].get("partial", False),
            "created": result["summary"]["total_created"],
            "updated": result["summary"]["total_updated"],
            "deleted": result["summary"]["total_deleted"],
            "errors": result["summary"]["total_errors"],
            "elapsed_seconds": result["summary"].get("elapsed_seconds"),
            "synced_at": result.get("synced_at"),
            "cache_age_seconds": 0,  # Just synced
        }

    def _sync_reminders(self, timeout: int = 60) -> dict:
        """Sync reminders from Apple Reminders using EventKit.

        Args:
            timeout: Timeout in seconds

        Returns:
            dict with sync results or error if EventKit unavailable/unauthorized
        """
        # EventKit is required - no AppleScript fallback (causes auth popups)
        if not EVENTKIT_AVAILABLE:
            return {
                "success": False,
                "error": "EventKit not installed. Run: uv pip install pyobjc-framework-EventKit",
                "method": "eventkit",
            }

        ek_status = check_eventkit()
        if not ek_status.get("authorized"):
            return {
                "success": False,
                "error": f"Reminders access not authorized (status: {ek_status.get('status')}). "
                "Please enable in System Settings > Privacy & Security > Reminders",
                "method": "eventkit",
            }

        result = sync_reminders_eventkit(
            cache_path=str(self.reminders_cache), timeout=timeout
        )
        result["method"] = "eventkit"
        result["cache_age_seconds"] = 0
        return result

    def _sync_single_list(self, list_name: Optional[str], timeout: int = 120) -> dict:
        """Sync a single reminder list - DEPRECATED, use full sync instead.

        EventKit syncs are fast enough that single-list sync is no longer needed.
        This now just runs a full sync.
        """
        # EventKit is fast enough that we just do a full sync
        return self._sync_reminders(timeout=timeout)

    def _notes_status(self) -> dict:
        """Get Notes.app sync status with cache freshness."""
        syncer = NotesSync()
        return syncer.get_status()

    def _reminders_status(self) -> dict:
        """Get reminders cache status."""
        return get_cache_info(self.reminders_cache)

    def _cache_status(self) -> dict:
        """Get status of all caches."""
        return {
            "reminders": get_cache_info(self.reminders_cache),
            "notes": get_notes_cache_info(),
            "recommendation": self._get_sync_recommendation(),
        }

    def _get_sync_recommendation(self) -> str:
        """Get recommendation based on cache staleness."""
        freshness = self._get_cache_freshness()

        if freshness["reminders"]["is_stale"] and freshness["notes"]["is_stale"]:
            return "Both caches are stale. Run morning_routine to sync everything."
        elif freshness["reminders"]["is_stale"]:
            return "Reminders cache is stale. Run sync_reminders to refresh."
        elif freshness["notes"]["is_stale"]:
            return "Notes cache is stale. Run sync_notes to refresh."
        else:
            return "All caches are fresh. Use morning_quick for fast startup."

    def _focus(self) -> dict:
        """Get items needing immediate attention with cache freshness.

        Uses the tickler model:
        - 'deadline' field (from text [due: X]) = hard deadlines
        - 'due' field (native date picker) = tickler/surface date
        - 'flagged' = urgent items

        Focus sections (in priority order):
        1. Flagged (urgent)
        2. Past deadline (deadline < today)
        3. Deadline today (deadline == today)
        4. Tickled today (due == today, surfaced for review)
        5. Deadline this week (deadline within 7 days)
        """
        reminders = load_reminders_cache(self.reminders_cache)
        cache_info = get_cache_info(self.reminders_cache)

        focus_items = {
            "flagged": [],
            "past_deadline": [],
            "deadline_today": [],
            "tickled_today": [],
            "deadline_this_week": [],
        }

        today = datetime.now().date()
        week_end = today.replace(day=today.day + 7) if today.day <= 24 else today

        for r in reminders:
            if r.get("completed"):
                continue

            title = r.get("title", "")
            list_name = r.get("list", "Unknown")
            deadline = r.get("deadline")  # From text [due: X]
            tickler = r.get("due")  # Native date field (tickler/surface date)

            # Skip someday/waiting items unless they have a tickler for today
            tags = r.get("tags", [])
            is_someday = "someday" in tags or list_name == "Someday/Maybe"
            is_waiting = "waiting" in tags or list_name == "Waiting For"

            # Flagged items (urgent) - always show
            if r.get("flagged"):
                focus_items["flagged"].append(
                    {"title": title, "list": list_name, "deadline": deadline}
                )
                continue

            # Check deadline (from text [due: X])
            if deadline:
                try:
                    deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
                    if deadline_date < today:
                        focus_items["past_deadline"].append(
                            {
                                "title": title,
                                "list": list_name,
                                "deadline": deadline,
                                "days_overdue": (today - deadline_date).days,
                            }
                        )
                        continue
                    elif deadline_date == today:
                        focus_items["deadline_today"].append(
                            {"title": title, "list": list_name}
                        )
                        continue
                    elif deadline_date <= week_end:
                        focus_items["deadline_this_week"].append(
                            {
                                "title": title,
                                "list": list_name,
                                "deadline": deadline,
                                "days_until": (deadline_date - today).days,
                            }
                        )
                        continue
                except Exception:
                    pass

            # Check tickler date (native date field = surface/review date)
            if tickler:
                try:
                    # Handle both ISO format and YYYY-MM-DD
                    if "T" in tickler:
                        tickler_date = datetime.fromisoformat(
                            tickler.replace("Z", "+00:00")
                        ).date()
                    else:
                        tickler_date = datetime.strptime(tickler, "%Y-%m-%d").date()

                    if tickler_date == today:
                        focus_items["tickled_today"].append(
                            {
                                "title": title,
                                "list": list_name,
                                "source": "someday" if is_someday else "tickler",
                            }
                        )
                        continue
                    elif tickler_date < today and not is_someday and not is_waiting:
                        # Past tickler on active items = should have been reviewed
                        focus_items["tickled_today"].append(
                            {
                                "title": title,
                                "list": list_name,
                                "source": "overdue_tickler",
                                "days_past": (today - tickler_date).days,
                            }
                        )
                        continue
                except Exception:
                    pass

        return {
            "flagged_count": len(focus_items["flagged"]),
            "past_deadline_count": len(focus_items["past_deadline"]),
            "deadline_today_count": len(focus_items["deadline_today"]),
            "tickled_today_count": len(focus_items["tickled_today"]),
            "deadline_this_week_count": len(focus_items["deadline_this_week"]),
            "items": focus_items,
            "cache_age_seconds": cache_info.get("cache_age_seconds"),
            "cache_age_human": cache_info.get("cache_age_human"),
            "is_stale": cache_info.get("is_stale", True),
        }

    def _inbox_list(self, limit: int = 20) -> dict:
        """List items in the Inbox that need processing.

        Items with linked beads issues will have a 'linked_beads' field.
        """
        reminders = load_reminders_cache(self.reminders_cache)
        cache_info = get_cache_info(self.reminders_cache)

        inbox_items = [
            {"title": r["title"], "id": r.get("id")}
            for r in reminders
            if r.get("list") == "Inbox" and not r.get("completed")
        ][:limit]

        # Enrich with linked beads issues
        inbox_items = enrich_reminders_with_links(inbox_items)

        return {
            "count": len(inbox_items),
            "items": inbox_items,
            "cache_age_seconds": cache_info.get("cache_age_seconds"),
            "cache_age_human": cache_info.get("cache_age_human"),
            "is_stale": cache_info.get("is_stale", True),
        }

    def _waiting_for(self, limit: int = 20) -> dict:
        """List items tagged with #waiting."""
        reminders = load_reminders_cache(self.reminders_cache)
        cache_info = get_cache_info(self.reminders_cache)

        waiting_items = []
        for r in reminders:
            if r.get("completed"):
                continue
            tags = r.get("tags", [])
            if "waiting" in tags:
                waiting_items.append(
                    {"title": r["title"], "list": r.get("list", "Unknown")}
                )

        return {
            "count": len(waiting_items),
            "items": waiting_items[:limit],
            "cache_age_seconds": cache_info.get("cache_age_seconds"),
            "cache_age_human": cache_info.get("cache_age_human"),
            "is_stale": cache_info.get("is_stale", True),
        }

    def _projects_list(self) -> dict:
        """List reminder lists (which represent projects/contexts)."""
        import json

        cache_info = get_cache_info(self.reminders_cache)

        if not self.reminders_cache.exists():
            return {
                "lists": [],
                "error": "Reminders cache not found",
                "cache_age_seconds": None,
                "is_stale": True,
            }

        with open(self.reminders_cache) as f:
            cache = json.load(f)

        lists_info = []
        for list_name, items in cache.get("byList", {}).items():
            incomplete = [i for i in items if not i.get("completed")]
            lists_info.append({"name": list_name, "count": len(incomplete)})

        # Sort by count descending
        lists_info.sort(key=lambda x: x["count"], reverse=True)

        return {
            "total_lists": len(lists_info),
            "lists": lists_info,
            "cache_age_seconds": cache_info.get("cache_age_seconds"),
            "cache_age_human": cache_info.get("cache_age_human"),
            "is_stale": cache_info.get("is_stale", True),
        }

    # ==================== REMINDER MUTATIONS ====================

    def _reminder_update(
        self,
        reminder_id: Optional[str] = None,
        title_match: Optional[str] = None,
        list_name: Optional[str] = None,
        new_title: Optional[str] = None,
        due_date: Optional[str] = None,
        notes: Optional[str] = None,
        priority: Optional[int] = None,
        completed: Optional[bool] = None,
    ) -> dict:
        """Update a reminder's properties using EventKit."""
        if not reminder_id and not title_match:
            return {
                "success": False,
                "error": "Either reminder_id or title_match is required",
            }

        if not EVENTKIT_AVAILABLE:
            return {"success": False, "error": "EventKit not available"}

        result = update_reminder(
            reminder_id=reminder_id,
            title_match=title_match,
            list_name=list_name,
            new_title=new_title,
            due_date=due_date,
            notes=notes,
            priority=priority,
            completed=completed,
        )

        # Trigger a cache refresh if successful
        if result.get("success"):
            try:
                sync_reminders_eventkit(
                    cache_path=str(self.reminders_cache), timeout=30
                )
                result["cache_refreshed"] = True
            except Exception:
                result["cache_refreshed"] = False

        return result

    def _reminder_delete(
        self,
        reminder_id: Optional[str] = None,
        title_match: Optional[str] = None,
        list_name: Optional[str] = None,
    ) -> dict:
        """Delete a reminder using EventKit."""
        if not reminder_id and not title_match:
            return {
                "success": False,
                "error": "Either reminder_id or title_match is required",
            }

        if not EVENTKIT_AVAILABLE:
            return {"success": False, "error": "EventKit not available"}

        result = delete_reminder(
            reminder_id=reminder_id, title_match=title_match, list_name=list_name
        )

        # Trigger a cache refresh if successful
        if result.get("success"):
            try:
                sync_reminders_eventkit(
                    cache_path=str(self.reminders_cache), timeout=30
                )
                result["cache_refreshed"] = True
            except Exception:
                result["cache_refreshed"] = False

        return result

    def _reminder_complete(
        self,
        reminder_id: Optional[str] = None,
        title_match: Optional[str] = None,
        list_name: Optional[str] = None,
    ) -> dict:
        """Mark a reminder as complete using EventKit."""
        if not reminder_id and not title_match:
            return {
                "success": False,
                "error": "Either reminder_id or title_match is required",
            }

        if not EVENTKIT_AVAILABLE:
            return {"success": False, "error": "EventKit not available"}

        result = complete_reminder(
            reminder_id=reminder_id, title_match=title_match, list_name=list_name
        )

        # Trigger a cache refresh if successful
        if result.get("success"):
            try:
                sync_reminders_eventkit(
                    cache_path=str(self.reminders_cache), timeout=30
                )
                result["cache_refreshed"] = True
            except Exception:
                result["cache_refreshed"] = False

        return result

    def _process_inbox(self, dry_run: bool = False) -> dict:
        """Process inbox and auto-move items to appropriate lists.

        Items with dates or tags are moved to their proper GTD lists:
        - #someday tag → Someday/Maybe
        - #waiting tag → Waiting For
        - Has due date (native) → Next Actions
        - Has [due: X] text deadline → Next Actions

        Args:
            dry_run: If True, report what would be moved without moving.

        Returns:
            dict with items_scanned, items_moved, items_failed, moves, errors
        """
        # Ensure target lists exist
        created_lists = inbox_processor.ensure_lists_exist()

        # Process inbox
        result = inbox_processor.process_inbox(dry_run=dry_run)

        # Refresh cache after moving items (unless dry run)
        cache_refreshed = False
        if not dry_run and result.items_moved > 0:
            try:
                sync_reminders_eventkit(
                    cache_path=str(self.reminders_cache), timeout=30
                )
                cache_refreshed = True
            except Exception:
                pass

        return {
            "success": result.items_failed == 0,
            "dry_run": dry_run,
            "items_scanned": result.items_scanned,
            "items_moved": result.items_moved,
            "items_failed": result.items_failed,
            "moves": [
                {
                    "title": m.title,
                    "from": m.from_list,
                    "to": m.to_list,
                    "success": m.success,
                    "error": m.error,
                }
                for m in result.moves
            ],
            "errors": result.errors,
            "lists_created": created_lists,
            "cache_refreshed": cache_refreshed,
        }

    # ==================== PRESENTATIONS ====================

    def _pres_list(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        include_archived: bool = False,
    ) -> dict:
        """List presentations."""
        try:
            items = presentations.list_presentations(
                status=status, priority=priority, include_archived=include_archived
            )
            stats = presentations.get_stats()
            return {
                "success": True,
                "count": len(items),
                "stats": stats,
                "items": items,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _pres_add(
        self,
        url: Optional[str],
        title: Optional[str],
        deadline: Optional[str] = None,
        priority: str = "medium",
        notion_url: Optional[str] = None,
        slack_url: Optional[str] = None,
        tags: Optional[list] = None,
        notes: str = "",
        estimated_hours: Optional[float] = None,
    ) -> dict:
        """Add a new presentation."""
        try:
            if not url:
                return {"success": False, "error": "URL is required"}
            if not title:
                return {"success": False, "error": "Title is required"}

            pres = presentations.add_presentation(
                url=url,
                title=title,
                deadline=deadline,
                priority=priority,
                notion_url=notion_url,
                slack_url=slack_url,
                tags=tags,
                notes=notes,
                estimated_hours=estimated_hours,
            )
            return {"success": True, "presentation": pres}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _pres_complete(
        self,
        pres_id: Optional[str],
        actual_hours: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Mark presentation as complete."""
        try:
            if not pres_id:
                return {"success": False, "error": "Presentation ID is required"}

            pres = presentations.complete_presentation(
                pres_id, actual_hours=actual_hours, notes=notes
            )
            return {"success": True, "presentation": pres}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _pres_archive(self, pres_id: Optional[str]) -> dict:
        """Archive a presentation."""
        try:
            if not pres_id:
                return {"success": False, "error": "Presentation ID is required"}

            pres = presentations.archive_presentation(pres_id)
            return {"success": True, "presentation": pres}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _pres_update(self, pres_id: Optional[str], **kwargs) -> dict:
        """Update presentation metadata."""
        try:
            if not pres_id:
                return {"success": False, "error": "Presentation ID is required"}

            # Filter out None values and operation
            updates = {
                k: v
                for k, v in kwargs.items()
                if v is not None and k not in ("operation", "id")
            }
            pres = presentations.update_presentation(pres_id, **updates)
            return {"success": True, "presentation": pres}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _pres_stats(self) -> dict:
        """Get presentation statistics."""
        try:
            stats = presentations.get_stats()
            return {"success": True, "stats": stats}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== READING QUEUE ====================

    def _read_list(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        include_archived: bool = False,
    ) -> dict:
        """List reading items."""
        try:
            items = reading.list_reading(
                status=status, priority=priority, include_archived=include_archived
            )
            stats = reading.get_stats()
            return {
                "success": True,
                "count": len(items),
                "stats": stats,
                "items": items,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _read_add(
        self,
        url: Optional[str],
        title: Optional[str],
        deadline: Optional[str] = None,
        priority: str = "medium",
        source: str = "manual",
        tags: Optional[list] = None,
        notes: str = "",
        estimated_minutes: Optional[int] = None,
    ) -> dict:
        """Add a new reading item."""
        try:
            if not url:
                return {"success": False, "error": "URL is required"}
            if not title:
                return {"success": False, "error": "Title is required"}

            item = reading.add_reading(
                input_str=url,
                title=title,
                deadline=deadline,
                priority=priority,
                source=source,
                tags=tags,
                notes=notes,
                estimated_minutes=estimated_minutes,
            )
            return {"success": True, "item": item}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _read_start(self, item_id: Optional[str]) -> dict:
        """Start reading an item."""
        try:
            if not item_id:
                return {"success": False, "error": "Item ID is required"}

            item = reading.start_reading(item_id)
            return {"success": True, "item": item}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _read_finish(self, item_id: Optional[str], notes: Optional[str] = None) -> dict:
        """Finish reading an item."""
        try:
            if not item_id:
                return {"success": False, "error": "Item ID is required"}

            item = reading.finish_reading(item_id, notes=notes)
            return {"success": True, "item": item}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _read_archive(self, item_id: Optional[str]) -> dict:
        """Archive a reading item."""
        try:
            if not item_id:
                return {"success": False, "error": "Item ID is required"}

            item = reading.archive_reading(item_id)
            return {"success": True, "item": item}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _read_stats(self) -> dict:
        """Get reading queue statistics."""
        try:
            stats = reading.get_stats()
            return {"success": True, "stats": stats}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== PROJECTS ====================

    def _project_status(
        self, status: Optional[str] = None, priority: Optional[str] = None
    ) -> dict:
        """Get unified project status with linked repo information.

        Reads repos.json and project-status.json, joins by repoId,
        and returns a focused dashboard view.
        """
        import json
        from datetime import datetime

        repos_file = self.vault_path / "amplifier" / "repos.json"
        projects_file = self.vault_path / "amplifier" / "project-status.json"

        result = {
            "success": True,
            "summary": {},
            "needs_attention": [],
            "projects": [],
            "repos_stale": False,
        }

        # Load repos.json
        repos_by_id = {}
        repos_data = {}
        if repos_file.exists():
            try:
                repos_data = json.loads(repos_file.read_text())
                for repo in repos_data.get("repos", []):
                    repos_by_id[repo.get("id")] = repo
                    repos_by_id[repo.get("name")] = repo  # Also index by name

                # Check staleness
                last_synced = repos_data.get("lastSynced")
                if last_synced:
                    try:
                        synced_dt = datetime.fromisoformat(
                            last_synced.replace("Z", "+00:00")
                        )
                        age_hours = (
                            datetime.now(synced_dt.tzinfo) - synced_dt
                        ).total_seconds() / 3600
                        result["repos_last_synced"] = last_synced
                        result["repos_age_hours"] = round(age_hours, 1)
                        result["repos_stale"] = age_hours > 24
                    except Exception:
                        result["repos_stale"] = True
            except Exception as e:
                result["repos_error"] = str(e)
        else:
            result["repos_error"] = "repos.json not found"

        # Load project-status.json
        projects = []
        if projects_file.exists():
            try:
                projects_data = json.loads(projects_file.read_text())
                projects = projects_data.get("projects", [])
            except Exception as e:
                result["projects_error"] = str(e)
        else:
            result["projects_error"] = "project-status.json not found"

        # Filter by status/priority if specified
        if status:
            projects = [p for p in projects if p.get("status") == status]
        if priority:
            projects = [p for p in projects if p.get("priority") == priority]

        # Join projects with repos and build output
        active_count = 0
        high_priority_count = 0
        dirty_repos = 0

        for proj in projects:
            repo_id = proj.get("repoId")
            repo = repos_by_id.get(repo_id, {}) if repo_id else {}

            # Build project entry
            entry = {
                "id": proj.get("id"),
                "title": proj.get("title"),
                "status": proj.get("status"),
                "priority": proj.get("priority"),
                "next_action": proj.get("nextActions", [""])[0]
                if proj.get("nextActions")
                else None,
            }

            # Add repo info if linked
            if repo:
                entry["repo"] = {
                    "name": repo.get("name"),
                    "branch": repo.get("currentBranch"),
                    "commit": repo.get("localCommit"),
                    "sync_status": repo.get("syncStatus"),
                    "dirty": not repo.get("workingTreeClean", True),
                    "version": repo.get("version"),
                }
                if not repo.get("workingTreeClean", True):
                    dirty_repos += 1

            # Track stats
            if proj.get("status") in ("started", "in-progress"):
                active_count += 1
            if proj.get("priority") == "high":
                high_priority_count += 1

            result["projects"].append(entry)

            # Flag items needing attention
            needs_attention = False
            attention_reasons = []

            if proj.get("priority") == "high" and proj.get("status") == "started":
                needs_attention = True
                attention_reasons.append("high priority + active")
            if repo and not repo.get("workingTreeClean", True):
                needs_attention = True
                attention_reasons.append("uncommitted changes")
            if repo and repo.get("syncStatus") in ("behind", "diverged"):
                needs_attention = True
                attention_reasons.append(f"repo {repo.get('syncStatus')}")

            if needs_attention:
                result["needs_attention"].append(
                    {
                        "title": proj.get("title"),
                        "reasons": attention_reasons,
                        "next_action": entry.get("next_action"),
                    }
                )

        # Build summary
        result["summary"] = {
            "total_projects": len(projects),
            "active": active_count,
            "high_priority": high_priority_count,
            "repos_dirty": dirty_repos,
            "total_repos": len(repos_data.get("repos", [])),
        }

        return result

    def _sync_emails(
        self, dry_run: bool = False, max_emails: int = 100, create_drafts: bool = False
    ) -> dict:
        """Sync starred Gmail emails to Apple Reminders.

        Features:
        - Thread-aware: Only imports the latest email per thread
        - Deduplication: Tracks imported threads to prevent re-importing
        - Existing check: Skips emails already in reminders
        - Optional AI draft generation with links in reminders

        Args:
            dry_run: If True, show what would be imported without creating reminders
            max_emails: Maximum emails to fetch from Gmail
            create_drafts: If True, generate AI draft replies and include links

        Returns:
            dict with sync results
        """
        return email_sync.sync_emails_to_reminders(
            dry_run=dry_run,
            max_emails=max_emails,
            create_drafts=create_drafts,
        )

    # ==================== KIMONO ====================

    def _kimono_scan(self, days_ahead: int = 90) -> dict:
        """Scan calendar for events requiring kimono attire.

        Only uses explicit #kimono* tags in event titles/descriptions.
        Never infers from event names or content.

        Args:
            days_ahead: Number of days to look ahead (default 90)

        Returns:
            dict with scan results and CSV output path
        """
        return kimono.scan_kimono_events(days_ahead=days_ahead)
