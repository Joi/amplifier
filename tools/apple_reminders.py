#!/usr/bin/env python3
"""
Apple Reminders Tool - Create, read, list, complete, and manage Apple Reminders.

Uses EventKit (native macOS framework) for fast, reliable access to Reminders.
Falls back to AppleScript via osascript when EventKit is unavailable.

Usage:
    # Add a reminder to a list
    python apple_reminders.py add "Buy groceries" --list "Shopping"
    python apple_reminders.py add "Call dentist" --list "Personal" --due "tomorrow 2pm"
    python apple_reminders.py add "Review PR" --list "Amplifier" --notes "Check the new feature"

    # List reminders
    python apple_reminders.py list                      # All incomplete reminders
    python apple_reminders.py list --list "Shopping"    # From specific list
    python apple_reminders.py list --all                # Include completed

    # Complete a reminder
    python apple_reminders.py complete "Buy groceries"
    python apple_reminders.py complete --id "x-apple-reminder://..."

    # Show reminder lists
    python apple_reminders.py lists

    # Search reminders
    python apple_reminders.py search "dentist"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from datetime import timedelta
from typing import Any

# =============================================================================
# EventKit Support (macOS native framework - fast, reliable)
# =============================================================================

EventKit: Any
NSRunLoop: Any
NSDate: Any
NSDateComponents: Any

try:
    import EventKit  # type: ignore[import-not-found]
    from Foundation import NSDate  # type: ignore[import-not-found]
    from Foundation import NSDateComponents  # type: ignore[import-not-found]
    from Foundation import NSRunLoop  # type: ignore[import-not-found]

    EVENTKIT_AVAILABLE = True
except ImportError:
    EVENTKIT_AVAILABLE = False


def _get_eventkit_store():
    """Get an authorized EventKit store."""
    if not EVENTKIT_AVAILABLE:
        return None

    store = EventKit.EKEventStore.alloc().init()
    status = EventKit.EKEventStore.authorizationStatusForEntityType_(EventKit.EKEntityTypeReminder)

    # Status 3 = Authorized, 4 = Full Access
    if status not in (3, 4):
        return None

    return store


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
        NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.1))

    if not done[0]:
        return None  # Timeout

    return reminders


# =============================================================================
# AppleScript Fallback (slower, but works without EventKit)
# =============================================================================


def run_applescript(script: str) -> str:
    """Execute AppleScript and return result. Uses temp file for complex scripts."""
    # Use temp file to avoid shell escaping issues
    with tempfile.NamedTemporaryFile(mode="w", suffix=".scpt", delete=False) as f:
        f.write(script)
        temp_path = f.name

    try:
        result = subprocess.run(["osascript", temp_path], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"AppleScript error: {e.stderr}")
    finally:
        os.unlink(temp_path)


def escape_applescript_string(s: str) -> str:
    """Escape a string for use in AppleScript."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def parse_due_date(due_str: str) -> str | None:
    """Parse human-friendly due date to AppleScript date format."""
    if not due_str:
        return None

    due_lower = due_str.lower().strip()
    now = datetime.now()

    # Handle relative dates
    if due_lower == "today":
        target = now.replace(hour=17, minute=0, second=0)  # Default 5 PM
    elif due_lower == "tomorrow":
        target = (now + timedelta(days=1)).replace(hour=17, minute=0, second=0)
    elif due_lower == "next week":
        target = (now + timedelta(weeks=1)).replace(hour=9, minute=0, second=0)
    elif "tomorrow" in due_lower:
        # "tomorrow 2pm" style
        target = now + timedelta(days=1)
        time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", due_lower)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            ampm = time_match.group(3)
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            target = target.replace(hour=hour, minute=minute, second=0)
        else:
            target = target.replace(hour=17, minute=0, second=0)
    else:
        # Try to parse as date
        try:
            # Try various formats
            for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y", "%m/%d"]:
                try:
                    target = datetime.strptime(due_str, fmt)
                    if fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m/%d"]:
                        target = target.replace(hour=17, minute=0, second=0)
                    break
                except ValueError:
                    continue
            else:
                # Fallback: just use as-is and let AppleScript try
                return due_str
        except Exception:
            return due_str

    # Format for AppleScript: "January 7, 2026 5:00 PM"
    return target.strftime("%B %d, %Y %I:%M %p")


def add_reminder_applescript(
    title: str,
    list_name: str = "Reminders",
    due_date: str | None = None,
    notes: str | None = None,
    priority: int = 0,
) -> dict:
    """Add a new reminder to a list using AppleScript (fallback)."""
    escaped_title = escape_applescript_string(title)
    escaped_list = escape_applescript_string(list_name)

    props = [f'name:"{escaped_title}"']

    if notes:
        escaped_notes = escape_applescript_string(notes)
        props.append(f'body:"{escaped_notes}"')

    if priority > 0:
        # Apple priority: 0=none, 1=high, 5=medium, 9=low
        apple_priority = {1: 1, 2: 5, 3: 9}.get(priority, 0)
        props.append(f"priority:{apple_priority}")

    props_str = ", ".join(props)

    # Build script
    if due_date:
        parsed_due = parse_due_date(due_date)
        script = f'''
tell application "Reminders"
    set targetList to list "{escaped_list}"
    set dueDate to date "{parsed_due}"
    set newReminder to make new reminder at targetList with properties {{{props_str}, due date:dueDate}}
    return id of newReminder
end tell
'''
    else:
        script = f'''
tell application "Reminders"
    set targetList to list "{escaped_list}"
    set newReminder to make new reminder at targetList with properties {{{props_str}}}
    return id of newReminder
end tell
'''

    reminder_id = run_applescript(script)

    return {
        "success": True,
        "id": reminder_id,
        "title": title,
        "list": list_name,
        "due_date": due_date,
        "message": f'Created reminder "{title}" in list "{list_name}"',
    }


def list_reminders_applescript(
    list_name: str | None = None, include_completed: bool = False, limit: int = 50
) -> list[dict]:
    """List reminders using AppleScript (fallback)."""

    if list_name:
        escaped_list = escape_applescript_string(list_name)
        list_filter = f'list "{escaped_list}"'
    else:
        list_filter = "every list"

    completed_filter = "" if include_completed else "whose completed is false"

    script = f"""
tell application "Reminders"
    set output to ""
    set counter to 0
    repeat with aList in ({list_filter} as list)
        set listName to name of aList
        repeat with r in (reminders of aList {completed_filter})
            if counter < {limit} then
                set rId to id of r
                set rName to name of r
                set rCompleted to completed of r
                set rPriority to priority of r
                try
                    set rDue to (due date of r) as string
                on error
                    set rDue to "none"
                end try
                try
                    set rNotes to body of r
                on error
                    set rNotes to ""
                end try
                set output to output & rId & "|||" & rName & "|||" & listName & "|||" & rCompleted & "|||" & rPriority & "|||" & rDue & "|||" & rNotes & linefeed
                set counter to counter + 1
            end if
        end repeat
    end repeat
    return output
end tell
"""

    output = run_applescript(script)

    reminders = []
    if output:
        for line in output.strip().split("\n"):
            if line.strip():
                parts = line.split("|||")
                if len(parts) >= 6:
                    reminders.append(
                        {
                            "id": parts[0].strip(),
                            "title": parts[1].strip(),
                            "list": parts[2].strip(),
                            "completed": parts[3].strip() == "true",
                            "priority": int(parts[4].strip()) if parts[4].strip().isdigit() else 0,
                            "due_date": parts[5].strip() if parts[5].strip() != "none" else None,
                            "notes": parts[6].strip() if len(parts) > 6 else "",
                        }
                    )

    return reminders


def get_lists_applescript() -> list[dict]:
    """Get all reminder lists using AppleScript (fallback)."""
    script = """
tell application "Reminders"
    set output to ""
    repeat with aList in lists
        set listId to id of aList
        set listName to name of aList
        set reminderCount to count of (reminders of aList whose completed is false)
        set output to output & listId & "|||" & listName & "|||" & reminderCount & linefeed
    end repeat
    return output
end tell
"""

    output = run_applescript(script)

    lists = []
    if output:
        for line in output.strip().split("\n"):
            if line.strip():
                parts = line.split("|||")
                if len(parts) >= 3:
                    lists.append(
                        {
                            "id": parts[0].strip(),
                            "name": parts[1].strip(),
                            "incomplete_count": int(parts[2].strip()) if parts[2].strip().isdigit() else 0,
                        }
                    )

    return lists


def complete_reminder_applescript(title: str | None = None, reminder_id: str | None = None) -> dict:
    """Mark a reminder as completed using AppleScript (fallback)."""
    if reminder_id:
        escaped_id = escape_applescript_string(reminder_id)
        script = f'''
tell application "Reminders"
    set r to reminder id "{escaped_id}"
    set completed of r to true
    return name of r
end tell
'''
    elif title:
        escaped_title = escape_applescript_string(title)
        script = f'''
tell application "Reminders"
    set found to false
    repeat with aList in lists
        repeat with r in (reminders of aList whose completed is false)
            if name of r is "{escaped_title}" then
                set completed of r to true
                set found to true
                return name of r
            end if
        end repeat
    end repeat
    if not found then
        error "Reminder not found: {escaped_title}"
    end if
end tell
'''
    else:
        raise ValueError("Either title or reminder_id must be provided")

    result = run_applescript(script)
    return {"success": True, "title": result, "message": f"Completed reminder: {result}"}


def search_reminders_applescript(query: str, include_completed: bool = False) -> list[dict]:
    """Search reminders by title using AppleScript (fallback)."""
    escaped_query = escape_applescript_string(query.lower())
    completed_filter = "" if include_completed else "whose completed is false"

    script = f'''
tell application "Reminders"
    set output to ""
    set searchQuery to "{escaped_query}"
    repeat with aList in lists
        set listName to name of aList
        repeat with r in (reminders of aList {completed_filter})
            set rName to name of r
            if rName contains searchQuery then
                set rId to id of r
                set rCompleted to completed of r
                try
                    set rDue to (due date of r) as string
                on error
                    set rDue to "none"
                end try
                set output to output & rId & "|||" & rName & "|||" & listName & "|||" & rCompleted & "|||" & rDue & linefeed
            end if
        end repeat
    end repeat
    return output
end tell
'''

    output = run_applescript(script)

    reminders = []
    if output:
        for line in output.strip().split("\n"):
            if line.strip():
                parts = line.split("|||")
                if len(parts) >= 4:
                    reminders.append(
                        {
                            "id": parts[0].strip(),
                            "title": parts[1].strip(),
                            "list": parts[2].strip(),
                            "completed": parts[3].strip() == "true",
                            "due_date": parts[4].strip() if len(parts) > 4 and parts[4].strip() != "none" else None,
                        }
                    )

    return reminders


# =============================================================================
# EventKit Implementations (fast, native)
# =============================================================================


def get_lists_eventkit() -> list[dict]:
    """Get all reminder lists using EventKit."""
    store = _get_eventkit_store()
    if not store:
        raise RuntimeError("EventKit not available")

    calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)

    lists = []
    for cal in calendars:
        # Count incomplete reminders
        pred = store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(None, None, [cal])
        reminders = _fetch_with_predicate(store, pred, timeout=5)
        count = len(reminders) if reminders else 0

        lists.append({"id": cal.calendarIdentifier(), "name": cal.title(), "incomplete_count": count})

    return lists


def list_reminders_eventkit(
    list_name: str | None = None, include_completed: bool = False, limit: int = 50
) -> list[dict]:
    """List reminders using EventKit."""
    store = _get_eventkit_store()
    if not store:
        raise RuntimeError("EventKit not available")

    calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)

    # Filter to specific list if requested
    if list_name:
        calendars = [cal for cal in calendars if cal.title() == list_name]

    reminders = []
    for cal in calendars:
        if len(reminders) >= limit:
            break

        # Fetch incomplete reminders
        pred = store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(None, None, [cal])
        batch = _fetch_with_predicate(store, pred, timeout=10)

        if include_completed:
            # Also fetch completed
            pred_complete = store.predicateForCompletedRemindersWithCompletionDateStarting_ending_calendars_(
                None, None, [cal]
            )
            completed_batch = _fetch_with_predicate(store, pred_complete, timeout=10)
            if completed_batch:
                batch = (batch or []) + completed_batch

        if batch:
            for r in batch:
                if len(reminders) >= limit:
                    break

                reminder_dict = {
                    "id": r.calendarItemIdentifier(),
                    "title": r.title() or "(no title)",
                    "list": cal.title(),
                    "completed": r.isCompleted(),
                    "priority": r.priority(),
                    "notes": r.notes() or "",
                }

                # Due date
                if r.dueDateComponents():
                    due = r.dueDateComponents()
                    reminder_dict["due_date"] = f"{due.year()}-{due.month():02d}-{due.day():02d}"
                else:
                    reminder_dict["due_date"] = None

                reminders.append(reminder_dict)

    return reminders


def add_reminder_eventkit(
    title: str,
    list_name: str = "Reminders",
    due_date: str | None = None,
    notes: str | None = None,
    priority: int = 0,
) -> dict:
    """Add a new reminder using EventKit."""
    store = _get_eventkit_store()
    if not store:
        raise RuntimeError("EventKit not available")

    # Find the target calendar/list
    calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)
    target_cal = None
    for cal in calendars:
        if cal.title() == list_name:
            target_cal = cal
            break

    if not target_cal:
        # Try to create the list
        sources = store.sources()
        reminder_source = None
        for source in sources:
            source_type = source.sourceType()
            if source_type in (1, 2, 4):  # Local, Exchange, iCloud
                reminder_source = source
                if source_type == 4:  # Prefer iCloud
                    break

        if not reminder_source and sources:
            reminder_source = sources[0]

        if not reminder_source:
            raise RuntimeError("No reminder source available")

        target_cal = EventKit.EKCalendar.calendarForEntityType_eventStore_(EventKit.EKEntityTypeReminder, store)
        target_cal.setTitle_(list_name)
        target_cal.setSource_(reminder_source)

        success, error = store.saveCalendar_commit_error_(target_cal, True, None)
        if not success:
            raise RuntimeError(f"Failed to create list: {error}")

    # Create the reminder
    reminder = EventKit.EKReminder.reminderWithEventStore_(store)
    reminder.setTitle_(title)
    reminder.setCalendar_(target_cal)

    if notes:
        reminder.setNotes_(notes)

    if priority > 0:
        # Convert user priority (1=high, 2=medium, 3=low) to Apple priority (1, 5, 9)
        apple_priority = {1: 1, 2: 5, 3: 9}.get(priority, 0)
        reminder.setPriority_(apple_priority)

    # Set due date if provided
    if due_date:
        # Parse due date
        target = _parse_due_date_for_eventkit(due_date)
        if target:
            components = NSDateComponents.alloc().init()
            components.setYear_(target.year)
            components.setMonth_(target.month)
            components.setDay_(target.day)
            if target.hour != 0 or target.minute != 0:
                components.setHour_(target.hour)
                components.setMinute_(target.minute)
            reminder.setDueDateComponents_(components)

    # Save the reminder
    success, error = store.saveReminder_commit_error_(reminder, True, None)

    if not success:
        raise RuntimeError(f"Failed to save reminder: {error}")

    return {
        "success": True,
        "id": reminder.calendarItemIdentifier(),
        "title": title,
        "list": list_name,
        "due_date": due_date,
        "message": f'Created reminder "{title}" in list "{list_name}"',
    }


def _parse_due_date_for_eventkit(due_str: str) -> datetime | None:
    """Parse human-friendly due date to datetime for EventKit."""
    if not due_str:
        return None

    due_lower = due_str.lower().strip()
    now = datetime.now()

    if due_lower == "today":
        return now.replace(hour=17, minute=0, second=0, microsecond=0)
    if due_lower == "tomorrow":
        return (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
    if due_lower == "next week":
        return (now + timedelta(weeks=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    if "tomorrow" in due_lower:
        target = now + timedelta(days=1)
        time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", due_lower)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            ampm = time_match.group(3)
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            return target.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return target.replace(hour=17, minute=0, second=0, microsecond=0)
    # Try to parse as date
    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y", "%m/%d"]:
        try:
            target = datetime.strptime(due_str, fmt)
            if fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m/%d"]:
                target = target.replace(hour=17, minute=0, second=0)
            return target
        except ValueError:
            continue

    return None


def complete_reminder_eventkit(title: str | None = None, reminder_id: str | None = None) -> dict:
    """Mark a reminder as completed using EventKit."""
    store = _get_eventkit_store()
    if not store:
        raise RuntimeError("EventKit not available")

    reminder = None

    if reminder_id:
        reminder = _find_reminder_by_id_eventkit(store, reminder_id)
    elif title:
        reminder = _find_reminder_by_title_eventkit(store, title)
    else:
        raise ValueError("Either title or reminder_id must be provided")

    if not reminder:
        raise RuntimeError(f"Reminder not found: {reminder_id or title}")

    reminder_title = reminder.title()
    reminder.setCompleted_(True)

    success, error = store.saveReminder_commit_error_(reminder, True, None)

    if not success:
        raise RuntimeError(f"Failed to complete reminder: {error}")

    return {"success": True, "title": reminder_title, "message": f"Completed reminder: {reminder_title}"}


def _find_reminder_by_id_eventkit(store, reminder_id: str):
    """Find a reminder by its calendarItemIdentifier."""
    calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)

    for cal in calendars:
        # Search incomplete reminders
        pred = store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(None, None, [cal])
        reminders = _fetch_with_predicate(store, pred, timeout=5)
        if reminders:
            for r in reminders:
                if r.calendarItemIdentifier() == reminder_id:
                    return r

        # Also search completed reminders
        pred = store.predicateForCompletedRemindersWithCompletionDateStarting_ending_calendars_(None, None, [cal])
        reminders = _fetch_with_predicate(store, pred, timeout=5)
        if reminders:
            for r in reminders:
                if r.calendarItemIdentifier() == reminder_id:
                    return r

    return None


def _find_reminder_by_title_eventkit(store, title: str):
    """Find a reminder by title."""
    calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)

    for cal in calendars:
        pred = store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(None, None, [cal])
        reminders = _fetch_with_predicate(store, pred, timeout=5)
        if reminders:
            for r in reminders:
                if r.title() == title:
                    return r

    return None


def search_reminders_eventkit(query: str, include_completed: bool = False) -> list[dict]:
    """Search reminders by title using EventKit."""
    store = _get_eventkit_store()
    if not store:
        raise RuntimeError("EventKit not available")

    calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)
    query_lower = query.lower()

    results = []
    for cal in calendars:
        # Fetch incomplete reminders
        pred = store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(None, None, [cal])
        batch = _fetch_with_predicate(store, pred, timeout=10)

        if include_completed:
            pred_complete = store.predicateForCompletedRemindersWithCompletionDateStarting_ending_calendars_(
                None, None, [cal]
            )
            completed_batch = _fetch_with_predicate(store, pred_complete, timeout=10)
            if completed_batch:
                batch = (batch or []) + completed_batch

        if batch:
            for r in batch:
                title = r.title() or ""
                if query_lower in title.lower():
                    due_date = None
                    if r.dueDateComponents():
                        due = r.dueDateComponents()
                        due_date = f"{due.year()}-{due.month():02d}-{due.day():02d}"

                    results.append(
                        {
                            "id": r.calendarItemIdentifier(),
                            "title": title,
                            "list": cal.title(),
                            "completed": r.isCompleted(),
                            "due_date": due_date,
                        }
                    )

    return results


# =============================================================================
# Public API (tries EventKit first, falls back to AppleScript)
# =============================================================================


def get_lists() -> list[dict]:
    """Get all reminder lists. Uses EventKit if available, else AppleScript."""
    try:
        if EVENTKIT_AVAILABLE:
            return get_lists_eventkit()
    except Exception:
        pass  # Fall back to AppleScript
    return get_lists_applescript()


def list_reminders(list_name: str | None = None, include_completed: bool = False, limit: int = 50) -> list[dict]:
    """List reminders. Uses EventKit if available, else AppleScript."""
    try:
        if EVENTKIT_AVAILABLE:
            return list_reminders_eventkit(list_name, include_completed, limit)
    except Exception:
        pass  # Fall back to AppleScript
    return list_reminders_applescript(list_name, include_completed, limit)


def add_reminder(
    title: str,
    list_name: str = "Reminders",
    due_date: str | None = None,
    notes: str | None = None,
    priority: int = 0,
) -> dict:
    """Add a new reminder. Uses EventKit if available, else AppleScript."""
    try:
        if EVENTKIT_AVAILABLE:
            return add_reminder_eventkit(title, list_name, due_date, notes, priority)
    except Exception:
        pass  # Fall back to AppleScript
    return add_reminder_applescript(title, list_name, due_date, notes, priority)


def complete_reminder(title: str | None = None, reminder_id: str | None = None) -> dict:
    """Mark a reminder as completed. Uses EventKit if available, else AppleScript."""
    try:
        if EVENTKIT_AVAILABLE:
            return complete_reminder_eventkit(title, reminder_id)
    except Exception:
        pass  # Fall back to AppleScript
    return complete_reminder_applescript(title, reminder_id)


def search_reminders(query: str, include_completed: bool = False) -> list[dict]:
    """Search reminders by title. Uses EventKit if available, else AppleScript."""
    try:
        if EVENTKIT_AVAILABLE:
            return search_reminders_eventkit(query, include_completed)
    except Exception:
        pass  # Fall back to AppleScript
    return search_reminders_applescript(query, include_completed)


def main():
    parser = argparse.ArgumentParser(
        description="Apple Reminders CLI - Create, list, and manage reminders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s add "Buy milk" --list "Shopping"
    %(prog)s add "Call mom" --due "tomorrow 2pm" --list "Personal"
    %(prog)s list --list "Work"
    %(prog)s complete "Buy milk"
    %(prog)s search "meeting"
    %(prog)s lists
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new reminder")
    add_parser.add_argument("title", help="Reminder title")
    add_parser.add_argument("--list", "-l", default="Reminders", help="List name (default: Reminders)")
    add_parser.add_argument("--due", "-d", help='Due date (e.g., "tomorrow", "2024-01-15", "tomorrow 2pm")')
    add_parser.add_argument("--notes", "-n", help="Additional notes")
    add_parser.add_argument(
        "--priority", "-p", type=int, choices=[0, 1, 2, 3], default=0, help="Priority: 0=none, 1=high, 2=medium, 3=low"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List reminders")
    list_parser.add_argument("--list", "-l", help="Filter by list name")
    list_parser.add_argument("--all", "-a", action="store_true", help="Include completed reminders")
    list_parser.add_argument("--limit", type=int, default=50, help="Maximum reminders to show")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Lists command
    lists_parser = subparsers.add_parser("lists", help="Show all reminder lists")
    lists_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Complete command
    complete_parser = subparsers.add_parser("complete", help="Mark a reminder as completed")
    complete_parser.add_argument("title", nargs="?", help="Reminder title")
    complete_parser.add_argument("--id", help="Reminder ID")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search reminders")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--all", "-a", action="store_true", help="Include completed")
    search_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "add":
            result = add_reminder(
                title=args.title, list_name=args.list, due_date=args.due, notes=args.notes, priority=args.priority
            )
            print(f"✓ {result['message']}")
            if result.get("due_date"):
                print(f"  Due: {result['due_date']}")

        elif args.command == "list":
            reminders = list_reminders(list_name=args.list, include_completed=args.all, limit=args.limit)
            if args.json:
                print(json.dumps(reminders, indent=2))
            else:
                if not reminders:
                    print("No reminders found.")
                else:
                    current_list = None
                    for r in reminders:
                        if r["list"] != current_list:
                            current_list = r["list"]
                            print(f"\n📋 {current_list}")
                        status = "✓" if r["completed"] else "○"
                        due = f" (due: {r['due_date']})" if r["due_date"] else ""
                        priority_mark = {1: "❗", 5: "❕", 9: "▪"}.get(r["priority"], "")
                        print(f"  {status} {priority_mark}{r['title']}{due}")

        elif args.command == "lists":
            lists = get_lists()
            if args.json:
                print(json.dumps(lists, indent=2))
            else:
                print("📋 Reminder Lists:\n")
                for lst in lists:
                    count = f"({lst['incomplete_count']} items)" if lst["incomplete_count"] > 0 else "(empty)"
                    print(f"  • {lst['name']} {count}")

        elif args.command == "complete":
            if not args.title and not args.id:
                print("Error: Either title or --id must be provided")
                sys.exit(1)
            result = complete_reminder(title=args.title, reminder_id=args.id)
            print(f"✓ {result['message']}")

        elif args.command == "search":
            reminders = search_reminders(args.query, include_completed=args.all)
            if args.json:
                print(json.dumps(reminders, indent=2))
            else:
                if not reminders:
                    print(f"No reminders matching '{args.query}'")
                else:
                    print(f"Found {len(reminders)} reminder(s):\n")
                    for r in reminders:
                        status = "✓" if r["completed"] else "○"
                        due = f" (due: {r['due_date']})" if r["due_date"] else ""
                        print(f"  {status} {r['title']}{due} [{r['list']}]")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
