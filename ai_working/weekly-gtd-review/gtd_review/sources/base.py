"""
Base contract for all data sources.

This defines the "stud" interface that all source "bricks" must implement.
"""

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any


@dataclass
class ReviewItem:
    """Normalized item across all data sources"""

    id: str
    source: str  # "reminders", "reading", "calendar"
    title: str
    description: str | None = None
    due_date: datetime | None = None
    priority: int | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    url: str | None = None


class DataSource(ABC):
    """Abstract base for all data sources - defines the contract"""

    @abstractmethod
    def name(self: "DataSource") -> str:
        """Source identifier (e.g., 'reminders', 'reading')"""
        pass

    @abstractmethod
    async def load_items(self: "DataSource") -> list[ReviewItem]:
        """Load all items needing review from this source"""
        pass

    @abstractmethod
    async def execute_action(self: "DataSource", item: ReviewItem, action: str, **kwargs) -> None:
        """Execute user decision on item"""
        pass

    @abstractmethod
    def get_context(self: "DataSource", item: ReviewItem) -> dict[str, Any]:
        """Get AI context for this item"""
        pass
