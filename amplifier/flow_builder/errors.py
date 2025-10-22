"""
Error handling - Phase 8.

Custom exceptions with helpful messages.
"""


class FlowBuilderError(Exception):
    """Base exception for flow builder."""

    pass


class InvalidWorkflowError(FlowBuilderError):
    """Workflow validation failed."""

    pass


class AgentNotFoundError(FlowBuilderError):
    """Specified agent doesn't exist."""

    pass


class WorkflowNotFoundError(FlowBuilderError):
    """Workflow file not found."""

    pass


def format_error_message(error: Exception) -> str:
    """Convert exception to user-friendly message."""
    if isinstance(error, InvalidWorkflowError):
        return f"Invalid workflow: {error}. Check your workflow YAML file."
    elif isinstance(error, AgentNotFoundError):
        return f"Agent not found: {error}. Run 'amplifier flow-builder' to see available agents."
    elif isinstance(error, WorkflowNotFoundError):
        return f"Workflow not found: {error}. Check ai_flows/ directory."
    else:
        return f"Error: {error}"
