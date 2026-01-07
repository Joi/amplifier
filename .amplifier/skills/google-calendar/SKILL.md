---
name: google-calendar
description: Create, list, search, and manage Google Calendar events. Use when user asks about their schedule, wants to create meetings, or check upcoming events.
version: 1.0.0
---

# Google Calendar Skill

Native integration with Google Calendar API via OAuth2. Works in subagents, scripts, cron jobs.

## When to Use

- User asks about their schedule or calendar
- User wants to create a meeting or event
- User asks "what's on my calendar today?"
- User wants to schedule something
- Part of morning routine workflows

## Setup (One-Time)

```bash
# Authorize Calendar access (opens browser)
python -m amplifier.skills.google_calendar auth
```

Requires OAuth credentials at `~/.googleauth/credentials.json`

## Python API (Preferred)

```python
from amplifier.skills import (
    list_events, get_event, create_event, update_event, delete_event,
    quick_add, get_todays_events, get_upcoming_events, get_calendars,
    CalendarEvent, Calendar
)

# List upcoming events
events = await list_events(max_results=10)
for event in events:
    print(f"{event.start}: {event.summary}")

# Today's events
today = await get_todays_events()

# Next 7 days
upcoming = await get_upcoming_events(days=7)

# Search events
results = await list_events(query="team meeting")

# Events in a date range
events = await list_events(
    time_min="2024-01-15",
    time_max="2024-01-20"
)

# Create an event
event = await create_event(
    summary="Team Meeting",
    start="2024-01-15 10:00",
    end="2024-01-15 11:00",
    description="Weekly sync",
    location="Conference Room A"
)

# Create with attendees
event = await create_event(
    summary="Project Review",
    start="tomorrow 2pm",
    end="tomorrow 3pm",
    attendees=["alice@example.com", "bob@example.com"]
)

# Create all-day event
event = await create_event(
    summary="Company Holiday",
    start="2024-12-25",
    all_day=True
)

# Quick add (natural language!)
event = await quick_add("Lunch with Bob tomorrow at noon")
event = await quick_add("Team standup every Monday at 9am")

# Update an event
updated = await update_event(
    event_id,
    summary="Updated Title",
    start="2024-01-15 11:00"
)

# Delete an event
await delete_event(event_id)

# List all calendars
calendars = await get_calendars()
for cal in calendars:
    print(f"{cal.summary} (primary: {cal.primary})")
```

## Sync Wrappers

```python
from amplifier.skills import (
    list_events_sync, get_event_sync, create_event_sync,
    quick_add_sync, get_todays_events_sync
)

# For use outside async context
events = list_events_sync(max_results=5)
event = create_event_sync("Meeting", "tomorrow 10am")
```

## Data Classes

```python
@dataclass
class CalendarEvent:
    id: str
    summary: str
    description: str
    location: str
    start: datetime | None
    end: datetime | None
    all_day: bool
    status: str  # confirmed, tentative, cancelled
    html_link: str
    hangout_link: str
    attendees: list[Attendee]
    organizer_email: str
    is_recurring: bool

@dataclass
class Calendar:
    id: str
    summary: str
    description: str
    primary: bool
    access_role: str
    timezone: str

@dataclass
class Attendee:
    email: str
    name: str
    response_status: str  # needsAction, declined, tentative, accepted
    organizer: bool
```

## Date/Time Formats

The skill accepts flexible datetime formats:

| Format | Example |
|--------|---------|
| ISO | `"2024-01-15T10:00:00"` |
| Date + Time | `"2024-01-15 10:00"` |
| Date only | `"2024-01-15"` |
| Relative | `"today"`, `"tomorrow"`, `"next week"` |
| US format | `"01/15/2024 10:00"` |

## CLI Interface

```bash
# List upcoming events
python -m amplifier.skills.google_calendar list
python -m amplifier.skills.google_calendar list --days 14 --limit 20

# Today's events
python -m amplifier.skills.google_calendar today

# Create event
python -m amplifier.skills.google_calendar create "Team Meeting" \
    --start "tomorrow 10am" --end "tomorrow 11am"

# Quick add (natural language)
python -m amplifier.skills.google_calendar quick "Lunch with Bob tomorrow at noon"

# List calendars
python -m amplifier.skills.google_calendar calendars
```

## Multiple Calendars

```python
# Use a specific calendar
events = await list_events(calendar_id="work@group.calendar.google.com")

event = await create_event(
    summary="Personal Appointment",
    start="tomorrow 2pm",
    calendar_id="personal@gmail.com"
)
```

## Advantages Over MCP

- ✅ Works in subagents (MCP tools don't inherit)
- ✅ Async-first with sync wrappers
- ✅ Quick add with natural language
- ✅ Works in scripts, cron jobs, SDK calls
- ✅ Returns proper Python dataclasses
- ✅ Shares OAuth infrastructure with Gmail
