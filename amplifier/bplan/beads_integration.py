"""
Beads CLI integration for issue tracking.

Provides a Python wrapper around the bd command-line tool for managing
project issues, epics, and dependencies.
"""

import json
import re
import subprocess
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any


class BeadsError(Exception):
    """Error raised when beads CLI command fails."""


class IssueStatus(str, Enum):
    """Issue status values."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class IssueType(str, Enum):
    """Issue type values."""

    EPIC = "epic"
    TASK = "task"
    BUG = "bug"
    FEATURE = "feature"
    CHORE = "chore"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass
class BeadsIssue:
    """Represents a beads issue."""

    id: str
    title: str
    type: IssueType
    status: IssueStatus
    priority: int = 2
    description: str = ""
    labels: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    assignee: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    requires_evidence: bool = True
    required_evidence_type: str | None = None

    def attach_evidence(self, evidence_id: str) -> None:
        """Attach evidence ID to this issue."""
        if evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)

    @property
    def content(self) -> str:
        """Alias for title to match EvidenceRequiredTodo interface."""
        return self.title

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BeadsIssue":
        """Create BeadsIssue from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            type=IssueType(data["type"]),
            status=IssueStatus(data["status"].replace("-", "_")),
            priority=data.get("priority", 2),
            description=data.get("description", ""),
            labels=data.get("labels", []),
            dependencies=data.get("dependencies", []),
            assignee=data.get("assignee", ""),
            evidence_ids=data.get("evidence_ids", []),
            requires_evidence=data.get("requires_evidence", True),
            required_evidence_type=data.get("required_evidence_type"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert BeadsIssue to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type.value,
            "status": self.status.value.replace("_", "-"),
            "priority": self.priority,
            "description": self.description,
            "labels": self.labels,
            "dependencies": self.dependencies,
            "assignee": self.assignee,
            "evidence_ids": self.evidence_ids,
            "requires_evidence": self.requires_evidence,
            "required_evidence_type": self.required_evidence_type,
        }


class BeadsClient:
    """Client for interacting with beads CLI."""

    def __init__(self, bd_path: str = "bd") -> None:
        """
        Initialize BeadsClient.

        Args:
            bd_path: Path to bd executable (default: "bd" in PATH)
        """
        self.bd_path = bd_path

    def _run_command(self, args: list[str], capture_output: bool = True) -> subprocess.CompletedProcess[str]:
        """
        Run a bd command.

        Args:
            args: Command arguments (excluding 'bd' itself)
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess with command results

        Raises:
            BeadsError: If command fails
        """
        cmd = [self.bd_path] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                raise BeadsError(f"bd command failed: {error_msg}")

            return result

        except FileNotFoundError:
            raise BeadsError(f"bd executable not found at: {self.bd_path}")
        except Exception as e:
            raise BeadsError(f"Failed to run bd command: {e!s}")

    def _parse_issue_id(self, output: str) -> str:
        """
        Parse issue ID from bd command output.

        Args:
            output: Command output text

        Returns:
            Issue ID (e.g., "amplifier-123")

        Raises:
            BeadsError: If issue ID cannot be parsed
        """
        # Look for patterns like "amplifier-123" or "bd-456"
        match = re.search(r"([a-zA-Z]+-\d+)", output)
        if match:
            return match.group(1)

        raise BeadsError(f"Could not parse issue ID from output: {output}")

    def create_issue(
        self,
        title: str,
        description: str = "",
        issue_type: IssueType = IssueType.TASK,
        priority: int = 2,
        depends_on: list[str] | None = None,
        labels: list[str] | None = None,
        assignee: str = "",
    ) -> str:
        """
        Create a new issue.

        Args:
            title: Issue title
            description: Issue description
            issue_type: Type of issue (epic, task, bug, feature)
            priority: Priority (0-4, 0=highest)
            depends_on: List of issue IDs this depends on
            labels: List of labels
            assignee: Assignee username

        Returns:
            Created issue ID

        Raises:
            BeadsError: If creation fails
        """
        args = ["create", title, "-t", issue_type.value, "-p", str(priority)]

        if description:
            args.extend(["-d", description])

        if depends_on:
            # Convert to beads dependency format: "blocks:id1,blocks:id2"
            deps_str = ",".join(f"blocks:{dep}" for dep in depends_on)
            args.extend(["--deps", deps_str])

        if labels:
            args.extend(["-l", ",".join(labels)])

        if assignee:
            args.extend(["-a", assignee])

        result = self._run_command(args)
        return self._parse_issue_id(result.stdout)

    def update_status(self, issue_id: str, status: IssueStatus) -> None:
        """
        Update issue status.

        Args:
            issue_id: Issue ID to update
            status: New status

        Raises:
            BeadsError: If update fails
        """
        # Convert status to bd format (e.g., IN_PROGRESS -> in_progress)
        status_str = status.value.replace("_", "-")
        args = ["update", issue_id, "--status", status_str]
        self._run_command(args)

    def close_issue(self, issue_id: str) -> None:
        """
        Close an issue.

        Args:
            issue_id: Issue ID to close

        Raises:
            BeadsError: If closing fails
        """
        args = ["close", issue_id]
        self._run_command(args)

    def add_comment(self, issue_id: str, comment: str) -> None:
        """
        Add a comment/note to an issue.

        Args:
            issue_id: Issue ID
            comment: Comment text

        Raises:
            BeadsError: If adding comment fails
        """
        # Beads doesn't have a separate comment command, so we append to description
        # Get current issue first
        issue = self.get_issue(issue_id)
        updated_desc = f"{issue.description}\n\n---\n{comment}" if issue.description else comment

        args = ["update", issue_id, "-d", updated_desc]
        self._run_command(args)

    def list_issues(self, status: IssueStatus | None = None) -> list[BeadsIssue]:
        """
        List issues.

        Args:
            status: Filter by status (optional)

        Returns:
            List of BeadsIssue objects

        Raises:
            BeadsError: If listing fails
        """
        args = ["list", "--json"]

        # Note: bd might not support status filtering in list command
        # We'll filter in Python after fetching all issues

        result = self._run_command(args)

        try:
            issues_data = json.loads(result.stdout)
            issues = [BeadsIssue.from_dict(issue_data) for issue_data in issues_data]

            # Filter by status if requested
            if status:
                issues = [issue for issue in issues if issue.status == status]

            return issues

        except json.JSONDecodeError as e:
            raise BeadsError(f"Failed to parse JSON output: {e}")

    def get_issue(self, issue_id: str) -> BeadsIssue:
        """
        Get a specific issue.

        Args:
            issue_id: Issue ID

        Returns:
            BeadsIssue object

        Raises:
            BeadsError: If issue not found or retrieval fails
        """
        args = ["show", issue_id, "--json"]
        result = self._run_command(args)

        try:
            issue_data = json.loads(result.stdout)
            return BeadsIssue.from_dict(issue_data)
        except json.JSONDecodeError as e:
            raise BeadsError(f"Failed to parse JSON output: {e}")

    def get_ready_issues(self) -> list[BeadsIssue]:
        """
        Get issues that are ready to work on (no blockers).

        Returns:
            List of ready BeadsIssue objects

        Raises:
            BeadsError: If retrieval fails
        """
        args = ["ready", "--json"]
        result = self._run_command(args)

        try:
            issues_data = json.loads(result.stdout)
            return [BeadsIssue.from_dict(issue_data) for issue_data in issues_data]
        except json.JSONDecodeError as e:
            raise BeadsError(f"Failed to parse JSON output: {e}")

    def close_with_evidence(self, issue: BeadsIssue, enforcer: Any) -> Any:
        """
        Close an issue with evidence validation.

        Args:
            issue: Issue to close
            enforcer: BlockingEnforcer instance for validation

        Returns:
            CompletionResult indicating success or failure

        Raises:
            BeadsError: If closing fails
        """
        # Import here to avoid circular dependency

        # Validate evidence before closing
        result = enforcer.attempt_completion(issue)

        if not result.blocked:
            # Evidence validated, update status to closed
            issue.status = IssueStatus.CLOSED

        return result

    def close_issue_with_validation(self, issue: BeadsIssue, enforcer: Any) -> bool:
        """
        Close an issue with evidence validation, raising on failure.

        Args:
            issue: Issue to close
            enforcer: BlockingEnforcer instance for validation

        Returns:
            True if successfully closed

        Raises:
            EvidenceValidationError: If validation fails
        """
        # Import here to avoid circular dependency
        from amplifier.bplan.todowrite_integration import EvidenceValidationError

        # Validate evidence
        if not enforcer.validator.validate_completion(issue):
            raise EvidenceValidationError("Evidence validation failed")

        # Update status to closed
        issue.status = IssueStatus.CLOSED
        return True
