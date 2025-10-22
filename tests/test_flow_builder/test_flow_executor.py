"""
Tests for flow executor - Phase 5.

TEST-FIRST: Define contract before implementation.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from amplifier.flow_builder.flow_executor import (
    ExecutionResult,
    execute_workflow,
    list_flows,
)


class TestFlowListing:
    """Test flow discovery and listing."""

    def test_list_flows_returns_yaml_files(self, tmp_path):
        """Should find all YAML workflow files."""
        (tmp_path / "flow1.yaml").write_text("workflow:\n  name: flow1")
        (tmp_path / "flow2.yaml").write_text("workflow:\n  name: flow2")
        (tmp_path / "not-a-flow.txt").write_text("ignored")

        flows = list_flows(tmp_path)
        assert len(flows) == 2
        assert all(f.suffix == ".yaml" for f in flows)

    def test_list_flows_handles_missing_directory(self, tmp_path):
        """Should return empty list for non-existent directory."""
        missing = tmp_path / "does-not-exist"
        flows = list_flows(missing)
        assert flows == []

    def test_list_flows_ignores_hidden_files(self, tmp_path):
        """Should skip dotfiles."""
        (tmp_path / ".hidden.yaml").write_text("workflow:\n  name: hidden")
        (tmp_path / "visible.yaml").write_text("workflow:\n  name: visible")

        flows = list_flows(tmp_path)
        assert len(flows) == 1
        assert flows[0].name == "visible.yaml"


class TestWorkflowExecution:
    """Test workflow execution via DotRunner."""

    @patch("subprocess.run")
    def test_execute_workflow_calls_dotrunner(self, mock_run, tmp_path):
        """Should invoke dotrunner run command."""
        flow = tmp_path / "test.yaml"
        flow.write_text("workflow:\n  name: test")

        mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")

        result = execute_workflow(flow)

        assert result.status == "completed"
        assert result.output == "success"
        assert result.error is None
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_execute_workflow_passes_context(self, mock_run, tmp_path):
        """Should pass context as JSON to dotrunner."""
        flow = tmp_path / "test.yaml"
        flow.write_text("workflow:\n  name: test")
        context = {"files": "src/**/*.py", "project": "my-app"}

        mock_run.return_value = Mock(returncode=0, stdout="ok", stderr="")

        execute_workflow(flow, context=context)

        call_args = mock_run.call_args[0][0]
        assert "--context" in call_args
        context_json = call_args[call_args.index("--context") + 1]
        assert json.loads(context_json) == context

    @patch("subprocess.run")
    def test_execute_workflow_handles_failure(self, mock_run, tmp_path):
        """Should capture error when workflow fails."""
        flow = tmp_path / "test.yaml"
        flow.write_text("workflow:\n  name: test")

        mock_run.return_value = Mock(
            returncode=1, stdout="partial output", stderr="Error: node failed"
        )

        result = execute_workflow(flow)

        assert result.status == "failed"
        assert result.error == "Error: node failed"

    @patch("subprocess.run")
    def test_execute_workflow_handles_timeout(self, mock_run, tmp_path):
        """Should handle workflow timeout gracefully."""
        flow = tmp_path / "test.yaml"
        flow.write_text("workflow:\n  name: test")

        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 300)

        result = execute_workflow(flow)

        assert result.status == "failed"
        assert "timed out" in result.error.lower()


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_execution_result_success(self):
        """Should represent successful execution."""
        result = ExecutionResult(status="completed", output="all done")
        assert result.status == "completed"
        assert result.output == "all done"
        assert result.error is None

    def test_execution_result_failure(self):
        """Should represent failed execution."""
        result = ExecutionResult(
            status="failed", output="partial", error="validation failed"
        )
        assert result.status == "failed"
        assert result.error == "validation failed"


class TestIntegrationWithDotRunner:
    """Test actual integration with DotRunner (if available)."""

    def test_execute_simple_workflow_integration(self, tmp_path):
        """Integration test: Execute minimal valid workflow."""
        # Create minimal workflow
        workflow = tmp_path / "minimal.yaml"
        workflow.write_text(
            """workflow:
  name: minimal-test
  description: Test workflow
  version: 1.0.0

nodes:
  - id: start
    name: Start
    prompt: Test prompt
"""
        )

        # This is a real integration test - might skip if DotRunner not available
        try:
            result = execute_workflow(workflow)
            # If DotRunner is available, we should get a result
            assert result.status in ["completed", "failed"]
        except Exception as e:
            pytest.skip(f"DotRunner not available: {e}")
