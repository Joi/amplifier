"""
Session state schema for GTD review.

Defines the data structures for session persistence.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime


@dataclass
class Decision:
    """User decision on a review item"""

    action: str  # complete, defer, delete, reschedule, prioritize
    timestamp: datetime
    scheduled_date: datetime | None = None
    priority: int | None = None
    notes: str | None = None


@dataclass
class SessionState:
    """State for a GTD review session"""

    session_id: str
    created_at: datetime
    updated_at: datetime
    current_source: str
    current_index: int
    reviewed_items: list[str] = field(default_factory=list)
    decisions: dict[str, Decision] = field(default_factory=dict)
    completed: bool = False
