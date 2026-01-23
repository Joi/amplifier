#!/usr/bin/env python3
"""
GTD Dashboard Generator - Action-focused GTD dashboard for Obsidian.

Generates a dashboard showing actual tasks organized by GTD categories:
- Focus (urgent, overdue, due today)
- Inbox (needs processing)
- Next Actions (by project/context)
- Waiting For
- Someday/Maybe

Features:
- Shows data freshness (when caches were last synced)
- Warns when data is stale
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


def get_cache_age_info(cache_path: Path) -> dict:
    """Get cache age information."""
    if not cache_path.exists():
        return {
            "exists": False,
            "age_seconds": None,
            "age_human": "no data",
            "is_stale": True,
            "synced_at": None,
        }

    try:
        # Use file modification time (always local timezone, reliable)
        mtime = cache_path.stat().st_mtime
        age_seconds = int(time.time() - mtime)
        synced_at = datetime.fromtimestamp(mtime).isoformat()

        # Consider stale after 1 hour
        is_stale = age_seconds > 3600

        # Human-readable
        if age_seconds < 60:
            age_human = f"{age_seconds}s ago"
        elif age_seconds < 3600:
            age_human = f"{age_seconds // 60}m ago"
        elif age_seconds < 86400:
            age_human = f"{age_seconds // 3600}h ago"
        else:
            age_human = f"{age_seconds // 86400}d ago"

        return {
            "exists": True,
            "age_seconds": age_seconds,
            "age_human": age_human,
            "is_stale": is_stale,
            "synced_at": synced_at,
        }
    except Exception as e:
        return {
            "exists": True,
            "error": str(e),
            "age_seconds": None,
            "age_human": "error",
            "is_stale": True,
            "synced_at": None,
        }


class GTDDashboard:
    """Generates action-focused GTD dashboard."""

    def __init__(self, config: Optional[dict] = None):
        config = config or {}
        self.vault_path = Path(
            os.path.expanduser(config.get("vault_path", "~/switchboard"))
        )
        self.reminders_cache = self.vault_path / "reminders" / "reminders_cache.json"
        self.gmail_cache = (
            Path.home() / ".cache" / "amplifier" / "gmail" / "starred_cache.json"
        )
        self.dashboard_path = self.vault_path / "GTD Dashboard.md"

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
            return cache.get("emails", [])
        except Exception:
            return []

    def extract_tags(self, text: str) -> list[str]:
        """Extract #tags from text."""
        if not text:
            return []
        return [m.group(1).lower() for m in re.finditer(r"#([A-Za-z0-9_:-]+)", text)]

    def extract_project(self, tags: list[str]) -> Optional[str]:
        """Extract project name from tags."""
        for tag in tags:
            if tag.startswith("project:"):
                return tag.replace("project:", "")
        return None

    def extract_context(self, title: str) -> Optional[str]:
        """Extract @context from title.

        Only matches contexts that appear at word boundaries (start of string
        or after whitespace), NOT email addresses like user@domain.com.
        """
        # Match @context only at start of string or after whitespace
        # This prevents matching email addresses like foo@bar.com
        match = re.search(r"(?:^|(?<=\s))@(\w+)", title)
        return match.group(1) if match else None

    def is_today(self, date_str: str) -> bool:
        """Check if date is today."""
        if not date_str:
            return False
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return date.date() == datetime.now().date()
        except Exception:
            return False

    def is_overdue(self, date_str: str) -> bool:
        """Check if date is before today."""
        if not date_str:
            return False
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return date.date() < datetime.now().date()
        except Exception:
            return False

    def is_this_week(self, date_str: str) -> bool:
        """Check if date is within this week."""
        if not date_str:
            return False
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            today = datetime.now().date()
            end_of_week = today + timedelta(days=(6 - today.weekday()))
            return today <= date.date() <= end_of_week
        except Exception:
            return False

    def format_due_date(self, date_str: str) -> str:
        """Format due date for display."""
        if not date_str:
            return ""
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return date.strftime("%b %d")
        except Exception:
            return ""

    def categorize_reminders(self, reminders: list[dict]) -> dict:
        """Categorize reminders into GTD buckets.

        Uses the tickler model:
        - 'deadline' field (from text [due: X]) = hard deadlines
        - 'due' field (native date picker) = tickler/surface date
        - 'flagged' = urgent items
        """
        categories = {
            "flagged": [],
            "past_deadline": [],
            "deadline_today": [],
            "tickled_today": [],
            "deadline_this_week": [],
            "inbox": [],
            "next_actions": [],
            "waiting": [],
            "someday": [],
            "by_project": {},
            "by_context": {},
        }

        today = datetime.now().date()

        for r in reminders:
            if r.get("completed"):
                continue

            title = r.get("title", "")
            notes = r.get("notes") or ""
            list_name = r.get("list", "Unknown")
            text = title + " " + notes
            tags = self.extract_tags(text)
            deadline = r.get("deadline")  # From text [due: X]
            tickler = r.get("due")  # Native date field (tickler/surface date)

            # Add computed fields
            r["_tags"] = tags
            r["_project"] = self.extract_project(tags)
            r["_context"] = self.extract_context(title)
            r["_deadline_formatted"] = deadline if deadline else ""

            # Track if item is someday/waiting for tickler logic
            is_someday = "someday" in tags or list_name == "Someday/Maybe"
            is_waiting = "waiting" in tags or list_name == "Waiting For"

            # Categorize
            if "waiting" in tags:
                categories["waiting"].append(r)
                continue

            if "someday" in tags and not tickler:
                # Someday items without tickler go to someday
                categories["someday"].append(r)
                continue

            # Inbox
            if list_name == "Inbox":
                categories["inbox"].append(r)
                # Don't continue - inbox items can also have deadlines/ticklers

            # Flagged items (urgent)
            if r.get("flagged") or "!!" in title:
                categories["flagged"].append(r)

            # Check deadline (from text [due: X])
            if deadline:
                try:
                    deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
                    if deadline_date < today:
                        r["_days_overdue"] = (today - deadline_date).days
                        categories["past_deadline"].append(r)
                    elif deadline_date == today:
                        categories["deadline_today"].append(r)
                    elif deadline_date <= today + timedelta(days=7):
                        r["_days_until"] = (deadline_date - today).days
                        categories["deadline_this_week"].append(r)
                except Exception:
                    pass

            # Check tickler date (native date field = surface/review date)
            if tickler:
                try:
                    # Handle both ISO format and YYYY-MM-DD
                    if "T" in tickler:
                        tickler_date = datetime.fromisoformat(
                            tickler.replace("Z", "+00:00")
                        ).date()
                    else:
                        tickler_date = datetime.strptime(tickler, "%Y-%m-%d").date()

                    if tickler_date == today:
                        r["_tickler_source"] = "someday" if is_someday else "tickler"
                        categories["tickled_today"].append(r)
                    elif tickler_date < today and not is_someday and not is_waiting:
                        # Past tickler on active items = should have been reviewed
                        r["_tickler_source"] = "overdue_tickler"
                        r["_days_past"] = (today - tickler_date).days
                        categories["tickled_today"].append(r)
                    elif is_someday and tickler_date == today:
                        # Someday item surfaced today
                        r["_tickler_source"] = "someday"
                        categories["tickled_today"].append(r)
                except Exception:
                    pass

            # Someday items with past ticklers that didn't surface
            if is_someday and r not in categories["tickled_today"]:
                categories["someday"].append(r)
                continue

            # By project
            project = r["_project"]
            if project:
                if project not in categories["by_project"]:
                    categories["by_project"][project] = []
                categories["by_project"][project].append(r)

            # By context
            context = r["_context"]
            if context:
                if context not in categories["by_context"]:
                    categories["by_context"][context] = []
                categories["by_context"][context].append(r)

            # All active = next actions (excluding inbox-only items)
            if list_name != "Inbox":
                categories["next_actions"].append(r)

        return categories

    def format_task(
        self, r: dict, show_list: bool = True, show_deadline: bool = True
    ) -> str:
        """Format a task as markdown checkbox."""
        title = r.get("title", "")
        parts = [f"- [ ] {title}"]

        if show_deadline and r.get("_deadline_formatted"):
            parts.append(f"*[due: {r['_deadline_formatted']}]*")

        if show_list and r.get("list") and r["list"] != "Inbox":
            parts.append(f"*({r['list']})*")

        return " ".join(parts)

    def generate(self) -> str:
        """Generate the complete GTD dashboard."""
        reminders = self.load_reminders()
        emails = self.load_flagged_emails()
        categories = self.categorize_reminders(reminders)

        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M")

        # Get cache freshness
        reminders_info = get_cache_age_info(self.reminders_cache)

        sections = []

        # Header with data freshness
        freshness_line = f"Data synced: {reminders_info['age_human']}"
        if reminders_info["is_stale"]:
            freshness_line += " ⚠️ **STALE** - run `gtd sync_reminders`"

        sections.append(f"""# GTD Dashboard

*Generated: {timestamp}* | *{freshness_line}*

[[dailynote/{now.strftime("%Y-%m-%d")}|📅 Today's Note]]

---
""")

        # Focus section - uses new tickler model
        # Order: Flagged, Past Deadline, Deadline Today, Tickled Today
        focus_items = (
            categories["flagged"]
            + categories["past_deadline"]
            + categories["deadline_today"]
            + categories["tickled_today"]
        )
        if focus_items:
            sections.append("## 🔥 Focus Now\n")

            # Flagged (urgent)
            for r in categories["flagged"][:5]:
                sections.append(f"- [ ] 🚨 {r['title']}")

            # Past deadline
            for r in categories["past_deadline"][:5]:
                days = r.get("_days_overdue", "?")
                sections.append(f"- [ ] ⚠️ **{days}d OVERDUE** {r['title']}")

            # Deadline today
            for r in categories["deadline_today"][:5]:
                sections.append(f"- [ ] 📅 **DUE TODAY** {r['title']}")

            # Tickled today (surfaced for review)
            for r in categories["tickled_today"][:5]:
                source = r.get("_tickler_source", "tickler")
                if source == "overdue_tickler":
                    days = r.get("_days_past", "?")
                    sections.append(f"- [ ] 🔔 Review ({days}d ago): {r['title']}")
                elif source == "someday":
                    sections.append(f"- [ ] 💭 Surfaced: {r['title']}")
                else:
                    sections.append(f"- [ ] 🔔 Tickled: {r['title']}")

            sections.append("")

        # Deadline This Week
        if categories["deadline_this_week"]:
            sections.append(
                f"## 📅 Deadlines This Week ({len(categories['deadline_this_week'])})\n"
            )
            for r in sorted(
                categories["deadline_this_week"],
                key=lambda x: x.get("deadline") or "",
            )[:10]:
                days = r.get("_days_until", "?")
                deadline = r.get("deadline", "")
                sections.append(f"- [ ] {r['title']} *(due {deadline}, {days}d)*")
            sections.append("")

        # Inbox
        if categories["inbox"]:
            sections.append(f"## 📥 Inbox ({len(categories['inbox'])} items)\n")
            for r in categories["inbox"][:20]:
                sections.append(self.format_task(r, show_list=False))
            if len(categories["inbox"]) > 20:
                sections.append(f"\n*...and {len(categories['inbox']) - 20} more*")
            sections.append(
                "\n*Process during weekly review: Add dates or #someday tag*\n"
            )

        # Flagged Emails
        if emails:
            sections.append(f"## 📧 Flagged Emails ({len(emails)})\n")
            for email in emails[:10]:
                sender = email.get("from_name") or email.get("from", "Unknown")
                subject = email.get("subject", "No subject")[:50]
                msg_id = email.get("id", "")
                link = f"message://%3C{msg_id}%3E" if msg_id else ""
                sections.append(f"- [ ] {sender} - {subject} [→]({link})")
            sections.append("")

        # By Project
        if categories["by_project"]:
            sections.append("## 📁 By Project\n")
            for project, tasks in sorted(categories["by_project"].items()):
                sections.append(f"### {project} ({len(tasks)})")
                for r in tasks[:5]:
                    sections.append(self.format_task(r, show_list=False))
                if len(tasks) > 5:
                    sections.append(f"*...and {len(tasks) - 5} more*")
                sections.append("")

        # By Context
        if categories["by_context"]:
            sections.append("## 🏷️ By Context\n")
            for context, tasks in sorted(categories["by_context"].items()):
                sections.append(f"### @{context} ({len(tasks)})")
                for r in tasks[:5]:
                    sections.append(self.format_task(r, show_list=True))
                sections.append("")

        # Waiting For
        if categories["waiting"]:
            sections.append(f"## ⏸️ Waiting For ({len(categories['waiting'])} items)\n")
            for r in categories["waiting"][:10]:
                sections.append(self.format_task(r))
            sections.append("")

        # Someday/Maybe
        if categories["someday"]:
            sections.append(
                f"## 💭 Someday/Maybe ({len(categories['someday'])} items)\n"
            )
            for r in categories["someday"][:10]:
                sections.append(f"- {r['title']}")
            if len(categories["someday"]) > 10:
                sections.append(f"\n*...and {len(categories['someday']) - 10} more*")
            sections.append("")

        return "\n".join(sections)

    def save(self) -> Path:
        """Generate and save the dashboard."""
        content = self.generate()

        with open(self.dashboard_path, "w") as f:
            f.write(content)

        print(f"✅ Generated GTD Dashboard: {self.dashboard_path}")
        return self.dashboard_path


def main():
    """CLI entry point."""
    import sys

    dashboard = GTDDashboard()

    if len(sys.argv) > 1:
        if sys.argv[1] == "preview":
            print(dashboard.generate())
        elif sys.argv[1] == "save":
            dashboard.save()
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage: python dashboard.py [preview|save]")
    else:
        # Default: save
        dashboard.save()


if __name__ == "__main__":
    main()
