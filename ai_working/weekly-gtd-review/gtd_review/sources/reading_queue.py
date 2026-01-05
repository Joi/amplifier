"""
Reading Queue data source - integrates with switchboard reading queue.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from ..utils import read_json
from ..utils import write_json
from .base import DataSource
from .base import ReviewItem


class ReadingQueueSource(DataSource):
    """Reading Queue integration via switchboard data"""

    def __init__(self, queue_path: Path | None = None) -> None:
        if queue_path is None:
            queue_path = Path.home() / "switchboard" / "data" / "reading-queue.json"
        self.queue_path = queue_path

    def name(self) -> str:
        return "reading"

    async def load_items(self) -> list[ReviewItem]:
        """Load items from reading queue"""
        data = read_json(self.queue_path)

        items = []
        for item_data in data.get("items", []):
            # Skip if marked as read
            if item_data.get("read", False):
                continue

            # Convert to ReviewItem
            item = ReviewItem(
                id=f"reading:{item_data.get('id', item_data.get('url', 'unknown'))}",
                source="reading",
                title=item_data.get("title", "Untitled"),
                description=item_data.get("description"),
                due_date=None,  # Reading queue doesn't have due dates
                priority=item_data.get("priority", 0),
                tags=item_data.get("tags", []),
                metadata={
                    "added_date": item_data.get("added_date"),
                    "source": item_data.get("source"),
                    "category": item_data.get("category"),
                },
                url=item_data.get("url"),
            )
            items.append(item)

        return items

    async def execute_action(self, item: ReviewItem, action: str, **kwargs) -> None:
        """
        Execute decision on reading queue item.

        Updates the reading-queue.json file directly.
        """
        # Load current queue
        data = read_json(self.queue_path)

        # Find the item
        item_id = item.id.replace("reading:", "")
        for queue_item in data.get("items", []):
            if queue_item.get("id") == item_id or queue_item.get("url") == item_id:
                if action == "complete":
                    # Mark as read
                    queue_item["read"] = True
                    queue_item["read_date"] = datetime.now().isoformat()
                elif action == "delete":
                    # Remove from queue
                    data["items"].remove(queue_item)
                elif action == "prioritize":
                    # Update priority
                    queue_item["priority"] = kwargs.get("priority", 0)
                elif action == "defer":
                    # Add defer date marker
                    queue_item["deferred_until"] = (
                        kwargs.get("scheduled_date", "").isoformat() if kwargs.get("scheduled_date") else None
                    )

                # Save updated queue
                write_json(data, self.queue_path)
                break

    def get_context(self, item: ReviewItem) -> dict[str, Any]:
        """Get context for AI recommendation"""
        age_days = None
        if item.metadata.get("added_date"):
            added = datetime.fromisoformat(item.metadata["added_date"])
            age_days = (datetime.now() - added).days

        return {
            "age_days": age_days,
            "source": item.metadata.get("source"),
            "category": item.metadata.get("category"),
            "has_url": bool(item.url),
        }
