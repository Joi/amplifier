"""
YAML generator module for flow builder.

Converts WorkflowSpec to DotRunner-compatible YAML format.
NO custom logic - just serialize the spec to YAML.
"""

from pathlib import Path

import yaml

from amplifier.flow_builder.validation import WorkflowSpec


def generate_yaml(spec: WorkflowSpec, output_path: Path) -> None:
    """
    Generate DotRunner workflow YAML from WorkflowSpec.

    Converts WorkflowSpec to dict and writes clean YAML to file.
    Creates parent directories if needed.

    Args:
        spec: Workflow specification to convert
        output_path: Path where YAML should be written

    Examples:
        >>> spec = WorkflowSpec(name="test", description="Test", nodes=[...])
        >>> generate_yaml(spec, Path("ai_flows/test.yaml"))
    """
    # Create parent directories if they don't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert spec to DotRunner's format
    # DotRunner expects: workflow: { name, description, version, context }
    # and nodes: [] at top level
    workflow_info = {
        "name": spec.name,
        "description": spec.description,
        "version": spec.version,
    }

    # Add context if present
    if spec.context:
        workflow_info["context"] = spec.context

    # Convert nodes (clean up optional fields)
    nodes_list = []
    for node_dict in spec.nodes:
        clean_node = {
            "id": node_dict["id"],
            "name": node_dict["name"],
            "prompt": node_dict.get("prompt", ""),
        }

        # Add optional fields only if present
        if node_dict.get("description"):
            clean_node["description"] = node_dict["description"]

        if node_dict.get("inputs"):
            clean_node["inputs"] = node_dict["inputs"]

        if node_dict.get("agent"):
            clean_node["agent"] = node_dict["agent"]

        if node_dict.get("agent_mode"):
            clean_node["agent_mode"] = node_dict["agent_mode"]

        if node_dict.get("workflow"):
            clean_node["workflow"] = node_dict["workflow"]

        if node_dict.get("outputs"):
            clean_node["outputs"] = node_dict["outputs"]

        if node_dict.get("next"):
            clean_node["next"] = node_dict["next"]

        if node_dict.get("retry_on_failure") is not None:
            clean_node["retry_on_failure"] = node_dict["retry_on_failure"]

        if node_dict.get("type"):
            clean_node["type"] = node_dict["type"]

        nodes_list.append(clean_node)

    # Build final structure (DotRunner format)
    output_dict = {
        "workflow": workflow_info,
        "nodes": nodes_list,
    }

    # Write YAML with clean formatting
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            output_dict,
            f,
            default_flow_style=False,  # Use block style (more readable)
            sort_keys=False,  # Maintain field order
            allow_unicode=True,
        )
