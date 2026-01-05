"""Tests for RemindersSource"""

import json
import tempfile
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest
from gtd_review.sources import RemindersSource
from gtd_review.sources import ReviewItem


@pytest.fixture
def sample_reminders_cache():
    """Create sample reminders cache data"""
    return {
        "lists": [
            {
                "name": "Work",
                "reminders": [
                    {
                        "id": "reminder-1",
                        "title": "Review pull requests",
                        "notes": "Check the pending PRs",
                        "completed": False,
                        "dueDate": "2026-01-10T09:00:00",
                        "priority": 1,
                        "creationDate": "2026-01-05T08:00:00",
                    },
                    {
                        "id": "reminder-2",
                        "title": "Update documentation",
                        "completed": True,  # Should be filtered out
                        "dueDate": "2026-01-08T10:00:00",
                        "creationDate": "2026-01-03T14:00:00",
                    },
                ],
            },
            {
                "name": "Personal",
                "reminders": [
                    {
                        "id": "reminder-3",
                        "title": "Buy groceries",
                        "completed": False,
                        "creationDate": "2026-01-06T18:00:00",
                    }
                ],
            },
        ]
    }


@pytest.fixture
def temp_cache_file(sample_reminders_cache):
    """Create temporary cache file"""
    temp_file = Path(tempfile.mktemp(suffix=".json"))
    temp_file.write_text(json.dumps(sample_reminders_cache))
    yield temp_file
    temp_file.unlink()


@pytest.mark.asyncio
async def test_load_items(temp_cache_file):
    """Test loading reminders from cache"""
    source = RemindersSource(cache_path=temp_cache_file)
    items = await source.load_items()

    # Should load 2 incomplete items (reminder-1 and reminder-3)
    assert len(items) == 2

    # Check first item
    item1 = next(i for i in items if i.title == "Review pull requests")
    assert item1.source == "reminders"
    assert item1.description == "Check the pending PRs"
    assert item1.priority == 1
    assert "Work" in item1.tags
    assert item1.metadata["list"] == "Work"
    assert item1.metadata["reminder_id"] == "reminder-1"

    # Check second item
    item2 = next(i for i in items if i.title == "Buy groceries")
    assert item2.source == "reminders"
    assert item2.due_date is None  # No due date
    assert "Personal" in item2.tags


@pytest.mark.asyncio
async def test_get_context(temp_cache_file):
    """Test context generation for AI"""
    source = RemindersSource(cache_path=temp_cache_file)
    items = await source.load_items()

    item = next(i for i in items if i.title == "Review pull requests")
    context = source.get_context(item)

    assert context["list_name"] == "Work"
    assert context["has_notes"] is True
    assert context["age_days"] is not None
    assert context["overdue_days"] is not None


def test_review_item_normalization():
    """Test ReviewItem creation with various field combinations"""
    # Minimal item
    item1 = ReviewItem(id="test-1", source="reminders", title="Test reminder")
    assert item1.description is None
    assert item1.due_date is None
    assert len(item1.tags) == 0

    # Full item
    item2 = ReviewItem(
        id="test-2",
        source="reminders",
        title="Full reminder",
        description="With notes",
        due_date=datetime(2026, 1, 15, tzinfo=UTC),
        priority=2,
        tags=["work", "urgent"],
        metadata={"custom": "data"},
        url="https://example.com",
    )
    assert item2.description == "With notes"
    assert item2.priority == 2
    assert len(item2.tags) == 2
    assert item2.metadata["custom"] == "data"
