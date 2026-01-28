#!/usr/bin/env python3
"""
EventKit-based Reminders Sync - Fast native access to Apple Reminders.

Uses EventKit framework (via pyobjc) for much faster and more reliable
access to Reminders compared to AppleScript.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# macOS-specific imports (pyobjc)
EventKit: Any
NSRunLoop: Any
NSDate: Any

try:
    import EventKit  # type: ignore[import-not-found]
    from Foundation import NSRunLoop, NSDate  # type: ignore[import-not-found]

    EVENTKIT_AVAILABLE = True
except ImportError:
    EVENTKIT_AVAILABLE = False


def check_eventkit():
    """Check if EventKit is available and authorized."""
    if not EVENTKIT_AVAILABLE:
        return {
            "available": False,
            "error": "EventKit not installed. Run: uv pip install pyobjc-framework-EventKit",
        }

    status = EventKit.EKEventStore.authorizationStatusForEntityType_(
        EventKit.EKEntityTypeReminder
    )
    status_names = {
        0: "not_determined",
        1: "restricted",
        2: "denied",
        3: "authorized",
        4: "full_access",
        5: "write_only",
    }

    return {
        "available": True,
        "status": status_names.get(status, f"unknown_{status}"),
        "authorized": status in (3, 4),  # Authorized or Full Access
    }


def request_full_access() -> dict:
    """Request full access to Reminders using the modern macOS API.

    This shows the permission dialog ONCE. After the user grants permission,
    it's stored in the TCC database and never prompts again (even after restarts).

    Returns:
        dict with 'granted' bool and 'error' if any
    """
    if not EVENTKIT_AVAILABLE:
        return {"granted": False, "error": "EventKit not installed"}

    # Check current status first
    status = EventKit.EKEventStore.authorizationStatusForEntityType_(
        EventKit.EKEntityTypeReminder
    )

    # Already authorized - no need to request
    if status in (3, 4):  # Authorized or Full Access
        return {"granted": True, "already_authorized": True}

    # Denied or restricted - user must fix in System Settings
    if status in (1, 2):  # Restricted or Denied
        return {
            "granted": False,
            "error": "Permission denied. Please enable in System Settings > Privacy & Security > Reminders",
        }

    # Status is 'not_determined' - need to request
    store = EventKit.EKEventStore.alloc().init()

    # Use modern API (macOS 17+/iOS 17+)
    result = {"granted": False, "error": None}
    done = [False]

    def completion_handler(granted, error):
        result["granted"] = granted
        if error:
            result["error"] = str(error)
        done[0] = True

    # requestFullAccessToRemindersWithCompletion: is the modern API
    # This shows the permission dialog ONCE and stores the result permanently
    store.requestFullAccessToRemindersWithCompletion_(completion_handler)

    # Wait for completion (with timeout)
    timeout = 60  # Give user time to respond to dialog
    start = datetime.now()
    while not done[0] and (datetime.now() - start).seconds < timeout:
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.1)
        )

    if not done[0]:
        return {"granted": False, "error": "Authorization request timed out"}

    return result


def fetch_all_reminders(
    include_completed: bool = False,
    timeout: int = 30,
    max_total_timeout: Optional[int] = None,
) -> dict:
    """Fetch all reminders from all lists using EventKit.

    Args:
        include_completed: Include completed reminders
        timeout: Timeout per list in seconds
        max_total_timeout: Maximum total time for entire operation (default: timeout * 3)

    Returns dict with:
        - syncedAt: timestamp
        - totalCount: total reminders
        - listCount: number of lists
        - byList: dict of list_name -> list of reminder dicts
    """
    import time

    if not EVENTKIT_AVAILABLE:
        raise RuntimeError("EventKit not installed")

    # Ensure we have authorization (requests once if needed, then permanent)
    status = EventKit.EKEventStore.authorizationStatusForEntityType_(
        EventKit.EKEntityTypeReminder
    )
    if status == 0:  # not_determined
        auth_result = request_full_access()
        if not auth_result["granted"]:
            raise RuntimeError(auth_result.get("error", "Authorization request failed"))

    # Set default max_total_timeout if not provided
    if max_total_timeout is None:
        max_total_timeout = timeout * 3  # Reasonable default

    start_time = time.time()

    store = EventKit.EKEventStore.alloc().init()
    calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)

    result = {
        "syncedAt": datetime.now().isoformat(),  # Use local time for cache freshness
        "totalCount": 0,
        "listCount": len(calendars),
        "listsTotal": len(calendars),
        "listsFailed": [],
        "partial": False,
        "byList": {},
    }

    for cal in calendars:
        # Check total timeout
        elapsed = time.time() - start_time
        if elapsed > max_total_timeout:
            remaining = [
                c.title() for c in calendars if c.title() not in result["byList"]
            ]
            result["listsFailed"].extend(remaining)
            result["partial"] = True
            print(
                f"   Total timeout ({max_total_timeout}s) reached after {len(result['byList'])} lists"
            )
            break

        # Calculate remaining time for this list (don't exceed total timeout)
        remaining_time = max_total_timeout - elapsed
        list_timeout = min(timeout, remaining_time)

        list_name = cal.title()

        # Create predicate for reminders
        if include_completed:
            # All reminders (need to fetch both complete and incomplete)
            pred_incomplete = store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(
                None, None, [cal]
            )
            pred_complete = store.predicateForCompletedRemindersWithCompletionDateStarting_ending_calendars_(
                None, None, [cal]
            )
            # Fetch both
            reminders = []
            for pred in [pred_incomplete, pred_complete]:
                batch = _fetch_with_predicate(store, pred, list_timeout)
                if batch:
                    reminders.extend(batch)
        else:
            pred = store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(
                None, None, [cal]
            )
            reminders = _fetch_with_predicate(store, pred, list_timeout)

        if reminders is None:
            result["listsFailed"].append(list_name)
            result["partial"] = True
            continue

        # Convert to dicts
        reminder_list = []
        for r in reminders:
            reminder_dict = {
                "id": r.calendarItemIdentifier(),
                "title": r.title() or "(no title)",
                "completed": r.isCompleted(),
                "priority": r.priority(),
            }

            # Due date
            if r.dueDateComponents():
                due = r.dueDateComponents()
                reminder_dict["dueDate"] = (
                    f"{due.year()}-{due.month():02d}-{due.day():02d}"
                )

            # Notes
            if r.notes():
                reminder_dict["notes"] = r.notes()

            reminder_list.append(reminder_dict)

        result["byList"][list_name] = reminder_list
        result["totalCount"] += len(reminder_list)

    return result


def _fetch_with_predicate(store, predicate, timeout: float = 30):
    """Fetch reminders with a predicate, with timeout."""
    reminders = []
    done = [False]

    def callback(result):
        if result:
            reminders.extend(result)
        done[0] = True

    store.fetchRemindersMatchingPredicate_completion_(predicate, callback)

    # Wait for completion
    start = datetime.now()
    while not done[0] and (datetime.now() - start).seconds < timeout:
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.1)
        )

    if not done[0]:
        return None  # Timeout

    return reminders


def sync_reminders_eventkit(
    cache_path: str, include_completed: bool = False, timeout: int = 60
) -> dict:
    """Sync all reminders to cache using EventKit.

    Args:
        cache_path: Path to the cache JSON file
        include_completed: Whether to include completed reminders
        timeout: Total timeout in seconds (default 60s) - used as max_total_timeout

    Returns:
        Summary dict with sync results
    """
    import time

    start_time = time.time()

    cache_file = Path(cache_path).expanduser()
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    # Backup existing cache
    if cache_file.exists():
        backup_path = cache_file.with_suffix(".backup.json")
        shutil.copy2(cache_file, backup_path)
        print(f"   Backed up existing cache to {backup_path.name}")

    print("   Fetching reminders via EventKit...")
    # Use timeout as max_total_timeout, with reasonable per-list timeout
    per_list_timeout = min(15, timeout // 4)  # 15s per list max, or 1/4 of total
    data = fetch_all_reminders(
        include_completed=include_completed,
        timeout=per_list_timeout,
        max_total_timeout=timeout,
    )

    elapsed = time.time() - start_time

    # Write cache
    with open(cache_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"   Completed in {elapsed:.1f}s")

    return {
        "success": len(data["listsFailed"]) == 0,
        "partial": data["partial"],
        "total": data["totalCount"],
        "lists": data["listCount"],
        "lists_synced": data["listCount"] - len(data["listsFailed"]),
        "lists_failed": data["listsFailed"],
        "cache_path": str(cache_file),
        "elapsed_seconds": elapsed,
    }


# ==================== WRITE OPERATIONS ====================


def _get_store():
    """Get an authorized EventKit store.

    Automatically requests full access if not yet authorized.
    The permission dialog only appears ONCE - after that, the permission
    is stored permanently in the TCC database.
    """
    if not EVENTKIT_AVAILABLE:
        raise RuntimeError(
            "EventKit not installed. Run: uv pip install pyobjc-framework-EventKit"
        )

    # Check current status
    status = EventKit.EKEventStore.authorizationStatusForEntityType_(
        EventKit.EKEntityTypeReminder
    )

    # If not yet determined, request full access
    if status == 0:  # not_determined
        auth_result = request_full_access()
        if not auth_result["granted"]:
            raise RuntimeError(auth_result.get("error", "Authorization request failed"))
        # Re-check status after authorization
        status = EventKit.EKEventStore.authorizationStatusForEntityType_(
            EventKit.EKEntityTypeReminder
        )

    if status not in (3, 4):  # Authorized or Full Access
        status_names = {
            0: "not_determined",
            1: "restricted",
            2: "denied",
            3: "authorized",
            4: "full_access",
            5: "write_only",
        }
        status_name = status_names.get(status, f"unknown_{status}")
        raise RuntimeError(
            f"Reminders access not authorized (status: {status_name}). "
            "Please enable in System Settings > Privacy & Security > Reminders"
        )

    return EventKit.EKEventStore.alloc().init()


def _find_reminder_by_id(store, reminder_id: str):
    """Find a reminder by its calendarItemIdentifier."""
    # EventKit doesn't have a direct lookup by ID, so we search all calendars
    calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)

    for cal in calendars:
        # Search incomplete reminders
        pred = (
            store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(
                None, None, [cal]
            )
        )
        reminders = _fetch_with_predicate(store, pred, timeout=10)
        if reminders:
            for r in reminders:
                if r.calendarItemIdentifier() == reminder_id:
                    return r

        # Also search completed reminders
        pred = store.predicateForCompletedRemindersWithCompletionDateStarting_ending_calendars_(
            None, None, [cal]
        )
        reminders = _fetch_with_predicate(store, pred, timeout=10)
        if reminders:
            for r in reminders:
                if r.calendarItemIdentifier() == reminder_id:
                    return r

    return None


def _find_reminder_by_title(store, title: str, list_name: Optional[str] = None):
    """Find a reminder by title (and optionally list name)."""
    calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)

    for cal in calendars:
        if list_name and cal.title() != list_name:
            continue

        pred = (
            store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(
                None, None, [cal]
            )
        )
        reminders = _fetch_with_predicate(store, pred, timeout=10)
        if reminders:
            for r in reminders:
                if r.title() == title:
                    return r

    return None


def update_reminder(
    reminder_id: Optional[str] = None,
    title_match: Optional[str] = None,
    list_name: Optional[str] = None,
    new_title: Optional[str] = None,
    due_date: Optional[str] = None,  # YYYY-MM-DD format
    notes: Optional[str] = None,
    priority: Optional[int] = None,  # 0=none, 1=high, 5=medium, 9=low
    completed: Optional[bool] = None,
    new_list: Optional[str] = None,  # Move to a different list
) -> dict:
    """Update a reminder's properties.

    Args:
        reminder_id: The reminder's calendarItemIdentifier (preferred)
        title_match: Find reminder by exact title match (fallback)
        list_name: List to search in (optional, for title_match)
        new_title: New title for the reminder
        due_date: Due date in YYYY-MM-DD format, or "today", or None to clear
        notes: New notes text
        priority: Priority (0=none, 1=high, 5=medium, 9=low)
        completed: Set completion status
        new_list: Move the reminder to a different list

    Returns:
        dict with success status and reminder info
    """
    try:
        from Foundation import NSDateComponents  # type: ignore[import-not-found]
    except ImportError:
        return {"success": False, "error": "Foundation framework not available"}

    store = _get_store()

    # Find the reminder
    reminder = None
    if reminder_id:
        reminder = _find_reminder_by_id(store, reminder_id)
    elif title_match:
        reminder = _find_reminder_by_title(store, title_match, list_name)

    if not reminder:
        return {
            "success": False,
            "error": f"Reminder not found: {reminder_id or title_match}",
        }

    # Apply updates
    if new_title is not None:
        reminder.setTitle_(new_title)

    if due_date is not None:
        if due_date == "" or due_date.lower() == "none":
            # Clear due date
            reminder.setDueDateComponents_(None)
        else:
            # Parse and set due date
            if due_date.lower() == "today":
                target = datetime.now()
            else:
                target = datetime.strptime(due_date, "%Y-%m-%d")

            components = NSDateComponents.alloc().init()
            components.setYear_(target.year)
            components.setMonth_(target.month)
            components.setDay_(target.day)
            reminder.setDueDateComponents_(components)

    if notes is not None:
        reminder.setNotes_(notes)

    if priority is not None:
        reminder.setPriority_(priority)

    if completed is not None:
        reminder.setCompleted_(completed)

    # Move to a different list if requested
    if new_list is not None:
        calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)
        target_cal = None
        for cal in calendars:
            if cal.title() == new_list:
                target_cal = cal
                break

        if not target_cal:
            return {"success": False, "error": f"List not found: {new_list}"}

        reminder.setCalendar_(target_cal)

    # Save changes
    success, error = store.saveReminder_commit_error_(reminder, True, None)

    if not success:
        return {"success": False, "error": str(error) if error else "Save failed"}

    return {
        "success": True,
        "reminder": {
            "id": reminder.calendarItemIdentifier(),
            "title": reminder.title(),
            "completed": reminder.isCompleted(),
            "due_date": _format_due_date(reminder),
            "list": reminder.calendar().title(),
        },
    }


def create_reminder(
    title: str,
    list_name: str,
    notes: Optional[str] = None,
    due_date: Optional[str] = None,  # YYYY-MM-DD format or "today"
    priority: int = 0,  # 0=none, 1=high, 5=medium, 9=low
) -> dict:
    """Create a new reminder in the specified list.

    Args:
        title: The reminder title
        list_name: Name of the list to create in (will be created if doesn't exist)
        notes: Optional notes text
        due_date: Due date in YYYY-MM-DD format, or "today"
        priority: Priority (0=none, 1=high, 5=medium, 9=low)

    Returns:
        dict with success status and reminder info
    """
    store = _get_store()

    # Find the target calendar/list
    calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)
    target_cal = None
    for cal in calendars:
        if cal.title() == list_name:
            target_cal = cal
            break

    # Create the list if it doesn't exist
    if not target_cal:
        # Find the default source for reminders
        sources = store.sources()
        reminder_source = None
        for source in sources:
            # Prefer iCloud or Local source
            source_type = source.sourceType()
            if source_type in (1, 2, 4):  # Local, Exchange, iCloud
                reminder_source = source
                if source_type == 4:  # Prefer iCloud
                    break

        if not reminder_source and sources:
            reminder_source = sources[0]

        if not reminder_source:
            return {"success": False, "error": "No reminder source available"}

        target_cal = EventKit.EKCalendar.calendarForEntityType_eventStore_(
            EventKit.EKEntityTypeReminder, store
        )
        target_cal.setTitle_(list_name)
        target_cal.setSource_(reminder_source)

        success, error = store.saveCalendar_commit_error_(target_cal, True, None)
        if not success:
            return {
                "success": False,
                "error": f"Failed to create list: {error if error else 'unknown'}",
            }

    # Create the reminder
    reminder = EventKit.EKReminder.reminderWithEventStore_(store)
    reminder.setTitle_(title)
    reminder.setCalendar_(target_cal)

    if notes:
        reminder.setNotes_(notes)

    if priority:
        reminder.setPriority_(priority)

    # Set due date if provided
    if due_date:
        try:
            from Foundation import NSDateComponents  # type: ignore[import-not-found]

            components = NSDateComponents.alloc().init()

            if due_date == "today":
                from datetime import date

                today = date.today()
                components.setYear_(today.year)
                components.setMonth_(today.month)
                components.setDay_(today.day)
            else:
                parts = due_date.split("-")
                components.setYear_(int(parts[0]))
                components.setMonth_(int(parts[1]))
                components.setDay_(int(parts[2]))

            reminder.setDueDateComponents_(components)
        except Exception as e:
            return {"success": False, "error": f"Invalid due_date format: {e}"}

    # Save the reminder
    success, error = store.saveReminder_commit_error_(reminder, True, None)

    if not success:
        return {
            "success": False,
            "error": f"Failed to save reminder: {error if error else 'unknown'}",
        }

    return {
        "success": True,
        "reminder": {
            "id": reminder.calendarItemIdentifier(),
            "title": reminder.title(),
            "list": target_cal.title(),
            "notes": reminder.notes() if reminder.notes() else None,
            "due_date": _format_due_date(reminder),
        },
    }


def delete_reminder(
    reminder_id: Optional[str] = None,
    title_match: Optional[str] = None,
    list_name: Optional[str] = None,
) -> dict:
    """Delete a reminder.

    Args:
        reminder_id: The reminder's calendarItemIdentifier (preferred)
        title_match: Find reminder by exact title match (fallback)
        list_name: List to search in (optional, for title_match)

    Returns:
        dict with success status
    """
    store = _get_store()

    # Find the reminder
    reminder = None
    if reminder_id:
        reminder = _find_reminder_by_id(store, reminder_id)
    elif title_match:
        reminder = _find_reminder_by_title(store, title_match, list_name)

    if not reminder:
        return {
            "success": False,
            "error": f"Reminder not found: {reminder_id or title_match}",
        }

    title = reminder.title()
    list_name = reminder.calendar().title()

    # Delete the reminder
    success, error = store.removeReminder_commit_error_(reminder, True, None)

    if not success:
        return {"success": False, "error": str(error) if error else "Delete failed"}

    return {"success": True, "deleted": {"title": title, "list": list_name}}


def complete_reminder(
    reminder_id: Optional[str] = None,
    title_match: Optional[str] = None,
    list_name: Optional[str] = None,
) -> dict:
    """Mark a reminder as complete.

    Args:
        reminder_id: The reminder's calendarItemIdentifier (preferred)
        title_match: Find reminder by exact title match (fallback)
        list_name: List to search in (optional, for title_match)

    Returns:
        dict with success status
    """
    return update_reminder(
        reminder_id=reminder_id,
        title_match=title_match,
        list_name=list_name,
        completed=True,
    )


def _format_due_date(reminder) -> Optional[str]:
    """Format a reminder's due date as YYYY-MM-DD."""
    if reminder.dueDateComponents():
        due = reminder.dueDateComponents()
        return f"{due.year()}-{due.month():02d}-{due.day():02d}"
    return None


if __name__ == "__main__":
    import sys

    # Check EventKit status
    status = check_eventkit()
    if not status["available"]:
        print(f"Error: {status['error']}")
        sys.exit(1)

    if not status["authorized"]:
        print(f"Error: Reminders access not authorized (status: {status['status']})")
        print(
            "Please grant Reminders access in System Preferences > Privacy & Security > Reminders"
        )
        sys.exit(1)

    # Default cache path
    cache_path = os.path.expanduser("~/switchboard/reminders/reminders_cache.json")

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            print(f"EventKit: {status}")
        elif cmd == "sync":
            print("Syncing reminders via EventKit...")
            result = sync_reminders_eventkit(cache_path)
            print(f"Result: {json.dumps(result, indent=2)}")
        elif cmd == "lists":
            if not EVENTKIT_AVAILABLE:
                print("EventKit not available")
                sys.exit(1)
            store = EventKit.EKEventStore.alloc().init()  # type: ignore[union-attr]
            calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)  # type: ignore[union-attr]
            print(f"Found {len(calendars)} reminder lists:")
            for cal in calendars:
                print(f"  - {cal.title()}")
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: eventkit_sync.py [status|sync|lists]")
    else:
        print("Usage: eventkit_sync.py [status|sync|lists]")
