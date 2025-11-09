"""
Tests for beads CLI integration utility.

Following test-first philosophy:
- Tests written before implementation
- Tests use real subprocess calls (mocked for testing)
- Tests verify actual command construction and error handling
"""

import json
import subprocess
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from amplifier.bplan.beads_integration import BeadsClient
from amplifier.bplan.beads_integration import BeadsError
from amplifier.bplan.beads_integration import BeadsIssue
from amplifier.bplan.beads_integration import IssueStatus
from amplifier.bplan.beads_integration import IssueType


class TestBeadsClient:
    """Test BeadsClient for bd CLI integration."""

    @pytest.fixture
    def client(self) -> BeadsClient:
        """Create a BeadsClient instance for testing."""
        return BeadsClient(bd_path="/usr/local/bin/bd")

    @pytest.fixture
    def mock_run(self):  # type: ignore[misc]
        """Create a mock subprocess.run function."""
        with patch("subprocess.run") as mock:
            yield mock

    def test_create_epic_success(self, client: BeadsClient, mock_run: MagicMock) -> None:
        """Test creating an epic issue."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="✓ Created issue: amplifier-100\n"
        )

        issue_id = client.create_issue(
            title="Test Epic",
            description="Test epic description",
            issue_type=IssueType.EPIC,
            priority=1,
        )

        assert issue_id == "amplifier-100"
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "bd" in cmd[0]
        assert "create" in cmd
        assert "Test Epic" in cmd
        assert "-t" in cmd
        assert "epic" in cmd

    def test_create_task_with_dependencies(self, client: BeadsClient, mock_run: MagicMock) -> None:
        """Test creating a task with dependencies."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="✓ Created issue: amplifier-101\n"
        )

        issue_id = client.create_issue(
            title="Test Task",
            description="Test task description",
            issue_type=IssueType.TASK,
            depends_on=["amplifier-100"],
            labels=["test", "phase-1"],
        )

        assert issue_id == "amplifier-101"
        cmd = mock_run.call_args[0][0]
        assert "--deps" in cmd
        # Find the deps value
        deps_idx = cmd.index("--deps")
        assert "blocks:amplifier-100" in cmd[deps_idx + 1]
        assert "--labels" in cmd or "-l" in cmd

    def test_update_issue_status(self, client: BeadsClient, mock_run: MagicMock) -> None:
        """Test updating issue status."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="✓ Updated issue: amplifier-101\n"
        )

        client.update_status("amplifier-101", IssueStatus.IN_PROGRESS)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "bd" in cmd[0]
        assert "update" in cmd
        assert "amplifier-101" in cmd
        assert "--status" in cmd
        assert "in_progress" in cmd or "in-progress" in cmd

    def test_close_issue(self, client: BeadsClient, mock_run: MagicMock) -> None:
        """Test closing an issue."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="✓ Closed amplifier-101: Closed\n"
        )

        client.close_issue("amplifier-101")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "bd" in cmd[0]
        assert "close" in cmd
        assert "amplifier-101" in cmd

    def test_add_comment(self, client: BeadsClient, mock_run: MagicMock) -> None:
        """Test adding a comment to an issue."""
        # First call is get_issue (returns JSON), second is update
        mock_json = {
            "id": "amplifier-101",
            "title": "Test Task",
            "type": "task",
            "status": "open",
            "priority": 2,
            "description": "Original description",
        }
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(mock_json)),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="✓ Updated issue: amplifier-101\n"),
        ]

        client.add_comment("amplifier-101", "Test comment")

        assert mock_run.call_count == 2
        # Second call should be update
        update_cmd = mock_run.call_args_list[1][0][0]
        assert "bd" in update_cmd[0]
        assert "update" in update_cmd
        assert "amplifier-101" in update_cmd
        # Comment should be appended to description
        assert "-d" in update_cmd

    def test_list_issues(self, client: BeadsClient, mock_run: MagicMock) -> None:
        """Test listing issues."""
        mock_json = [
            {
                "id": "amplifier-100",
                "title": "Test Epic",
                "type": "epic",
                "status": "open",
                "priority": 1,
            },
            {
                "id": "amplifier-101",
                "title": "Test Task",
                "type": "task",
                "status": "in_progress",
                "priority": 2,
            },
        ]
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(mock_json))

        issues = client.list_issues()

        assert len(issues) == 2
        assert issues[0].id == "amplifier-100"
        assert issues[0].title == "Test Epic"
        assert issues[0].type == IssueType.EPIC
        assert issues[1].status == IssueStatus.IN_PROGRESS

    def test_get_issue(self, client: BeadsClient, mock_run: MagicMock) -> None:
        """Test getting a specific issue."""
        mock_json = {
            "id": "amplifier-100",
            "title": "Test Epic",
            "type": "epic",
            "status": "open",
            "priority": 1,
            "description": "Test description",
        }
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(mock_json))

        issue = client.get_issue("amplifier-100")

        assert issue.id == "amplifier-100"
        assert issue.title == "Test Epic"
        assert issue.description == "Test description"

    def test_command_failure(self, client: BeadsClient, mock_run: MagicMock) -> None:
        """Test handling of bd command failure."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stderr="Error: Issue not found")

        with pytest.raises(BeadsError) as exc_info:
            client.get_issue("amplifier-999")

        assert "Issue not found" in str(exc_info.value)

    def test_parse_issue_id_from_output(self, client: BeadsClient) -> None:
        """Test parsing issue ID from bd command output."""
        output = "✓ Created issue: amplifier-123\n  Title: Test\n  Status: open\n"
        issue_id = client._parse_issue_id(output)
        assert issue_id == "amplifier-123"

    def test_parse_issue_id_alternate_format(self, client: BeadsClient) -> None:
        """Test parsing issue ID from alternate output format."""
        output = "✓ Updated issue: amplifier-456"
        issue_id = client._parse_issue_id(output)
        assert issue_id == "amplifier-456"

    def test_parse_issue_id_not_found(self, client: BeadsClient) -> None:
        """Test error when issue ID not found in output."""
        output = "Some output without an issue ID"
        with pytest.raises(BeadsError) as exc_info:
            client._parse_issue_id(output)
        assert "Could not parse issue ID" in str(exc_info.value)


class TestBeadsIssue:
    """Test BeadsIssue data model."""

    def test_issue_creation(self) -> None:
        """Test creating a BeadsIssue."""
        issue = BeadsIssue(
            id="amplifier-1",
            title="Test Issue",
            type=IssueType.TASK,
            status=IssueStatus.OPEN,
            priority=2,
            description="Test description",
        )

        assert issue.id == "amplifier-1"
        assert issue.title == "Test Issue"
        assert issue.type == IssueType.TASK
        assert issue.status == IssueStatus.OPEN

    def test_issue_from_dict(self) -> None:
        """Test creating BeadsIssue from dictionary."""
        data = {
            "id": "amplifier-2",
            "title": "Test",
            "type": "epic",
            "status": "in_progress",
            "priority": 1,
        }

        issue = BeadsIssue.from_dict(data)

        assert issue.id == "amplifier-2"
        assert issue.type == IssueType.EPIC
        assert issue.status == IssueStatus.IN_PROGRESS

    def test_issue_to_dict(self) -> None:
        """Test converting BeadsIssue to dictionary."""
        issue = BeadsIssue(
            id="amplifier-3",
            title="Test",
            type=IssueType.TASK,
            status=IssueStatus.CLOSED,
            priority=3,
        )

        data = issue.to_dict()

        assert data["id"] == "amplifier-3"
        assert data["type"] == "task"
        assert data["status"] == "closed"


class TestIssueStatus:
    """Test IssueStatus enum."""

    def test_status_values(self) -> None:
        """Test that status enum has expected values."""
        assert IssueStatus.OPEN.value in ["open", "OPEN"]
        assert IssueStatus.IN_PROGRESS.value in ["in_progress", "in-progress", "IN_PROGRESS"]
        assert IssueStatus.CLOSED.value in ["closed", "CLOSED"]

    def test_status_from_string(self) -> None:
        """Test creating status from string."""
        assert IssueStatus("open") == IssueStatus.OPEN
        assert IssueStatus("closed") == IssueStatus.CLOSED


class TestIssueType:
    """Test IssueType enum."""

    def test_type_values(self) -> None:
        """Test that type enum has expected values."""
        assert IssueType.EPIC.value == "epic"
        assert IssueType.TASK.value == "task"
        assert IssueType.BUG.value == "bug"
        assert IssueType.FEATURE.value == "feature"

    def test_type_from_string(self) -> None:
        """Test creating type from string."""
        assert IssueType("epic") == IssueType.EPIC
        assert IssueType("task") == IssueType.TASK
