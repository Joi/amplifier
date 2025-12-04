#!/usr/bin/env python3
"""
State management for Knowledge Curator.

Handles incremental saves and resume capability for long-running curation jobs.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


class FileState(BaseModel):
    """State for a single file being processed."""

    path: str
    claims_extracted: bool = False
    sources_found: bool = False
    citations_added: bool = False
    claims: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    citations_count: int = 0
    error: str | None = None


class CurationState(BaseModel):
    """Overall state for a curation run."""

    version: str = "1.0"
    vault_path: str
    domain: str | None = None
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    stage: str = "scan"  # scan, search, cite, report
    files: dict[str, FileState] = Field(default_factory=dict)
    stats: dict[str, int] = Field(
        default_factory=lambda: {
            "total_files": 0,
            "files_scanned": 0,
            "files_with_claims": 0,
            "sources_found": 0,
            "citations_added": 0,
        }
    )


class StateManager:
    """Manages curation state with incremental saves."""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "curation_state.json"
        self.state: CurationState | None = None

    def initialize(self, vault_path: str, domain: str | None = None) -> CurationState:
        """Initialize a new curation state."""
        self.state = CurationState(vault_path=vault_path, domain=domain)
        self._save()
        return self.state

    def load(self) -> CurationState | None:
        """Load existing state for resume."""
        if not self.state_file.exists():
            return None

        try:
            data = json.loads(self.state_file.read_text())
            self.state = CurationState(**data)
            logger.info(f"Resumed curation from stage: {self.state.stage}")
            return self.state
        except Exception as e:
            logger.warning(f"Could not load state: {e}")
            return None

    def update_file(self, file_path: str, **updates: Any) -> None:
        """Update state for a specific file and save."""
        if self.state is None:
            raise RuntimeError("State not initialized")

        if file_path not in self.state.files:
            self.state.files[file_path] = FileState(path=file_path)

        file_state = self.state.files[file_path]
        for key, value in updates.items():
            if hasattr(file_state, key):
                setattr(file_state, key, value)

        self._save()

    def update_stage(self, stage: str) -> None:
        """Update the current processing stage."""
        if self.state is None:
            raise RuntimeError("State not initialized")
        self.state.stage = stage
        self._save()

    def update_stats(self, **updates: int) -> None:
        """Update statistics."""
        if self.state is None:
            raise RuntimeError("State not initialized")
        self.state.stats.update(updates)
        self._save()

    def mark_complete(self) -> None:
        """Mark curation as complete."""
        if self.state is None:
            raise RuntimeError("State not initialized")
        self.state.completed_at = datetime.now().isoformat()
        self._save()

    def _save(self) -> None:
        """Save state to disk."""
        if self.state is None:
            return

        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(self.state.model_dump_json(indent=2))
