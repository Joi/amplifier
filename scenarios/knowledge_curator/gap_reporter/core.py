#!/usr/bin/env python3
"""
Gap Reporter - Generates knowledge status reports.

Updates knowledge-status.json with curation results for daily notes integration.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from amplifier.utils.logger import get_logger

from ..state import CurationState

logger = get_logger(__name__)


class GapReporter:
    """Generates knowledge status reports."""

    def __init__(self, status_file: Path):
        self.status_file = Path(status_file)

    async def generate_report(
        self,
        state: CurationState,
        vault_path: Path,
        domain: str | None,
    ) -> None:
        """Generate knowledge-status.json report."""
        # Load existing status or create new
        if self.status_file.exists():
            try:
                status = json.loads(self.status_file.read_text())
            except Exception:
                status = self._create_empty_status()
        else:
            status = self._create_empty_status()

        # Update last run timestamp
        status["lastCuratorRun"] = datetime.now().isoformat()

        # Determine vault name from domain or path
        vault_name = domain.rstrip("/") if domain else vault_path.name

        # Initialize vault entry if needed
        if vault_name not in status["vaults"]:
            status["vaults"][vault_name] = {
                "path": f"{vault_name}/",
                "lastAnalyzed": None,
                "stats": {
                    "totalFiles": 0,
                    "citedFiles": 0,
                    "pendingVerification": 0,
                },
                "needsAttention": [],
            }

        vault_status = status["vaults"][vault_name]
        vault_status["lastAnalyzed"] = datetime.now().strftime("%Y-%m-%d")

        # Update stats from state
        vault_status["stats"]["totalFiles"] = state.stats["total_files"]
        vault_status["stats"]["citedFiles"] = state.stats["citations_added"]
        vault_status["stats"]["pendingVerification"] = self._count_pending(state)

        # Generate needs attention list
        needs_attention = []
        for rel_path, file_state in state.files.items():
            if file_state.error:
                needs_attention.append(
                    {
                        "file": rel_path,
                        "reason": "error",
                        "priority": "high",
                        "details": file_state.error,
                    }
                )
            elif file_state.claims and not file_state.sources_found:
                needs_attention.append(
                    {
                        "file": rel_path,
                        "reason": "uncited-claims",
                        "priority": "medium",
                    }
                )
            elif file_state.sources and not file_state.citations_added:
                needs_attention.append(
                    {
                        "file": rel_path,
                        "reason": "needs-expansion",
                        "priority": "low",
                    }
                )

        # Sort by priority and limit to top 10
        priority_order = {"high": 0, "medium": 1, "low": 2}
        needs_attention.sort(key=lambda x: priority_order.get(x["priority"], 99))
        vault_status["needsAttention"] = needs_attention[:10]

        # Add to recent activity
        if state.stats["citations_added"] > 0:
            activity = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "vault": vault_name,
                "action": "added-citations",
                "file": "multiple"
                if state.stats["citations_added"] > 1
                else next((p for p, f in state.files.items() if f.citations_count > 0), "unknown"),
                "citations": state.stats["citations_added"],
            }
            status["recentActivity"].insert(0, activity)

        # Keep only last 20 activities
        status["recentActivity"] = status["recentActivity"][:20]

        # Write status file
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file.write_text(json.dumps(status, indent=2, ensure_ascii=False))
        logger.info(f"Updated knowledge status: {self.status_file}")

    def _create_empty_status(self) -> dict[str, Any]:
        """Create empty status structure."""
        return {
            "version": "1.0",
            "lastCuratorRun": None,
            "vaults": {},
            "recentActivity": [],
        }

    def _count_pending(self, state: CurationState) -> int:
        """Count files with claims still pending verification."""
        return sum(1 for f in state.files.values() if f.claims and not f.citations_added)
