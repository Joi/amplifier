"""
Tests for error handling - Phase 8.

TEST-FIRST: Define contract for custom exceptions and error formatting.
"""

import pytest

from amplifier.flow_builder.errors import (
    AgentNotFoundError,
    FlowBuilderError,
    InvalidWorkflowError,
    WorkflowNotFoundError,
    format_error_message,
)


class TestExceptionHierarchy:
    """Test custom exception classes."""

    def test_flow_builder_error_is_base_exception(self):
        """Should have base FlowBuilderError."""
        error = FlowBuilderError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_invalid_workflow_error_inherits_from_base(self):
        """InvalidWorkflowError should inherit from FlowBuilderError."""
        error = InvalidWorkflowError("invalid yaml")
        assert isinstance(error, FlowBuilderError)
        assert isinstance(error, Exception)

    def test_agent_not_found_error_inherits_from_base(self):
        """AgentNotFoundError should inherit from FlowBuilderError."""
        error = AgentNotFoundError("missing-agent")
        assert isinstance(error, FlowBuilderError)

    def test_workflow_not_found_error_inherits_from_base(self):
        """WorkflowNotFoundError should inherit from FlowBuilderError."""
        error = WorkflowNotFoundError("missing.yaml")
        assert isinstance(error, FlowBuilderError)


class TestErrorMessageFormatting:
    """Test user-friendly error message formatting."""

    def test_format_invalid_workflow_error(self):
        """Should format InvalidWorkflowError with helpful message."""
        error = InvalidWorkflowError("missing required field 'name'")
        message = format_error_message(error)

        assert "Invalid workflow" in message
        assert "missing required field 'name'" in message
        assert "YAML" in message

    def test_format_agent_not_found_error(self):
        """Should format AgentNotFoundError with helpful message."""
        error = AgentNotFoundError("code-reviewer")
        message = format_error_message(error)

        assert "Agent not found" in message
        assert "code-reviewer" in message
        assert "available agents" in message

    def test_format_workflow_not_found_error(self):
        """Should format WorkflowNotFoundError with helpful message."""
        error = WorkflowNotFoundError("auth-flow.yaml")
        message = format_error_message(error)

        assert "Workflow not found" in message
        assert "auth-flow.yaml" in message
        assert "ai_flows/" in message

    def test_format_generic_error(self):
        """Should format non-FlowBuilder errors with simple message."""
        error = ValueError("unexpected value")
        message = format_error_message(error)

        assert "Error:" in message
        assert "unexpected value" in message

    def test_format_error_preserves_original_message(self):
        """Should include original exception message in formatted output."""
        error = InvalidWorkflowError("nodes must be a list")
        message = format_error_message(error)

        assert "nodes must be a list" in message


class TestErrorUsagePatterns:
    """Test common error usage patterns."""

    def test_raise_invalid_workflow_error(self):
        """Should be able to raise and catch InvalidWorkflowError."""
        with pytest.raises(InvalidWorkflowError) as exc_info:
            raise InvalidWorkflowError("missing version field")

        assert "missing version field" in str(exc_info.value)

    def test_raise_agent_not_found_error(self):
        """Should be able to raise and catch AgentNotFoundError."""
        with pytest.raises(AgentNotFoundError) as exc_info:
            raise AgentNotFoundError("unknown-agent")

        assert "unknown-agent" in str(exc_info.value)

    def test_catch_flow_builder_error_catches_subclasses(self):
        """Should be able to catch all FlowBuilder errors with base class."""
        with pytest.raises(FlowBuilderError):
            raise InvalidWorkflowError("test")

        with pytest.raises(FlowBuilderError):
            raise AgentNotFoundError("test")

        with pytest.raises(FlowBuilderError):
            raise WorkflowNotFoundError("test")


class TestErrorMessageClarity:
    """Test that error messages are clear and actionable."""

    def test_invalid_workflow_error_suggests_yaml_check(self):
        """Should suggest checking YAML file."""
        error = InvalidWorkflowError("invalid syntax")
        message = format_error_message(error)

        assert "Check your workflow YAML file" in message

    def test_agent_not_found_error_suggests_listing(self):
        """Should suggest running flow-builder to see agents."""
        error = AgentNotFoundError("missing")
        message = format_error_message(error)

        assert "amplifier flow-builder" in message

    def test_workflow_not_found_error_suggests_directory(self):
        """Should suggest checking ai_flows/ directory."""
        error = WorkflowNotFoundError("missing.yaml")
        message = format_error_message(error)

        assert "ai_flows/" in message


class TestErrorContext:
    """Test errors include useful context."""

    def test_error_with_detailed_context(self):
        """Should allow detailed context in error messages."""
        error = InvalidWorkflowError(
            "Node 'validate' missing required field 'prompt' at line 15"
        )
        message = format_error_message(error)

        assert "Node 'validate'" in message
        assert "line 15" in message

    def test_format_error_does_not_lose_details(self):
        """Should not truncate or lose error details."""
        long_error = AgentNotFoundError(
            "Agent 'super-long-agent-name-that-does-not-exist' "
            "not found in available agents list"
        )
        message = format_error_message(long_error)

        assert "super-long-agent-name-that-does-not-exist" in message
        assert "not found in available agents list" in message
