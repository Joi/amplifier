"""
Reading Queue data source - integrates with ~/switchboard/data/reading-queue.json

Contract:
- Loads unread/unarchived items from reading queue
- Provides context (age, type, estimated time)
- Executes actions (complete, defer, delete, prioritize)
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from amplifier.utils.file_io import read_json
from amplifier.utils.file_io import write_json

from .base import DataSource
from .base import ReviewItem


class ReadingQueueSource(DataSource):
    """Reading queue integration"""

    def __init__(self, queue_file: Path | None = None):
        if queue_file is None:
            queue_file = Path.home() / "switchboard" / "data" / "reading-queue.json"
        self.queue_file = queue_file

    def name(self) -> str:
        return "reading"

    async def load_items(self) -> list[ReviewItem]:
        """Load unread/unarchived items from reading queue"""
        if not self.queue_file.exists():
            return []

        data = read_json(self.queue_file)
        items = []

        for item_data in data.get("items", []):
            # Skip archived items
            if item_data.get("status") == "archived":
                continue

            # Convert to ReviewItem
            added_date = datetime.fromisoformat(item_data["addedDate"]) if item_data.get("addedDate") else None

            item = ReviewItem(
                id=f"reading:{item_data['id']}",
                source="reading",
                title=item_data.get("title", "Untitled"),
                description=item_data.get("notes"),
                due_date=datetime.fromisoformat(item_data["deadline"]) if item_data.get("deadline") else None,
                priority=self._map_priority(item_data.get("priority", "medium")),
                tags=item_data.get("tags", []),
                metadata={
                    "type": item_data.get("type"),  # url or pdf
                    "url": item_data.get("url"),
                    "path": item_data.get("path"),
                    "added_date": item_data.get("addedDate"),
                    "estimated_minutes": item_data.get("estimatedMinutes"),
                    "source": item_data.get("source"),
                },
                url=item_data.get("url"),
            )
            items.append(item)

        return items

    def _map_priority(self, priority_str: str) -> int:
        """Map string priority to int"""
        mapping = {"low": 3, "medium": 2, "high": 1}
        return mapping.get(priority_str, 2)

    async def execute_action(self, item: ReviewItem, action: str, **kwargs) -> None:
        """Execute decision on reading queue item"""
        # Load current queue
        data = read_json(self.queue_file)

        # Find the item
        item_id = item.id.replace("reading:", "")
        item_data = None
        item_index = None
        for i, existing in enumerate(data.get("items", [])):
            if existing["id"] == item_id:
                item_data = existing
                item_index = i
                break

        if not item_data:
            raise ValueError(f"Reading item {item_id} not found in queue")

        # Update based on action
        if action == "complete":
            item_data["status"] = "archived"
            item_data["finishedDate"] = datetime.now().isoformat()
            item_data["archivedDate"] = datetime.now().isoformat()
            item_data["notes"] = "Completed via GTD review"

        elif action == "defer":
            # Keep as to-read but update notes
            scheduled_date = kwargs.get("scheduled_date")
            if scheduled_date:
                item_data["deadline"] = scheduled_date.isoformat()
            notes = kwargs.get("notes", "Deferred via GTD review")
            existing_notes = item_data.get("notes", "")
            item_data["notes"] = f"{existing_notes}; {notes}".strip("; ")

        elif action == "delete":
            item_data["status"] = "archived"
            item_data["archivedDate"] = datetime.now().isoformat()
            item_data["notes"] = "Archived: No longer relevant (GTD review)"

        elif action == "prioritize":
            new_priority = kwargs.get("priority", 1)
            priority_map = {1: "high", 2: "medium", 3: "low"}
            item_data["priority"] = priority_map.get(new_priority, "high")

        # Save updated queue
        write_json(data, self.queue_file)

    def get_context(self, item: ReviewItem) -> dict[str, Any]:
        """Get context for AI recommendation"""
        age_days = None
        if item.metadata and item.metadata.get("added_date"):
            added = datetime.fromisoformat(item.metadata["added_date"])
            age_days = (datetime.now() - added).days

        overdue_days = None
        if item.due_date and item.due_date < datetime.now():
            overdue_days = (datetime.now() - item.due_date).days

        return {
            "type": item.metadata.get("type") if item.metadata else None,  # url or pdf
            "age_days": age_days,
            "overdue_days": overdue_days,
            "estimated_minutes": item.metadata.get("estimated_minutes") if item.metadata else None,
            "source": item.metadata.get("source") if item.metadata else None,
            "has_url": bool(item.metadata.get("url") if item.metadata else None),
        }
