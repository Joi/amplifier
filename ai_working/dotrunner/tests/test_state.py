"""
Tests for state management dataclasses.

Tests the data structures used to track workflow execution state.
"""

from dataclasses import asdict

from ai_working.dotrunner.state import NodeResult
from ai_working.dotrunner.state import WorkflowResult
from ai_working.dotrunner.state import WorkflowState


class TestNodeResult:
    """Test NodeResult dataclass"""

    def test_node_result_success(self):
        """Test creating a successful node result"""
        result = NodeResult(
            node_id="test-node",
            status="success",
            outputs={"analysis": "Complete"},
            raw_response="The analysis shows...",
            execution_time=1.5,
        )

        assert result.node_id == "test-node"
        assert result.status == "success"
        assert result.outputs == {"analysis": "Complete"}
        assert result.raw_response == "The analysis shows..."
        assert result.error is None
        assert result.execution_time == 1.5

    def test_node_result_failed(self):
        """Test creating a failed node result"""
        result = NodeResult(
            node_id="broken-node",
            status="failed",
            outputs={},
            raw_response="",
            error="Missing context variable: file_path",
            execution_time=0.1,
        )

        assert result.node_id == "broken-node"
        assert result.status == "failed"
        assert result.outputs == {}
        assert result.error == "Missing context variable: file_path"

    def test_node_result_with_multiple_outputs(self):
        """Test node result with multiple named outputs"""
        result = NodeResult(
            node_id="analysis",
            status="success",
            outputs={"summary": "Well-structured code", "recommendations": "Add more tests", "score": 8.5},
            raw_response="Full analysis text...",
            execution_time=2.3,
        )

        assert len(result.outputs) == 3
        assert "summary" in result.outputs
        assert "recommendations" in result.outputs
        assert "score" in result.outputs

    def test_node_result_serialization(self):
        """Test that NodeResult can be converted to dict"""
        result = NodeResult(
            node_id="test", status="success", outputs={"key": "value"}, raw_response="response", execution_time=1.0
        )

        data = asdict(result)

        assert isinstance(data, dict)
        assert data["node_id"] == "test"
        assert data["status"] == "success"
        assert data["outputs"] == {"key": "value"}


class TestWorkflowState:
    """Test WorkflowState dataclass"""

    def test_workflow_state_initialization(self):
        """Test creating initial workflow state"""
        state = WorkflowState(
            workflow_id="test-workflow", current_node=None, context={"topic": "AI"}, results=[], status="running"
        )

        assert state.workflow_id == "test-workflow"
        assert state.current_node is None
        assert state.context == {"topic": "AI"}
        assert state.results == []
        assert state.status == "running"

    def test_workflow_state_with_results(self):
        """Test workflow state with accumulated results"""
        result1 = NodeResult(node_id="node1", status="success", outputs={"a": 1}, raw_response="", execution_time=1.0)
        result2 = NodeResult(node_id="node2", status="success", outputs={"b": 2}, raw_response="", execution_time=1.5)

        state = WorkflowState(
            workflow_id="test",
            current_node="node2",
            context={"a": 1, "b": 2},
            results=[result1, result2],
            status="running",
        )

        assert len(state.results) == 2
        assert state.current_node == "node2"
        assert "a" in state.context
        assert "b" in state.context

    def test_workflow_state_context_accumulation(self):
        """Test that context can be accumulated"""
        state = WorkflowState(
            workflow_id="test", current_node=None, context={"initial": "value"}, results=[], status="running"
        )

        # Simulate context accumulation
        state.context.update({"node1_output": "result1"})
        state.context.update({"node2_output": "result2"})

        assert len(state.context) == 3
        assert "initial" in state.context
        assert "node1_output" in state.context
        assert "node2_output" in state.context


class TestWorkflowResult:
    """Test WorkflowResult dataclass"""

    def test_workflow_result_completed(self):
        """Test creating a completed workflow result"""
        results = [
            NodeResult("n1", "success", {"a": 1}, "", execution_time=1.0),
            NodeResult("n2", "success", {"b": 2}, "", execution_time=1.5),
        ]

        result = WorkflowResult(
            workflow_id="test-workflow",
            status="completed",
            total_time=5.7,
            node_results=results,
            final_context={"a": 1, "b": 2},
            error=None,
        )

        assert result.workflow_id == "test-workflow"
        assert result.status == "completed"
        assert result.total_time == 5.7
        assert len(result.node_results) == 2
        assert result.error is None
        assert "a" in result.final_context
        assert "b" in result.final_context

    def test_workflow_result_failed(self):
        """Test creating a failed workflow result"""
        results = [
            NodeResult("n1", "success", {"a": 1}, "", execution_time=1.0),
            NodeResult("n2", "failed", {}, "", error="API timeout", execution_time=0.5),
        ]

        result = WorkflowResult(
            workflow_id="failed-workflow",
            status="failed",
            total_time=2.0,
            node_results=results,
            final_context={"a": 1},
            error="Node n2 failed: API timeout",
        )

        assert result.status == "failed"
        assert result.error is not None
        assert "API timeout" in result.error

    def test_workflow_result_serialization(self):
        """Test that WorkflowResult can be converted to dict"""
        result = WorkflowResult(
            workflow_id="test",
            status="completed",
            total_time=3.0,
            node_results=[],
            final_context={"key": "value"},
            error=None,
        )

        data = asdict(result)

        assert isinstance(data, dict)
        assert data["workflow_id"] == "test"
        assert data["status"] == "completed"
        assert data["total_time"] == 3.0
        assert data["final_context"] == {"key": "value"}
