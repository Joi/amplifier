"""
Workflow and Node data models for DotRunner.

These dataclasses represent the core structure of workflow definitions
loaded from YAML files.
"""

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Union

import yaml


class AgentMode(str, Enum):
    """
    Standard agent execution modes.

    These modes provide semantic hints about what the agent should do:
    - ANALYZE: Examine and break down information
    - EVALUATE: Assess quality, completeness, or correctness
    - EXECUTE: Perform actions or implement changes
    - REVIEW: Check work for issues or improvements
    - GENERATE: Create new content or artifacts

    Note: Natural language mode strings are also supported for flexibility.
    The enum provides standard modes for common cases, but any string is valid.
    """

    ANALYZE = "ANALYZE"
    EVALUATE = "EVALUATE"
    EXECUTE = "EXECUTE"
    REVIEW = "REVIEW"
    GENERATE = "GENERATE"


@dataclass
class Node:
    """
    Single workflow node representing a task.

    A node is the atomic unit of work in a workflow. Each node:
    - Has a unique ID within the workflow
    - Has a name (human-readable) and optional description
    - Can have inputs mapped from parent context
    - Defines a prompt to execute (with context interpolation)
    - Can specify which agent to use
    - Can produce named outputs for downstream nodes
    - Can route to next node(s) conditionally or unconditionally
    """

    id: str  # Unique node identifier
    name: str  # Human-readable name
    prompt: str = ""  # Prompt template (required for agent nodes, empty for workflow nodes)

    # Optional fields with defaults
    description: str | None = None  # Node purpose description
    inputs: dict[str, Any] = field(default_factory=dict)  # Input parameter mapping
    agent: str | None = None  # Agent to use (None for AI, name for specific agent)
    agent_mode: str | None = None  # Optional mode for agent (e.g., "REVIEW", "ANALYZE")
    workflow: str | None = None  # Path to sub-workflow YAML (for workflow nodes)
    outputs: list[str] = field(default_factory=list)  # Named outputs to capture
    next: Union[str, dict[str, str], list[dict[str, str]]] | None = None  # Routing config
    retry_on_failure: int = 1  # Number of retry attempts
    type: str | None = None  # "terminal" for end nodes


@dataclass
class Workflow:
    """
    Complete workflow definition with nodes and global context.

    A workflow is a directed graph of nodes that execute in sequence or
    based on conditional routing. It includes:
    - Metadata (name, description, version)
    - List of nodes to execute
    - Global context available to all nodes
    """

    name: str  # Workflow identifier
    description: str  # What this workflow does
    nodes: list[Node]  # Ordered list of nodes

    # Optional fields with defaults
    version: str = "1.0.0"  # Semantic version
    context: dict[str, Any] = field(default_factory=dict)  # Global context

    def get_node(self, node_id: str) -> Node | None:
        """
        Get node by ID.

        Args:
            node_id: Node identifier to find

        Returns:
            Node if found, None otherwise
        """
        return next((n for n in self.nodes if n.id == node_id), None)

    def validate(self) -> list[str]:
        """
        Validate workflow structure and relationships.

        Returns:
            List of validation errors (empty if valid)

        Checks:
        - At least one node exists
        - All node IDs are unique
        - All node references point to valid nodes
        - No circular dependencies exist
        """
        errors = []

        # Check at least one node
        if not self.nodes:
            errors.append("Workflow must have at least one node")
            return errors

        # Check for duplicate node IDs
        node_ids = [n.id for n in self.nodes]
        duplicates = [nid for nid in node_ids if node_ids.count(nid) > 1]
        if duplicates:
            errors.append(f"Duplicate node ID found: {duplicates[0]}")

        # Check all node references are valid
        for node in self.nodes:
            if isinstance(node.next, str):
                # Simple next reference
                if not self.get_node(node.next):
                    errors.append(f"Node '{node.id}' references nonexistent node '{node.next}'")
            elif isinstance(node.next, dict):
                # Dictionary-based conditional routing
                for condition, target in node.next.items():
                    if condition != "default":  # Skip default, it's not a node reference
                        if not self.get_node(target):
                            errors.append(
                                f"Node '{node.id}' has invalid routing target '{target}' for condition '{condition}'"
                            )
                    elif target and not self.get_node(target):  # Check default target if it exists
                        errors.append(f"Node '{node.id}' has invalid default routing target '{target}'")

        # Check for circular dependencies
        try:
            self._detect_cycles()
        except ValueError as e:
            errors.append(str(e))

        return errors

    def _detect_cycles(self) -> None:
        """
        Detect circular dependencies in workflow graph.

        Uses depth-first search to find cycles.

        Raises:
            ValueError: If circular dependency detected
        """
        # Track visited nodes and current path
        visited = set()
        rec_stack = set()

        def visit(node_id: str, path: list[str]) -> None:
            if node_id in rec_stack:
                cycle_path = " -> ".join(path + [node_id])
                raise ValueError(f"Circular dependency detected: {cycle_path}")

            if node_id in visited:
                return

            visited.add(node_id)
            rec_stack.add(node_id)

            node = self.get_node(node_id)
            if node:
                # Get next node(s)
                next_nodes = []
                if isinstance(node.next, str):
                    next_nodes = [node.next]
                elif isinstance(node.next, dict):
                    # Dictionary-based conditional routing
                    next_nodes = list(node.next.values())
                elif isinstance(node.next, list):
                    # Legacy list format (if still supported)
                    next_nodes = [c["goto"] for c in node.next if "goto" in c]

                # Visit each next node
                for next_id in next_nodes:
                    if next_id:  # Skip None values
                        visit(next_id, path + [node_id])

            rec_stack.remove(node_id)

        # Start from each node (to catch disconnected components)
        for node in self.nodes:
            if node.id not in visited:
                visit(node.id, [])

    @classmethod
    def from_yaml(cls, path: Path) -> "Workflow":
        """
        Load workflow from YAML file.

        Args:
            path: Path to YAML workflow file

        Returns:
            Workflow instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid or missing required fields
        """
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {path}")

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}")

        if not data:
            raise ValueError("Empty YAML file")

        if "workflow" not in data:
            raise ValueError("Missing required field: workflow")

        workflow_data = data["workflow"]

        # Validate required workflow fields
        for field_name in ["name", "description"]:
            if field_name not in workflow_data:
                raise ValueError(f"Missing required field: workflow.{field_name}")

        if "nodes" not in data:
            raise ValueError("Missing required field: nodes")

        # Parse nodes
        nodes_data = data["nodes"]
        if not isinstance(nodes_data, list):
            raise ValueError("nodes must be a list")

        nodes = []
        for node_data in nodes_data:
            # Validate required node fields
            for field_name in ["id", "name"]:
                if field_name not in node_data:
                    raise ValueError(f"Missing required field in node: {field_name}")

            # Node must have either prompt or workflow
            has_prompt = "prompt" in node_data and node_data["prompt"]
            has_workflow = "workflow" in node_data and node_data["workflow"]
            if not has_prompt and not has_workflow:
                raise ValueError(f"Node '{node_data.get('id')}' must have either 'prompt' or 'workflow' field")

            # Create node with all fields
            node = Node(
                id=node_data["id"],
                name=node_data["name"],
                prompt=node_data.get("prompt", ""),
                description=node_data.get("description"),
                inputs=node_data.get("inputs", {}),
                agent=node_data.get("agent"),
                agent_mode=node_data.get("agent_mode"),
                workflow=node_data.get("workflow"),
                outputs=node_data.get("outputs", []),
                next=node_data.get("next"),
                retry_on_failure=node_data.get("retry_on_failure", 1),
                type=node_data.get("type"),
            )
            nodes.append(node)

        # Create workflow
        workflow = cls(
            name=workflow_data["name"],
            description=workflow_data["description"],
            nodes=nodes,
            version=workflow_data.get("version", "1.0.0"),
            context=workflow_data.get("context", {}),
        )

        # Validate workflow structure
        errors = workflow.validate()
        if errors:
            raise ValueError(f"Workflow validation failed: {'; '.join(errors)}")

        return workflow

    def to_dict(self) -> dict:
        """
        Convert workflow to dictionary for YAML serialization.

        Returns:
            Dictionary representation matching YAML format
        """
        # Convert nodes to dict format
        nodes_data = []
        for node in self.nodes:
            node_dict = {"id": node.id, "name": node.name}

            # Include prompt if present (agent nodes)
            if node.prompt:
                node_dict["prompt"] = node.prompt

            # Include workflow if present (workflow nodes)
            if node.workflow is not None:
                node_dict["workflow"] = node.workflow

            # Only include non-default values
            if node.description is not None:
                node_dict["description"] = node.description
            if node.inputs:
                node_dict["inputs"] = node.inputs
            if node.agent is not None:
                node_dict["agent"] = node.agent
            if node.agent_mode is not None:
                node_dict["agent_mode"] = node.agent_mode
            if node.outputs:
                node_dict["outputs"] = node.outputs
            if node.next is not None:
                node_dict["next"] = node.next
            if node.retry_on_failure != 1:
                node_dict["retry_on_failure"] = node.retry_on_failure
            if node.type is not None:
                node_dict["type"] = node.type

            nodes_data.append(node_dict)

        # Build complete workflow dict
        workflow_dict = {
            "workflow": {
                "name": self.name,
                "description": self.description,
                "version": self.version,
            },
            "nodes": nodes_data,
        }

        # Add context if not empty
        if self.context:
            workflow_dict["workflow"]["context"] = self.context

        return workflow_dict
