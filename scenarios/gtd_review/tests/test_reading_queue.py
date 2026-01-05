"""Tests for reading queue source"""

import asyncio
import json
import sys
import tempfile
from datetime import datetime
from datetime import timedelta
from pathlib import Path

import pytest

# Add parent directory to path so we can import from scenarios
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scenarios.gtd_review.sources.reading_queue import ReadingQueueSource


@pytest.fixture
def temp_queue_file():
    """Create temporary reading queue file"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        queue_data = {
            "items": [
                {
                    "id": "test-1",
                    "title": "Test Article",
                    "type": "url",
                    "url": "https://example.com/article",
                    "status": "to-read",
                    "priority": "high",
                    "addedDate": (datetime.now() - timedelta(days=5)).isoformat(),
                    "deadline": (datetime.now() + timedelta(days=2)).isoformat(),
                    "tags": ["tech", "ai"],
                    "notes": "Interesting article",
                    "estimatedMinutes": 15,
                },
                {
                    "id": "test-2",
                    "title": "Old PDF",
                    "type": "pdf",
                    "path": "/path/to/pdf",
                    "status": "to-read",
                    "priority": "low",
                    "addedDate": (datetime.now() - timedelta(days=30)).isoformat(),
                },
                {
                    "id": "test-3",
                    "title": "Archived Article",
                    "type": "url",
                    "url": "https://example.com/old",
                    "status": "archived",
                    "archivedDate": datetime.now().isoformat(),
                },
            ]
        }
        json.dump(queue_data, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink()


def test_load_items(temp_queue_file):
    """Test loading items from queue"""
    source = ReadingQueueSource(queue_file=temp_queue_file)
    items = asyncio.run(source.load_items())

    # Should load 2 items (excluding archived)
    assert len(items) == 2

    # Check first item
    item = items[0]
    assert item.id == "reading:test-1"
    assert item.source == "reading"
    assert item.title == "Test Article"
    assert item.priority == 1  # high -> 1
    assert "tech" in item.tags
    assert item.url == "https://example.com/article"


def test_get_context(temp_queue_file):
    """Test getting context for recommendations"""
    source = ReadingQueueSource(queue_file=temp_queue_file)
    items = asyncio.run(source.load_items())

    item = items[0]
    context = source.get_context(item)

    assert context["type"] == "url"
    assert context["age_days"] == 5
    assert context["estimated_minutes"] == 15
    assert context["has_url"] is True


def test_execute_complete(temp_queue_file):
    """Test completing an item"""
    source = ReadingQueueSource(queue_file=temp_queue_file)
    items = asyncio.run(source.load_items())

    item = items[0]
    asyncio.run(source.execute_action(item, "complete"))

    # Reload and verify
    updated_items = asyncio.run(source.load_items())
    assert len(updated_items) == 1  # One less item (now archived)


def test_execute_defer(temp_queue_file):
    """Test deferring an item"""
    source = ReadingQueueSource(queue_file=temp_queue_file)
    items = asyncio.run(source.load_items())

    item = items[0]
    new_date = datetime.now() + timedelta(days=7)
    asyncio.run(source.execute_action(item, "defer", scheduled_date=new_date, notes="Deferred for later"))

    # Reload and verify still exists
    updated_items = asyncio.run(source.load_items())
    assert len(updated_items) == 2


def test_execute_delete(temp_queue_file):
    """Test deleting an item"""
    source = ReadingQueueSource(queue_file=temp_queue_file)
    items = asyncio.run(source.load_items())

    item = items[1]
    asyncio.run(source.execute_action(item, "delete"))

    # Reload and verify archived
    updated_items = asyncio.run(source.load_items())
    assert len(updated_items) == 1


def test_execute_prioritize(temp_queue_file):
    """Test prioritizing an item"""
    source = ReadingQueueSource(queue_file=temp_queue_file)
    items = asyncio.run(source.load_items())

    item = items[1]  # Low priority item
    asyncio.run(source.execute_action(item, "prioritize", priority=1))

    # Reload and verify priority changed
    updated_items = asyncio.run(source.load_items())
    updated_item = [i for i in updated_items if i.id == item.id][0]
    assert updated_item.priority == 1  # Now high priority
