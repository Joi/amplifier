"""Google Calendar skill - Create, list, search, and manage calendar events.

Native Amplifier skill for Google Calendar. Works everywhere:
main session, subagents, SDK, scripts, cron jobs.

Usage:
    from amplifier.skills.google_calendar import (
        list_events, get_event, create_event, update_event,
        delete_event, get_calendars, quick_add
    )

    # List upcoming events
    events = await list_events(max_results=10)

    # Today's events
    events = await list_events(time_min="today", time_max="tomorrow")

    # Create an event
    event = await create_event(
        summary="Team Meeting",
        start="2024-01-15 10:00",
        end="2024-01-15 11:00",
        description="Weekly sync",
        attendees=["alice@example.com", "bob@example.com"]
    )

    # Quick add (natural language)
    event = await quick_add("Lunch with Bob tomorrow at noon")
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

import httpx

from amplifier.utils.google_auth import (
    GoogleCredentials,
    GoogleScopes,
    get_google_credentials,
)

# Calendar API base URL
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"

# Default timezone
DEFAULT_TIMEZONE = "America/Los_Angeles"


@dataclass
class Attendee:
    """Event attendee."""

    email: str
    name: str = ""
    response_status: str = "needsAction"  # needsAction, declined, tentative, accepted
    organizer: bool = False
    self_: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "Attendee":
        return cls(
            email=data.get("email", ""),
            name=data.get("displayName", ""),
            response_status=data.get("responseStatus", "needsAction"),
            organizer=data.get("organizer", False),
            self_=data.get("self", False),
        )


@dataclass
class CalendarEvent:
    """Represents a Google Calendar event."""

    id: str
    summary: str = ""
    description: str = ""
    location: str = ""
    start: datetime | None = None
    end: datetime | None = None
    all_day: bool = False
    status: str = "confirmed"  # confirmed, tentative, cancelled
    html_link: str = ""
    hangout_link: str = ""
    attendees: list[Attendee] = field(default_factory=list)
    organizer_email: str = ""
    calendar_id: str = "primary"
    recurrence: list[str] = field(default_factory=list)
    is_recurring: bool = False


@dataclass
class Calendar:
    """Represents a Google Calendar."""

    id: str
    summary: str
    description: str = ""
    primary: bool = False
    access_role: str = "reader"  # reader, writer, owner
    background_color: str = ""
    timezone: str = ""


def _get_credentials(
    scopes: list[str] | None = None,
) -> GoogleCredentials:
    """Get Calendar credentials."""
    scopes = scopes or [GoogleScopes.CALENDAR_EVENTS]
    return get_google_credentials(
        app_name="amplifier",
        scopes=scopes,
        service="google",  # Shared token with Gmail
    )


def _get_headers(creds: GoogleCredentials) -> dict:
    """Get HTTP headers with auth."""
    return {
        "Authorization": f"Bearer {creds.access_token}",
        "Content-Type": "application/json",
    }


def _parse_datetime(dt_data: dict) -> tuple[datetime | None, bool]:
    """Parse datetime from Calendar API response.

    Returns:
        Tuple of (datetime, is_all_day)
    """
    if "dateTime" in dt_data:
        # Has time component
        dt_str = dt_data["dateTime"]
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return dt, False
        except ValueError:
            return None, False
    elif "date" in dt_data:
        # All-day event
        try:
            dt = datetime.strptime(dt_data["date"], "%Y-%m-%d")
            return dt, True
        except ValueError:
            return None, True
    return None, False


def _format_datetime(
    dt: datetime | str,
    all_day: bool = False,
    tz: str = DEFAULT_TIMEZONE,
) -> dict:
    """Format datetime for Calendar API request."""
    if isinstance(dt, str):
        dt = _parse_human_datetime(dt, tz)

    if all_day:
        return {"date": dt.strftime("%Y-%m-%d")}
    else:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(tz))
        return {"dateTime": dt.isoformat(), "timeZone": tz}


def _parse_human_datetime(dt_str: str, tz: str = DEFAULT_TIMEZONE) -> datetime:
    """Parse human-friendly datetime string."""
    dt_lower = dt_str.lower().strip()
    now = datetime.now(ZoneInfo(tz))

    # Handle relative dates
    if dt_lower == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif dt_lower == "tomorrow":
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif dt_lower == "next week":
        return (now + timedelta(weeks=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    # Try standard formats
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(dt_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo(tz))
            return dt
        except ValueError:
            continue

    # If nothing worked, try ISO format
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"Could not parse datetime: {dt_str}")


def _parse_event(data: dict) -> CalendarEvent:
    """Parse Calendar API event response into CalendarEvent."""
    start_dt, all_day = _parse_datetime(data.get("start", {}))
    end_dt, _ = _parse_datetime(data.get("end", {}))

    attendees = [
        Attendee.from_dict(a) for a in data.get("attendees", [])
    ]

    organizer = data.get("organizer", {})

    return CalendarEvent(
        id=data.get("id", ""),
        summary=data.get("summary", "(No title)"),
        description=data.get("description", ""),
        location=data.get("location", ""),
        start=start_dt,
        end=end_dt,
        all_day=all_day,
        status=data.get("status", "confirmed"),
        html_link=data.get("htmlLink", ""),
        hangout_link=data.get("hangoutLink", ""),
        attendees=attendees,
        organizer_email=organizer.get("email", ""),
        recurrence=data.get("recurrence", []),
        is_recurring="recurringEventId" in data or bool(data.get("recurrence")),
    )


async def list_events(
    calendar_id: str = "primary",
    max_results: int = 20,
    time_min: datetime | str | None = None,
    time_max: datetime | str | None = None,
    single_events: bool = True,
    order_by: Literal["startTime", "updated"] = "startTime",
    query: str | None = None,
) -> list[CalendarEvent]:
    """List calendar events.

    Args:
        calendar_id: Calendar ID (default: "primary")
        max_results: Maximum events to return
        time_min: Start of time range (default: now)
        time_max: End of time range
        single_events: Expand recurring events into instances
        order_by: Sort order ("startTime" or "updated")
        query: Free-text search query

    Returns:
        List of CalendarEvent objects
    """
    creds = _get_credentials([GoogleScopes.CALENDAR_READONLY])

    # Handle time_min
    if time_min is None:
        time_min_dt = datetime.now(timezone.utc)
    elif isinstance(time_min, str):
        time_min_dt = _parse_human_datetime(time_min)
    else:
        time_min_dt = time_min

    # Handle time_max
    time_max_dt = None
    if time_max:
        if isinstance(time_max, str):
            time_max_dt = _parse_human_datetime(time_max)
        else:
            time_max_dt = time_max

    params = {
        "maxResults": max_results,
        "singleEvents": single_events,
        "orderBy": order_by,
        "timeMin": time_min_dt.isoformat() if time_min_dt else None,
    }

    if time_max_dt:
        params["timeMax"] = time_max_dt.isoformat()

    if query:
        params["q"] = query

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            headers=_get_headers(creds),
            params=params,
        )
        response.raise_for_status()
        data = response.json()

        return [_parse_event(e) for e in data.get("items", [])]


async def get_event(
    event_id: str,
    calendar_id: str = "primary",
) -> CalendarEvent:
    """Get a specific event by ID.

    Args:
        event_id: Event ID
        calendar_id: Calendar ID

    Returns:
        CalendarEvent object
    """
    creds = _get_credentials([GoogleScopes.CALENDAR_READONLY])

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            headers=_get_headers(creds),
        )
        response.raise_for_status()
        return _parse_event(response.json())


async def create_event(
    summary: str,
    start: datetime | str,
    end: datetime | str | None = None,
    description: str = "",
    location: str = "",
    attendees: list[str] | None = None,
    calendar_id: str = "primary",
    all_day: bool = False,
    timezone: str = DEFAULT_TIMEZONE,
    send_notifications: bool = True,
) -> CalendarEvent:
    """Create a new calendar event.

    Args:
        summary: Event title
        start: Start time (datetime or string like "2024-01-15 10:00")
        end: End time (default: 1 hour after start)
        description: Event description
        location: Event location
        attendees: List of attendee email addresses
        calendar_id: Calendar ID
        all_day: Create as all-day event
        timezone: Timezone for the event
        send_notifications: Send email notifications to attendees

    Returns:
        Created CalendarEvent
    """
    creds = _get_credentials([GoogleScopes.CALENDAR_EVENTS])

    # Parse start time
    if isinstance(start, str):
        start_dt = _parse_human_datetime(start, timezone)
    else:
        start_dt = start

    # Parse/calculate end time
    if end is None:
        if all_day:
            end_dt = start_dt + timedelta(days=1)
        else:
            end_dt = start_dt + timedelta(hours=1)
    elif isinstance(end, str):
        end_dt = _parse_human_datetime(end, timezone)
    else:
        end_dt = end

    event_body = {
        "summary": summary,
        "start": _format_datetime(start_dt, all_day, timezone),
        "end": _format_datetime(end_dt, all_day, timezone),
    }

    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location
    if attendees:
        event_body["attendees"] = [{"email": email} for email in attendees]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            headers=_get_headers(creds),
            json=event_body,
            params={"sendNotifications": send_notifications},
        )
        response.raise_for_status()
        return _parse_event(response.json())


async def update_event(
    event_id: str,
    summary: str | None = None,
    start: datetime | str | None = None,
    end: datetime | str | None = None,
    description: str | None = None,
    location: str | None = None,
    calendar_id: str = "primary",
    timezone: str = DEFAULT_TIMEZONE,
) -> CalendarEvent:
    """Update an existing event.

    Args:
        event_id: Event ID to update
        summary: New title (None to keep existing)
        start: New start time
        end: New end time
        description: New description
        location: New location
        calendar_id: Calendar ID
        timezone: Timezone for datetime values

    Returns:
        Updated CalendarEvent
    """
    creds = _get_credentials([GoogleScopes.CALENDAR_EVENTS])

    # Get existing event
    existing = await get_event(event_id, calendar_id)

    # Build update body
    event_body = {}

    if summary is not None:
        event_body["summary"] = summary
    if description is not None:
        event_body["description"] = description
    if location is not None:
        event_body["location"] = location

    if start is not None:
        if isinstance(start, str):
            start_dt = _parse_human_datetime(start, timezone)
        else:
            start_dt = start
        event_body["start"] = _format_datetime(start_dt, existing.all_day, timezone)

    if end is not None:
        if isinstance(end, str):
            end_dt = _parse_human_datetime(end, timezone)
        else:
            end_dt = end
        event_body["end"] = _format_datetime(end_dt, existing.all_day, timezone)

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            headers=_get_headers(creds),
            json=event_body,
        )
        response.raise_for_status()
        return _parse_event(response.json())


async def delete_event(
    event_id: str,
    calendar_id: str = "primary",
    send_notifications: bool = True,
) -> None:
    """Delete an event.

    Args:
        event_id: Event ID to delete
        calendar_id: Calendar ID
        send_notifications: Send cancellation emails
    """
    creds = _get_credentials([GoogleScopes.CALENDAR_EVENTS])

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            headers=_get_headers(creds),
            params={"sendNotifications": send_notifications},
        )
        response.raise_for_status()


async def quick_add(
    text: str,
    calendar_id: str = "primary",
) -> CalendarEvent:
    """Create event from natural language text.

    Args:
        text: Natural language event description
              e.g., "Lunch with Bob tomorrow at noon"
        calendar_id: Calendar ID

    Returns:
        Created CalendarEvent
    """
    creds = _get_credentials([GoogleScopes.CALENDAR_EVENTS])

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/quickAdd",
            headers=_get_headers(creds),
            params={"text": text},
        )
        response.raise_for_status()
        return _parse_event(response.json())


async def get_calendars() -> list[Calendar]:
    """Get all calendars accessible by the user.

    Returns:
        List of Calendar objects
    """
    creds = _get_credentials([GoogleScopes.CALENDAR_READONLY])

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CALENDAR_API_BASE}/users/me/calendarList",
            headers=_get_headers(creds),
        )
        response.raise_for_status()
        data = response.json()

        calendars = []
        for cal_data in data.get("items", []):
            calendars.append(
                Calendar(
                    id=cal_data.get("id", ""),
                    summary=cal_data.get("summary", ""),
                    description=cal_data.get("description", ""),
                    primary=cal_data.get("primary", False),
                    access_role=cal_data.get("accessRole", "reader"),
                    background_color=cal_data.get("backgroundColor", ""),
                    timezone=cal_data.get("timeZone", ""),
                )
            )

        return calendars


async def get_todays_events(calendar_id: str = "primary") -> list[CalendarEvent]:
    """Get all events for today.

    Returns:
        List of today's CalendarEvent objects
    """
    now = datetime.now(ZoneInfo(DEFAULT_TIMEZONE))
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    return await list_events(
        calendar_id=calendar_id,
        time_min=start_of_day,
        time_max=end_of_day,
    )


async def get_upcoming_events(
    days: int = 7,
    calendar_id: str = "primary",
    max_results: int = 50,
) -> list[CalendarEvent]:
    """Get upcoming events for the next N days.

    Args:
        days: Number of days to look ahead
        calendar_id: Calendar ID
        max_results: Maximum events to return

    Returns:
        List of upcoming CalendarEvent objects
    """
    now = datetime.now(ZoneInfo(DEFAULT_TIMEZONE))
    end_date = now + timedelta(days=days)

    return await list_events(
        calendar_id=calendar_id,
        time_min=now,
        time_max=end_date,
        max_results=max_results,
    )


# =============================================================================
# Synchronous Wrappers
# =============================================================================


def list_events_sync(
    calendar_id: str = "primary",
    max_results: int = 20,
    time_min: datetime | str | None = None,
    time_max: datetime | str | None = None,
) -> list[CalendarEvent]:
    """Sync wrapper for list_events."""
    return asyncio.run(list_events(calendar_id, max_results, time_min, time_max))


def get_event_sync(event_id: str, calendar_id: str = "primary") -> CalendarEvent:
    """Sync wrapper for get_event."""
    return asyncio.run(get_event(event_id, calendar_id))


def create_event_sync(
    summary: str,
    start: datetime | str,
    end: datetime | str | None = None,
    **kwargs,
) -> CalendarEvent:
    """Sync wrapper for create_event."""
    return asyncio.run(create_event(summary, start, end, **kwargs))


def quick_add_sync(text: str, calendar_id: str = "primary") -> CalendarEvent:
    """Sync wrapper for quick_add."""
    return asyncio.run(quick_add(text, calendar_id))


def get_todays_events_sync(calendar_id: str = "primary") -> list[CalendarEvent]:
    """Sync wrapper for get_todays_events."""
    return asyncio.run(get_todays_events(calendar_id))


# =============================================================================
# CLI Interface
# =============================================================================


def _cli_main() -> None:
    """CLI entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Google Calendar CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_p = subparsers.add_parser("list", help="List upcoming events")
    list_p.add_argument("--limit", "-n", type=int, default=10, help="Max events")
    list_p.add_argument("--days", "-d", type=int, default=7, help="Days ahead")

    # Today command
    subparsers.add_parser("today", help="Show today's events")

    # Create command
    create_p = subparsers.add_parser("create", help="Create an event")
    create_p.add_argument("summary", help="Event title")
    create_p.add_argument("--start", "-s", required=True, help="Start time")
    create_p.add_argument("--end", "-e", help="End time")
    create_p.add_argument("--description", "-d", help="Description")
    create_p.add_argument("--location", "-l", help="Location")

    # Quick add command
    quick_p = subparsers.add_parser("quick", help="Quick add (natural language)")
    quick_p.add_argument("text", help="Event description (e.g., 'Lunch tomorrow at noon')")

    # Calendars command
    subparsers.add_parser("calendars", help="List calendars")

    # Auth command
    subparsers.add_parser("auth", help="Authorize Calendar access")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "auth":
            from amplifier.utils.google_auth import authorize_google
            authorize_google(
                app_name="amplifier",
                scopes=[GoogleScopes.CALENDAR_EVENTS],
                service="calendar",
            )

        elif args.command == "list":
            events = asyncio.run(get_upcoming_events(args.days, max_results=args.limit))
            if not events:
                print("No upcoming events.")
            else:
                current_date = None
                for event in events:
                    if event.start:
                        event_date = event.start.strftime("%A, %B %d")
                        if event_date != current_date:
                            current_date = event_date
                            print(f"\n📅 {current_date}")

                        if event.all_day:
                            time_str = "All day"
                        else:
                            time_str = event.start.strftime("%I:%M %p")

                        print(f"  {time_str:>10}  {event.summary}")

        elif args.command == "today":
            events = get_todays_events_sync()
            if not events:
                print("No events today.")
            else:
                print("📅 Today's Events:\n")
                for event in events:
                    if event.all_day:
                        time_str = "All day"
                    elif event.start:
                        time_str = event.start.strftime("%I:%M %p")
                    else:
                        time_str = "?"
                    print(f"  {time_str:>10}  {event.summary}")

        elif args.command == "create":
            event = create_event_sync(
                summary=args.summary,
                start=args.start,
                end=args.end,
                description=args.description or "",
                location=args.location or "",
            )
            print(f"✓ Created: {event.summary}")
            if event.start:
                print(f"  When: {event.start.strftime('%A, %B %d at %I:%M %p')}")
            if event.html_link:
                print(f"  Link: {event.html_link}")

        elif args.command == "quick":
            event = quick_add_sync(args.text)
            print(f"✓ Created: {event.summary}")
            if event.start:
                print(f"  When: {event.start.strftime('%A, %B %d at %I:%M %p')}")

        elif args.command == "calendars":
            calendars = asyncio.run(get_calendars())
            print("📅 Calendars:\n")
            for cal in calendars:
                primary = " (primary)" if cal.primary else ""
                print(f"  • {cal.summary}{primary}")
                print(f"    ID: {cal.id}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
