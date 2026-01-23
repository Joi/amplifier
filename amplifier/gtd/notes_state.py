#!/usr/bin/env python3
"""
Sync state manager for Notes.app ↔ Obsidian sync

Tracks which notes have been synced and their last known state
to detect changes and handle conflicts.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class SyncState:
    """State manager for sync tracking."""

    def __init__(self, sync_dir: Path):
        self.sync_dir = sync_dir
        self.state_file = sync_dir / ".sync-state.json"
        self.state = self._load()

    def _load(self) -> dict:
        """Load state from file, or create default state."""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load sync state: {e}")

        # Return default state
        return {"enabledSince": datetime.now().isoformat(), "notes": {}}

    def save(self) -> None:
        """Save current state to file."""
        try:
            # Ensure directory exists
            self.sync_dir.mkdir(parents=True, exist_ok=True)

            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save sync state: {e}")

    def get_enabled_since(self) -> datetime:
        """Get the date when sync was enabled."""
        return datetime.fromisoformat(self.state["enabledSince"])

    def is_tracked(self, note_id: str) -> bool:
        """Check if a note is being tracked."""
        return note_id in self.state["notes"]

    def get_note_state(self, note_id: str) -> Optional[dict]:
        """Get tracking info for a note."""
        return self.state["notes"].get(note_id)

    def find_note_id_by_path(self, obsidian_path: str) -> Optional[str]:
        """Find note ID by Obsidian path."""
        for note_id, info in self.state["notes"].items():
            if info.get("obsidianPath") == obsidian_path:
                return note_id
        return None

    def track_note(
        self,
        note_id: str,
        obsidian_path: str,
        notes_modified_at: datetime,
        obsidian_mtime: datetime,
    ) -> None:
        """Track a new note."""
        self.state["notes"][note_id] = {
            "obsidianPath": obsidian_path,
            "lastSyncedAt": datetime.now().isoformat(),
            "notesModifiedAt": notes_modified_at.isoformat(),
            "obsidianMtime": obsidian_mtime.isoformat(),
        }
        self.save()

    def update_sync_time(
        self, note_id: str, notes_modified_at: datetime, obsidian_mtime: datetime
    ) -> None:
        """Update sync timestamp for a note."""
        if note_id in self.state["notes"]:
            self.state["notes"][note_id]["lastSyncedAt"] = datetime.now().isoformat()
            self.state["notes"][note_id]["notesModifiedAt"] = (
                notes_modified_at.isoformat()
            )
            self.state["notes"][note_id]["obsidianMtime"] = obsidian_mtime.isoformat()
            self.save()

    def untrack_note(self, note_id: str) -> None:
        """Remove a note from tracking."""
        if note_id in self.state["notes"]:
            del self.state["notes"][note_id]
            self.save()

    def get_all_tracked(self) -> dict:
        """Get all tracked notes."""
        return dict(self.state["notes"])

    def initialize(self, since: Optional[datetime] = None) -> None:
        """Initialize sync state (for first-time setup)."""
        self.state = {
            "enabledSince": (since or datetime.now()).isoformat(),
            "notes": {},
        }
        self.save()

    def update_last_sync(self) -> None:
        """Update the global last sync timestamp."""
        self.state["lastSyncAt"] = datetime.now().isoformat()
        self.save()

    def get_stats(self) -> dict:
        """Get summary statistics."""
        notes = list(self.state["notes"].values())
        return {
            "enabledSince": self.state["enabledSince"],
            "lastSyncAt": self.state.get("lastSyncAt"),
            "totalTracked": len(notes),
            "notes": [
                {"path": n["obsidianPath"], "lastSynced": n["lastSyncedAt"]}
                for n in notes
            ],
        }
