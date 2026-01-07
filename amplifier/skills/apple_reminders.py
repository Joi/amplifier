"""Apple Reminders skill - Create, list, complete, and search reminders.

Native Amplifier skill for Apple Reminders. Works everywhere:
main session, subagents, SDK, scripts, cron jobs.

Usage:
    from amplifier.skills.apple_reminders import (
        add_reminder, list_reminders, complete_reminder, search_reminders, get_lists
    )

    # Add a reminder
    result = add_reminder("Buy groceries", list_name="Shopping")
    result = add_reminder("Call dentist", list_name="Personal", due_date="tomorrow 2pm")

    # List reminders
    reminders = list_reminders(list_name="Work")

    # Complete a reminder
    complete_reminder("Buy groceries")

    # Search
    results = search_reminders("meeting")
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal


@dataclass
class Reminder:
    """Represents an Apple Reminder."""

    id: str
    title: str
    list_name: str
    completed: bool = False
    priority: int = 0  # 0=none, 1=high, 5=medium, 9=low
    due_date: str | None = None
    notes: str = ""


@dataclass
class ReminderList:
    """Represents an Apple Reminders list."""

    id: str
    name: str
    incomplete_count: int = 0


def _run_applescript(script: str) -> str:
    """Execute AppleScript and return result. Uses temp file for complex scripts."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".scpt", delete=False) as f:
        f.write(script)
        temp_path = f.name

    try:
        result = subprocess.run(
            ["osascript", temp_path], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"AppleScript error: {e.stderr}")
    finally:
        os.unlink(temp_path)


def _escape_applescript_string(s: str) -> str:
    """Escape a string for use in AppleScript."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _parse_due_date(due_str: str) -> str | None:
    """Parse human-friendly due date to AppleScript date format."""
    if not due_str:
        return None

    due_lower = due_str.lower().strip()
    now = datetime.now()

    # Handle relative dates
    if due_lower == "today":
        target = now.replace(hour=17, minute=0, second=0)
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
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y", "%m/%d"]:
            try:
                target = datetime.strptime(due_str, fmt)
                if fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m/%d"]:
                    target = target.replace(hour=17, minute=0, second=0)
                break
            except ValueError:
                continue
        else:
            # Fallback: just use as-is
            return due_str

    # Format for AppleScript: "January 7, 2026 5:00 PM"
    return target.strftime("%B %d, %Y %I:%M %p")


def add_reminder(
    title: str,
    list_name: str = "Reminders",
    due_date: str | None = None,
    notes: str | None = None,
    priority: Literal[0, 1, 2, 3] = 0,
) -> Reminder:
    """Add a new reminder to a list.

    Args:
        title: Reminder title
        list_name: Target list name (default: "Reminders")
        due_date: Due date (e.g., "tomorrow", "tomorrow 2pm", "2024-01-15")
        notes: Additional notes
        priority: 0=none, 1=high, 2=medium, 3=low

    Returns:
        The created Reminder
    """
    escaped_title = _escape_applescript_string(title)
    escaped_list = _escape_applescript_string(list_name)

    props = [f'name:"{escaped_title}"']

    if notes:
        escaped_notes = _escape_applescript_string(notes)
        props.append(f'body:"{escaped_notes}"')

    if priority > 0:
        # Apple priority: 0=none, 1=high, 5=medium, 9=low
        apple_priority = {1: 1, 2: 5, 3: 9}.get(priority, 0)
        props.append(f"priority:{apple_priority}")

    props_str = ", ".join(props)

    if due_date:
        parsed_due = _parse_due_date(due_date)
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

    reminder_id = _run_applescript(script)

    return Reminder(
        id=reminder_id,
        title=title,
        list_name=list_name,
        completed=False,
        priority={1: 1, 2: 5, 3: 9}.get(priority, 0),
        due_date=due_date,
        notes=notes or "",
    )


def list_reminders(
    list_name: str | None = None,
    include_completed: bool = False,
    limit: int = 50,
) -> list[Reminder]:
    """List reminders, optionally filtered by list.

    Args:
        list_name: Filter by list name (None for all lists)
        include_completed: Include completed reminders
        limit: Maximum reminders to return

    Returns:
        List of Reminder objects
    """
    if list_name:
        escaped_list = _escape_applescript_string(list_name)
        list_filter = f'list "{escaped_list}"'
    else:
        list_filter = "every list"

    completed_filter = "" if include_completed else "whose completed is false"

    script = f'''
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
'''

    output = _run_applescript(script)

    reminders = []
    if output:
        for line in output.strip().split("\n"):
            if line.strip():
                parts = line.split("|||")
                if len(parts) >= 6:
                    reminders.append(
                        Reminder(
                            id=parts[0].strip(),
                            title=parts[1].strip(),
                            list_name=parts[2].strip(),
                            completed=parts[3].strip() == "true",
                            priority=(
                                int(parts[4].strip())
                                if parts[4].strip().isdigit()
                                else 0
                            ),
                            due_date=(
                                parts[5].strip()
                                if parts[5].strip() != "none"
                                else None
                            ),
                            notes=parts[6].strip() if len(parts) > 6 else "",
                        )
                    )

    return reminders


def get_lists() -> list[ReminderList]:
    """Get all reminder lists.

    Returns:
        List of ReminderList objects
    """
    script = '''
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
'''

    output = _run_applescript(script)

    lists = []
    if output:
        for line in output.strip().split("\n"):
            if line.strip():
                parts = line.split("|||")
                if len(parts) >= 3:
                    lists.append(
                        ReminderList(
                            id=parts[0].strip(),
                            name=parts[1].strip(),
                            incomplete_count=(
                                int(parts[2].strip())
                                if parts[2].strip().isdigit()
                                else 0
                            ),
                        )
                    )

    return lists


def complete_reminder(title: str | None = None, reminder_id: str | None = None) -> str:
    """Mark a reminder as completed.

    Args:
        title: Reminder title (finds first match)
        reminder_id: Reminder ID (takes precedence over title)

    Returns:
        Title of the completed reminder

    Raises:
        ValueError: If neither title nor reminder_id provided
        RuntimeError: If reminder not found
    """
    if reminder_id:
        escaped_id = _escape_applescript_string(reminder_id)
        script = f'''
tell application "Reminders"
    set r to reminder id "{escaped_id}"
    set completed of r to true
    return name of r
end tell
'''
    elif title:
        escaped_title = _escape_applescript_string(title)
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

    return _run_applescript(script)


def search_reminders(
    query: str, include_completed: bool = False
) -> list[Reminder]:
    """Search reminders by title.

    Args:
        query: Search query (case-insensitive contains)
        include_completed: Include completed reminders

    Returns:
        List of matching Reminder objects
    """
    escaped_query = _escape_applescript_string(query.lower())
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
            end if
        end repeat
    end repeat
    return output
end tell
'''

    output = _run_applescript(script)

    reminders = []
    if output:
        for line in output.strip().split("\n"):
            if line.strip():
                parts = line.split("|||")
                if len(parts) >= 5:
                    reminders.append(
                        Reminder(
                            id=parts[0].strip(),
                            title=parts[1].strip(),
                            list_name=parts[2].strip(),
                            completed=parts[3].strip() == "true",
                            priority=(
                                int(parts[4].strip())
                                if parts[4].strip().isdigit()
                                else 0
                            ),
                            due_date=(
                                parts[5].strip()
                                if len(parts) > 5 and parts[5].strip() != "none"
                                else None
                            ),
                            notes=parts[6].strip() if len(parts) > 6 else "",
                        )
                    )

    return reminders


# =============================================================================
# CLI Interface
# =============================================================================


def _cli_main() -> None:
    """CLI entry point."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Apple Reminders CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add command
    add_p = subparsers.add_parser("add", help="Add a reminder")
    add_p.add_argument("title", help="Reminder title")
    add_p.add_argument("--list", "-l", default="Reminders", help="List name")
    add_p.add_argument("--due", "-d", help="Due date")
    add_p.add_argument("--notes", "-n", help="Notes")
    add_p.add_argument(
        "--priority", "-p", type=int, choices=[0, 1, 2, 3], default=0, help="Priority"
    )

    # List command
    list_p = subparsers.add_parser("list", help="List reminders")
    list_p.add_argument("--list", "-l", dest="list_name", help="Filter by list")
    list_p.add_argument("--all", "-a", action="store_true", help="Include completed")
    list_p.add_argument("--limit", type=int, default=50, help="Limit")
    list_p.add_argument("--json", action="store_true", help="Output JSON")

    # Lists command
    lists_p = subparsers.add_parser("lists", help="Show all lists")
    lists_p.add_argument("--json", action="store_true", help="Output JSON")

    # Complete command
    comp_p = subparsers.add_parser("complete", help="Complete a reminder")
    comp_p.add_argument("title", nargs="?", help="Reminder title")
    comp_p.add_argument("--id", help="Reminder ID")

    # Search command
    search_p = subparsers.add_parser("search", help="Search reminders")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--all", "-a", action="store_true", help="Include completed")
    search_p.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "add":
            r = add_reminder(
                title=args.title,
                list_name=args.list,
                due_date=args.due,
                notes=args.notes,
                priority=args.priority,
            )
            print(f"✓ Created reminder: {r.title} in {r.list_name}")
            if r.due_date:
                print(f"  Due: {r.due_date}")

        elif args.command == "list":
            reminders = list_reminders(
                list_name=args.list_name,
                include_completed=args.all,
                limit=args.limit,
            )
            if args.json:
                print(json.dumps([r.__dict__ for r in reminders], indent=2))
            else:
                if not reminders:
                    print("No reminders found.")
                else:
                    current_list = None
                    for r in reminders:
                        if r.list_name != current_list:
                            current_list = r.list_name
                            print(f"\n📋 {current_list}")
                        status = "✓" if r.completed else "○"
                        due = f" (due: {r.due_date})" if r.due_date else ""
                        priority_mark = {1: "❗", 5: "❕", 9: "▪"}.get(r.priority, "")
                        print(f"  {status} {priority_mark}{r.title}{due}")

        elif args.command == "lists":
            lists = get_lists()
            if args.json:
                print(json.dumps([lst.__dict__ for lst in lists], indent=2))
            else:
                print("📋 Reminder Lists:\n")
                for lst in lists:
                    count = (
                        f"({lst.incomplete_count} items)"
                        if lst.incomplete_count > 0
                        else "(empty)"
                    )
                    print(f"  • {lst.name} {count}")

        elif args.command == "complete":
            if not args.title and not args.id:
                print("Error: Either title or --id must be provided")
                sys.exit(1)
            result = complete_reminder(title=args.title, reminder_id=args.id)
            print(f"✓ Completed: {result}")

        elif args.command == "search":
            reminders = search_reminders(args.query, include_completed=args.all)
            if args.json:
                print(json.dumps([r.__dict__ for r in reminders], indent=2))
            else:
                if not reminders:
                    print(f"No reminders matching '{args.query}'")
                else:
                    print(f"Found {len(reminders)} reminder(s):\n")
                    for r in reminders:
                        status = "✓" if r.completed else "○"
                        due = f" (due: {r.due_date})" if r.due_date else ""
                        print(f"  {status} {r.title}{due} [{r.list_name}]")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
