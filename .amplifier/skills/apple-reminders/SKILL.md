---
name: apple-reminders
description: Create, list, complete, and search Apple Reminders. Use when user wants to add tasks, check their reminders, mark items complete, or manage their task lists.
version: 2.0.0
---

# Apple Reminders Skill

Native integration with Apple Reminders via AppleScript. Works in subagents, scripts, cron jobs.

## When to Use

- User says "remind me to..." or "add a reminder"
- User asks about their tasks or to-do items
- User wants to complete/check off a task
- User mentions a specific reminder list
- Part of morning routine or GTD workflows

## Python API (Preferred)

```python
from amplifier.skills import (
    add_reminder, list_reminders, complete_reminder,
    search_reminders, get_reminder_lists, Reminder
)

# Add a reminder
reminder = add_reminder("Buy groceries", list_name="Shopping")
reminder = add_reminder(
    "Call dentist",
    list_name="Personal",
    due_date="tomorrow 2pm",
    notes="Annual checkup",
    priority=1  # 0=none, 1=high, 2=medium, 3=low
)

# List reminders
reminders = list_reminders()  # All incomplete
reminders = list_reminders(list_name="Work")
reminders = list_reminders(include_completed=True, limit=100)

for r in reminders:
    print(f"{r.title} - {r.list_name} - Due: {r.due_date}")

# Complete a reminder
complete_reminder("Buy groceries")
complete_reminder(reminder_id="x-apple-reminder://...")

# Search
results = search_reminders("meeting")
results = search_reminders("project", include_completed=True)

# Get all lists
lists = get_reminder_lists()
for lst in lists:
    print(f"{lst.name}: {lst.incomplete_count} items")
```

## Data Classes

```python
@dataclass
class Reminder:
    id: str
    title: str
    list_name: str
    completed: bool = False
    priority: int = 0  # 0=none, 1=high, 5=medium, 9=low
    due_date: str | None = None
    notes: str = ""

@dataclass
class ReminderList:
    id: str
    name: str
    incomplete_count: int = 0
```

## Due Date Formats

The `due_date` parameter accepts:
- Relative: `"today"`, `"tomorrow"`, `"next week"`
- With time: `"tomorrow 2pm"`, `"tomorrow 14:00"`
- Dates: `"2024-01-15"`, `"01/15/2024"`, `"2024-01-15 14:00"`

## CLI Interface

```bash
# Add reminder
python -m amplifier.skills.apple_reminders add "Buy milk" --list Shopping
python -m amplifier.skills.apple_reminders add "Call mom" --due "tomorrow 2pm"

# List reminders
python -m amplifier.skills.apple_reminders list
python -m amplifier.skills.apple_reminders list --list Work --json

# Complete
python -m amplifier.skills.apple_reminders complete "Buy milk"

# Search
python -m amplifier.skills.apple_reminders search "meeting"

# Show lists
python -m amplifier.skills.apple_reminders lists
```

## Integration with Continuous Improvement

When encountering issues during work, use this skill to create improvement reminders:

```python
add_reminder(
    "Fix flaky test in auth module",
    list_name="Amplifier",
    notes="Test fails intermittently on CI",
    priority=2
)
```

## Advantages Over MCP

- ✅ Works in subagents (MCP tools don't inherit)
- ✅ Works in scripts, cron jobs, SDK calls
- ✅ Returns proper Python dataclasses
- ✅ No MCP server overhead
