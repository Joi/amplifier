#!/usr/bin/env python3
"""
Inbox Processor - Auto-move processed inbox items to appropriate lists.

When items in Inbox have been triaged (given a date or tag), they should
be moved to the appropriate list automatically during sync.

Uses EventKit directly for all operations (no CLI subprocess calls).

Rules:
- #someday tag → Someday/Maybe
- #waiting tag → Waiting For
- Has due date (native) → Next Actions
- Has [due: X] text deadline → Next Actions
"""

import re
from dataclasses import dataclass
from typing import Any, Optional

from .eventkit_sync import (
    EVENTKIT_AVAILABLE,
    create_reminder,
    delete_reminder,
    fetch_all_reminders,
)


@dataclass
class MoveResult:
    """Result of moving a single item."""

    title: str
    from_list: str
    to_list: str
    success: bool
    error: Optional[str] = None


@dataclass
class ProcessResult:
    """Result of processing inbox."""

    items_scanned: int
    items_moved: int
    items_failed: int
    moves: list[MoveResult]
    errors: list[str]


def extract_tags(text: str) -> list[str]:
    """Extract #tags from text."""
    if not text:
        return []
    return [m.group(1).lower() for m in re.finditer(r"#([A-Za-z0-9_:-]+)", text)]


def get_target_list(item: dict[str, Any]) -> Optional[str]:
    """Determine target list for an inbox item based on tags/dates.

    Returns None if item should stay in Inbox.
    """
    title = item.get("title", "")
    notes = item.get("notes", "") or ""
    text = f"{title} {notes}"
    tags = extract_tags(text)

    # Check tags first (explicit intent)
    if "someday" in tags:
        return "Someday/Maybe"

    if "waiting" in tags:
        return "Waiting For"

    # Check for due date (native date picker = tickler, means it's actionable)
    if item.get("dueDate"):
        return "Next Actions"

    # Check for text deadline [due: X]
    if re.search(r"\[due:\s*[^\]]+\]", text, re.IGNORECASE):
        return "Next Actions"

    # No processing indicators - stay in Inbox
    return None


def get_inbox_items() -> list[dict[str, Any]]:
    """Get all items from Inbox using EventKit."""
    if not EVENTKIT_AVAILABLE:
        return []

    try:
        # Fetch all reminders and get Inbox items
        data = fetch_all_reminders(include_completed=False, timeout=30)
        return data.get("byList", {}).get("Inbox", [])
    except Exception:
        return []


def move_item(item: dict[str, Any], target_list: str) -> MoveResult:
    """Move an item from Inbox to target list using EventKit.

    Since EventKit doesn't have a move operation, we:
    1. Create new reminder in target list with same properties
    2. Delete the original from Inbox
    """
    title = item.get("title", "")
    reminder_id = item.get("id", "")

    if not reminder_id:
        return MoveResult(
            title=title,
            from_list="Inbox",
            to_list=target_list,
            success=False,
            error="No reminder ID",
        )

    try:
        # Step 1: Create in target list with preserved properties
        due_date = None
        if item.get("dueDate"):
            # Convert to YYYY-MM-DD format if needed
            due_date = item["dueDate"][:10] if len(item["dueDate"]) >= 10 else None

        # Map EventKit priority (0=none, 1=high, 5=medium, 9=low)
        priority = item.get("priority", 0)

        create_result = create_reminder(
            title=title,
            list_name=target_list,
            notes=item.get("notes"),
            due_date=due_date,
            priority=priority,
        )

        if not create_result.get("success"):
            return MoveResult(
                title=title,
                from_list="Inbox",
                to_list=target_list,
                success=False,
                error=f"Failed to create: {create_result.get('error', 'unknown')}",
            )

        # Step 2: Delete from Inbox
        delete_result = delete_reminder(reminder_id=reminder_id)

        if not delete_result.get("success"):
            return MoveResult(
                title=title,
                from_list="Inbox",
                to_list=target_list,
                success=False,
                error=f"Created but failed to delete original: {delete_result.get('error', 'unknown')}",
            )

        return MoveResult(
            title=title,
            from_list="Inbox",
            to_list=target_list,
            success=True,
        )

    except Exception as e:
        return MoveResult(
            title=title,
            from_list="Inbox",
            to_list=target_list,
            success=False,
            error=str(e),
        )


def process_inbox(dry_run: bool = False) -> ProcessResult:
    """Process inbox and move items to appropriate lists.

    Args:
        dry_run: If True, don't actually move items, just report what would be moved.

    Returns:
        ProcessResult with details of what was moved.
    """
    items = get_inbox_items()
    moves: list[MoveResult] = []
    errors: list[str] = []

    for item in items:
        if item.get("completed"):
            continue

        target = get_target_list(item)
        if target is None:
            continue  # Item should stay in Inbox

        if dry_run:
            moves.append(
                MoveResult(
                    title=item.get("title", ""),
                    from_list="Inbox",
                    to_list=target,
                    success=True,  # Would succeed
                )
            )
        else:
            result = move_item(item, target)
            moves.append(result)
            if not result.success and result.error:
                errors.append(f"{result.title}: {result.error}")

    return ProcessResult(
        items_scanned=len([i for i in items if not i.get("completed")]),
        items_moved=len([m for m in moves if m.success]),
        items_failed=len([m for m in moves if not m.success]),
        moves=moves,
        errors=errors,
    )


def ensure_lists_exist() -> list[str]:
    """Ensure required lists exist, create if missing using EventKit.

    Returns list of lists that were created.
    """
    if not EVENTKIT_AVAILABLE:
        return []

    required = ["Next Actions", "Someday/Maybe", "Waiting For"]
    created = []

    try:
        # Get existing lists by fetching reminders (which returns byList keys)
        data = fetch_all_reminders(include_completed=False, timeout=30)
        existing = list(data.get("byList", {}).keys())

        for list_name in required:
            if list_name not in existing:
                # Create the list by creating a dummy reminder and deleting it
                # This is a workaround since EventKit list creation requires a reminder
                result = create_reminder(
                    title="__list_creation_placeholder__",
                    list_name=list_name,
                )
                if result.get("success"):
                    # Delete the placeholder
                    reminder_id = result.get("reminder", {}).get("id")
                    if reminder_id:
                        delete_reminder(reminder_id=reminder_id)
                    created.append(list_name)

    except Exception:
        pass

    return created
