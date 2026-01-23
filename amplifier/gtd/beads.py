#!/usr/bin/env python3
"""Beads integration for GTD bundle.

Wraps the `bd` CLI for issue tracking within the GTD workflow.
Beads provides persistent, structured memory for coding agents with
dependency-aware graph tracking.
"""

from pathlib import Path
from typing import Any

from amplifier_lib_beads import (
    beads_list_repos as _beads_list_repos,
    beads_ready_all as _beads_ready_all,
    beads_search_all as _beads_search_all,
    beads_stats_all as _beads_stats_all,
    enrich_beads_with_links,
    get_all_links as _get_all_links,
    get_occurrence_count,
    link_reminder_to_beads as _link_reminder_to_beads,
    run_bd,
    unlink_reminder_from_beads as _unlink_reminder_from_beads,
)


def _enrich_with_occurrences(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add occurrence_count field and sort by it (highest first, then by priority)."""
    for issue in issues:
        issue["occurrence_count"] = get_occurrence_count(issue)

    # Sort by occurrence_count (descending), then priority (ascending)
    return sorted(issues, key=lambda i: (-i["occurrence_count"], i.get("priority", 99)))


def beads_ready(cwd: str | None = None) -> dict[str, Any]:
    """Get tasks that are ready to work on (no blockers).

    This is the primary command for finding what to work on next.
    Issues are sorted by occurrence count (recurring issues first), then by priority.
    Issues with linked reminders will have a 'linked_reminders' field.
    """
    result = run_bd(["ready"], cwd=cwd)
    if result.get("success") and "data" in result:
        data = result["data"]
        # Handle both single object and list responses
        if isinstance(data, list):
            enriched = _enrich_with_occurrences(data)
            enriched = enrich_beads_with_links(enriched)
            return {"success": True, "count": len(enriched), "issues": enriched}
        elif isinstance(data, dict) and "issues" in data:
            enriched = _enrich_with_occurrences(data["issues"])
            enriched = enrich_beads_with_links(enriched)
            return {
                "success": True,
                "count": len(enriched),
                "issues": enriched,
            }
        else:
            return {"success": True, "data": data}
    return result


def beads_list(
    status: str | None = None,
    priority: int | None = None,
    issue_type: str | None = None,
    cwd: str | None = None,
) -> dict[str, Any]:
    """List all issues with optional filters.

    Args:
        status: Filter by status (open, closed, all)
        priority: Filter by priority (0-4)
        issue_type: Filter by type (epic, task, bug, feature, chore)
        cwd: Working directory
    """
    args = ["list"]
    if status:
        args.extend(["--status", status])
    if priority is not None:
        args.extend(["-p", str(priority)])
    if issue_type:
        args.extend(["--type", issue_type])

    return run_bd(args, cwd=cwd)


def beads_feature_backlog(
    status: str = "open",
    cwd: str | None = None,
) -> dict[str, Any]:
    """Get feature backlog - all feature-type issues.

    Returns features sorted by priority, with occurrence counts.
    This is the dedicated view for tracking feature ideas.

    Args:
        status: Filter by status (open, closed, all). Default: open
        cwd: Working directory
    """
    args = ["list", "--type", "feature"]
    if status:
        args.extend(["--status", status])

    result = run_bd(args, cwd=cwd)
    if result.get("success") and "data" in result:
        data = result["data"]
        if isinstance(data, list):
            enriched = _enrich_with_occurrences(data)
            return {
                "success": True,
                "count": len(enriched),
                "issues": enriched,
                "view": "feature_backlog",
            }
    return result


def beads_show(issue_id: str | None, cwd: str | None = None) -> dict[str, Any]:
    """Show detailed information about an issue.

    Args:
        issue_id: The issue ID (e.g., 'amplifier-bundle-gtd-ke5')
        cwd: Working directory
    """
    if not issue_id:
        return {"success": False, "error": "issue_id is required"}

    return run_bd(["show", issue_id], cwd=cwd)


def beads_create(
    title: str,
    priority: int = 2,
    issue_type: str = "task",
    description: str | None = None,
    parent: str | None = None,
    cwd: str | None = None,
) -> dict[str, Any]:
    """Create a new issue.

    Args:
        title: Issue title (required)
        priority: Priority 0-4 (0 = highest, default 2)
        issue_type: Type (epic, task, bug, feature, chore)
        description: Detailed description
        parent: Parent issue ID for hierarchy
        cwd: Working directory
    """
    if not title:
        return {"success": False, "error": "title is required"}

    args = ["create", title, "-p", str(priority), "--type", issue_type]
    if description:
        args.extend(["--description", description])
    if parent:
        args.extend(["--parent", parent])

    return run_bd(args, cwd=cwd, json_output=False)


def beads_close(
    issue_id: str | None,
    notes: str | None = None,
    cwd: str | None = None,
) -> dict[str, Any]:
    """Close an issue.

    Args:
        issue_id: The issue ID to close
        notes: Optional closing notes
        cwd: Working directory
    """
    if not issue_id:
        return {"success": False, "error": "issue_id is required"}

    args = ["close", issue_id]
    if notes:
        args.extend(["--notes", notes])

    return run_bd(args, cwd=cwd, json_output=False)


def beads_update(
    issue_id: str | None,
    status: str | None = None,
    priority: int | None = None,
    title: str | None = None,
    notes: str | None = None,
    cwd: str | None = None,
) -> dict[str, Any]:
    """Update an issue.

    Args:
        issue_id: The issue ID to update
        status: New status (open, in_progress, blocked, closed)
        priority: New priority (0-4)
        title: New title
        notes: Add notes
        cwd: Working directory
    """
    if not issue_id:
        return {"success": False, "error": "issue_id is required"}

    args = ["update", issue_id]
    if status:
        args.extend(["--status", status])
    if priority is not None:
        args.extend(["-p", str(priority)])
    if title:
        args.extend(["--title", title])
    if notes:
        args.extend(["--notes", notes])

    return run_bd(args, cwd=cwd, json_output=False)


def beads_dep_add(
    child_id: str | None,
    parent_id: str | None,
    dep_type: str = "blocks",
    cwd: str | None = None,
) -> dict[str, Any]:
    """Add a dependency between issues.

    Args:
        child_id: The child issue ID (depends on parent)
        parent_id: The parent issue ID (blocks child)
        dep_type: Dependency type (blocks, related, parent)
        cwd: Working directory
    """
    if not child_id or not parent_id:
        return {"success": False, "error": "Both child_id and parent_id are required"}

    args = ["dep", "add", child_id, parent_id, "--type", dep_type]
    return run_bd(args, cwd=cwd, json_output=False)


def beads_sync(cwd: str | None = None) -> dict[str, Any]:
    """Sync beads database with git.

    This should be called before git operations to ensure
    the JSONL files are up to date.
    """
    return run_bd(["sync"], cwd=cwd, json_output=False)


def beads_stats(cwd: str | None = None) -> dict[str, Any]:
    """Get project statistics."""
    return run_bd(["stats"], cwd=cwd)


def beads_blocked(cwd: str | None = None) -> dict[str, Any]:
    """Get issues that are blocked by other issues."""
    return run_bd(["blocked"], cwd=cwd)


def beads_search(
    query: str,
    cwd: str | None = None,
) -> dict[str, Any]:
    """Search issues by text.

    Args:
        query: Search query
        cwd: Working directory
    """
    if not query:
        return {"success": False, "error": "query is required"}

    return run_bd(["search", query], cwd=cwd)


def check_beads_initialized(cwd: str | None = None) -> dict[str, Any]:
    """Check if beads is initialized in the given directory.

    Returns:
        dict with 'initialized' boolean and path info
    """
    check_path = Path(cwd) if cwd else Path.cwd()
    beads_dir = check_path / ".beads"

    if beads_dir.exists() and (beads_dir / "beads.db").exists():
        return {
            "initialized": True,
            "path": str(check_path),
            "database": str(beads_dir / "beads.db"),
        }
    else:
        return {
            "initialized": False,
            "path": str(check_path),
            "hint": "Run 'bd init' to initialize beads in this directory",
        }


def get_beads_context(cwd: str | None = None) -> dict[str, Any]:
    """Get current beads context for session awareness.

    Returns a summary of:
    - Ready issues (what to work on)
    - Blocked issues (what's waiting)
    - Recent activity

    This is useful for session start/end to understand state.
    """
    status = check_beads_initialized(cwd)
    if not status["initialized"]:
        return status

    context = {
        "initialized": True,
        "path": status["path"],
    }

    # Get ready issues
    ready = beads_ready(cwd)
    if ready.get("success"):
        context["ready_count"] = ready.get("count", 0)
        context["ready_issues"] = ready.get("issues", [])[:5]  # Top 5

    # Get stats
    stats = beads_stats(cwd)
    if stats.get("success") and "data" in stats:
        context["stats"] = stats["data"]

    # Get blocked issues
    blocked = beads_blocked(cwd)
    if blocked.get("success") and "data" in blocked:
        context["blocked_count"] = len(blocked.get("data", []))

    return context


# =============================================================================
# Multi-repo aggregation operations
# =============================================================================


def beads_ready_all() -> dict[str, Any]:
    """Get ready issues across ALL beads-enabled repositories.

    Aggregates issues from all repos with beads_enabled=true in repos.json.
    Issues are sorted by occurrence count (recurring issues first), then priority.
    Each issue is tagged with _repo indicating its source repository.

    Returns:
        Dict with aggregated issues, count, and metadata including:
        - issues: List of ready issues from all repos
        - repos_queried: Number of repos checked
        - repos_with_issues: Repos that had ready issues
        - errors: Any repos that failed to query
    """
    return _beads_ready_all()


def beads_stats_all() -> dict[str, Any]:
    """Get aggregated statistics across ALL beads-enabled repositories.

    Returns:
        Dict with:
        - totals: Aggregate counts (open, closed, blocked, ready)
        - by_repo: Per-repo breakdown of stats
        - repos_queried: Number of repos checked
    """
    return _beads_stats_all()


def beads_search_all(query: str) -> dict[str, Any]:
    """Search issues across ALL beads-enabled repositories.

    Args:
        query: Search query string

    Returns:
        Dict with matching issues from all repos, tagged with _repo source
    """
    return _beads_search_all(query)


def beads_list_repos() -> dict[str, Any]:
    """List all repositories and their beads status.

    Shows which repos have beads_enabled in repos.json and whether
    they actually have a .beads directory initialized.

    Returns:
        Dict with:
        - repos: List of all repos with beads status
        - beads_enabled_count: Repos with beads_enabled flag
        - has_beads_dir_count: Repos with actual .beads directory
    """
    return _beads_list_repos()


# =============================================================================
# Beads ↔ Reminders linking operations
# =============================================================================


def beads_link_reminder(
    reminder_id: str,
    beads_id: str,
    reminder_title: str | None = None,
    beads_title: str | None = None,
) -> dict[str, Any]:
    """Link an Apple Reminder to a beads issue.

    Creates a bidirectional link stored locally (no EventKit write needed).

    Args:
        reminder_id: UUID of the Apple Reminder (from inbox_list)
        beads_id: ID of the beads issue (e.g., "amplifier-bundle-joi-xyz")
        reminder_title: Optional title for display caching
        beads_title: Optional title for display caching

    Returns:
        Result with link details
    """
    return _link_reminder_to_beads(
        reminder_id=reminder_id,
        beads_id=beads_id,
        reminder_title=reminder_title,
        beads_title=beads_title,
    )


def beads_unlink_reminder(
    reminder_id: str | None = None,
    beads_id: str | None = None,
) -> dict[str, Any]:
    """Remove a link between a reminder and a beads issue.

    Can remove by:
    - Both IDs (specific link)
    - Just reminder_id (all links for that reminder)
    - Just beads_id (all links for that issue)

    Args:
        reminder_id: UUID of the Apple Reminder
        beads_id: ID of the beads issue

    Returns:
        Result with count of removed links
    """
    return _unlink_reminder_from_beads(
        reminder_id=reminder_id,
        beads_id=beads_id,
    )


def beads_list_links() -> dict[str, Any]:
    """List all links between reminders and beads issues.

    Returns:
        Dict with all links and summary statistics
    """
    return _get_all_links()
