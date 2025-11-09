"""
State management data structures for workflow execution.

This module provides pure data classes to track workflow execution state,
node results, and final workflow results. No behavior, just type-safe data.
"""

from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass
class NodeResult:
    """Result of executing a single node.

    Attributes:
        node_id: Unique identifier of the executed node
        status: Execution status ("success", "failed", "skipped")
        outputs: Named outputs extracted from the node
        raw_response: Full AI response text
        error: Error message if execution failed (optional)
        execution_time: Time taken to execute node in seconds
    """

    node_id: str
    status: str  # "success", "failed", "skipped"
    outputs: dict[str, Any]  # Named outputs extracted
    raw_response: str  # Full AI response
    error: str | None = None
    execution_time: float = 0.0


@dataclass
class WorkflowState:
    """Current state of workflow execution.

    Tracks the real-time state of a running workflow including current position,
    accumulated context, and history of node executions.

    Attributes:
        workflow_id: Unique identifier for this workflow instance
        current_node: ID of node currently being executed (None if not running)
        context: Accumulated context variables from all executed nodes
        results: History of all node results in execution order
        status: Current workflow status ("running", "completed", "failed")
        execution_path: List of node IDs in order of execution
    """

    workflow_id: str
    current_node: str | None
    context: dict[str, Any]  # Accumulated context
    results: list[NodeResult]  # History of node results
    status: str  # "running", "completed", "failed"
    execution_path: list[str] = field(default_factory=list)  # Track nodes executed


@dataclass
class WorkflowResult:
    """Final result of workflow execution.

    Complete summary of a finished workflow execution including all node results,
    final context state, and overall execution metrics.

    Attributes:
        workflow_id: Unique identifier for this workflow instance
        status: Final status ("completed", "failed")
        total_time: Total execution time in seconds
        node_results: All node execution results in order
        final_context: Final accumulated context after all nodes
        error: Overall error message if workflow failed (optional)
        execution_path: List of node IDs in order of execution
    """

    workflow_id: str
    status: str  # "completed", "failed"
    total_time: float
    node_results: list[NodeResult]
    final_context: dict[str, Any]
    error: str | None = None
    execution_path: list[str] = field(default_factory=list)  # Track nodes executed
