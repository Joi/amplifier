"""
Session Manager brick - handles session persistence and state management.

This is the foundation for resume capability. Saves progress after every decision.
"""

from dataclasses import asdict
from datetime import datetime

from ..utils import get_data_dir
from ..utils import read_json
from ..utils import write_json
from .schema import Decision
from .schema import SessionState


class SessionManager:
    """Manages GTD review session state with automatic persistence"""

    def __init__(self: "SessionManager") -> None:
        self.session_dir = get_data_dir() / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = self.session_dir / "current_session.json"

    def create_session(self: "SessionManager") -> SessionState:
        """Create a new review session"""
        session_id = f"gtd-review-{datetime.now().strftime('%Y-%m-%d-%H-%M')}"
        state = SessionState(
            session_id=session_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            current_source="",
            current_index=0,
        )
        self.save_progress(state)
        return state

    def load_session(self: "SessionManager", session_id: str) -> SessionState:
        """Load an existing session by ID"""
        data = read_json(self.current_file)
        if data.get("session_id") != session_id:
            raise ValueError(f"Session {session_id} not found")
        return self._dict_to_state(data)

    def save_progress(self: "SessionManager", state: SessionState) -> None:
        """Save session progress (called after every decision)"""
        state.updated_at = datetime.now()
        data = asdict(state)
        # Convert datetime objects to ISO strings
        data["created_at"] = state.created_at.isoformat()
        data["updated_at"] = state.updated_at.isoformat()
        for _item_id, decision in data["decisions"].items():
            decision["timestamp"] = decision["timestamp"].isoformat()
            if decision.get("scheduled_date"):
                decision["scheduled_date"] = decision["scheduled_date"].isoformat()

        write_json(data, self.current_file)

    def mark_reviewed(self: "SessionManager", state: SessionState, item_id: str, decision: Decision) -> None:
        """Mark an item as reviewed with the user's decision"""
        state.reviewed_items.append(item_id)
        state.decisions[item_id] = decision
        self.save_progress(state)

    def can_resume(self: "SessionManager") -> bool:
        """Check if there's a resumable session"""
        if not self.current_file.exists():
            return False
        data = read_json(self.current_file)
        return not data.get("completed", True)

    def get_latest_session(self: "SessionManager") -> SessionState | None:
        """Get the latest session if it exists and is incomplete"""
        if not self.can_resume():
            return None
        data = read_json(self.current_file)
        return self._dict_to_state(data)

    def _dict_to_state(self: "SessionManager", data: dict) -> SessionState:
        """Convert dict to SessionState"""
        # Convert ISO strings back to datetime
        decisions = {}
        for item_id, dec_data in data.get("decisions", {}).items():
            decisions[item_id] = Decision(
                action=dec_data["action"],
                timestamp=datetime.fromisoformat(dec_data["timestamp"]),
                scheduled_date=(
                    datetime.fromisoformat(dec_data["scheduled_date"]) if dec_data.get("scheduled_date") else None
                ),
                priority=dec_data.get("priority"),
                notes=dec_data.get("notes"),
            )

        return SessionState(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            current_source=data.get("current_source", ""),
            current_index=data.get("current_index", 0),
            reviewed_items=data.get("reviewed_items", []),
            decisions=decisions,
            completed=data.get("completed", False),
        )
