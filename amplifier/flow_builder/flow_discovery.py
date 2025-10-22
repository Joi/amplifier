"""
Flow discovery module for flow builder.

Phase 4: Scan existing workflows to avoid duplication.
Simple directory scan with YAML parsing.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class FlowInfo:
    """
    Workflow metadata extracted from YAML file.

    Attributes:
        name: Workflow identifier
        description: What the workflow does
        file_path: Path to the workflow YAML file
        node_count: Number of nodes in workflow
    """

    name: str
    description: str
    file_path: Path
    node_count: int


def scan_flows(flows_dir: Path) -> list[FlowInfo]:
    """
    Scan directory for workflow YAML files and extract metadata.

    Phase 4.1 implementation: Simple directory scan with YAML parsing.
    NO caching, NO indexing - just read and parse.

    Args:
        flows_dir: Directory containing workflow YAML files

    Returns:
        List of FlowInfo objects with metadata

    Examples:
        >>> flows = scan_flows(Path("ai_flows"))
        >>> for flow in flows:
        ...     print(f"{flow.name}: {flow.description} ({flow.node_count} nodes)")
    """
    if not flows_dir.exists():
        return []

    flows = []

    # Find all .yaml files
    for yaml_file in flows_dir.glob("*.yaml"):
        # Skip hidden files
        if yaml_file.name.startswith("."):
            continue

        try:
            # Read YAML
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Extract workflow metadata
            if not data or "workflow" not in data:
                continue

            workflow = data["workflow"]
            name = workflow.get("name", yaml_file.stem)
            description = workflow.get("description", "")

            # Count nodes
            nodes = data.get("nodes", [])
            node_count = len(nodes)

            # Create FlowInfo object
            flow_info = FlowInfo(
                name=name,
                description=description,
                file_path=yaml_file,
                node_count=node_count,
            )
            flows.append(flow_info)

        except (yaml.YAMLError, OSError, KeyError):
            # Skip files with invalid YAML or read errors
            continue

    return flows


async def check_similarity(user_goal: str, existing_flows: list[FlowInfo]) -> FlowInfo | None:
    """
    Use AI to check if user's goal matches existing flow.

    Phase 4.2 implementation: Simple AI call to detect semantic similarity.
    Returns first similar flow found, or None.

    Args:
        user_goal: What the user wants to accomplish
        existing_flows: List of existing workflows to check against

    Returns:
        FlowInfo if similar flow found, None otherwise

    Examples:
        >>> flows = scan_flows(Path("ai_flows"))
        >>> similar = await check_similarity("Add authentication", flows)
        >>> if similar:
        ...     print(f"Found similar flow: {similar.name}")
    """
    if not existing_flows:
        return None

    # Import here to avoid circular dependency
    from amplifier.ccsdk_toolkit.core.session import ClaudeSession

    # Build catalog of existing flows
    flow_list = []
    for flow in existing_flows:
        flow_list.append(f"- {flow.name}: {flow.description}")

    catalog = "\n".join(flow_list)

    # Build prompt
    prompt = f"""Given this user goal and existing workflows, is there a similar workflow?

User goal: {user_goal}

Existing workflows:
{catalog}

If there is a workflow that does something very similar to the user's goal, respond with ONLY the workflow name (exactly as shown).
If there is NO similar workflow, respond with: NONE

Be strict - only match if the workflows are truly similar in purpose.

Example responses:
- auth-flow
- NONE
"""

    # Call Claude
    async with ClaudeSession() as session:
        response = await session.query(prompt, stream=False)

    # Handle error or empty response
    if response.error or not response.content:
        return None

    # Parse response
    result = response.content.strip()

    if result == "NONE" or not result:
        return None

    # Find matching flow (case-insensitive)
    result_lower = result.lower()
    for flow in existing_flows:
        if flow.name.lower() == result_lower:
            return flow

    # No match found
    return None
