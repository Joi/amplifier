"""
Review session data structures.

Defines Decision dataclass for capturing user choices during review.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Decision:
    """
    User's decision about a review item.

    Captures what action to take and any associated details.
    """

    action: str  # complete, defer, delete, reschedule, prioritize
    timestamp: datetime
    scheduled_date: datetime | None = None  # For defer/reschedule
    priority: int | None = None  # For prioritize (1=high, 2=medium, 3=low)
    notes: str | None = None  # Optional user notes
