"""
Git History Analyzer

Extracts commit, PR, and review data from git repositories.
Provides raw data for LLM analysis.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Commit:
    """A git commit with metadata"""

    sha: str
    message: str
    author: str
    date: datetime
    files_changed: list[str]
    insertions: int
    deletions: int
    diff: str


@dataclass
class FileChange:
    """A file change in a commit"""

    path: str
    insertions: int
    deletions: int
    diff: str


class GitAnalyzer:
    """Extract commit data from git repositories"""

    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path)

    def get_recent_commits(self, limit: int = 100) -> list[Commit]:
        """Get recent commits with full metadata"""
        commits = []

        # Get commit SHAs
        result = subprocess.run(
            ["git", "log", f"-{limit}", "--format=%H"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        shas = result.stdout.strip().split("\n")

        for sha in shas:
            commit = self._get_commit_details(sha)
            if commit:
                commits.append(commit)

        return commits

    def _get_commit_details(self, sha: str) -> Commit | None:
        """Get detailed information about a commit"""

        # Get commit metadata
        result = subprocess.run(
            ["git", "show", "--format=%an%n%aI%n%s%n%b", "--no-patch", sha],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        lines = result.stdout.strip().split("\n")
        if len(lines) < 3:
            return None

        author = lines[0]
        date_str = lines[1]
        subject = lines[2]
        body = "\n".join(lines[3:]) if len(lines) > 3 else ""
        message = f"{subject}\n{body}".strip()

        # Get stats
        stats_result = subprocess.run(
            ["git", "show", "--stat", "--format=", sha],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        files_changed = []
        insertions = 0
        deletions = 0

        for line in stats_result.stdout.strip().split("\n"):
            if "|" in line:
                file_path = line.split("|")[0].strip()
                files_changed.append(file_path)

        # Get diff
        diff_result = subprocess.run(
            ["git", "show", sha],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        return Commit(
            sha=sha,
            message=message,
            author=author,
            date=datetime.fromisoformat(date_str.replace("Z", "+00:00")),
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
            diff=diff_result.stdout,
        )

    def get_bug_fix_commits(self, limit: int = 100) -> list[Commit]:
        """Find commits that likely fixed bugs (by commit message)"""
        all_commits = self.get_recent_commits(limit)

        bug_keywords = ["fix", "bug", "error", "crash", "issue", "broken", "revert"]

        bug_fixes = []
        for commit in all_commits:
            message_lower = commit.message.lower()
            if any(keyword in message_lower for keyword in bug_keywords):
                bug_fixes.append(commit)

        return bug_fixes

    def get_file_history(self, file_path: str, limit: int = 50) -> list[Commit]:
        """Get commit history for a specific file"""
        result = subprocess.run(
            ["git", "log", f"-{limit}", "--format=%H", "--", file_path],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        shas = result.stdout.strip().split("\n")
        commits = []

        for sha in shas:
            if sha:
                commit = self._get_commit_details(sha)
                if commit:
                    commits.append(commit)

        return commits
