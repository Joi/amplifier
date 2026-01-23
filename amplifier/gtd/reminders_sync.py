#!/usr/bin/env python3
"""
Apple Reminders Cache Utilities.

Provides utility functions for reading and parsing the reminders cache.
Sync operations now use EventKit exclusively (see eventkit_sync.py).

NOTE: AppleScript-based sync was removed because it triggers macOS
authorization popups that block automated workflows. EventKit uses
a one-time permission grant stored in the TCC database.
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_cache_age(cache_path: Path) -> Optional[int]:
    """Get age of cache in seconds, or None if cache doesn't exist."""
    if not cache_path.exists():
        return None

    try:
        with open(cache_path) as f:
            cache = json.load(f)
        synced_at = cache.get("syncedAt") or cache.get("timestamp")
        if synced_at:
            synced_time = datetime.fromisoformat(synced_at)
            return int((datetime.now() - synced_time).total_seconds())
    except Exception:
        pass

    # Fallback to file modification time
    return int(time.time() - cache_path.stat().st_mtime)


def extract_deadline_from_text(
    title: str, notes: Optional[str] = None
) -> Optional[str]:
    """Extract deadline date from title or notes text.

    Supports patterns like:
    - [due: Jan 25] or [due: 1/25] or [due: 2026-01-25]
    - (due Jan 25) or (due: Jan 25)
    - due: Jan 25 (at end of title)

    Returns date in YYYY-MM-DD format or None if no deadline found.
    """
    text = f"{title} {notes or ''}"

    # Patterns to match
    patterns = [
        r"\[due:\s*([^\]]+)\]",  # [due: X]
        r"\(due:?\s*([^)]+)\)",  # (due X) or (due: X)
        r"(?:^|[\s-])due:\s*(\S+)",  # due: X
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            parsed = _parse_flexible_date(date_str)
            if parsed:
                return parsed

    return None


def _parse_flexible_date(date_str: str) -> Optional[str]:
    """Parse various date formats into YYYY-MM-DD.

    Supports:
    - 2026-01-25 (ISO)
    - 1/25 or 01/25 (M/D, assumes current year)
    - 1/25/26 or 1/25/2026 (M/D/Y)
    - Jan 25 or January 25 (month name)
    - Jan 25, 2026 (month name with year)
    """
    date_str = date_str.strip().rstrip(",")
    current_year = datetime.now().year

    # Try ISO format first: 2026-01-25
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", date_str):
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Try M/D/Y formats: 1/25/26 or 1/25/2026
    if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", date_str):
        try:
            parts = date_str.split("/")
            month, day = int(parts[0]), int(parts[1])
            year = int(parts[2])
            if year < 100:
                year += 2000
            return f"{year}-{month:02d}-{day:02d}"
        except (ValueError, IndexError):
            pass

    # Try M/D format: 1/25 (assumes current year)
    if re.match(r"^\d{1,2}/\d{1,2}$", date_str):
        try:
            parts = date_str.split("/")
            month, day = int(parts[0]), int(parts[1])
            return f"{current_year}-{month:02d}-{day:02d}"
        except (ValueError, IndexError):
            pass

    # Try month name formats: Jan 25, January 25, Jan 25 2026
    month_patterns = [
        (
            r"^([A-Za-z]+)\s+(\d{1,2})(?:,?\s+(\d{4}))?$",
            "%b %d",
        ),  # Jan 25 or Jan 25, 2026
    ]

    for pattern, _ in month_patterns:
        match = re.match(pattern, date_str)
        if match:
            try:
                month_name = match.group(1)
                day = int(match.group(2))
                year = int(match.group(3)) if match.group(3) else current_year

                # Parse month name
                for fmt in ["%B", "%b"]:
                    try:
                        month = datetime.strptime(month_name, fmt).month
                        return f"{year}-{month:02d}-{day:02d}"
                    except ValueError:
                        continue
            except (ValueError, IndexError):
                pass

    return None


def load_reminders_cache(cache_path: Optional[Path] = None) -> list[dict]:
    """Load reminders from cache file with field normalization.

    Normalizes fields for consistent access:
    - dueDate (EventKit) -> due (tickler/start date)
    - Extracts deadline from text [due: X] -> deadline field
    """
    if cache_path is None:
        cache_path = Path.home() / "switchboard" / "reminders" / "reminders_cache.json"

    cache_path = Path(os.path.expanduser(str(cache_path)))

    if not cache_path.exists():
        return []

    with open(cache_path) as f:
        cache = json.load(f)

    # Handle both old and new schema
    by_list = cache.get("byList") or cache.get("lists", {})

    reminders = []
    for list_name, items in by_list.items():
        for item in items:
            item["list"] = list_name

            # Normalize date field: dueDate (EventKit) -> due
            if "dueDate" in item and "due" not in item:
                item["due"] = item["dueDate"]

            # Extract deadline from text [due: X] pattern
            title = item.get("title", "")
            notes = item.get("notes")
            deadline = extract_deadline_from_text(title, notes)
            if deadline:
                item["deadline"] = deadline

            reminders.append(item)

    return reminders


def get_cache_info(cache_path: Optional[Path] = None) -> dict:
    """Get cache metadata including freshness."""
    if cache_path is None:
        cache_path = Path.home() / "switchboard" / "reminders" / "reminders_cache.json"

    cache_path = Path(os.path.expanduser(str(cache_path)))

    if not cache_path.exists():
        return {
            "exists": False,
            "cache_age_seconds": None,
            "cache_age_human": "no cache",
            "is_stale": True,
            "synced_at": None,
        }

    try:
        with open(cache_path) as f:
            cache = json.load(f)

        # Handle both old and new schema
        synced_at = cache.get("syncedAt") or cache.get("timestamp")
        total_count = cache.get("totalCount") or cache.get("totalReminders", 0)
        list_count = cache.get("listCount") or len(
            cache.get("byList", cache.get("lists", {}))
        )

        age_seconds = get_cache_age(cache_path)

        # Consider cache stale after 1 hour
        is_stale = age_seconds is None or age_seconds > 3600

        # Human-readable age
        if age_seconds is None:
            age_human = "unknown"
        elif age_seconds < 60:
            age_human = f"{age_seconds}s ago"
        elif age_seconds < 3600:
            age_human = f"{age_seconds // 60}m ago"
        elif age_seconds < 86400:
            age_human = f"{age_seconds // 3600}h ago"
        else:
            age_human = f"{age_seconds // 86400}d ago"

        return {
            "exists": True,
            "cache_age_seconds": age_seconds,
            "cache_age_human": age_human,
            "is_stale": is_stale,
            "synced_at": synced_at,
            "total_count": total_count,
            "list_count": list_count,
            "partial": cache.get("partial", False),
            "lists_failed": cache.get("listsFailed", cache.get("listsFailed", [])),
        }
    except Exception as e:
        return {
            "exists": True,
            "error": str(e),
            "cache_age_seconds": None,
            "cache_age_human": "error reading cache",
            "is_stale": True,
            "synced_at": None,
        }
