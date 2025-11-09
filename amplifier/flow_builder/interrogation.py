"""
Basic interrogation module for flow builder.

Phase 1: Simple helper functions for building workflows from user input.
Phase 3: AI-enhanced interrogation with agent recommendations.
"""

import re
from typing import Any

from amplifier.flow_builder.ai_analysis import recommend_agent
from amplifier.flow_builder.discovery import Agent
from amplifier.flow_builder.validation import WorkflowSpec


def build_minimal_workflow(
    name: str,
    description: str,
    node_name: str,
    node_prompt: str,
    agent: str | None = None,
    agent_mode: str | None = None,
    outputs: list[str] | None = None,
) -> WorkflowSpec:
    """
    Build a minimal single-node workflow from basic inputs.

    Phase 1 implementation: No AI, just data gathering.
    Creates a simple WorkflowSpec with one node.

    Args:
        name: Workflow name
        description: Workflow description
        node_name: Name for the single node
        node_prompt: Prompt text for the node
        agent: Optional agent to use
        agent_mode: Optional agent mode
        outputs: Optional list of output variable names

    Returns:
        WorkflowSpec ready for validation and generation

    Examples:
        >>> spec = build_minimal_workflow(
        ...     name="my-workflow",
        ...     description="Test workflow",
        ...     node_name="First Step",
        ...     node_prompt="Do something"
        ... )
        >>> spec.name
        'my-workflow'
    """
    # Generate node ID from name (slug format)
    node_id = _generate_node_id(node_name)

    # Build node dict
    node: dict[str, Any] = {
        "id": node_id,
        "name": node_name,
        "prompt": node_prompt,
    }

    # Add optional fields
    if agent:
        node["agent"] = agent

    if agent_mode:
        node["agent_mode"] = agent_mode

    if outputs:
        node["outputs"] = outputs

    # Create WorkflowSpec
    return WorkflowSpec(
        name=name,
        description=description,
        nodes=[node],
        version="1.0.0",
    )


def interrogate_multi_node() -> WorkflowSpec:
    """
    Build a multi-node workflow from user input.

    Phase 2 implementation: Ask for 2-5 nodes, link them linearly.
    NO AI recommendations yet - just collect data.

    Prompts for:
    - Workflow name and description
    - Number of nodes (1-5)
    - For each node: name, prompt, agent (optional), outputs (optional)

    Returns:
        WorkflowSpec with 1-5 nodes linked linearly

    Examples:
        >>> spec = interrogate_multi_node()
        # User inputs collected via input()
        >>> len(spec.nodes)
        3
    """
    # Collect workflow metadata
    name = input("Workflow name: ").strip()
    description = input("Workflow description: ").strip()

    # Collect number of nodes
    while True:
        try:
            count_str = input("How many steps/nodes? (1-5): ").strip()
            node_count = int(count_str)
            if 1 <= node_count <= 5:
                break
            print("Please enter a number between 1 and 5")
        except ValueError:
            print("Please enter a valid number")

    # Collect nodes
    nodes: list[dict[str, Any]] = []
    for i in range(node_count):
        print(f"\n--- Node {i + 1} of {node_count} ---")

        node_name = input("Node name: ").strip()
        node_prompt = input("Node prompt/task: ").strip()
        agent = input("Agent (optional, press Enter to skip): ").strip()
        outputs_input = input("Outputs (comma-separated, press Enter to skip): ").strip()

        # Parse outputs
        outputs = None
        if outputs_input:
            outputs = [o.strip() for o in outputs_input.split(",") if o.strip()]

        # Generate node ID
        node_id = _generate_node_id(node_name)

        # Build node dict
        node: dict[str, Any] = {
            "id": node_id,
            "name": node_name,
            "prompt": node_prompt,
        }

        if agent:
            node["agent"] = agent

        if outputs:
            node["outputs"] = outputs

        nodes.append(node)

    # Link nodes linearly (each node points to next)
    for i in range(len(nodes) - 1):
        nodes[i]["next"] = nodes[i + 1]["id"]

    # Create WorkflowSpec
    return WorkflowSpec(
        name=name,
        description=description,
        nodes=nodes,
        version="1.0.0",
    )


def set_conditional_routing(
    spec: WorkflowSpec,
    node_id: str,
    routing: dict[str, str],
) -> WorkflowSpec:
    """
    Set conditional routing for a specific node.

    Updates the node's 'next' field to be a routing dictionary
    instead of a simple string.

    Args:
        spec: WorkflowSpec to modify
        node_id: ID of node to update
        routing: Dict mapping conditions to target node IDs
                 e.g., {"success": "next-node", "failure": "error-handler", "default": "next-node"}

    Returns:
        Updated WorkflowSpec

    Examples:
        >>> spec = WorkflowSpec(name="test", description="Test", nodes=[...])
        >>> spec = set_conditional_routing(spec, "router", {"success": "path-a", "default": "path-a"})
    """
    # Find the node
    node_found = False
    for node in spec.nodes:
        if node["id"] == node_id:
            node["next"] = routing
            node_found = True
            break

    if not node_found:
        raise ValueError(f"Node with ID '{node_id}' not found in workflow")

    return spec


def _generate_node_id(name: str) -> str:
    """
    Generate a valid node ID from a human-readable name.

    Converts to lowercase, replaces spaces with hyphens,
    removes special characters.

    Args:
        name: Human-readable node name

    Returns:
        Valid node ID (slug format)

    Examples:
        >>> _generate_node_id("My Step Name")
        'my-step-name'
        >>> _generate_node_id("Name with @#$% chars!")
        'name-with-chars'
    """
    # Convert to lowercase
    node_id = name.lower()

    # Replace spaces (including multiple spaces) with single hyphen
    node_id = re.sub(r"\s+", "-", node_id)

    # Remove all non-alphanumeric except hyphens
    node_id = re.sub(r"[^a-z0-9-]", "", node_id)

    # Remove leading/trailing hyphens
    node_id = node_id.strip("-")

    # Collapse multiple hyphens to single hyphen
    node_id = re.sub(r"-+", "-", node_id)

    return node_id


async def interrogate_with_ai_recommendations(agents: list[Agent]) -> WorkflowSpec:
    """
    Build a multi-node workflow with AI agent recommendations.

    Phase 3.2 implementation: Uses AI to recommend agents but allows user override.

    For each node:
    1. Collect node name and task description
    2. Use AI to recommend best agent for the task
    3. Show recommendation to user
    4. Allow user to accept (y), override (enter agent name), or skip (empty)

    Args:
        agents: List of available agents for recommendations

    Returns:
        WorkflowSpec with nodes that may have AI-recommended or user-selected agents

    Examples:
        >>> agents = [Agent("zen-architect", "Design", Path("test.toml"))]
        >>> spec = await interrogate_with_ai_recommendations(agents)
        # User interacts with prompts, AI recommends agents
        >>> len(spec.nodes)
        2
    """
    # Collect workflow metadata
    name = input("Workflow name: ").strip()
    description = input("Workflow description: ").strip()

    # Collect number of nodes
    while True:
        try:
            count_str = input("How many steps/nodes? (1-5): ").strip()
            node_count = int(count_str)
            if 1 <= node_count <= 5:
                break
            print("Please enter a number between 1 and 5")
        except ValueError:
            print("Please enter a valid number")

    # Collect nodes with AI recommendations
    nodes: list[dict[str, Any]] = []
    for i in range(node_count):
        print(f"\n--- Node {i + 1} of {node_count} ---")

        node_name = input("Node name: ").strip()
        node_prompt = input("Node prompt/task: ").strip()

        # AI recommendation if agents available
        agent = None
        if agents:
            # Get AI recommendation
            recommended = await recommend_agent(node_prompt, agents)
            print(f"\nRecommended agent: {recommended.name}")
            print(f"  ({recommended.description})")

            # Ask user to accept or override
            accept = input("Use this agent? (y/n or enter different agent name): ").strip().lower()

            if accept == "y":
                agent = recommended.name
            elif accept == "n" or accept == "":
                # User rejected, ask for override
                if accept == "n":
                    override = input("Enter agent name (or press Enter to skip): ").strip()
                    if override:
                        agent = override
            else:
                # User entered agent name directly
                agent = accept
        else:
            # No agents available, ask directly
            agent = input("Agent (optional, press Enter to skip): ").strip()

        # Collect outputs
        outputs_input = input("Outputs (comma-separated, press Enter to skip): ").strip()
        outputs = None
        if outputs_input:
            outputs = [o.strip() for o in outputs_input.split(",") if o.strip()]

        # Generate node ID
        node_id = _generate_node_id(node_name)

        # Build node dict
        node: dict[str, Any] = {
            "id": node_id,
            "name": node_name,
            "prompt": node_prompt,
        }

        if agent:
            node["agent"] = agent

        if outputs:
            node["outputs"] = outputs

        nodes.append(node)

    # Link nodes linearly (each node points to next)
    for i in range(len(nodes) - 1):
        nodes[i]["next"] = nodes[i + 1]["id"]

    # Create WorkflowSpec
    return WorkflowSpec(
        name=name,
        description=description,
        nodes=nodes,
        version="1.0.0",
    )
