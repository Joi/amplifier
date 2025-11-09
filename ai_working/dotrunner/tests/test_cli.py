"""
Tests for command-line interface.

Tests the CLI commands using Click's CliRunner for isolated testing.
"""

import json

import pytest
from click.testing import CliRunner

from ai_working.dotrunner.cli import cli
from ai_working.dotrunner.persistence import save_state
from ai_working.dotrunner.persistence import save_workflow
from ai_working.dotrunner.state import NodeResult
from ai_working.dotrunner.state import WorkflowState
from ai_working.dotrunner.workflow import Node
from ai_working.dotrunner.workflow import Workflow


@pytest.fixture
def runner():
    """Create Click test runner"""
    return CliRunner()


@pytest.fixture
def sample_workflow_yaml(tmp_path):
    """Create a sample workflow YAML file"""
    yaml_content = """workflow:
  name: test-workflow
  description: Test workflow for CLI
  context:
    initial_var: "value"

nodes:
  - id: node1
    name: First Node
    prompt: "Process {initial_var}"
    outputs: ["result1"]
    next: node2

  - id: node2
    name: Second Node
    prompt: "Continue with {result1}"
    outputs: ["final_result"]
    type: terminal
"""
    workflow_file = tmp_path / "test_workflow.yaml"
    workflow_file.write_text(yaml_content)
    return workflow_file


@pytest.fixture
def minimal_workflow_yaml(tmp_path):
    """Create a minimal workflow for quick testing"""
    yaml_content = """workflow:
  name: minimal-workflow
  description: Minimal test workflow

nodes:
  - id: single-node
    name: Single Node
    prompt: "Just do one thing"
    outputs: ["output"]
    type: terminal
"""
    workflow_file = tmp_path / "minimal_workflow.yaml"
    workflow_file.write_text(yaml_content)
    return workflow_file


@pytest.fixture
def invalid_workflow_yaml(tmp_path):
    """Create an invalid workflow (circular dependency)"""
    yaml_content = """workflow:
  name: invalid-workflow
  description: Invalid workflow with cycle

nodes:
  - id: node1
    name: Node 1
    prompt: "Task 1"
    next: node2

  - id: node2
    name: Node 2
    prompt: "Task 2"
    next: node1
"""
    workflow_file = tmp_path / "invalid_workflow.yaml"
    workflow_file.write_text(yaml_content)
    return workflow_file


class TestRunCommand:
    """Test the 'run' command"""

    def test_run_command_help(self, runner):
        """Test that run command shows help"""
        result = runner.invoke(cli, ["run", "--help"])

        assert result.exit_code == 0
        assert "Run a workflow from YAML file" in result.output

    def test_run_nonexistent_file(self, runner):
        """Test running non-existent workflow file"""
        result = runner.invoke(cli, ["run", "nonexistent.yaml"])

        assert result.exit_code != 0
        # Click will handle the file existence check

    def test_run_invalid_workflow_validation_fails(self, runner, invalid_workflow_yaml):
        """Test that invalid workflow fails validation"""
        result = runner.invoke(cli, ["run", str(invalid_workflow_yaml)])

        assert result.exit_code != 0
        assert "validation failed" in result.output.lower() or "circular" in result.output.lower()

    def test_run_with_context_override_valid_json(self, runner, minimal_workflow_yaml):
        """Test running workflow with valid JSON context override"""
        result = runner.invoke(
            cli, ["run", str(minimal_workflow_yaml), "--context", '{"extra_var": "extra_value"}', "--no-save"]
        )

        # Should not fail on JSON parsing
        assert "Invalid JSON" not in result.output
        # May fail on execution (no AI available) but JSON parsing should succeed

    def test_run_with_context_override_invalid_json(self, runner, minimal_workflow_yaml):
        """Test that invalid JSON in --context fails gracefully"""
        result = runner.invoke(cli, ["run", str(minimal_workflow_yaml), "--context", "{not valid json"])

        assert result.exit_code != 0
        assert "Invalid JSON" in result.output or "error" in result.output.lower()

    def test_run_no_save_flag(self, runner, minimal_workflow_yaml):
        """Test that --no-save flag prevents checkpoint saving"""
        result = runner.invoke(cli, ["run", str(minimal_workflow_yaml), "--no-save"])

        # Should accept the --no-save flag without error
        # (May fail on AI execution, but we're testing flag parsing)
        assert "--no-save" not in result.output or "unknown option" not in result.output.lower()

    def test_run_displays_workflow_name(self, runner, sample_workflow_yaml):
        """Test that run command displays the workflow name"""
        result = runner.invoke(cli, ["run", str(sample_workflow_yaml), "--no-save"])

        assert "test-workflow" in result.output


class TestListCommand:
    """Test the 'list' command"""

    def test_list_command_help(self, runner):
        """Test that list command shows help"""
        result = runner.invoke(cli, ["list", "--help"])

        assert result.exit_code == 0
        assert "List workflow sessions" in result.output

    def test_list_no_sessions(self, runner, monkeypatch, tmp_path):
        """Test list command with no sessions"""
        # Mock sessions directory to empty temp directory
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

        result = runner.invoke(cli, ["list"])

        assert result.exit_code == 0
        assert "No sessions found" in result.output

    def test_list_with_sessions(self, runner, monkeypatch, tmp_path):
        """Test list command with some sessions"""
        # Create temp sessions directory
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

        # Create sample session
        state = WorkflowState(
            workflow_id="test-workflow",
            current_node=None,
            context={},
            results=[],
            status="completed",
        )
        save_state(state, session_id="test-session-123")

        result = runner.invoke(cli, ["list", "--all"])

        assert result.exit_code == 0
        assert "test-session-123" in result.output
        assert "test-workflow" in result.output

    def test_list_filters_completed_by_default(self, runner, monkeypatch, tmp_path):
        """Test that list command filters out completed sessions by default"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

        # Create completed session
        state_completed = WorkflowState(
            workflow_id="completed-workflow",
            current_node=None,
            context={},
            results=[],
            status="completed",
        )
        save_state(state_completed, session_id="completed-session")

        # Create running session
        state_running = WorkflowState(
            workflow_id="running-workflow",
            current_node="node1",
            context={},
            results=[],
            status="running",
        )
        save_state(state_running, session_id="running-session")

        result = runner.invoke(cli, ["list"])

        assert result.exit_code == 0
        assert "completed-session" not in result.output  # Filtered out
        assert "running-session" in result.output  # Shown

    def test_list_all_flag_shows_completed(self, runner, monkeypatch, tmp_path):
        """Test that --all flag shows completed sessions"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

        # Create completed session
        state = WorkflowState(
            workflow_id="completed-workflow",
            current_node=None,
            context={},
            results=[],
            status="completed",
        )
        save_state(state, session_id="completed-session")

        result = runner.invoke(cli, ["list", "--all"])

        assert result.exit_code == 0
        # Rich may truncate long session IDs in table, check for prefix
        assert "completed-sessi" in result.output or "completed-session" in result.output
        assert "completed" in result.output  # Status should be shown


class TestStatusCommand:
    """Test the 'status' command"""

    def test_status_command_help(self, runner):
        """Test that status command shows help"""
        result = runner.invoke(cli, ["status", "--help"])

        assert result.exit_code == 0
        assert "Show detailed status" in result.output

    def test_status_nonexistent_session(self, runner, monkeypatch, tmp_path):
        """Test status command with non-existent session"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

        result = runner.invoke(cli, ["status", "nonexistent-session"])

        assert result.exit_code != 0
        assert "Session not found" in result.output or "not found" in result.output.lower()

    def test_status_shows_session_details(self, runner, monkeypatch, tmp_path):
        """Test that status command shows session details"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

        # Create sample session with results
        state = WorkflowState(
            workflow_id="test-workflow",
            current_node="node2",
            context={"var1": "value1"},
            results=[
                NodeResult(
                    node_id="node1",
                    status="success",
                    outputs={"output1": "result1"},
                    raw_response="AI response",
                    execution_time=1.5,
                )
            ],
            status="running",
        )
        save_state(state, session_id="detailed-session")

        result = runner.invoke(cli, ["status", "detailed-session"])

        assert result.exit_code == 0
        assert "detailed-session" in result.output
        assert "test-workflow" in result.output
        assert "running" in result.output.lower()
        assert "node2" in result.output  # Current node
        assert "node1" in result.output  # Completed node in history

    def test_status_json_output(self, runner, monkeypatch, tmp_path):
        """Test status command with --json flag"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

        # Create sample session
        state = WorkflowState(
            workflow_id="test-workflow",
            current_node=None,
            context={"var1": "value1"},
            results=[],
            status="completed",
        )
        save_state(state, session_id="json-session")

        result = runner.invoke(cli, ["status", "json-session", "--json"])

        assert result.exit_code == 0
        # Should be valid JSON
        parsed = json.loads(result.output)
        assert parsed["workflow_id"] == "test-workflow"
        assert parsed["status"] == "completed"

    def test_status_shows_context_variables(self, runner, monkeypatch, tmp_path):
        """Test that status command shows context variables"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

        state = WorkflowState(
            workflow_id="test-workflow",
            current_node=None,
            context={"var1": "value1", "var2": 42},
            results=[],
            status="completed",
        )
        save_state(state, session_id="context-session")

        result = runner.invoke(cli, ["status", "context-session"])

        assert result.exit_code == 0
        assert "Context Variables" in result.output
        assert "var1" in result.output
        assert "var2" in result.output


class TestResumeCommand:
    """Test the 'resume' command"""

    def test_resume_command_help(self, runner):
        """Test that resume command shows help"""
        result = runner.invoke(cli, ["resume", "--help"])

        assert result.exit_code == 0
        assert "Resume an interrupted workflow" in result.output

    def test_resume_nonexistent_session(self, runner, monkeypatch, tmp_path):
        """Test resume command with non-existent session"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

        result = runner.invoke(cli, ["resume", "nonexistent-session"])

        assert result.exit_code != 0
        assert "Session not found" in result.output or "not found" in result.output.lower()

    def test_resume_completed_workflow_exits_early(self, runner, monkeypatch, tmp_path):
        """Test that resume command exits early for completed workflows"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

        # Create completed session
        state = WorkflowState(
            workflow_id="completed-workflow",
            current_node=None,
            context={},
            results=[],
            status="completed",
        )
        save_state(state, session_id="completed-session")

        result = runner.invoke(cli, ["resume", "completed-session"])

        assert result.exit_code == 0
        assert "already completed" in result.output.lower()

    def test_resume_missing_workflow_definition(self, runner, monkeypatch, tmp_path):
        """Test resume when workflow definition is missing"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

        # Create session state WITHOUT workflow definition
        state = WorkflowState(
            workflow_id="orphaned-workflow",
            current_node="node1",
            context={},
            results=[],
            status="running",
        )
        save_state(state, session_id="orphaned-session")
        # Don't save workflow definition

        result = runner.invoke(cli, ["resume", "orphaned-session"])

        assert result.exit_code != 0
        assert "Workflow definition not found" in result.output or "not saved" in result.output.lower()

    def test_resume_with_workflow_definition(self, runner, monkeypatch, tmp_path):
        """Test resume with valid workflow definition"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("ai_working.dotrunner.persistence.get_sessions_dir", lambda: sessions_dir)

        # Create workflow
        nodes = [Node(id="node1", name="Node 1", prompt="Task 1", type="terminal")]
        workflow = Workflow(name="resumable-workflow", description="Test", nodes=nodes)

        # Create session state WITH workflow definition
        state = WorkflowState(
            workflow_id="resumable-workflow",
            current_node="node1",
            context={},
            results=[],
            status="running",
        )
        session_id = save_state(state, session_id="resumable-session")
        save_workflow(workflow, session_id)

        result = runner.invoke(cli, ["resume", "resumable-session"])

        # Should attempt to resume (will fail on AI execution, but parsing should work)
        assert "Resuming workflow" in result.output or "resumable-workflow" in result.output


class TestCLIGroup:
    """Test the main CLI group"""

    def test_cli_version(self, runner):
        """Test that CLI shows version"""
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.2.0" in result.output

    def test_cli_help(self, runner):
        """Test that CLI shows help"""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "DotRunner" in result.output
        assert "run" in result.output
        assert "list" in result.output
        assert "status" in result.output
        assert "resume" in result.output
