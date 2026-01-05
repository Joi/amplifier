"""
Apple Reminders data source - integrates with obs-dailynotes reminders cache.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from ..utils import read_json
from .base import DataSource
from .base import ReviewItem


class RemindersSource(DataSource):
    """Apple Reminders integration via obs-dailynotes cache"""

    def __init__(self: "RemindersSource", cache_path: Path = None) -> None:
        if cache_path is None:
            cache_path = Path.home() / "switchboard" / "reminders" / "reminders_cache.json"
        self.cache_path = cache_path

    def name(self: "RemindersSource") -> str:
        return "reminders"

    async def load_items(self: "RemindersSource") -> list[ReviewItem]:
        """Load incomplete reminders from cache"""
        data = read_json(self.cache_path)

        items = []
        for list_data in data.get("lists", []):
            list_name = list_data.get("name", "Unknown")
            for reminder in list_data.get("reminders", []):
                # Skip completed items
                if reminder.get("completed", False):
                    continue

                # Convert to ReviewItem
                item = ReviewItem(
                    id=f"reminders:{reminder.get('id', 'unknown')}",
                    source="reminders",
                    title=reminder.get("title", "Untitled"),
                    description=reminder.get("notes"),
                    due_date=(datetime.fromisoformat(reminder["dueDate"]) if reminder.get("dueDate") else None),
                    priority=reminder.get("priority"),
                    tags=[list_name],
                    metadata={
                        "list": list_name,
                        "created_at": reminder.get("creationDate"),
                        "reminder_id": reminder.get("id"),
                    },
                )
                items.append(item)

        return items

    async def execute_action(self: "RemindersSource", item: ReviewItem, action: str, **kwargs) -> None:
        """
        Execute decision on reminder.

        NOTE: This currently just logs the action. Actual update requires
        either AppleScript integration or obs-dailynotes sync mechanism.
        TODO: Implement actual reminder updates
        """
        reminder_id = item.metadata.get("reminder_id")

        if action == "complete":
            # TODO: Mark reminder as complete via AppleScript or API
            print(f"Would mark reminder {reminder_id} as complete")
        elif action == "defer":
            # TODO: Update due date
            new_date = kwargs.get("scheduled_date")
            print(f"Would defer reminder {reminder_id} to {new_date}")
        elif action == "delete":
            # TODO: Delete reminder
            print(f"Would delete reminder {reminder_id}")
        elif action == "reschedule":
            # TODO: Update due date
            new_date = kwargs.get("scheduled_date")
            print(f"Would reschedule reminder {reminder_id} to {new_date}")
        elif action == "prioritize":
            # TODO: Update priority
            new_priority = kwargs.get("priority")
            print(f"Would set priority of reminder {reminder_id} to {new_priority}")

    def get_context(self: "RemindersSource", item: ReviewItem) -> dict[str, Any]:
        """Get context for AI recommendation"""
        age_days = None
        if item.metadata.get("created_at"):
            created = datetime.fromisoformat(item.metadata["created_at"])
            age_days = (datetime.now() - created).days

        overdue_days = None
        if item.due_date:
            overdue_days = (datetime.now() - item.due_date).days

        return {
            "list_name": item.metadata.get("list"),
            "age_days": age_days,
            "overdue_days": overdue_days,
            "has_notes": bool(item.description),
        }
