"""
Tests for CLI entry point.

Following TEST-FIRST discipline: These tests define the contract (studs)
for the CLI module before implementation.

Phase 1: Simple CLI that asks basic questions and generates a workflow.
"""

from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from amplifier.flow_builder.cli import cli


class TestCliCommand:
    """Tests for flow-builder CLI command."""

    def test_cli_command_exists(self):
        """CLI command exists and is callable."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "flow-builder" in result.output.lower() or "usage" in result.output.lower()

    def test_cli_creates_workflow_file(self, tmp_path):
        """CLI creates workflow YAML file."""
        runner = CliRunner()

        # Mock input responses
        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = [
                "test-workflow",  # name
                "Test workflow description",  # description
                "First Step",  # node name
                "Do something useful",  # node prompt
                "",  # agent (optional - empty)
                "",  # agent_mode (optional - empty)
                "",  # outputs (optional - empty)
            ]

            result = runner.invoke(cli, ["--output", str(tmp_path / "workflow.yaml")])

        assert result.exit_code == 0

        # Verify file created
        output_file = tmp_path / "workflow.yaml"
        assert output_file.exists()

        # Verify valid YAML
        with open(output_file) as f:
            data = yaml.safe_load(f)

        assert data["workflow"]["name"] == "test-workflow"
        assert data["workflow"]["description"] == "Test workflow description"
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["name"] == "First Step"

    def test_cli_validates_workflow(self, tmp_path):
        """CLI validates workflow before saving."""
        runner = CliRunner()

        # Mock input that creates invalid workflow (empty nodes - but we'll catch it)
        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = [
                "",  # name (empty - invalid)
                "Description",
                "Node",
                "Prompt",
                "",
                "",
                "",
            ]

            result = runner.invoke(cli, ["--output", str(tmp_path / "workflow.yaml")])

        # Should fail validation (name required)
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "invalid" in result.output.lower()

    def test_cli_uses_default_output_path(self):
        """CLI uses default output path if not specified."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            with patch("click.prompt") as mock_prompt:
                mock_prompt.side_effect = [
                    "test",
                    "Test",
                    "Step",
                    "Prompt",
                    "",
                    "",
                    "",
                ]

                result = runner.invoke(cli)

            assert result.exit_code == 0

            # Should create file in ai_flows/ directory
            default_file = Path("ai_flows/test.yaml")
            assert default_file.exists()

    def test_cli_accepts_agent_parameter(self, tmp_path):
        """CLI accepts and includes agent parameter."""
        runner = CliRunner()

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = [
                "test",
                "Test",
                "Step",
                "Prompt",
                "zen-architect",  # agent
                "",
                "",
            ]

            result = runner.invoke(cli, ["--output", str(tmp_path / "workflow.yaml")])

        assert result.exit_code == 0

        # Verify agent included
        with open(tmp_path / "workflow.yaml") as f:
            data = yaml.safe_load(f)

        assert data["nodes"][0].get("agent") == "zen-architect"

    def test_cli_accepts_agent_mode_parameter(self, tmp_path):
        """CLI accepts and includes agent_mode parameter."""
        runner = CliRunner()

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = [
                "test",
                "Test",
                "Step",
                "Prompt",
                "",
                "ANALYZE",  # agent_mode
                "",
            ]

            result = runner.invoke(cli, ["--output", str(tmp_path / "workflow.yaml")])

        assert result.exit_code == 0

        # Verify agent_mode included
        with open(tmp_path / "workflow.yaml") as f:
            data = yaml.safe_load(f)

        assert data["nodes"][0].get("agent_mode") == "ANALYZE"

    def test_cli_accepts_outputs_parameter(self, tmp_path):
        """CLI accepts and includes outputs parameter."""
        runner = CliRunner()

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = [
                "test",
                "Test",
                "Step",
                "Prompt",
                "",
                "",
                "result, status",  # outputs (comma-separated)
            ]

            result = runner.invoke(cli, ["--output", str(tmp_path / "workflow.yaml")])

        assert result.exit_code == 0

        # Verify outputs included
        with open(tmp_path / "workflow.yaml") as f:
            data = yaml.safe_load(f)

        assert data["nodes"][0].get("outputs") == ["result", "status"]

    def test_cli_shows_success_message(self, tmp_path):
        """CLI shows success message after creating workflow."""
        runner = CliRunner()

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = [
                "test",
                "Test",
                "Step",
                "Prompt",
                "",
                "",
                "",
            ]

            result = runner.invoke(cli, ["--output", str(tmp_path / "workflow.yaml")])

        assert result.exit_code == 0
        assert "success" in result.output.lower() or "created" in result.output.lower()

    def test_cli_shows_error_message_on_failure(self, tmp_path):
        """CLI shows clear error message on failure."""
        runner = CliRunner()

        # Mock validation to fail
        with patch("amplifier.flow_builder.cli.validate_workflow") as mock_validate:
            mock_validate.return_value = ["Test error message"]

            with patch("click.prompt") as mock_prompt:
                mock_prompt.side_effect = [
                    "test",
                    "Test",
                    "Step",
                    "Prompt",
                    "",
                    "",
                    "",
                ]

                result = runner.invoke(cli, ["--output", str(tmp_path / "workflow.yaml")])

        assert result.exit_code != 0
        assert "error" in result.output.lower()
        assert "test error message" in result.output.lower()
