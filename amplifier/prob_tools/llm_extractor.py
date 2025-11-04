"""
LLM-based Event Extraction

Uses LLMs to analyze commits and extract structured bug/refactoring patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic

from amplifier.prob_tools.git_analyzer import Commit


@dataclass
class BugEvent:
    """A bug pattern extracted from a commit"""

    commit_sha: str
    bug_type: str  # "null_pointer", "race_condition", "type_error", etc.
    root_cause: str  # What caused it
    fix_pattern: str  # How it was fixed
    file_path: str
    function_name: str | None
    severity: str  # "low", "medium", "high", "critical"
    could_be_prevented: bool
    prevention_method: str | None  # How it could have been prevented


@dataclass
class RefactoringEvent:
    """A refactoring outcome extracted from commits/PRs"""

    commit_sha: str
    refactoring_type: str  # "dependency_injection", "extract_method", etc.
    approach: str  # "big_bang", "incremental"
    outcome: str  # "success", "failure", "partial"
    cost_hours: float | None
    tests_broken: int
    files_affected: int


class LLMExtractor:
    """Extract structured events from git commits using LLM"""

    def __init__(self, api_key: str | None = None):
        self.client = Anthropic(api_key=api_key)

    async def extract_bug_event(self, commit: Commit) -> BugEvent | None:
        """Extract bug pattern from a bug fix commit"""

        prompt = f"""Analyze this git commit and extract bug pattern information.

Commit message: {commit.message}

Files changed: {", ".join(commit.files_changed[:5])}

Diff (first 500 chars):
{commit.diff[:500]}

Extract:
1. bug_type: Type of bug (null_pointer, race_condition, type_error, logic_error, etc.)
2. root_cause: What caused the bug (missing_null_check, incorrect_logic, etc.)
3. fix_pattern: How it was fixed (added_guard_clause, fixed_condition, etc.)
4. file_path: Main file where bug was
5. function_name: Function where bug was (if identifiable)
6. severity: low/medium/high/critical
7. could_be_prevented: true/false - could this have been caught earlier?
8. prevention_method: If preventable, how? (linting, type_checking, better_tests, etc.)

Return ONLY valid JSON in this exact format:
{{
  "bug_type": "...",
  "root_cause": "...",
  "fix_pattern": "...",
  "file_path": "...",
  "function_name": "..." or null,
  "severity": "...",
  "could_be_prevented": true or false,
  "prevention_method": "..." or null
}}

If this is NOT a bug fix commit, return: {{"not_bug_fix": true}}
"""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        import json

        result = json.loads(response.content[0].text)

        if result.get("not_bug_fix"):
            return None

        return BugEvent(
            commit_sha=commit.sha,
            bug_type=result["bug_type"],
            root_cause=result["root_cause"],
            fix_pattern=result["fix_pattern"],
            file_path=result["file_path"],
            function_name=result.get("function_name"),
            severity=result["severity"],
            could_be_prevented=result["could_be_prevented"],
            prevention_method=result.get("prevention_method"),
        )

    async def extract_refactoring_event(self, commit: Commit) -> RefactoringEvent | None:
        """Extract refactoring pattern from commit"""

        prompt = f"""Analyze this git commit for refactoring patterns.

Commit message: {commit.message}

Files changed: {len(commit.files_changed)} files

Extract:
1. refactoring_type: Type of refactoring (dependency_injection, extract_method, rename, etc.)
2. approach: big_bang (all at once) or incremental (step by step)
3. outcome: success/failure/partial
4. tests_broken: How many tests were affected (estimate from diff)
5. files_affected: {len(commit.files_changed)}

Return ONLY valid JSON:
{{
  "refactoring_type": "...",
  "approach": "big_bang" or "incremental",
  "outcome": "success" or "failure" or "partial",
  "tests_broken": number,
  "files_affected": {len(commit.files_changed)}
}}

If this is NOT a refactoring commit, return: {{"not_refactoring": true}}
"""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022", max_tokens=1000, messages=[{"role": "user", "content": prompt}]
        )

        import json

        result = json.loads(response.content[0].text)

        if result.get("not_refactoring"):
            return None

        return RefactoringEvent(
            commit_sha=commit.sha,
            refactoring_type=result["refactoring_type"],
            approach=result["approach"],
            outcome=result["outcome"],
            cost_hours=None,
            tests_broken=result["tests_broken"],
            files_affected=result["files_affected"],
        )

    async def analyze_commit_batch(self, commits: list[Commit]) -> dict[str, list[Any]]:
        """Analyze a batch of commits and extract all events"""

        bug_events = []
        refactoring_events = []

        for commit in commits:
            # Try to extract bug event
            bug_event = await self.extract_bug_event(commit)
            if bug_event:
                bug_events.append(bug_event)

            # Try to extract refactoring event
            refactoring_event = await self.extract_refactoring_event(commit)
            if refactoring_event:
                refactoring_events.append(refactoring_event)

        return {"bug_events": bug_events, "refactoring_events": refactoring_events}
