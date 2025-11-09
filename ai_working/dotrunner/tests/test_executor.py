"""
Tests for node executor with AI integration.

Tests the NodeExecutor class that executes individual workflow nodes
using AI (mocked for testing).
"""

from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from ai_working.dotrunner.context import ContextError
from ai_working.dotrunner.executor import NodeExecutor
from ai_working.dotrunner.workflow import Node


@pytest.fixture
def mock_claude_session():
    """Mock ClaudeSession for controlled AI responses"""

    async def mock_query(prompt: str) -> str:
        """Return controlled responses based on prompt content"""
        if "analyze" in prompt.lower():
            return "analysis: The code is well-structured with clear modules"
        if "find bugs" in prompt.lower() or "bugs" in prompt.lower():
            return "bugs_found: No critical bugs detected"
        if "summarize" in prompt.lower():
            return "summary: Overall the code is production-ready"
        if "json" in prompt.lower():
            return '{"result": "success", "score": 8.5}'
        return "output: Task completed successfully"

    mock = AsyncMock()
    mock.query = mock_query
    return mock


@pytest.fixture
def sample_node():
    """Create a sample node for testing"""
    return Node(
        id="test-node",
        name="Test Node",
        prompt="Analyze the file at {file_path}",
        outputs=["analysis"],
        next="next-node",
    )


class TestNodeExecutor:
    """Test NodeExecutor class"""

    @pytest.mark.asyncio
    async def test_execute_node_success(self, mock_claude_session, sample_node):
        """Test successful node execution"""
        executor = NodeExecutor()
        context = {"file_path": "/src/main.py"}

        with patch("ai_working.dotrunner.executor.ClaudeSession") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_claude_session

            result = await executor.execute(sample_node, context)

        assert result.node_id == "test-node"
        assert result.status == "success"
        assert "analysis" in result.outputs
        assert result.outputs["analysis"] == "The code is well-structured with clear modules"
        assert result.error is None
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_execute_node_with_multiple_outputs(self, mock_claude_session):
        """Test node with multiple named outputs"""
        executor = NodeExecutor()
        node = Node(
            id="multi-output",
            name="Multi Output Node",
            prompt="Analyze this code",
            outputs=["analysis", "score", "recommendations"],
        )
        context = {}

        # Mock response with multiple outputs
        async def mock_multi_output(prompt):
            return """
            analysis: Code is well structured
            score: 8.5
            recommendations: Add more tests
            """

        mock_claude_session.query = mock_multi_output

        with patch("ai_working.dotrunner.executor.ClaudeSession") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_claude_session

            result = await executor.execute(node, context)

        assert result.status == "success"
        assert len(result.outputs) == 3
        assert "analysis" in result.outputs
        assert "score" in result.outputs
        assert "recommendations" in result.outputs

    @pytest.mark.asyncio
    async def test_execute_node_missing_context_variable(self, mock_claude_session):
        """Test that missing context variables cause failure"""
        executor = NodeExecutor()
        node = Node(id="broken-node", name="Broken Node", prompt="Analyze {missing_variable}", outputs=["result"])
        context = {}  # Missing 'missing_variable'

        result = await executor.execute(node, context)

        assert result.status == "failed"
        assert result.error is not None
        assert "missing_variable" in result.error.lower()
        assert result.outputs == {}

    @pytest.mark.asyncio
    async def test_execute_node_interpolates_context(self, mock_claude_session):
        """Test that context variables are interpolated into prompt"""
        executor = NodeExecutor()
        node = Node(id="test", name="Test", prompt="Process {file} with {config}", outputs=["output"])
        context = {"file": "data.csv", "config": "strict"}

        # Track what prompt was sent to AI
        sent_prompt = None

        async def capture_prompt(prompt):
            nonlocal sent_prompt
            sent_prompt = prompt
            return "output: Success"

        mock_claude_session.query = capture_prompt

        with patch("ai_working.dotrunner.executor.ClaudeSession") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_claude_session

            await executor.execute(node, context)

        assert "data.csv" in sent_prompt
        assert "strict" in sent_prompt
        assert "{file}" not in sent_prompt
        assert "{config}" not in sent_prompt

    @pytest.mark.asyncio
    async def test_execute_node_extracts_json_outputs(self, mock_claude_session):
        """Test extraction of JSON-formatted outputs"""
        executor = NodeExecutor()
        node = Node(id="json-node", name="JSON Node", prompt="Return JSON analysis", outputs=["result", "score"])
        context = {}

        # Mock JSON response
        async def mock_json_response(prompt):
            return '{"result": "success", "score": 8.5, "extra": "ignored"}'

        mock_claude_session.query = mock_json_response

        with patch("ai_working.dotrunner.executor.ClaudeSession") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_claude_session

            result = await executor.execute(node, context)

        assert result.status == "success"
        assert result.outputs["result"] == "success"
        assert result.outputs["score"] == 8.5
        assert "extra" not in result.outputs  # Only requested outputs

    @pytest.mark.asyncio
    async def test_execute_node_handles_ai_timeout(self, mock_claude_session):
        """Test handling of AI execution timeout"""
        executor = NodeExecutor()
        node = Node(id="timeout-node", name="Timeout Node", prompt="Long running task", outputs=["result"])
        context = {}

        # Mock timeout error
        async def mock_timeout(prompt):
            raise TimeoutError("ClaudeSession timeout after 60s")

        mock_claude_session.query = mock_timeout

        with patch("ai_working.dotrunner.executor.ClaudeSession") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_claude_session

            result = await executor.execute(node, context)

        assert result.status == "failed"
        assert result.error is not None
        assert result.outputs == {}

    @pytest.mark.asyncio
    async def test_execute_node_handles_ai_error(self, mock_claude_session):
        """Test handling of general AI execution errors"""
        executor = NodeExecutor()
        node = Node(id="error-node", name="Error Node", prompt="Task that fails", outputs=["result"])
        context = {}

        # Mock API error
        async def mock_error(prompt):
            raise RuntimeError("API rate limit exceeded")

        mock_claude_session.query = mock_error

        with patch("ai_working.dotrunner.executor.ClaudeSession") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_claude_session

            result = await executor.execute(node, context)

        assert result.status == "failed"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_node_partial_output_extraction(self, mock_claude_session):
        """Test when only some expected outputs are found"""
        executor = NodeExecutor()
        node = Node(
            id="partial-node",
            name="Partial Node",
            prompt="Generate analysis",
            outputs=["analysis", "recommendations", "score"],
        )
        context = {}

        # Mock response with only partial outputs
        async def mock_partial(prompt):
            return "analysis: Good code\nscore: 7"

        mock_claude_session.query = mock_partial

        with patch("ai_working.dotrunner.executor.ClaudeSession") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_claude_session

            result = await executor.execute(node, context)

        # Should succeed with partial outputs
        assert result.status == "success"
        assert "analysis" in result.outputs
        assert "score" in result.outputs
        # Missing outputs are filled with empty strings (Phase 5 behavior)
        assert "recommendations" in result.outputs
        assert result.outputs["recommendations"] == ""

    @pytest.mark.asyncio
    async def test_execute_node_no_outputs_requested(self, mock_claude_session):
        """Test node that doesn't request any outputs"""
        executor = NodeExecutor()
        node = Node(
            id="no-output-node",
            name="No Output Node",
            prompt="Just execute this task",
            outputs=[],  # No outputs requested
        )
        context = {}

        with patch("ai_working.dotrunner.executor.ClaudeSession") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_claude_session

            result = await executor.execute(node, context)

        assert result.status == "success"
        assert result.outputs == {}
        assert len(result.raw_response) > 0

    @pytest.mark.asyncio
    async def test_execute_node_timing(self, mock_claude_session):
        """Test that execution time is recorded"""
        import asyncio

        executor = NodeExecutor()

        node = Node(id="timed-node", name="Timed Node", prompt="Quick task", outputs=["result"])
        context = {}

        # Mock slow response
        async def mock_slow(prompt):
            await asyncio.sleep(0.1)  # 100ms delay
            return "result: Done"

        mock_claude_session.query = mock_slow

        with patch("ai_working.dotrunner.executor.ClaudeSession") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_claude_session

            result = await executor.execute(node, context)

        assert result.execution_time >= 0.1  # At least 100ms
        assert result.execution_time < 1.0  # But not too long


class TestOutputExtraction:
    """Test output extraction utilities"""

    def test_extract_outputs_pattern_based(self):
        """Test pattern-based output extraction"""
        executor = NodeExecutor()

        response = """
        Here's the analysis:
        analysis: Code is well structured
        score: 8.5
        recommendations: Add more tests
        """

        outputs = executor._extract_outputs(response, ["analysis", "score", "recommendations"])

        assert outputs["analysis"] == "Code is well structured"
        assert outputs["score"] == "8.5"
        assert outputs["recommendations"] == "Add more tests"

    def test_extract_outputs_json_format(self):
        """Test JSON-based output extraction"""
        executor = NodeExecutor()

        response = '{"analysis": "Good", "score": 9}'

        outputs = executor._extract_outputs(response, ["analysis", "score"])

        assert outputs["analysis"] == "Good"
        assert outputs["score"] == 9

    def test_extract_outputs_missing_outputs(self):
        """Test extraction when outputs not found"""
        executor = NodeExecutor()

        response = "Just some text without the expected format"

        outputs = executor._extract_outputs(response, ["missing1", "missing2"])

        # Should return empty dict or partial results
        assert isinstance(outputs, dict)
        # Missing outputs don't cause exceptions


class TestPromptInterpolation:
    """Test prompt interpolation in executor"""

    def test_interpolate_prompt_single_var(self):
        """Test interpolating single variable"""
        executor = NodeExecutor()

        prompt = executor._interpolate_prompt("Analyze {file}", {"file": "main.py"})

        assert prompt == "Analyze main.py"

    def test_interpolate_prompt_multiple_vars(self):
        """Test interpolating multiple variables"""
        executor = NodeExecutor()

        prompt = executor._interpolate_prompt(
            "Process {file} with {config} mode", {"file": "data.csv", "config": "strict"}
        )

        assert prompt == "Process data.csv with strict mode"

    def test_interpolate_prompt_missing_var_raises(self):
        """Test that missing variables raise ContextError"""
        executor = NodeExecutor()

        with pytest.raises(ContextError) as exc:
            executor._interpolate_prompt("Use {missing}", {})

        assert "missing" in exc.value.missing_vars
