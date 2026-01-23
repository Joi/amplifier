#!/usr/bin/env python3
"""
Reading queue system - Python port from obs-dailynotes.

Manages a queue of URLs and PDFs to read with status tracking.
Data stored in ~/switchboard/data/reading-queue.json
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


# Data file location
DATA_DIR = Path(os.path.expanduser("~/switchboard/data"))
READING_FILE = DATA_DIR / "reading-queue.json"


def _ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_reading_queue() -> dict:
    """Load reading queue from JSON file."""
    _ensure_data_dir()

    if not READING_FILE.exists():
        initial = {"version": "1.0", "items": [], "nextId": 1}
        _save_reading_queue(initial)
        return initial

    return json.loads(READING_FILE.read_text())


def _save_reading_queue(data: dict):
    """Save reading queue to JSON file."""
    _ensure_data_dir()
    READING_FILE.write_text(json.dumps(data, indent=2) + "\n")


def _generate_id(next_id: int) -> str:
    """Generate unique reading ID."""
    date_str = datetime.now().strftime("%Y%m%d")
    return f"read-{date_str}-{next_id:03d}"


def _detect_type(input_str: str) -> str:
    """Detect if input is URL or file path."""
    if input_str.startswith("http://") or input_str.startswith("https://"):
        return "url"
    if input_str.endswith(".pdf"):
        return "pdf"
    if "://" in input_str or "www." in input_str:
        return "url"
    return "pdf"


def add_reading(
    input_str: str,
    title: str,
    item_type: Optional[str] = None,
    deadline: Optional[str] = None,
    priority: str = "medium",
    source: str = "manual",
    tags: Optional[list] = None,
    notes: str = "",
    estimated_minutes: Optional[int] = None,
) -> dict:
    """Add a new reading item (URL or PDF)."""
    if not title:
        raise ValueError("Title is required")

    data = _load_reading_queue()
    item_id = _generate_id(data["nextId"])
    detected_type = item_type or _detect_type(input_str)

    item = {
        "id": item_id,
        "type": detected_type,
        "title": title,
        "url": input_str if detected_type == "url" else None,
        "path": input_str if detected_type == "pdf" else None,
        "status": "to-read",
        "priority": priority,
        "deadline": deadline,
        "addedDate": datetime.now().isoformat(),
        "startedDate": None,
        "finishedDate": None,
        "archivedDate": None,
        "source": source,
        "tags": tags or [],
        "notes": notes,
        "estimatedMinutes": estimated_minutes,
        "reminderTaskId": None,
    }

    data["items"].append(item)
    data["nextId"] += 1

    _save_reading_queue(data)

    return item


def find_reading(item_id: str) -> tuple[dict, dict, int]:
    """Find reading item by ID. Returns (data, item, index)."""
    data = _load_reading_queue()

    for i, item in enumerate(data["items"]):
        if item["id"] == item_id:
            return data, item, i

    raise ValueError(
        f"Reading item {item_id} not found. Use 'gtd read_list' to see available items."
    )


def start_reading(item_id: str) -> dict:
    """Start reading (to-read -> reading)."""
    data, item, _ = find_reading(item_id)

    if item["status"] != "to-read":
        raise ValueError(
            f"Cannot start reading item in '{item['status']}' status. Only 'to-read' items can be started."
        )

    item["status"] = "reading"
    item["startedDate"] = datetime.now().isoformat()

    _save_reading_queue(data)
    return item


def finish_reading(item_id: str, notes: Optional[str] = None) -> dict:
    """Finish reading (reading -> read)."""
    data, item, _ = find_reading(item_id)

    if item["status"] != "reading":
        raise ValueError(
            f"Cannot finish reading item in '{item['status']}' status. Start it first with 'gtd read_start'."
        )

    item["status"] = "read"
    item["finishedDate"] = datetime.now().isoformat()

    if notes:
        date_str = datetime.now().strftime("%Y-%m-%d")
        existing_notes = item["notes"]
        item["notes"] = (
            f"{existing_notes}\n\nReading notes ({date_str}): {notes}"
            if existing_notes
            else f"Reading notes ({date_str}): {notes}"
        )

    _save_reading_queue(data)
    return item


def archive_reading(item_id: str) -> dict:
    """Archive reading item."""
    data, item, _ = find_reading(item_id)

    item["status"] = "archived"
    item["archivedDate"] = datetime.now().isoformat()

    _save_reading_queue(data)
    return item


def update_reading(item_id: str, **updates) -> dict:
    """Update reading item metadata."""
    data, item, _ = find_reading(item_id)

    if "title" in updates and updates["title"]:
        item["title"] = updates["title"]

    if "url" in updates and updates["url"]:
        item["url"] = updates["url"]

    if "deadline" in updates:
        item["deadline"] = updates["deadline"]

    if "priority" in updates and updates["priority"]:
        item["priority"] = updates["priority"]

    if "notes" in updates:
        item["notes"] = updates["notes"]

    if "estimated_minutes" in updates:
        item["estimatedMinutes"] = updates["estimated_minutes"]

    if "add_tag" in updates and updates["add_tag"]:
        if updates["add_tag"] not in item["tags"]:
            item["tags"].append(updates["add_tag"])

    if "remove_tag" in updates and updates["remove_tag"]:
        item["tags"] = [t for t in item["tags"] if t != updates["remove_tag"]]

    _save_reading_queue(data)
    return item


def list_reading(
    item_type: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tag: Optional[str] = None,
    include_archived: bool = False,
) -> list:
    """List reading items with optional filters."""
    data = _load_reading_queue()
    items = data["items"]

    # Filter by type
    if item_type:
        items = [i for i in items if i["type"] == item_type]

    # Filter by status
    if status:
        items = [i for i in items if i["status"] == status]

    # Filter by priority
    if priority:
        items = [i for i in items if i["priority"] == priority]

    # Filter by tag
    if tag:
        items = [i for i in items if tag in i["tags"]]

    # Exclude archived unless requested
    if not include_archived:
        items = [i for i in items if i["status"] != "archived"]

    # Sort: priority first, then deadline, then status
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    status_order = {"reading": 0, "to-read": 1, "read": 2, "archived": 3}

    def sort_key(item):
        prio = priority_order.get(item["priority"], 2)
        deadline = item["deadline"] or "9999-99-99"
        stat = status_order.get(item["status"], 1)
        return (prio, deadline, stat)

    items.sort(key=sort_key)

    return items


def get_stats() -> dict:
    """Get reading queue statistics."""
    data = _load_reading_queue()
    all_items = data["items"]

    return {
        "total": len(all_items),
        "to_read": len([i for i in all_items if i["status"] == "to-read"]),
        "reading": len([i for i in all_items if i["status"] == "reading"]),
        "read": len([i for i in all_items if i["status"] == "read"]),
        "archived": len([i for i in all_items if i["status"] == "archived"]),
        "urls": len(
            [i for i in all_items if i["type"] == "url" and i["status"] != "archived"]
        ),
        "pdfs": len(
            [i for i in all_items if i["type"] == "pdf" and i["status"] != "archived"]
        ),
    }


if __name__ == "__main__":
    # Quick test
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "list":
        items = list_reading()
        for item in items:
            type_icon = "PDF" if item["type"] == "pdf" else "URL"
            print(f"[{item['id']}] ({type_icon}) {item['title']} ({item['status']})")
    else:
        stats = get_stats()
        print(
            f"Reading: {stats['total']} total, {stats['to_read']} to-read, {stats['reading']} reading, {stats['read']} read"
        )
