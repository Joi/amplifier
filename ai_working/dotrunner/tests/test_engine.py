"""
Tests for workflow orchestration engine.

Tests the WorkflowEngine class that orchestrates complete workflow execution.
"""

from unittest.mock import MagicMock

import pytest

from ai_working.dotrunner.engine import WorkflowEngine
from ai_working.dotrunner.state import NodeResult
from ai_working.dotrunner.state import WorkflowState
from ai_working.dotrunner.workflow import Node
from ai_working.dotrunner.workflow import Workflow


@pytest.fixture
def simple_workflow():
    """Create a simple 3-node linear workflow"""
    return Workflow(
        name="test-workflow",
        description="Test workflow for testing",
        context={"initial": "value"},
        nodes=[
            Node(id="node1", name="First Node", prompt="Process {initial}", outputs=["output1"], next="node2"),
            Node(id="node2", name="Second Node", prompt="Use {output1}", outputs=["output2"], next="node3"),
            Node(
                id="node3",
                name="Third Node",
                prompt="Combine {output1} and {output2}",
                outputs=["final"],
                type="terminal",
            ),
        ],
    )


@pytest.fixture
def mock_executor():
    """Mock NodeExecutor for controlled node execution"""

    async def mock_execute(node: Node, context: dict) -> NodeResult:
        """Return successful results for any node"""
        return NodeResult(
            node_id=node.id,
            status="success",
            outputs={output: f"result_{output}" for output in node.outputs},
            raw_response=f"Response for {node.id}",
            execution_time=0.1,
        )

    executor = MagicMock()
    executor.execute = mock_execute
    return executor


class TestWorkflowEngine:
    """Test WorkflowEngine class"""

    @pytest.mark.asyncio
    async def test_run_simple_workflow(self, simple_workflow, mock_executor):
        """Test running a simple 3-node workflow"""
        engine = WorkflowEngine()
        engine.executor = mock_executor

        result = await engine.run(simple_workflow)

        assert result.workflow_id == "test-workflow"
        assert result.status == "completed"
        assert len(result.node_results) == 3
        assert all(nr.status == "success" for nr in result.node_results)
        assert result.total_time > 0

    @pytest.mark.asyncio
    async def test_run_workflow_context_accumulation(self, simple_workflow, mock_executor):
        """Test that context accumulates through nodes"""
        engine = WorkflowEngine()
        engine.executor = mock_executor

        result = await engine.run(simple_workflow)

        # Check context accumulation
        assert "initial" in result.final_context  # From workflow
        assert "output1" in result.final_context  # From node1
        assert "output2" in result.final_context  # From node2
        assert "final" in result.final_context  # From node3

    @pytest.mark.asyncio
    async def test_run_workflow_execution_order(self, simple_workflow, mock_executor):
        """Test that nodes execute in correct order"""
        engine = WorkflowEngine()
        engine.executor = mock_executor

        result = await engine.run(simple_workflow)

        # Check execution order
        assert result.node_results[0].node_id == "node1"
        assert result.node_results[1].node_id == "node2"
        assert result.node_results[2].node_id == "node3"

    @pytest.mark.asyncio
    async def test_run_workflow_stops_on_node_failure(self, simple_workflow):
        """Test that workflow stops when a node fails"""

        # Mock executor that fails on node2
        async def failing_executor(node: Node, context: dict) -> NodeResult:
            if node.id == "node2":
                return NodeResult(
                    node_id=node.id,
                    status="failed",
                    outputs={},
                    raw_response="",
                    error="Simulated failure",
                    execution_time=0.1,
                )
            return NodeResult(
                node_id=node.id,
                status="success",
                outputs={output: f"result_{output}" for output in node.outputs},
                raw_response=f"Response for {node.id}",
                execution_time=0.1,
            )

        executor = MagicMock()
        executor.execute = failing_executor

        engine = WorkflowEngine()
        engine.executor = executor

        result = await engine.run(simple_workflow)

        # Should stop after node2 fails
        assert result.status == "failed"
        assert len(result.node_results) == 2  # Only node1 and node2
        assert result.node_results[1].status == "failed"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_run_empty_workflow(self):
        """Test handling of workflow with no nodes"""
        workflow = Workflow(name="empty", description="Empty workflow", context={}, nodes=[])

        engine = WorkflowEngine()
        result = await engine.run(workflow)

        assert result.status == "completed"
        assert len(result.node_results) == 0

    @pytest.mark.asyncio
    async def test_run_workflow_with_exception(self, simple_workflow):
        """Test handling of unexpected exception during execution"""

        # Mock executor that raises exception
        async def exception_executor(node: Node, context: dict) -> NodeResult:
            if node.id == "node2":
                raise RuntimeError("Unexpected error")
            return NodeResult(
                node_id=node.id,
                status="success",
                outputs={output: f"result_{output}" for output in node.outputs},
                raw_response=f"Response for {node.id}",
                execution_time=0.1,
            )

        executor = MagicMock()
        executor.execute = exception_executor

        engine = WorkflowEngine()
        engine.executor = executor

        result = await engine.run(simple_workflow)

        # Should catch exception and return failed result
        assert result.status == "failed"
        assert "Unexpected error" in result.error or "error" in result.error.lower()


class TestGetNextNode:
    """Test _get_next_node method"""

    def test_get_next_node_first(self, simple_workflow):
        """Test getting first node when current_node is None"""
        engine = WorkflowEngine()
        state = WorkflowState(workflow_id="test", current_node=None, context={}, results=[], status="running")

        next_node = engine._get_next_node(simple_workflow, state)

        assert next_node is not None
        assert next_node.id == "node1"

    def test_get_next_node_follows_chain(self, simple_workflow):
        """Test following next chain through nodes"""
        engine = WorkflowEngine()

        # Test node1 -> node2
        state = WorkflowState(workflow_id="test", current_node="node1", context={}, results=[], status="running")
        next_node = engine._get_next_node(simple_workflow, state)
        assert next_node.id == "node2"

        # Test node2 -> node3
        state.current_node = "node2"
        next_node = engine._get_next_node(simple_workflow, state)
        assert next_node.id == "node3"

    def test_get_next_node_terminal(self, simple_workflow):
        """Test that terminal node returns None"""
        engine = WorkflowEngine()
        state = WorkflowState(
            workflow_id="test",
            current_node="node3",  # Terminal node
            context={},
            results=[],
            status="running",
        )

        next_node = engine._get_next_node(simple_workflow, state)

        assert next_node is None

    def test_get_next_node_nonexistent_node(self, simple_workflow):
        """Test handling of nonexistent node reference"""
        engine = WorkflowEngine()
        state = WorkflowState(workflow_id="test", current_node="nonexistent", context={}, results=[], status="running")

        next_node = engine._get_next_node(simple_workflow, state)

        assert next_node is None


class TestExecuteNode:
    """Test _execute_node method"""

    @pytest.mark.asyncio
    async def test_execute_node_delegates_to_executor(self, simple_workflow, mock_executor):
        """Test that _execute_node delegates to NodeExecutor"""
        engine = WorkflowEngine()
        engine.executor = mock_executor

        node = simple_workflow.nodes[0]
        state = WorkflowState(
            workflow_id="test", current_node=None, context={"initial": "value"}, results=[], status="running"
        )

        result = await engine._execute_node(node, state)

        assert result.node_id == node.id
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_execute_node_passes_context(self, simple_workflow, mock_executor):
        """Test that _execute_node passes current context"""

        # Track what context was passed
        passed_context = None

        async def capturing_executor(node: Node, context: dict) -> NodeResult:
            nonlocal passed_context
            passed_context = context.copy()
            return NodeResult(node_id=node.id, status="success", outputs={}, raw_response="", execution_time=0.1)

        executor = MagicMock()
        executor.execute = capturing_executor

        engine = WorkflowEngine()
        engine.executor = executor

        node = simple_workflow.nodes[0]
        state = WorkflowState(
            workflow_id="test",
            current_node=None,
            context={"initial": "value", "other": "data"},
            results=[],
            status="running",
        )

        await engine._execute_node(node, state)

        assert passed_context == {"initial": "value", "other": "data"}


class TestWorkflowInitialization:
    """Test workflow initialization"""

    @pytest.mark.asyncio
    async def test_initial_state_creation(self, simple_workflow, mock_executor):
        """Test that initial state is created correctly"""
        engine = WorkflowEngine()
        engine.executor = mock_executor

        result = await engine.run(simple_workflow)

        # Initial context should be preserved in final context
        assert "initial" in result.final_context
        assert result.final_context["initial"] == "value"

    @pytest.mark.asyncio
    async def test_workflow_id_preserved(self, simple_workflow, mock_executor):
        """Test that workflow ID is preserved"""
        engine = WorkflowEngine()
        engine.executor = mock_executor

        result = await engine.run(simple_workflow)

        assert result.workflow_id == simple_workflow.name


class TestWorkflowLogging:
    """Test workflow execution logging"""

    @pytest.mark.asyncio
    async def test_logs_workflow_start(self, simple_workflow, mock_executor, caplog):
        """Test that workflow start is logged"""
        import logging

        caplog.set_level(logging.INFO)

        engine = WorkflowEngine()
        engine.executor = mock_executor

        await engine.run(simple_workflow)

        assert "Starting workflow" in caplog.text
        assert "test-workflow" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_node_execution(self, simple_workflow, mock_executor, caplog):
        """Test that node execution is logged"""
        import logging

        caplog.set_level(logging.INFO)

        engine = WorkflowEngine()
        engine.executor = mock_executor

        await engine.run(simple_workflow)

        assert "Executing node: node1" in caplog.text
        assert "Executing node: node2" in caplog.text
        assert "Executing node: node3" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_workflow_completion(self, simple_workflow, mock_executor, caplog):
        """Test that workflow completion is logged"""
        import logging

        caplog.set_level(logging.INFO)

        engine = WorkflowEngine()
        engine.executor = mock_executor

        await engine.run(simple_workflow)

        assert "completed" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_logs_node_failure(self, simple_workflow, caplog):
        """Test that node failures are logged"""
        import logging

        caplog.set_level(logging.ERROR)

        # Mock executor that fails
        async def failing_executor(node: Node, context: dict) -> NodeResult:
            return NodeResult(
                node_id=node.id, status="failed", outputs={}, raw_response="", error="Test failure", execution_time=0.1
            )

        executor = MagicMock()
        executor.execute = failing_executor

        engine = WorkflowEngine()
        engine.executor = executor

        await engine.run(simple_workflow)

        assert "failed" in caplog.text.lower()
        assert "Test failure" in caplog.text
