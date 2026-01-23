#!/usr/bin/env python3
"""
Daily Note Generator - Dashboard-style daily note for Obsidian.

Generates a daily note that serves as a command center for the day,
integrating calendar events, GTD focus items, flagged emails, and more.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

# Try to import Google Calendar API
from typing import Any as _Any

Credentials: _Any
build: _Any

try:
    from google.oauth2.credentials import Credentials  # type: ignore[import-not-found]
    from googleapiclient.discovery import build  # type: ignore[import-not-found]

    GCAL_AVAILABLE = True
except ImportError:
    GCAL_AVAILABLE = False


class DailyNoteGenerator:
    """Generates dashboard-style daily notes."""

    # Default patterns to exclude from calendar display
    DEFAULT_EXCLUDED_PATTERNS = [
        "birthday",
        "walk",
        "car",
        "driving",
        "commute",
    ]

    def __init__(self, config: Optional[dict] = None):
        config = config or {}
        self.vault_path = Path(
            os.path.expanduser(config.get("vault_path", "~/switchboard"))
        )
        self.dailynote_path = self.vault_path / "dailynote"
        self.reminders_cache = self.vault_path / "reminders" / "reminders_cache.json"
        self.gmail_cache = (
            Path.home() / ".cache" / "amplifier" / "gmail" / "starred_cache.json"
        )

        # Google Calendar credentials
        self.gcal_token = Path(
            os.path.expanduser(
                config.get(
                    "gcal_token",
                    "~/.cache/amplifier/google-hydrated/calendar_token.json",
                )
            )
        )
        self.gcal_creds = Path(
            os.path.expanduser(
                config.get(
                    "gcal_creds", "~/.cache/amplifier/google-hydrated/credentials.json"
                )
            )
        )

        # Calendar event filtering
        self.excluded_patterns = config.get(
            "excluded_calendar_patterns", self.DEFAULT_EXCLUDED_PATTERNS
        )
        self.exclude_allday_birthdays = config.get("exclude_allday_birthdays", True)

        # Timezone for calendar queries (default to system local timezone)
        tz_name = config.get("timezone")
        if tz_name:
            self.timezone = ZoneInfo(tz_name)
        else:
            # Use system local timezone
            self.timezone = datetime.now().astimezone().tzinfo

    def load_reminders(self) -> list[dict]:
        """Load reminders from cache."""
        if not self.reminders_cache.exists():
            return []

        with open(self.reminders_cache) as f:
            cache = json.load(f)

        reminders = []
        for list_name, items in cache.get("byList", {}).items():
            for item in items:
                item["list"] = list_name
                reminders.append(item)

        return reminders

    def load_flagged_emails(self) -> list[dict]:
        """Load flagged emails from Gmail cache."""
        if not self.gmail_cache.exists():
            return []

        try:
            with open(self.gmail_cache) as f:
                cache = json.load(f)
            return cache.get("emails", [])[:10]  # Top 10
        except Exception:
            return []

    def get_calendar_events(self, date: datetime) -> list[dict]:
        """Fetch calendar events for a specific date."""
        if not GCAL_AVAILABLE or not self.gcal_token.exists():
            return []

        try:
            creds = Credentials.from_authorized_user_file(
                str(self.gcal_token),
                ["https://www.googleapis.com/auth/calendar.readonly"],
            )
            service = build("calendar", "v3", credentials=creds)

            # Start and end of day in local timezone
            # Make date timezone-aware if it isn't already
            if date.tzinfo is None:
                local_date = date.replace(tzinfo=self.timezone)
            else:
                local_date = date

            start_of_day = local_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = local_date.replace(
                hour=23, minute=59, second=59, microsecond=0
            )

            # Convert to UTC for the API (Google Calendar API expects RFC3339)
            start_utc = start_of_day.astimezone(timezone.utc)
            end_utc = end_of_day.astimezone(timezone.utc)

            result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_utc.isoformat().replace("+00:00", "Z"),
                    timeMax=end_utc.isoformat().replace("+00:00", "Z"),
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=50,
                )
                .execute()
            )

            return result.get("items", [])
        except Exception as e:
            print(f"Calendar fetch error: {e}")
            return []

    def should_exclude_event(self, event: dict) -> bool:
        """Check if a calendar event should be excluded from display."""
        summary = (event.get("summary") or "").lower()

        # Check if it's an all-day event
        start = event.get("start", {})
        is_allday = "date" in start and "dateTime" not in start

        # Exclude all-day birthdays
        if is_allday and self.exclude_allday_birthdays and "birthday" in summary:
            return True

        # Check against excluded patterns
        for pattern in self.excluded_patterns:
            if pattern.lower() in summary:
                return True

        return False

    def filter_events(self, events: list[dict]) -> list[dict]:
        """Filter out excluded calendar events."""
        return [e for e in events if not self.should_exclude_event(e)]

    def extract_tags(self, text: str) -> list[str]:
        """Extract #tags from text."""
        if not text:
            return []
        return [m.group(1).lower() for m in re.finditer(r"#([A-Za-z0-9_:-]+)", text)]

    def is_today(self, date_str: str, today: datetime) -> bool:
        """Check if date string is today."""
        if not date_str:
            return False
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return date.date() == today.date()
        except Exception:
            return False

    def is_overdue(self, date_str: str, today: datetime) -> bool:
        """Check if date string is before today."""
        if not date_str:
            return False
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return date.date() < today.date()
        except Exception:
            return False

    def days_overdue(self, date_str: str, today: datetime) -> int:
        """Get number of days overdue."""
        if not date_str:
            return 0
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return (today.date() - date.date()).days
        except Exception:
            return 0

    def get_focus_items(self, reminders: list[dict], today: datetime) -> dict:
        """Get items needing immediate attention."""
        focus = {
            "urgent": [],
            "overdue": [],
            "due_today": [],
        }

        for r in reminders:
            if r.get("completed"):
                continue

            title = r.get("title", "")
            tags = self.extract_tags(title + " " + (r.get("notes") or ""))

            # Skip someday/waiting items
            if "someday" in tags or "waiting" in tags:
                continue

            # Urgent (flagged or !!)
            if r.get("flagged") or "!!" in title:
                focus["urgent"].append(r)
                continue

            # Date-based
            due = r.get("due")
            if due and self.is_overdue(due, today):
                r["_days_overdue"] = self.days_overdue(due, today)
                focus["overdue"].append(r)
            elif due and self.is_today(due, today):
                focus["due_today"].append(r)

        return focus

    def format_time(self, dt_str: str) -> str:
        """Format datetime string to HH:MM."""
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return dt.strftime("%H:%M")
        except Exception:
            return ""

    def extract_meeting_link(self, event: dict) -> tuple[str, str]:
        """Extract video meeting link and type from event."""
        # Check for hangoutLink
        if event.get("hangoutLink"):
            return ("Meet", event["hangoutLink"])

        # Check description and location for links - strip HTML
        text = (event.get("description") or "") + " " + (event.get("location") or "")
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Zoom - get clean URL
        zoom_match = re.search(r'(https://[^\s"\'<>]*zoom\.us/j/\d+[^\s"\'<>]*)', text)
        if zoom_match:
            url = zoom_match.group(1).split("<")[0].split('"')[0]
            return ("Zoom", url)

        # Teams
        teams_match = re.search(r'(https://teams\.microsoft\.com/[^\s"\'<>]+)', text)
        if teams_match:
            url = teams_match.group(1).split("<")[0].split('"')[0]
            return ("Teams", url)

        # Webex
        webex_match = re.search(r'(https://[^\s"\'<>]*webex\.com/[^\s"\'<>]+)', text)
        if webex_match:
            url = webex_match.group(1).split("<")[0].split('"')[0]
            return ("Webex", url)

        return ("", "")

    def generate_header(self, date: datetime) -> str:
        """Generate the header section."""
        day_name = date.strftime("%A")
        date_str = date.strftime("%Y-%m-%d")

        prev_date = (date - timedelta(days=1)).strftime("%Y-%m-%d")
        next_date = (date + timedelta(days=1)).strftime("%Y-%m-%d")

        return f"""# {date_str} {day_name}

[[{prev_date}|← Yesterday]] | [[GTD Dashboard|📋 GTD]] | [[{next_date}|Tomorrow →]]

---
"""

    def generate_focus_section(self, focus: dict, emails: list[dict]) -> str:
        """Generate the Focus Now section."""
        lines = ["## 🔥 Focus Now\n"]

        has_items = False

        # Overdue items
        for r in focus["overdue"][:5]:
            days = r.get("_days_overdue", 1)
            lines.append(
                f"- [ ] ⚠️ **OVERDUE ({days}d)** {r['title']} *({r.get('list', 'Unknown')})*"
            )
            has_items = True

        # Urgent items
        for r in focus["urgent"][:5]:
            lines.append(
                f"- [ ] 🚨 **URGENT** {r['title']} *({r.get('list', 'Unknown')})*"
            )
            has_items = True

        # Top flagged emails needing response
        for email in emails[:3]:
            sender = email.get("from_name") or email.get("from", "Unknown")
            subject = email.get("subject", "No subject")[:50]
            msg_id = email.get("id", "")
            link = f"message://%3C{msg_id}%3E" if msg_id else ""
            lines.append(f"- [ ] 📧 {sender} - {subject} [→]({link})")
            has_items = True

        if not has_items:
            lines.append("\n*No urgent items - focus on your priorities!*\n")
        else:
            lines.append("")

        return "\n".join(lines)

    def generate_schedule_section(self, events: list[dict]) -> str:
        """Generate the Today's Schedule section."""
        lines = ["## 📅 Today's Schedule\n"]

        if not events:
            lines.append("*No calendar events today*\n")
            return "\n".join(lines)

        lines.append("| Time | Event | Link |")
        lines.append("|------|-------|------|")

        for event in events:
            summary = event.get("summary", "Untitled")[:40]

            # Get start time
            start = event.get("start", {})
            if start.get("dateTime"):
                time_str = self.format_time(start["dateTime"])
            else:
                time_str = "All day"

            # Get meeting link or location
            link_type, link_url = self.extract_meeting_link(event)
            if link_url:
                link_str = f"[{link_type}]({link_url})"
            elif event.get("location"):
                loc = event["location"][:20]
                link_str = loc
            else:
                link_str = ""

            lines.append(f"| {time_str} | {summary} | {link_str} |")

        lines.append("")
        return "\n".join(lines)

    def generate_tasks_section(self, focus: dict) -> str:
        """Generate Tasks Due Today section."""
        lines = ["## ✅ Tasks Due Today\n"]

        tasks = focus.get("due_today", [])
        if not tasks:
            lines.append("*No tasks due today*\n")
        else:
            for r in tasks[:10]:
                lines.append(f"- [ ] {r['title']}")
            lines.append("")

        return "\n".join(lines)

    def generate_emails_section(self, emails: list[dict]) -> str:
        """Generate Flagged Emails section."""
        if not emails:
            return ""

        lines = [f"## 📬 Flagged Emails ({len(emails)})\n"]

        for email in emails[:10]:
            sender = email.get("from_name") or email.get("from", "Unknown")
            subject = email.get("subject", "No subject")[:50]
            msg_id = email.get("id", "")
            link = f"message://%3C{msg_id}%3E" if msg_id else ""
            lines.append(f"- [ ] {sender} - {subject} [→]({link})")

        lines.append("")
        return "\n".join(lines)

    def generate_notes_section(self, events: list[dict]) -> str:
        """Generate Notes section with meeting stubs."""
        lines = ["\n---\n", "## 📝 Notes\n"]
        lines.append("*Meeting notes and captures go below*\n")

        seen = set()  # Track (time, summary) to skip duplicates
        for event in events:
            summary = event.get("summary", "Untitled")
            start = event.get("start", {})
            if not start.get("dateTime"):
                continue

            # Skip events with #nomeeting tag
            description = event.get("description") or ""
            if "#nomeeting" in summary.lower() or "#nomeeting" in description.lower():
                continue

            time_str = self.format_time(start["dateTime"])

            # Skip duplicates
            key = (time_str, summary)
            if key in seen:
                continue
            seen.add(key)

            lines.append(f"### {time_str} {summary}\n\n")

        return "\n".join(lines)

    def generate(self, date: Optional[datetime] = None) -> str:
        """Generate the complete daily note."""
        if date is None:
            date = datetime.now()

        # Load data
        reminders = self.load_reminders()
        emails = self.load_flagged_emails()
        events = self.filter_events(self.get_calendar_events(date))

        # Get focus items
        focus = self.get_focus_items(reminders, date)

        # Build the note
        sections = [
            self.generate_header(date),
            self.generate_focus_section(focus, emails),
            self.generate_schedule_section(events),
            self.generate_tasks_section(focus),
            self.generate_emails_section(emails),
            self.generate_notes_section(events),
        ]

        return "\n".join(sections)

    def save(self, date: Optional[datetime] = None) -> Path:
        """Generate and save the daily note."""
        if date is None:
            date = datetime.now()

        content = self.generate(date)

        # Ensure directory exists
        self.dailynote_path.mkdir(parents=True, exist_ok=True)

        # Save file
        filename = date.strftime("%Y-%m-%d") + ".md"
        filepath = self.dailynote_path / filename

        with open(filepath, "w") as f:
            f.write(content)

        print(f"✅ Generated daily note: {filepath}")
        return filepath


def main():
    """CLI entry point."""
    import sys

    generator = DailyNoteGenerator()

    if len(sys.argv) > 1:
        if sys.argv[1] == "preview":
            print(generator.generate())
        elif sys.argv[1] == "save":
            generator.save()
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage: python daily_note.py [preview|save]")
    else:
        # Default: save
        generator.save()


if __name__ == "__main__":
    main()
