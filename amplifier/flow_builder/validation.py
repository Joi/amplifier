"""
Workflow validation module for flow builder.

Validates workflow specifications using DotRunner's Workflow.validate().
ZERO custom logic initially - just use DotRunner's validation.
"""

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from ai_working.dotrunner.workflow import Node
from ai_working.dotrunner.workflow import Workflow


@dataclass
class WorkflowSpec:
    """
    Workflow specification for flow builder.

    Intermediate format before converting to DotRunner's Workflow.
    Simpler to work with during interrogation.

    Attributes:
        name: Workflow identifier
        description: What this workflow does
        nodes: List of node dictionaries
        version: Semantic version (default "1.0.0")
        context: Global context variables
    """

    name: str
    description: str
    nodes: list[dict[str, Any]]
    version: str = "1.0.0"
    context: dict[str, Any] = field(default_factory=dict)


def validate_workflow(spec: WorkflowSpec) -> list[str]:
    """
    Validate workflow specification using DotRunner's validation.

    Converts WorkflowSpec to DotRunner's Workflow format and calls
    workflow.validate(). NO custom validation logic - use DotRunner.

    Args:
        spec: Workflow specification to validate

    Returns:
        List of validation errors (empty if valid)

    Examples:
        >>> spec = WorkflowSpec(name="test", description="Test", nodes=[...])
        >>> errors = validate_workflow(spec)
        >>> if errors:
        ...     print(f"Validation failed: {errors}")
    """
    try:
        # Convert WorkflowSpec to DotRunner's Workflow format
        # Create Node objects from node dicts
        nodes = []
        for node_dict in spec.nodes:
            node = Node(
                id=node_dict["id"],
                name=node_dict["name"],
                prompt=node_dict.get("prompt", ""),
                description=node_dict.get("description"),
                inputs=node_dict.get("inputs", {}),
                agent=node_dict.get("agent"),
                agent_mode=node_dict.get("agent_mode"),
                workflow=node_dict.get("workflow"),
                outputs=node_dict.get("outputs", []),
                next=node_dict.get("next"),
                retry_on_failure=node_dict.get("retry_on_failure", 1),
                type=node_dict.get("type"),
            )
            nodes.append(node)

        # Create Workflow
        workflow = Workflow(
            name=spec.name, description=spec.description, nodes=nodes, version=spec.version, context=spec.context
        )

        # Use DotRunner's validation (returns list of errors)
        errors = workflow.validate()
        return errors

    except Exception as e:
        # If conversion fails, return error
        return [f"Workflow conversion failed: {str(e)}"]
