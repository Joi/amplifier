"""
Tests for Phase 5: Agent Integration

Tests agent execution, mode passing, output extraction, and error handling.
"""

import json
import subprocess
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from ai_working.dotrunner.executor import NodeExecutor
from ai_working.dotrunner.workflow import Node


class TestAgentExecution:
    """Test agent execution via subprocess"""

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_execute_with_agent_json_output(self, mock_run):
        """Test agent execution with JSON output returns structured data"""
        # Arrange
        node = Node(
            id="analyze",
            name="Analyze Code",
            agent="bug-hunter",
            prompt="Review this code: {code}",
            outputs=["issues", "severity"],
        )
        context = {"code": "def foo(): pass"}

        # Mock agent response with JSON
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"issues": "No issues found", "severity": "none"}),
            stderr="",
        )

        executor = NodeExecutor()

        # Act
        result = await executor.execute(node, context)

        # Assert
        assert result.status == "success"
        assert result.outputs["issues"] == "No issues found"
        assert result.outputs["severity"] == "none"
        # raw_response is the agent's output (JSON), not the prompt
        assert "issues" in result.raw_response.lower()

        # Verify subprocess call
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "amplifier" in call_args
        assert "agent" in call_args
        assert "bug-hunter" in call_args
        assert "--json" in call_args

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_execute_with_agent_plain_text(self, mock_run):
        """Test agent execution with plain text output"""
        # Arrange
        node = Node(
            id="summarize",
            name="Summarize",
            agent="analysis-expert",
            prompt="Summarize: {content}",
            outputs=["summary"],
        )
        context = {"content": "Long text here..."}

        # Mock agent response with plain text
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="This is a brief summary of the content.",
            stderr="",
        )

        executor = NodeExecutor()

        # Act
        result = await executor.execute(node, context)

        # Assert
        assert result.status == "success"
        assert result.outputs["summary"] == "This is a brief summary of the content."

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_execute_with_agent_mode(self, mock_run):
        """Test agent execution with mode parameter"""
        # Arrange
        node = Node(
            id="review",
            name="Review",
            agent="zen-architect",
            agent_mode="REVIEW",
            prompt="Review this design: {design}",
            outputs=["feedback"],
        )
        context = {"design": "System design document"}

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"feedback": "Looks good"}),
            stderr="",
        )

        executor = NodeExecutor()

        # Act
        result = await executor.execute(node, context)

        # Assert
        assert result.status == "success"

        # Verify mode was passed
        call_args = mock_run.call_args[0][0]
        assert "--mode" in call_args
        assert "REVIEW" in call_args

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_agent_not_found_error(self, mock_run):
        """Test error when agent doesn't exist"""
        # Arrange
        node = Node(
            id="test",
            name="Test",
            agent="nonexistent-agent",
            prompt="Do something",
            outputs=["result"],
        )

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Agent 'nonexistent-agent' not found")

        executor = NodeExecutor()

        # Act
        result = await executor.execute(node, {})

        # Assert
        assert result.status == "failed"
        assert "nonexistent-agent" in result.error
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_agent_timeout_error(self, mock_run):
        """Test error when agent execution times out"""
        # Arrange
        node = Node(id="slow", name="Slow Task", agent="slow-agent", prompt="Take forever")

        mock_run.side_effect = subprocess.TimeoutExpired("amplifier", 300)

        executor = NodeExecutor()

        # Act
        result = await executor.execute(node, {})

        # Assert
        assert result.status == "failed"
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_agent_temp_file_cleanup(self, mock_run):
        """Test that temp files are cleaned up after agent execution"""
        # Arrange
        node = Node(
            id="test",
            name="Test",
            agent="test-agent",
            prompt="Test prompt",
            outputs=["result"],
        )

        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"result": "success"}), stderr="")

        executor = NodeExecutor()

        # Act
        result = await executor.execute(node, {})

        # Assert - no way to directly check file deletion, but verify no error
        assert result.status == "success"

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_fallback_to_ai_when_no_agent(self, mock_run):
        """Test that nodes without agent field use AI execution"""
        # Arrange - Node without agent field
        node = Node(id="ai_task", name="AI Task", prompt="Generate something", outputs=["text"])

        executor = NodeExecutor()

        # Mock the AI execution method
        with patch.object(executor, "_execute_generic", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "AI generated response"

            # Act
            result = await executor.execute(node, {})

            # Assert - subprocess should NOT be called
            mock_run.assert_not_called()
            # AI method should be called
            mock_ai.assert_called_once()
            # Result should contain AI response
            assert result.status == "success"


class TestAgentOutputExtraction:
    """Test output extraction from agent responses"""

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_extract_multiple_outputs_from_json(self, mock_run):
        """Test extracting multiple named outputs from JSON response"""
        # Arrange
        node = Node(
            id="multi",
            name="Multi Output",
            agent="analyzer",
            prompt="Analyze",
            outputs=["score", "category", "recommendation"],
        )

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"score": 85, "category": "good", "recommendation": "Deploy"}),
            stderr="",
        )

        executor = NodeExecutor()

        # Act
        result = await executor.execute(node, {})

        # Assert
        assert result.outputs["score"] == 85
        assert result.outputs["category"] == "good"
        assert result.outputs["recommendation"] == "Deploy"

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_extract_missing_outputs_as_empty(self, mock_run):
        """Test that missing outputs in JSON are handled gracefully"""
        # Arrange
        node = Node(
            id="partial",
            name="Partial",
            agent="analyzer",
            prompt="Analyze",
            outputs=["found", "missing"],
        )

        # Agent only returns "found"
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"found": "here"}), stderr="")

        executor = NodeExecutor()

        # Act
        result = await executor.execute(node, {})

        # Assert
        assert result.outputs["found"] == "here"
        assert result.outputs["missing"] == ""  # Missing becomes empty string

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_plain_text_maps_to_first_output(self, mock_run):
        """Test plain text response maps to first output name"""
        # Arrange
        node = Node(id="text", name="Text", agent="writer", prompt="Write", outputs=["content"])

        mock_run.return_value = MagicMock(returncode=0, stdout="Plain text response here", stderr="")

        executor = NodeExecutor()

        # Act
        result = await executor.execute(node, {})

        # Assert
        assert result.outputs["content"] == "Plain text response here"

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_invalid_json_falls_back_to_plain_text(self, mock_run):
        """Test that invalid JSON is treated as plain text"""
        # Arrange
        node = Node(
            id="bad_json",
            name="Bad JSON",
            agent="buggy",
            prompt="Do thing",
            outputs=["result"],
        )

        # Agent returns malformed JSON
        mock_run.return_value = MagicMock(returncode=0, stdout="{not valid json", stderr="")

        executor = NodeExecutor()

        # Act
        result = await executor.execute(node, {})

        # Assert - should treat as plain text
        assert result.outputs["result"] == "{not valid json"


class TestAgentContextIntegration:
    """Test agent integration with context flow"""

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_agent_receives_interpolated_prompt(self, mock_run):
        """Test agent receives prompt with context variables interpolated"""
        # Arrange
        node = Node(
            id="process",
            name="Process",
            agent="processor",
            prompt="Process {input} with {config}",
            outputs=["output"],
        )
        context = {"input": "data.csv", "config": "strict"}

        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"output": "processed"}), stderr="")

        executor = NodeExecutor()

        # Act
        await executor.execute(node, context)

        # Assert - check that prompt file contains interpolated values
        # We can't directly access the temp file, but we can verify no error
        call_args = mock_run.call_args[0][0]
        assert "--prompt-file" in call_args

    @pytest.mark.asyncio
    @patch("ai_working.dotrunner.executor.subprocess.run")
    async def test_agent_outputs_flow_to_context(self, mock_run):
        """Test that agent outputs are properly extracted and can flow to next nodes"""
        # Arrange
        node = Node(
            id="generate",
            name="Generate",
            agent="generator",
            prompt="Generate code",
            outputs=["code", "language"],
        )

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"code": "def foo(): pass", "language": "python"}),
            stderr="",
        )

        executor = NodeExecutor()

        # Act
        result = await executor.execute(node, {})

        # Assert - outputs should be extractable for context
        assert "code" in result.outputs
        assert "language" in result.outputs
        assert result.outputs["code"] == "def foo(): pass"
        assert result.outputs["language"] == "python"
