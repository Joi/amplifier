---
name: apple-reminders
description: Create, list, complete, and search Apple Reminders. Use when user wants to add tasks, check their reminders, mark things done, or manage their todo lists.
version: 1.0.0
---

# Apple Reminders Tool

Create, list, complete, and search Apple Reminders via command line.

## When to Use

- User asks to "add a reminder" or "remind me to..."
- User asks to "add a task" or "add a todo"
- User wants to see their reminders or tasks
- User wants to mark something as done/complete
- User mentions a specific reminder list (Shopping, Work, Personal, etc.)
- Adding follow-up items from a conversation

## Tool Location

```bash
python3 /Users/joi/amplifier/tools/apple_reminders.py <command> [options]
```

## Commands

### Add a Reminder

```bash
# Basic reminder
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Buy groceries" --list "Shopping"

# With due date
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Call dentist" --list "Personal" --due "tomorrow 2pm"

# With notes
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Review PR" --list "Amplifier" --notes "Check the new feature branch"

# With priority (1=high, 2=medium, 3=low)
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Urgent task" --list "Work" --priority 1
```

### Due Date Formats

- `today` - Today at 5 PM
- `tomorrow` - Tomorrow at 5 PM
- `tomorrow 2pm` - Tomorrow at 2 PM
- `next week` - One week from now at 9 AM
- `2024-01-15` - Specific date at 5 PM
- `2024-01-15 14:00` - Specific date and time

### List Reminders

```bash
# All incomplete reminders
python3 /Users/joi/amplifier/tools/apple_reminders.py list

# From specific list
python3 /Users/joi/amplifier/tools/apple_reminders.py list --list "Shopping"

# Include completed reminders
python3 /Users/joi/amplifier/tools/apple_reminders.py list --all

# Limit results
python3 /Users/joi/amplifier/tools/apple_reminders.py list --limit 10

# Output as JSON
python3 /Users/joi/amplifier/tools/apple_reminders.py list --json
```

### Show All Lists

```bash
python3 /Users/joi/amplifier/tools/apple_reminders.py lists
```

### Complete a Reminder

```bash
# By title
python3 /Users/joi/amplifier/tools/apple_reminders.py complete "Buy groceries"

# By ID
python3 /Users/joi/amplifier/tools/apple_reminders.py complete --id "x-apple-reminder://..."
```

### Search Reminders

```bash
# Search by keyword
python3 /Users/joi/amplifier/tools/apple_reminders.py search "dentist"

# Include completed
python3 /Users/joi/amplifier/tools/apple_reminders.py search "meeting" --all
```

## Common Lists

The user typically has these lists:
- **Reminders** - Default/general tasks
- **Amplifier** - Software development tasks
- **Shopping** - Things to buy
- **Personal** - Personal tasks
- **Work** - Work-related tasks

## Examples

```bash
# Add follow-up from conversation
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Fix Notes sync escaping issue" --list "Amplifier" --notes "Use temp file approach for AppleScript"

# Add shopping item
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Matcha powder" --list "Shopping"

# Add time-sensitive task
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Submit expense report" --list "Work" --due "tomorrow" --priority 1

# Check what's due
python3 /Users/joi/amplifier/tools/apple_reminders.py list --list "Work"

# Mark task complete after finishing it
python3 /Users/joi/amplifier/tools/apple_reminders.py complete "Submit expense report"
```

## Proactive Usage

When encountering errors or issues during work that can't be fixed immediately:
1. Add a reminder to the appropriate list
2. Include context in the notes field
3. Set appropriate priority

Example:
```bash
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Fix special character escaping in notes-sync" \
  --list "Amplifier" \
  --notes "See ai_working/migration/NOTES_SYNC_FIX.md for solution" \
  --priority 2
```
