"""Tests for SessionManager"""

import shutil
import tempfile
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest
from gtd_review.session import Decision
from gtd_review.session import SessionManager


@pytest.fixture
def temp_session_dir():
    """Create temporary session directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def session_manager(temp_session_dir, monkeypatch):
    """Session manager with temporary storage"""
    manager = SessionManager()
    # Override session_dir to use temp directory
    manager.session_dir = temp_session_dir / "sessions"
    manager.session_dir.mkdir(parents=True, exist_ok=True)
    manager.current_file = manager.session_dir / "current_session.json"
    return manager


def test_create_session(session_manager):
    """Test session creation"""
    state = session_manager.create_session()

    assert state.session_id.startswith("gtd-review-")
    assert state.current_source == ""
    assert state.current_index == 0
    assert len(state.reviewed_items) == 0
    assert len(state.decisions) == 0
    assert state.completed is False


def test_save_and_load_session(session_manager):
    """Test session persistence"""
    # Create and save
    state = session_manager.create_session()
    session_id = state.session_id

    # Modify state
    state.current_source = "reminders"
    state.current_index = 5
    session_manager.save_progress(state)

    # Load and verify
    loaded = session_manager.load_session(session_id)
    assert loaded.session_id == session_id
    assert loaded.current_source == "reminders"
    assert loaded.current_index == 5


def test_mark_reviewed(session_manager):
    """Test marking items as reviewed"""
    state = session_manager.create_session()

    decision = Decision(
        action="complete",
        timestamp=datetime.now(),
        notes="Test completion",
    )

    session_manager.mark_reviewed(state, "item-1", decision)

    assert "item-1" in state.reviewed_items
    assert "item-1" in state.decisions
    assert state.decisions["item-1"].action == "complete"
    assert state.decisions["item-1"].notes == "Test completion"


def test_can_resume(session_manager):
    """Test resume capability detection"""
    # No session yet
    assert session_manager.can_resume() is False

    # Create incomplete session
    state = session_manager.create_session()
    assert session_manager.can_resume() is True

    # Mark completed
    state.completed = True
    session_manager.save_progress(state)
    assert session_manager.can_resume() is False


def test_get_latest_session(session_manager):
    """Test retrieving latest session"""
    # No session
    assert session_manager.get_latest_session() is None

    # Create session
    state = session_manager.create_session()
    state.current_source = "reminders"
    session_manager.save_progress(state)

    # Retrieve
    latest = session_manager.get_latest_session()
    assert latest is not None
    assert latest.session_id == state.session_id
    assert latest.current_source == "reminders"


def test_decision_serialization(session_manager):
    """Test that decisions serialize/deserialize correctly"""
    state = session_manager.create_session()

    decision = Decision(
        action="reschedule",
        timestamp=datetime.now(),
        scheduled_date=datetime(2026, 1, 15, 10, 0, tzinfo=UTC),
        priority=3,
        notes="Moved to next week",
    )

    session_manager.mark_reviewed(state, "item-1", decision)

    # Load and verify
    loaded = session_manager.load_session(state.session_id)
    loaded_decision = loaded.decisions["item-1"]

    assert loaded_decision.action == "reschedule"
    assert loaded_decision.priority == 3
    assert loaded_decision.notes == "Moved to next week"
    assert loaded_decision.scheduled_date.year == 2026
    assert loaded_decision.scheduled_date.month == 1
    assert loaded_decision.scheduled_date.day == 15
