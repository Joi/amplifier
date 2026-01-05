"""
Base abstractions for data sources.

Contract:
- DataSource: Interface for loading items and executing actions
- ReviewItem: Standard item representation across all sources
"""

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ReviewItem:
    """
    Standard representation of an item to review.

    All data sources convert their items to this format.
    """

    id: str  # Unique identifier (source:id)
    source: str  # Source name (reading, todos, calendar)
    title: str
    description: str | None = None
    due_date: datetime | None = None
    priority: int | None = None  # 1=high, 2=medium, 3=low
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None  # Source-specific data
    url: str | None = None


class DataSource(ABC):
    """
    Abstract interface for data sources.

    Each source (reading queue, todos, calendar) implements this interface
    to provide items for review and execute user decisions.
    """

    @abstractmethod
    def name(self) -> str:
        """Return source name (e.g., 'reading', 'todos')"""
        pass

    @abstractmethod
    async def load_items(self) -> list[ReviewItem]:
        """
        Load items requiring review from this source.

        Returns list of ReviewItem objects representing items
        that need attention (unread, overdue, etc.).
        """
        pass

    @abstractmethod
    async def execute_action(self, item: ReviewItem, action: str, **kwargs) -> None:
        """
        Execute user's decision on an item.

        Args:
            item: The ReviewItem to act on
            action: One of: complete, defer, delete, reschedule, prioritize
            **kwargs: Action-specific parameters:
                - scheduled_date: datetime (for defer/reschedule)
                - priority: int (for prioritize)
                - notes: str (for defer)

        Raises:
            ValueError: If action or kwargs are invalid
        """
        pass

    def get_context(self, item: ReviewItem) -> dict[str, Any]:
        """
        Get source-specific context for AI recommendations.

        Override to provide additional context like age, overdue status, etc.

        Returns dict with context data used for recommendations.
        """
        return {}
