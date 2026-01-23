#!/usr/bin/env python3
"""
Presentations tracking system - Python port from obs-dailynotes.

Manages Google Slides presentations with status tracking, deadlines, and metadata.
Data stored in ~/switchboard/data/presentations.json
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


# Data file location
DATA_DIR = Path(os.path.expanduser("~/switchboard/data"))
PRESENTATIONS_FILE = DATA_DIR / "presentations.json"


def _ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_presentations() -> dict:
    """Load presentations from JSON file."""
    _ensure_data_dir()

    if not PRESENTATIONS_FILE.exists():
        initial = {"version": "1.0", "presentations": [], "nextId": 1}
        _save_presentations(initial)
        return initial

    return json.loads(PRESENTATIONS_FILE.read_text())


def _save_presentations(data: dict):
    """Save presentations to JSON file."""
    _ensure_data_dir()
    PRESENTATIONS_FILE.write_text(json.dumps(data, indent=2) + "\n")


def _generate_id(next_id: int) -> str:
    """Generate unique presentation ID."""
    date_str = datetime.now().strftime("%Y%m%d")
    return f"pres-{date_str}-{next_id:03d}"


def _validate_slides_url(url: str) -> bool:
    """Validate Google Slides URL."""
    return "docs.google.com/presentation" in url


def add_presentation(
    url: str,
    title: str,
    deadline: Optional[str] = None,
    priority: str = "medium",
    notion_url: Optional[str] = None,
    slack_url: Optional[str] = None,
    tags: Optional[list] = None,
    notes: str = "",
    estimated_hours: Optional[float] = None,
) -> dict:
    """Add a new presentation."""
    if not _validate_slides_url(url):
        raise ValueError(
            "Invalid Google Slides URL. Expected: https://docs.google.com/presentation/d/..."
        )

    if not title:
        raise ValueError("Title is required")

    data = _load_presentations()
    pres_id = _generate_id(data["nextId"])

    presentation = {
        "id": pres_id,
        "title": title,
        "url": url,
        "notionUrl": notion_url,
        "slackUrl": slack_url,
        "status": "todo",
        "priority": priority,
        "deadline": deadline,
        "createdDate": datetime.now().isoformat(),
        "startedDate": None,
        "completedDate": None,
        "archivedDate": None,
        "tags": tags or [],
        "notes": notes,
        "reminderTaskId": None,
        "estimatedHours": estimated_hours,
        "actualHours": 0,
    }

    data["presentations"].append(presentation)
    data["nextId"] += 1

    _save_presentations(data)

    return presentation


def find_presentation(pres_id: str) -> tuple[dict, dict, int]:
    """Find presentation by ID. Returns (data, presentation, index)."""
    data = _load_presentations()

    for i, pres in enumerate(data["presentations"]):
        if pres["id"] == pres_id:
            return data, pres, i

    raise ValueError(
        f"Presentation {pres_id} not found. Use 'gtd pres_list' to see available presentations."
    )


def start_presentation(pres_id: str) -> dict:
    """Mark presentation as started."""
    data, pres, _ = find_presentation(pres_id)

    if pres["status"] == "done":
        raise ValueError("Presentation is already marked as done.")

    if not pres["startedDate"]:
        pres["startedDate"] = datetime.now().isoformat()

    _save_presentations(data)
    return pres


def complete_presentation(
    pres_id: str, actual_hours: Optional[float] = None, notes: Optional[str] = None
) -> dict:
    """Mark presentation as complete."""
    data, pres, _ = find_presentation(pres_id)

    if pres["status"] == "done":
        raise ValueError("Presentation is already marked as done.")

    pres["status"] = "done"
    pres["completedDate"] = datetime.now().isoformat()

    if actual_hours is not None:
        pres["actualHours"] = actual_hours

    if notes:
        date_str = datetime.now().strftime("%Y-%m-%d")
        existing_notes = pres["notes"]
        pres["notes"] = (
            f"{existing_notes}\n\nCompletion notes ({date_str}): {notes}"
            if existing_notes
            else f"Completion notes ({date_str}): {notes}"
        )

    _save_presentations(data)
    return pres


def archive_presentation(pres_id: str) -> dict:
    """Archive presentation."""
    data, pres, _ = find_presentation(pres_id)

    pres["status"] = "archived"
    pres["archivedDate"] = datetime.now().isoformat()

    _save_presentations(data)
    return pres


def update_presentation(pres_id: str, **updates) -> dict:
    """Update presentation metadata."""
    data, pres, _ = find_presentation(pres_id)

    if "title" in updates and updates["title"]:
        pres["title"] = updates["title"]

    if "url" in updates and updates["url"]:
        if not _validate_slides_url(updates["url"]):
            raise ValueError("Invalid Google Slides URL")
        pres["url"] = updates["url"]

    if "notion_url" in updates:
        pres["notionUrl"] = updates["notion_url"]

    if "slack_url" in updates:
        pres["slackUrl"] = updates["slack_url"]

    if "deadline" in updates:
        pres["deadline"] = updates["deadline"]

    if "priority" in updates and updates["priority"]:
        pres["priority"] = updates["priority"]

    if "notes" in updates:
        pres["notes"] = updates["notes"]

    if "estimated_hours" in updates:
        pres["estimatedHours"] = updates["estimated_hours"]

    if "add_tag" in updates and updates["add_tag"]:
        if updates["add_tag"] not in pres["tags"]:
            pres["tags"].append(updates["add_tag"])

    if "remove_tag" in updates and updates["remove_tag"]:
        pres["tags"] = [t for t in pres["tags"] if t != updates["remove_tag"]]

    _save_presentations(data)
    return pres


def list_presentations(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tag: Optional[str] = None,
    include_archived: bool = False,
) -> list:
    """List presentations with optional filters."""
    data = _load_presentations()
    presentations = data["presentations"]

    # Filter by status
    if status:
        presentations = [p for p in presentations if p["status"] == status]

    # Filter by priority
    if priority:
        presentations = [p for p in presentations if p["priority"] == priority]

    # Filter by tag
    if tag:
        presentations = [p for p in presentations if tag in p["tags"]]

    # Exclude archived unless requested
    if not include_archived:
        presentations = [p for p in presentations if p["status"] != "archived"]

    # Sort: priority first, then deadline, then status
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    status_order = {"todo": 0, "done": 1, "archived": 2}

    def sort_key(p):
        prio = priority_order.get(p["priority"], 2)
        deadline = p["deadline"] or "9999-99-99"  # None sorts last
        stat = status_order.get(p["status"], 1)
        return (prio, deadline, stat)

    presentations.sort(key=sort_key)

    return presentations


def get_stats() -> dict:
    """Get presentation statistics."""
    data = _load_presentations()
    all_pres = data["presentations"]
    now = datetime.now()

    return {
        "total": len(all_pres),
        "todo": len([p for p in all_pres if p["status"] == "todo"]),
        "done": len([p for p in all_pres if p["status"] == "done"]),
        "archived": len([p for p in all_pres if p["status"] == "archived"]),
        "in_progress": len(
            [p for p in all_pres if p["status"] == "todo" and p["startedDate"]]
        ),
        "planned": len(
            [p for p in all_pres if p["status"] == "todo" and not p["startedDate"]]
        ),
        "urgent": len(
            [
                p
                for p in all_pres
                if p["priority"] == "urgent" and p["status"] != "archived"
            ]
        ),
        "overdue": len(
            [
                p
                for p in all_pres
                if p["deadline"]
                and datetime.fromisoformat(p["deadline"]) < now
                and p["status"] not in ("done", "archived")
            ]
        ),
    }


if __name__ == "__main__":
    # Quick test
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "list":
        pres = list_presentations()
        for p in pres:
            print(f"[{p['id']}] {p['title']} ({p['status']})")
    else:
        stats = get_stats()
        print(
            f"Presentations: {stats['total']} total, {stats['todo']} todo, {stats['done']} done"
        )
