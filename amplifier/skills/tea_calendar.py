"""Tea Ceremony Calendar Skill - Two-way sync with Google Sheets.

Syncs tea ceremony events between a Google Sheet (source of truth)
and Google Calendar, with kimono/attire tagging.

Sheet format:
    Date | Event | Location | Style
    2026/1/11 | 初釜 | 東京 | 紋付袴

Calendar format:
    Title: 🍵 初釜
    Description: Location: 東京
                 Attire: 紋付袴
                 
                 tags: tea, kimono, 紋付袴

Usage:
    from amplifier.skills.tea_calendar import (
        sync_sheet_to_calendar,
        get_tea_events,
        get_kimono_events,
    )
    
    # Sync from sheet to calendar
    await sync_sheet_to_calendar()
    
    # Get all tea events
    events = await get_tea_events()
    
    # Get events requiring kimono
    kimono_events = await get_kimono_events()
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime, date
from typing import TYPE_CHECKING

import httpx

from .google_calendar import (
    list_events,
    create_event,
    update_event,
    delete_event,
    CalendarEvent,
)

if TYPE_CHECKING:
    pass

# Default sheet URL (Joi's tea calendar)
DEFAULT_SHEET_ID = "1hOwDgfhrLkeJzUmEWoUlH63l7q54cH9vCvQRSt5b--Q"
TEA_EMOJI = "🍵"


@dataclass
class TeaEvent:
    """A tea ceremony event."""
    
    date: date
    event: str
    location: str
    style: str  # 紋付袴, 黒紋付, etc.
    calendar_id: str | None = None  # Google Calendar event ID if synced
    
    @property
    def tags(self) -> list[str]:
        """Get tags for this event."""
        tags = ["tea"]
        if self.style:
            tags.append("kimono")
            tags.append(self.style)
        return tags
    
    @property
    def requires_kimono(self) -> bool:
        """Check if this event requires kimono."""
        return bool(self.style)
    
    @property
    def calendar_title(self) -> str:
        """Get the calendar event title."""
        return f"{TEA_EMOJI} {self.event}"
    
    @property
    def calendar_description(self) -> str:
        """Get the calendar event description."""
        lines = [f"Location: {self.location}"]
        if self.style:
            lines.append(f"Attire: {self.style}")
        lines.append("")
        lines.append(f"tags: {', '.join(self.tags)}")
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "date": self.date.isoformat(),
            "event": self.event,
            "location": self.location,
            "style": self.style,
            "calendar_id": self.calendar_id,
            "requires_kimono": self.requires_kimono,
        }


async def fetch_sheet(sheet_id: str = DEFAULT_SHEET_ID) -> list[TeaEvent]:
    """Fetch tea events from Google Sheet.
    
    Args:
        sheet_id: Google Sheet ID
        
    Returns:
        List of TeaEvent objects
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
    
    events = []
    reader = csv.DictReader(io.StringIO(response.text))
    
    for row in reader:
        # Parse date (format: 2026/1/11)
        date_str = row.get("Date", "").strip()
        if not date_str:
            continue
            
        try:
            # Handle both 2026/1/11 and 2026-01-11 formats
            if "/" in date_str:
                parts = date_str.split("/")
                event_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
            else:
                event_date = date.fromisoformat(date_str)
        except (ValueError, IndexError):
            continue
        
        events.append(TeaEvent(
            date=event_date,
            event=row.get("Event", "").strip(),
            location=row.get("Location", "").strip(),
            style=row.get("Style", "").strip(),
        ))
    
    return events


def fetch_sheet_sync(sheet_id: str = DEFAULT_SHEET_ID) -> list[TeaEvent]:
    """Sync version of fetch_sheet."""
    import asyncio
    return asyncio.run(fetch_sheet(sheet_id))


async def get_tea_events(
    time_min: str | date | None = None,
    time_max: str | date | None = None,
) -> list[CalendarEvent]:
    """Get tea ceremony events from Google Calendar.
    
    Finds events with 'tags: tea' in description or 🍵 in title.
    
    Args:
        time_min: Start date (default: today)
        time_max: End date (default: 1 year from now)
        
    Returns:
        List of CalendarEvent objects
    """
    events = await list_events(
        time_min=time_min,
        time_max=time_max,
        max_results=200,
    )
    
    tea_events = []
    for event in events:
        # Check for tea tag or emoji
        is_tea = (
            TEA_EMOJI in (event.summary or "") or
            "tags: tea" in (event.description or "").lower() or
            "tags:tea" in (event.description or "").lower()
        )
        if is_tea:
            tea_events.append(event)
    
    return tea_events


def get_tea_events_sync(
    time_min: str | date | None = None,
    time_max: str | date | None = None,
) -> list[CalendarEvent]:
    """Sync version of get_tea_events."""
    import asyncio
    return asyncio.run(get_tea_events(time_min, time_max))


async def get_kimono_events(
    time_min: str | date | None = None,
    time_max: str | date | None = None,
) -> list[CalendarEvent]:
    """Get events requiring kimono from Google Calendar.
    
    Finds events with 'tags: kimono' or 'tags: tea, kimono' in description.
    
    Args:
        time_min: Start date (default: today)
        time_max: End date (default: 1 year from now)
        
    Returns:
        List of CalendarEvent objects
    """
    events = await list_events(
        time_min=time_min,
        time_max=time_max,
        max_results=200,
    )
    
    kimono_events = []
    for event in events:
        desc = (event.description or "").lower()
        if "kimono" in desc or "紋付" in (event.description or ""):
            kimono_events.append(event)
    
    return kimono_events


def get_kimono_events_sync(
    time_min: str | date | None = None,
    time_max: str | date | None = None,
) -> list[CalendarEvent]:
    """Sync version of get_kimono_events."""
    import asyncio
    return asyncio.run(get_kimono_events(time_min, time_max))


def _parse_tags_from_description(description: str) -> list[str]:
    """Parse tags from event description."""
    match = re.search(r"tags:\s*(.+)$", description, re.MULTILINE | re.IGNORECASE)
    if match:
        return [t.strip() for t in match.group(1).split(",")]
    return []


async def sync_sheet_to_calendar(
    sheet_id: str = DEFAULT_SHEET_ID,
    dry_run: bool = False,
) -> dict:
    """Sync tea events from Google Sheet to Calendar.
    
    Creates new events, updates existing ones (matched by date + title).
    
    Args:
        sheet_id: Google Sheet ID
        dry_run: If True, don't actually create/update events
        
    Returns:
        Dict with counts: {"created": N, "updated": N, "unchanged": N}
    """
    # Fetch from sheet
    sheet_events = await fetch_sheet(sheet_id)
    
    # Fetch existing calendar events (next 2 years)
    calendar_events = await get_tea_events(
        time_min=date.today(),
        time_max=date(date.today().year + 2, 12, 31),
    )
    
    # Build lookup by date + title
    calendar_lookup: dict[tuple[date, str], CalendarEvent] = {}
    for ce in calendar_events:
        if ce.start:
            key = (ce.start.date(), ce.summary)
            calendar_lookup[key] = ce
    
    results = {"created": 0, "updated": 0, "unchanged": 0, "events": []}
    
    for se in sheet_events:
        key = (se.date, se.calendar_title)
        
        if key in calendar_lookup:
            # Event exists - check if needs update
            existing = calendar_lookup[key]
            needs_update = (
                existing.description != se.calendar_description or
                existing.location != se.location
            )
            
            if needs_update:
                if not dry_run:
                    await update_event(
                        existing.id,
                        description=se.calendar_description,
                        location=se.location,
                    )
                results["updated"] += 1
                results["events"].append({"action": "updated", "event": se.to_dict()})
            else:
                results["unchanged"] += 1
        else:
            # Create new event
            if not dry_run:
                await create_event(
                    summary=se.calendar_title,
                    start=se.date.isoformat(),
                    all_day=True,
                    description=se.calendar_description,
                    location=se.location,
                )
            results["created"] += 1
            results["events"].append({"action": "created", "event": se.to_dict()})
    
    return results


def sync_sheet_to_calendar_sync(
    sheet_id: str = DEFAULT_SHEET_ID,
    dry_run: bool = False,
) -> dict:
    """Sync version of sync_sheet_to_calendar."""
    import asyncio
    return asyncio.run(sync_sheet_to_calendar(sheet_id, dry_run))


async def generate_kimono_table(
    time_min: str | date | None = None,
    time_max: str | date | None = None,
    format: str = "markdown",
) -> str:
    """Generate a table of events requiring kimono.
    
    Args:
        time_min: Start date
        time_max: End date
        format: "markdown" or "csv"
        
    Returns:
        Formatted table string
    """
    events = await get_kimono_events(time_min, time_max)
    
    if format == "csv":
        lines = ["Date,Event,Location,Attire"]
        for e in events:
            # Extract attire from description
            attire = ""
            if e.description:
                match = re.search(r"Attire:\s*(.+)", e.description)
                if match:
                    attire = match.group(1).strip()
            lines.append(f"{e.start.date() if e.start else ''},{e.summary},{e.location},{attire}")
        return "\n".join(lines)
    
    else:  # markdown
        lines = [
            "| Date | Event | Location | Attire |",
            "|------|-------|----------|--------|",
        ]
        for e in events:
            attire = ""
            if e.description:
                match = re.search(r"Attire:\s*(.+)", e.description)
                if match:
                    attire = match.group(1).strip()
            date_str = e.start.strftime("%Y-%m-%d") if e.start else ""
            lines.append(f"| {date_str} | {e.summary} | {e.location or ''} | {attire} |")
        return "\n".join(lines)


def generate_kimono_table_sync(
    time_min: str | date | None = None,
    time_max: str | date | None = None,
    format: str = "markdown",
) -> str:
    """Sync version of generate_kimono_table."""
    import asyncio
    return asyncio.run(generate_kimono_table(time_min, time_max, format))


# =============================================================================
# CLI
# =============================================================================


def _cli_main() -> None:
    """CLI entry point."""
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Tea Ceremony Calendar")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync sheet to calendar")
    sync_parser.add_argument("--sheet-id", default=DEFAULT_SHEET_ID)
    sync_parser.add_argument("--dry-run", action="store_true")
    
    # list command
    list_parser = subparsers.add_parser("list", help="List tea events")
    list_parser.add_argument("--kimono", action="store_true", help="Only kimono events")
    
    # table command
    table_parser = subparsers.add_parser("table", help="Generate kimono table")
    table_parser.add_argument("--format", choices=["markdown", "csv"], default="markdown")
    
    # sheet command
    sheet_parser = subparsers.add_parser("sheet", help="Show events from sheet")
    sheet_parser.add_argument("--sheet-id", default=DEFAULT_SHEET_ID)
    
    args = parser.parse_args()
    
    if args.command == "sync":
        results = sync_sheet_to_calendar_sync(args.sheet_id, args.dry_run)
        prefix = "[DRY RUN] " if args.dry_run else ""
        print(f"{prefix}✅ Created: {results['created']}, Updated: {results['updated']}, Unchanged: {results['unchanged']}")
        
    elif args.command == "list":
        if args.kimono:
            events = get_kimono_events_sync()
        else:
            events = get_tea_events_sync()
        
        for e in events:
            date_str = e.start.strftime("%Y-%m-%d") if e.start else "?"
            print(f"{date_str}: {e.summary} @ {e.location or '?'}")
            
    elif args.command == "table":
        print(generate_kimono_table_sync(format=args.format))
        
    elif args.command == "sheet":
        events = fetch_sheet_sync(args.sheet_id)
        for e in events:
            kimono = "👘" if e.requires_kimono else "  "
            print(f"{e.date}: {kimono} {e.event} @ {e.location}")
            
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli_main()
