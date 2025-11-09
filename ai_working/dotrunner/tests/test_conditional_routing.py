"""
Tests for Phase 6: Conditional Routing

Tests conditional next routing, default fallback, path tracking, and error handling.
"""

import pytest

from ai_working.dotrunner.engine import WorkflowEngine
from ai_working.dotrunner.state import NodeResult
from ai_working.dotrunner.workflow import Node
from ai_working.dotrunner.workflow import Workflow


class TestConditionalRouting:
    """Test conditional routing based on node outputs"""

    def test_exact_match_routing(self):
        """Test that exact condition match routes to correct node"""
        # Arrange
        node = Node(
            id="check_severity",
            name="Check Severity",
            prompt="Check severity",
            outputs=["severity"],
            next={"critical": "escalate", "high": "assign_senior", "default": "assign_junior"},
        )

        context = {"severity": "critical"}
        engine = WorkflowEngine()

        # Act
        next_node_id = engine._get_next_node_id(node, context)

        # Assert
        assert next_node_id == "escalate"

    def test_case_insensitive_match(self):
        """Test that condition matching is case-insensitive"""
        # Arrange
        node = Node(
            id="status_check",
            name="Status Check",
            prompt="Check status",
            outputs=["status"],
            next={"success": "continue", "failure": "retry", "default": "unknown"},
        )

        # Test various cases
        for status_value in ["SUCCESS", "Success", "success", "SuCcEsS"]:
            context = {"status": status_value}
            engine = WorkflowEngine()

            # Act
            next_node_id = engine._get_next_node_id(node, context)

            # Assert
            assert next_node_id == "continue", f"Failed for status={status_value}"

    def test_default_fallback_when_no_match(self):
        """Test that default is used when no condition matches"""
        # Arrange
        node = Node(
            id="categorize",
            name="Categorize",
            prompt="Categorize",
            outputs=["category"],
            next={"red": "urgent", "yellow": "normal", "default": "review"},
        )

        context = {"category": "blue"}  # No matching condition
        engine = WorkflowEngine()

        # Act
        next_node_id = engine._get_next_node_id(node, context)

        # Assert
        assert next_node_id == "review"

    def test_error_when_no_match_and_no_default(self):
        """Test error raised when no match and no default"""
        # Arrange
        node = Node(
            id="strict_check",
            name="Strict Check",
            prompt="Check",
            outputs=["result"],
            next={"pass": "continue", "fail": "stop"},  # No default!
        )

        context = {"result": "unknown"}
        engine = WorkflowEngine()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            engine._get_next_node_id(node, context)

        assert "no routing condition matched" in str(exc_info.value).lower()
        assert "no default" in str(exc_info.value).lower()
        assert "unknown" in str(exc_info.value)

    def test_linear_routing_still_works(self):
        """Test that linear routing (string next) still works"""
        # Arrange
        node = Node(id="simple", name="Simple", prompt="Do thing", next="next_node")

        context = {}
        engine = WorkflowEngine()

        # Act
        next_node_id = engine._get_next_node_id(node, context)

        # Assert
        assert next_node_id == "next_node"

    def test_none_next_returns_none(self):
        """Test that terminal nodes (next=None) return None"""
        # Arrange
        node = Node(id="terminal", name="Terminal", prompt="Final step", next=None, type="terminal")

        context = {}
        engine = WorkflowEngine()

        # Act
        next_node_id = engine._get_next_node_id(node, context)

        # Assert
        assert next_node_id is None

    def test_uses_first_output_for_routing(self):
        """Test that first output value is used for routing decision"""
        # Arrange
        node = Node(
            id="multi_output",
            name="Multi Output",
            prompt="Generate multiple outputs",
            outputs=["priority", "category", "status"],  # First is "priority"
            next={"high": "urgent_path", "low": "normal_path", "default": "default_path"},
        )

        context = {"priority": "high", "category": "bug", "status": "new"}
        engine = WorkflowEngine()

        # Act
        next_node_id = engine._get_next_node_id(node, context)

        # Assert - should route based on "priority" (first output)
        assert next_node_id == "urgent_path"

    def test_empty_output_uses_default(self):
        """Test that empty output value uses default route"""
        # Arrange
        node = Node(
            id="maybe_empty",
            name="Maybe Empty",
            prompt="Might be empty",
            outputs=["value"],
            next={"something": "process", "default": "skip"},
        )

        context = {"value": ""}  # Empty string
        engine = WorkflowEngine()

        # Act
        next_node_id = engine._get_next_node_id(node, context)

        # Assert
        assert next_node_id == "skip"

    def test_missing_context_variable_uses_default(self):
        """Test that missing output variable in context uses default"""
        # Arrange
        node = Node(
            id="check",
            name="Check",
            prompt="Check",
            outputs=["result"],
            next={"pass": "continue", "default": "retry"},
        )

        context = {}  # No "result" key
        engine = WorkflowEngine()

        # Act
        next_node_id = engine._get_next_node_id(node, context)

        # Assert
        assert next_node_id == "retry"


class TestExecutionPathTracking:
    """Test that execution path is tracked in WorkflowState"""

    @pytest.mark.asyncio
    async def test_execution_path_recorded(self):
        """Test that execution path is recorded as nodes execute"""
        # Arrange
        workflow = Workflow(
            name="test_workflow",
            description="Test",
            context={},
            nodes=[
                Node(id="start", name="Start", prompt="Start", next="middle"),
                Node(id="middle", name="Middle", prompt="Middle", next="end"),
                Node(id="end", name="End", prompt="End", next=None, type="terminal"),
            ],
        )

        engine = WorkflowEngine(save_checkpoints=False)

        # Mock executor to avoid AI calls
        from unittest.mock import AsyncMock
        from unittest.mock import patch

        with patch.object(engine.executor, "execute", new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = [
                NodeResult(node_id="start", status="success", outputs={}, raw_response="", execution_time=0.1),
                NodeResult(node_id="middle", status="success", outputs={}, raw_response="", execution_time=0.1),
                NodeResult(node_id="end", status="success", outputs={}, raw_response="", execution_time=0.1),
            ]

            # Act
            result = await engine.run(workflow)

            # Assert - path should be tracked
            assert hasattr(result, "execution_path") or "execution_path" in result.final_context
            # Path should show the order of execution
            # (Implementation detail - might be in WorkflowState or WorkflowResult)

    @pytest.mark.asyncio
    async def test_conditional_path_recorded(self):
        """Test that conditional routing path is recorded"""
        # Arrange
        workflow = Workflow(
            name="conditional_test",
            description="Test conditional",
            context={"severity": "high"},
            nodes=[
                Node(
                    id="check",
                    name="Check",
                    prompt="Check severity: {severity}",
                    outputs=["level"],
                    next={"high": "urgent", "default": "normal"},
                ),
                Node(id="urgent", name="Urgent", prompt="Urgent path", next=None, type="terminal"),
                Node(id="normal", name="Normal", prompt="Normal path", next=None, type="terminal"),
            ],
        )

        engine = WorkflowEngine(save_checkpoints=False)

        # Mock executor
        from unittest.mock import AsyncMock
        from unittest.mock import patch

        with patch.object(engine.executor, "execute", new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = [
                NodeResult(
                    node_id="check", status="success", outputs={"level": "high"}, raw_response="", execution_time=0.1
                ),
                NodeResult(node_id="urgent", status="success", outputs={}, raw_response="", execution_time=0.1),
            ]

            # Act
            result = await engine.run(workflow)

            # Assert - should have executed check -> urgent (not normal)
            node_ids = [r.node_id for r in result.node_results]
            assert "check" in node_ids
            assert "urgent" in node_ids
            assert "normal" not in node_ids


class TestWorkflowValidation:
    """Test workflow validation for conditional routing"""

    def test_validate_all_next_targets_exist(self):
        """Test validation catches invalid next node references"""
        # Arrange
        workflow = Workflow(
            name="invalid_workflow",
            description="Test",
            context={},
            nodes=[
                Node(
                    id="start",
                    name="Start",
                    prompt="Start",
                    next={"success": "valid", "failure": "nonexistent", "default": "also_missing"},
                ),
                Node(id="valid", name="Valid", prompt="Valid", next=None),
            ],
        )

        # Act
        errors = workflow.validate()

        # Assert
        assert len(errors) > 0
        assert any("nonexistent" in err.lower() for err in errors)
        assert any("also_missing" in err.lower() for err in errors)

    def test_validate_accepts_valid_conditional_routing(self):
        """Test validation passes for valid conditional routing"""
        # Arrange
        workflow = Workflow(
            name="valid_workflow",
            description="Test",
            context={},
            nodes=[
                Node(
                    id="start",
                    name="Start",
                    prompt="Start",
                    next={"high": "urgent", "low": "normal", "default": "review"},
                ),
                Node(id="urgent", name="Urgent", prompt="Urgent", next=None),
                Node(id="normal", name="Normal", prompt="Normal", next=None),
                Node(id="review", name="Review", prompt="Review", next=None),
            ],
        )

        # Act
        errors = workflow.validate()

        # Assert
        assert len(errors) == 0


class TestConditionalIntegration:
    """Integration tests for conditional routing in complete workflows"""

    @pytest.mark.asyncio
    async def test_simple_conditional_workflow(self):
        """Test complete workflow with conditional routing"""
        # Arrange
        workflow = Workflow(
            name="bug_triage",
            description="Triage bugs by severity",
            context={"bug": "Critical authentication bypass"},
            nodes=[
                Node(
                    id="analyze",
                    name="Analyze Bug",
                    prompt="Analyze this bug: {bug}. Return JSON with 'severity' field.",
                    outputs=["severity"],
                    next={"critical": "escalate", "high": "assign_senior", "default": "assign_junior"},
                ),
                Node(id="escalate", name="Escalate", prompt="Escalate to security team", next=None, type="terminal"),
                Node(
                    id="assign_senior", name="Assign Senior", prompt="Assign to senior dev", next=None, type="terminal"
                ),
                Node(
                    id="assign_junior", name="Assign Junior", prompt="Assign to junior dev", next=None, type="terminal"
                ),
            ],
        )

        engine = WorkflowEngine(save_checkpoints=False)

        # Mock executor to control routing
        from unittest.mock import AsyncMock
        from unittest.mock import patch

        with patch.object(engine.executor, "execute", new_callable=AsyncMock) as mock_execute:
            # First call: analyze node returns "critical"
            mock_execute.side_effect = [
                NodeResult(
                    node_id="analyze",
                    status="success",
                    outputs={"severity": "critical"},
                    raw_response='{"severity": "critical"}',
                    execution_time=0.1,
                ),
                NodeResult(
                    node_id="escalate", status="success", outputs={}, raw_response="Escalated", execution_time=0.1
                ),
            ]

            # Act
            result = await engine.run(workflow)

            # Assert
            assert result.status == "completed"
            # Should have routed to escalate node
            node_ids = [r.node_id for r in result.node_results]
            assert node_ids == ["analyze", "escalate"]

    @pytest.mark.asyncio
    async def test_multi_stage_conditional_workflow(self):
        """Test workflow with multiple conditional routing points"""
        # Arrange
        workflow = Workflow(
            name="deployment",
            description="Deploy with multiple checks",
            context={},
            nodes=[
                Node(
                    id="run_tests",
                    name="Run Tests",
                    prompt="Run tests",
                    outputs=["test_result"],
                    next={"pass": "security_scan", "default": "notify_failure"},
                ),
                Node(
                    id="security_scan",
                    name="Security Scan",
                    prompt="Run security scan",
                    outputs=["scan_result"],
                    next={"clean": "deploy", "default": "review_vulnerabilities"},
                ),
                Node(id="deploy", name="Deploy", prompt="Deploy to production", next=None, type="terminal"),
                Node(
                    id="review_vulnerabilities",
                    name="Review",
                    prompt="Review vulnerabilities",
                    next=None,
                    type="terminal",
                ),
                Node(id="notify_failure", name="Notify", prompt="Notify about failure", next=None, type="terminal"),
            ],
        )

        engine = WorkflowEngine(save_checkpoints=False)

        # Mock executor - tests pass, security clean -> deploy
        from unittest.mock import AsyncMock
        from unittest.mock import patch

        with patch.object(engine.executor, "execute", new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = [
                NodeResult(
                    node_id="run_tests",
                    status="success",
                    outputs={"test_result": "pass"},
                    raw_response="",
                    execution_time=0.1,
                ),
                NodeResult(
                    node_id="security_scan",
                    status="success",
                    outputs={"scan_result": "clean"},
                    raw_response="",
                    execution_time=0.1,
                ),
                NodeResult(node_id="deploy", status="success", outputs={}, raw_response="", execution_time=0.1),
            ]

            # Act
            result = await engine.run(workflow)

            # Assert
            assert result.status == "completed"
            node_ids = [r.node_id for r in result.node_results]
            assert node_ids == ["run_tests", "security_scan", "deploy"]
