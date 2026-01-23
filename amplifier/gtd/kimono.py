#!/usr/bin/env python3
"""
Kimono Event Scanner - Scans Google Calendar for kimono-requiring events.

Only uses explicit #kimono* tags, never infers from titles.
Outputs to Google Sheets for preparation tracking.
"""

import csv
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

# Try to import Google APIs
Credentials: Any
build: Any

try:
    from google.oauth2.credentials import Credentials  # type: ignore[import-not-found]
    from googleapiclient.discovery import build  # type: ignore[import-not-found]

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# Try to import Anthropic for translation
anthropic: Any = None
ANTHROPIC_AVAILABLE = False
try:
    import anthropic  # type: ignore[import-not-found]

    ANTHROPIC_AVAILABLE = True
except ImportError:
    pass

# Default Google Sheet for kimono events
DEFAULT_SPREADSHEET_ID = "1hOwDgfhrLkeJzUmEWoUlH63l7q54cH9vCvQRSt5b--Q"


# Recognized kimono tags and their display names
KIMONO_TAGS = {
    "kimono": "General",
    "kimono-formal": "Formal",
    "kimono-semi": "Semi-formal",
    "kimono-casual": "Casual",
    "kimono-tea": "Tea ceremony",
}


def is_japanese(text: str) -> bool:
    """Check if text contains Japanese characters (hiragana, katakana, or kanji)."""
    for char in text:
        # Hiragana: U+3040-U+309F, Katakana: U+30A0-U+30FF, Kanji: U+4E00-U+9FFF
        if (
            "\u3040" <= char <= "\u309f"
            or "\u30a0" <= char <= "\u30ff"
            or "\u4e00" <= char <= "\u9fff"
        ):
            return True
    return False


def translate_to_japanese(text: str) -> str:
    """Translate English text to Japanese using Claude.

    Only translates if text appears to be English (no Japanese characters).
    Uses concise, natural Japanese suitable for calendar entries.

    Args:
        text: Text to translate

    Returns:
        Translated text, or original if already Japanese or translation fails
    """
    if not text or not ANTHROPIC_AVAILABLE:
        return text

    # Skip if already contains Japanese
    if is_japanese(text):
        return text

    # Skip if text is very short or looks like a name/proper noun only
    if len(text.strip()) < 3:
        return text

    try:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": f"""Translate this calendar event title to natural, concise Japanese. 
Keep it brief (suitable for a spreadsheet cell). Preserve any proper nouns/names.
If it's already Japanese or a proper noun that shouldn't be translated, return it unchanged.

Event: {text}

Japanese translation (just the translation, no explanation):""",
                }
            ],
        )
        result = message.content[0].text.strip()
        # Sanity check - if result is way longer or empty, use original
        if result and len(result) < len(text) * 3:
            return result
        return text
    except Exception:
        return text


def extract_kimono_tags(text: str) -> list[str]:
    """Extract #kimono* tags from text.

    Only matches explicit tags, never infers from content.

    Args:
        text: Text to search for tags

    Returns:
        List of matched kimono tag names (without #)
    """
    if not text:
        return []

    # Find all #tags in text
    tags = [m.group(1).lower() for m in re.finditer(r"#([A-Za-z0-9_-]+)", text)]

    # Filter to only kimono-related tags
    return [t for t in tags if t in KIMONO_TAGS]


def get_kimono_type(tags: list[str]) -> str:
    """Get the most specific kimono type from tags.

    Priority: formal > semi > tea > casual > general
    """
    if "kimono-formal" in tags:
        return "Formal"
    if "kimono-semi" in tags:
        return "Semi-formal"
    if "kimono-tea" in tags:
        return "Tea ceremony"
    if "kimono-casual" in tags:
        return "Casual"
    if "kimono" in tags:
        return "General"
    return "Unknown"


class KimonoScanner:
    """Scans Google Calendar for events requiring kimono attire."""

    def __init__(self, config: Optional[dict] = None):
        config = config or {}

        # Google Sheets spreadsheet ID
        self.spreadsheet_id = config.get("spreadsheet_id", DEFAULT_SPREADSHEET_ID)

        # Legacy CSV output path (fallback if Sheets fails)
        self.output_path = Path(
            os.path.expanduser(
                config.get("output_path", "~/switchboard/kimono-events.csv")
            )
        )

        # Google API credentials (separate tokens for different scopes)
        self.gcal_token = Path(
            os.path.expanduser(
                config.get(
                    "gcal_token",
                    "~/.cache/amplifier/google-hydrated/calendar_token.json",
                )
            )
        )
        self.sheets_token = Path(
            os.path.expanduser(
                config.get(
                    "sheets_token",
                    "~/.cache/amplifier/google-hydrated/sheets_token.json",
                )
            )
        )

        # Timezone
        tz_name = config.get("timezone")
        if tz_name:
            self.timezone = ZoneInfo(tz_name)
        else:
            self.timezone = datetime.now().astimezone().tzinfo

    def get_calendar_events(self, days_ahead: int = 90) -> list[dict]:
        """Fetch calendar events for the specified date range.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of calendar event dicts
        """
        if not GOOGLE_API_AVAILABLE or not self.gcal_token.exists():
            return []

        try:
            creds = Credentials.from_authorized_user_file(
                str(self.gcal_token),
                ["https://www.googleapis.com/auth/calendar.readonly"],
            )
            service = build("calendar", "v3", credentials=creds)

            # Date range
            now = datetime.now(tz=self.timezone)
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=days_ahead)

            # Convert to UTC for API
            start_utc = start_time.astimezone(timezone.utc)
            end_utc = end_time.astimezone(timezone.utc)

            result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_utc.isoformat().replace("+00:00", "Z"),
                    timeMax=end_utc.isoformat().replace("+00:00", "Z"),
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=500,
                )
                .execute()
            )

            return result.get("items", [])
        except Exception as e:
            print(f"Calendar fetch error: {e}")
            return []

    def filter_kimono_events(self, events: list[dict]) -> list[dict]:
        """Filter events to only those with explicit #kimono* tags.

        Args:
            events: List of calendar events

        Returns:
            List of events with kimono tags, enriched with tag info
        """
        kimono_events = []

        for event in events:
            summary = event.get("summary", "")
            description = event.get("description", "")

            # Combine text and extract tags
            text = f"{summary} {description}"
            tags = extract_kimono_tags(text)

            # Only include events with explicit kimono tags
            if tags:
                event["_kimono_tags"] = tags
                event["_kimono_type"] = get_kimono_type(tags)
                kimono_events.append(event)

        return kimono_events

    def format_date(self, event: dict) -> str:
        """Format event date for display."""
        start = event.get("start", {})
        if start.get("dateTime"):
            dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M")
        elif start.get("date"):
            return start["date"]
        return ""

    def format_date_for_sheets(self, event: dict) -> str:
        """Format event date for Google Sheets (YYYY/M/D format to match existing data)."""
        start = event.get("start", {})
        if start.get("dateTime"):
            dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
            return f"{dt.year}/{dt.month}/{dt.day}"
        elif start.get("date"):
            # Parse YYYY-MM-DD and convert to YYYY/M/D
            parts = start["date"].split("-")
            if len(parts) == 3:
                return f"{int(parts[0])}/{int(parts[1])}/{int(parts[2])}"
            return start["date"]
        return ""

    def parse_sheet_date(self, date_str: str) -> Optional[datetime]:
        """Parse a date from the sheet (YYYY/M/D format) to datetime."""
        if not date_str:
            return None
        try:
            parts = date_str.split("/")
            if len(parts) == 3:
                return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            pass
        return None

    def extract_location_city(self, location: str) -> str:
        """Extract city name from a full location string (Japanese format)."""
        if not location:
            return ""
        location_lower = location.lower()
        if "shibuya" in location_lower or "tokyo" in location_lower:
            return "東京"
        if "osaka" in location_lower:
            return "大阪"
        if "kyoto" in location_lower:
            return "京都"
        if "chiba" in location_lower:
            return "千葉"
        return location.split(",")[0].strip()

    def write_to_sheets(self, events: list[dict], spreadsheet_id: str) -> dict:
        """Write kimono events to Google Sheets using upsert logic.

        Reads existing data, merges new events by date, preserves existing entries.
        Sheet format: Date (YYYY/M/D), Event, Location, Style

        Args:
            events: List of kimono events to write
            spreadsheet_id: Google Sheets spreadsheet ID

        Returns:
            dict with success status and details
        """
        if not self.sheets_token.exists():
            return {
                "success": False,
                "error": f"Sheets token not found at {self.sheets_token}",
            }

        try:
            creds = Credentials.from_authorized_user_file(
                str(self.sheets_token),
                ["https://www.googleapis.com/auth/spreadsheets"],
            )
            service = build("sheets", "v4", credentials=creds)

            # Read existing data
            result = (
                service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range="A:Z",
                )
                .execute()
            )
            existing_rows = result.get("values", [])

            # Parse existing data into a dict keyed by date string
            # Header: Date, Event, Location, Style
            header = (
                existing_rows[0]
                if existing_rows
                else ["Date", "Event", "Location", "Style"]
            )
            existing_by_date: dict[str, list[str]] = {}
            for row in existing_rows[1:]:
                if row and len(row) >= 1:
                    date_key = row[0]
                    # Pad row to 4 columns, preserve all existing data
                    padded_row = (row + ["", "", "", ""])[:4]
                    existing_by_date[date_key] = padded_row

            # Process new events - upsert by date
            added = 0
            updated = 0
            translated = 0
            for event in events:
                date_str = self.format_date_for_sheets(event)
                if not date_str:
                    continue

                event_name = event.get("summary", "").strip()
                location = self.extract_location_city(event.get("location", ""))

                if date_str in existing_by_date:
                    # Update existing row - only update if new data is non-empty
                    # Preserve Style column (index 3) always
                    existing = existing_by_date[date_str]
                    if event_name:
                        existing[1] = event_name
                    if location:
                        existing[2] = location
                    # existing[3] (Style) preserved
                    updated += 1
                else:
                    # Add new row - translate English event names to Japanese
                    translated_name = translate_to_japanese(event_name)
                    if translated_name != event_name:
                        translated += 1
                    existing_by_date[date_str] = [
                        date_str,
                        translated_name,
                        location,
                        "",
                    ]
                    added += 1

            # Sort all rows by date
            def sort_key(date_str: str) -> tuple:
                dt = self.parse_sheet_date(date_str)
                if dt:
                    return (dt.year, dt.month, dt.day)
                return (9999, 12, 31)

            sorted_dates = sorted(existing_by_date.keys(), key=sort_key)
            sorted_rows = [header] + [existing_by_date[d] for d in sorted_dates]

            # Write back all data
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range="A:D",
            ).execute()

            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range="A1",
                valueInputOption="RAW",
                body={"values": sorted_rows},
            ).execute()

            result = {
                "success": True,
                "rows_total": len(sorted_rows) - 1,
                "rows_added": added,
                "rows_updated": updated,
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
            }
            if translated > 0:
                result["rows_translated"] = translated
            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write to Google Sheets: {e}",
            }

    def scan(self, days_ahead: int = 90) -> dict:
        """Scan calendar and output kimono events to CSV.

        Args:
            days_ahead: Number of days to look ahead (default 90)

        Returns:
            dict with scan results
        """
        if not GOOGLE_API_AVAILABLE:
            return {
                "success": False,
                "error": "Google Calendar API not installed. Run: uv pip install google-api-python-client google-auth",
            }

        if not self.gcal_token.exists():
            return {
                "success": False,
                "error": f"Calendar token not found at {self.gcal_token}",
            }

        # Fetch and filter events
        all_events = self.get_calendar_events(days_ahead)
        kimono_events = self.filter_kimono_events(all_events)

        # Sort by date
        kimono_events.sort(key=lambda e: self.format_date(e))

        # Write to Google Sheets
        sheets_result = self.write_to_sheets(kimono_events, self.spreadsheet_id)

        # Fallback to CSV if Sheets fails
        if not sheets_result.get("success"):
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Event", "Type", "Location", "Tags", "Notes"])
                for event in kimono_events:
                    writer.writerow(
                        [
                            self.format_date(event),
                            event.get("summary", ""),
                            event.get("_kimono_type", ""),
                            event.get("location", ""),
                            ", ".join(f"#{t}" for t in event.get("_kimono_tags", [])),
                            "",
                        ]
                    )
            output_location = str(self.output_path)
            sheets_error = sheets_result.get("error", "Unknown error")
        else:
            output_location = sheets_result["spreadsheet_url"]
            sheets_error = None

        result = {
            "success": True,
            "events_found": len(kimono_events),
            "days_scanned": days_ahead,
            "output_path": output_location,
            "events": [
                {
                    "date": self.format_date(e),
                    "event": e.get("summary", ""),
                    "type": e.get("_kimono_type", ""),
                    "location": e.get("location", ""),
                    "tags": e.get("_kimono_tags", []),
                }
                for e in kimono_events
            ],
        }

        if sheets_error:
            result["sheets_error"] = sheets_error
            result["fallback"] = "csv"

        return result


def scan_kimono_events(days_ahead: int = 90, config: Optional[dict] = None) -> dict:
    """Convenience function to scan for kimono events.

    Args:
        days_ahead: Number of days to look ahead
        config: Optional configuration dict

    Returns:
        Scan results dict
    """
    scanner = KimonoScanner(config)
    return scanner.scan(days_ahead)


if __name__ == "__main__":
    import json
    import sys

    days = 90
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass

    result = scan_kimono_events(days)
    print(json.dumps(result, indent=2))
