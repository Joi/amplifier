"""
Event Storage

Stores extracted events from git history analysis.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from amplifier.prob_tools.llm_extractor import BugEvent
from amplifier.prob_tools.llm_extractor import RefactoringEvent


class EventStore:
    """Store and retrieve extracted events"""

    def __init__(self, storage_path: Path | None = None):
        if storage_path is None:
            storage_path = Path.home() / ".amplifier" / "git_events"

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.bug_events_file = self.storage_path / "bug_events.jsonl"
        self.refactoring_events_file = self.storage_path / "refactoring_events.jsonl"

    def store_bug_event(self, event: BugEvent) -> None:
        """Store a bug event"""
        with open(self.bug_events_file, "a") as f:
            f.write(json.dumps(self._event_to_dict(event)) + "\n")

    def store_refactoring_event(self, event: RefactoringEvent) -> None:
        """Store a refactoring event"""
        with open(self.refactoring_events_file, "a") as f:
            f.write(json.dumps(self._event_to_dict(event)) + "\n")

    def get_all_bug_events(self) -> list[BugEvent]:
        """Get all stored bug events"""
        if not self.bug_events_file.exists():
            return []

        events = []
        with open(self.bug_events_file) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    events.append(
                        BugEvent(
                            commit_sha=data["commit_sha"],
                            bug_type=data["bug_type"],
                            root_cause=data["root_cause"],
                            fix_pattern=data["fix_pattern"],
                            file_path=data["file_path"],
                            function_name=data.get("function_name"),
                            severity=data["severity"],
                            could_be_prevented=data["could_be_prevented"],
                            prevention_method=data.get("prevention_method"),
                        )
                    )
        return events

    def get_all_refactoring_events(self) -> list[RefactoringEvent]:
        """Get all stored refactoring events"""
        if not self.refactoring_events_file.exists():
            return []

        events = []
        with open(self.refactoring_events_file) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    events.append(
                        RefactoringEvent(
                            commit_sha=data["commit_sha"],
                            refactoring_type=data["refactoring_type"],
                            approach=data["approach"],
                            outcome=data["outcome"],
                            cost_hours=data.get("cost_hours"),
                            tests_broken=data["tests_broken"],
                            files_affected=data["files_affected"],
                        )
                    )
        return events

    def get_bug_patterns(self) -> dict[str, Any]:
        """Get aggregate bug pattern statistics"""
        events = self.get_all_bug_events()

        if not events:
            return {}

        # Count by bug type
        by_type = {}
        for event in events:
            bug_type = event.bug_type
            if bug_type not in by_type:
                by_type[bug_type] = {
                    "count": 0,
                    "preventable": 0,
                    "prevention_methods": [],
                }
            by_type[bug_type]["count"] += 1
            if event.could_be_prevented:
                by_type[bug_type]["preventable"] += 1
                if event.prevention_method:
                    by_type[bug_type]["prevention_methods"].append(event.prevention_method)

        # Calculate preventable percentage
        for bug_type in by_type:
            total = by_type[bug_type]["count"]
            preventable = by_type[bug_type]["preventable"]
            by_type[bug_type]["preventable_pct"] = preventable / total if total > 0 else 0

        return by_type

    def _event_to_dict(self, event: BugEvent | RefactoringEvent) -> dict:
        """Convert event to dict for JSON serialization"""
        if isinstance(event, BugEvent):
            return {
                "commit_sha": event.commit_sha,
                "bug_type": event.bug_type,
                "root_cause": event.root_cause,
                "fix_pattern": event.fix_pattern,
                "file_path": event.file_path,
                "function_name": event.function_name,
                "severity": event.severity,
                "could_be_prevented": event.could_be_prevented,
                "prevention_method": event.prevention_method,
            }
        return {
            "commit_sha": event.commit_sha,
            "refactoring_type": event.refactoring_type,
            "approach": event.approach,
            "outcome": event.outcome,
            "cost_hours": event.cost_hours,
            "tests_broken": event.tests_broken,
            "files_affected": event.files_affected,
        }
