"""
Tests for YAML generator module.

Following TEST-FIRST discipline: These tests define the contract (studs)
for the generator module before implementation.
"""

import yaml

from amplifier.flow_builder.generator import generate_yaml
from amplifier.flow_builder.validation import WorkflowSpec


class TestYamlGenerator:
    """Tests for YAML generation from WorkflowSpec."""

    def test_generate_yaml_creates_valid_yaml(self, tmp_path):
        """generate_yaml() creates valid YAML file."""
        spec = WorkflowSpec(
            name="test-workflow",
            description="Test workflow",
            nodes=[
                {
                    "id": "step1",
                    "name": "First Step",
                    "prompt": "Do something",
                    "outputs": ["result"],
                }
            ],
        )

        output_path = tmp_path / "workflow.yaml"
        generate_yaml(spec, output_path)

        # Verify file exists
        assert output_path.exists()

        # Verify it's valid YAML
        with open(output_path) as f:
            data = yaml.safe_load(f)

        assert data is not None
        assert "workflow" in data
        assert "nodes" in data
        assert "name" in data["workflow"]

    def test_generate_yaml_preserves_workflow_fields(self, tmp_path):
        """generate_yaml() preserves all workflow fields correctly."""
        spec = WorkflowSpec(
            name="my-workflow",
            description="My test workflow",
            version="2.0.0",
            context={"project": "amplifier"},
            nodes=[
                {
                    "id": "step1",
                    "name": "Step 1",
                    "prompt": "Do task 1",
                    "outputs": ["data"],
                }
            ],
        )

        output_path = tmp_path / "workflow.yaml"
        generate_yaml(spec, output_path)

        # Load and verify
        with open(output_path) as f:
            data = yaml.safe_load(f)

        workflow = data["workflow"]
        assert workflow["name"] == "my-workflow"
        assert workflow["description"] == "My test workflow"
        assert workflow["version"] == "2.0.0"
        assert workflow["context"] == {"project": "amplifier"}

    def test_generate_yaml_preserves_node_fields(self, tmp_path):
        """generate_yaml() preserves all node fields correctly."""
        spec = WorkflowSpec(
            name="test",
            description="Test",
            nodes=[
                {
                    "id": "step1",
                    "name": "First",
                    "prompt": "Do A",
                    "description": "First step",
                    "inputs": {"data": "value"},
                    "agent": "zen-architect",
                    "agent_mode": "ANALYZE",
                    "outputs": ["result"],
                    "next": "step2",
                    "retry_on_failure": 3,
                }
            ],
        )

        output_path = tmp_path / "workflow.yaml"
        generate_yaml(spec, output_path)

        # Load and verify node fields
        with open(output_path) as f:
            data = yaml.safe_load(f)

        node = data["nodes"][0]
        assert node["id"] == "step1"
        assert node["name"] == "First"
        assert node["prompt"] == "Do A"
        assert node["description"] == "First step"
        assert node["inputs"] == {"data": "value"}
        assert node["agent"] == "zen-architect"
        assert node["agent_mode"] == "ANALYZE"
        assert node["outputs"] == ["result"]
        assert node["next"] == "step2"
        assert node["retry_on_failure"] == 3

    def test_generate_yaml_handles_multiple_nodes(self, tmp_path):
        """generate_yaml() handles workflows with multiple nodes."""
        spec = WorkflowSpec(
            name="multi-node",
            description="Multiple nodes",
            nodes=[
                {"id": "step1", "name": "First", "prompt": "Do A", "next": "step2"},
                {"id": "step2", "name": "Second", "prompt": "Do B", "next": "step3"},
                {"id": "step3", "name": "Third", "prompt": "Do C"},
            ],
        )

        output_path = tmp_path / "workflow.yaml"
        generate_yaml(spec, output_path)

        with open(output_path) as f:
            data = yaml.safe_load(f)

        assert len(data["nodes"]) == 3
        assert data["nodes"][0]["id"] == "step1"
        assert data["nodes"][1]["id"] == "step2"
        assert data["nodes"][2]["id"] == "step3"

    def test_generate_yaml_handles_conditional_routing(self, tmp_path):
        """generate_yaml() handles conditional routing (next as dict)."""
        spec = WorkflowSpec(
            name="conditional",
            description="Conditional routing",
            nodes=[
                {
                    "id": "step1",
                    "name": "Router",
                    "prompt": "Route",
                    "next": {"success": "step2", "failure": "step3", "default": "step2"},
                },
                {"id": "step2", "name": "Success", "prompt": "Handle success"},
                {"id": "step3", "name": "Failure", "prompt": "Handle failure"},
            ],
        )

        output_path = tmp_path / "workflow.yaml"
        generate_yaml(spec, output_path)

        with open(output_path) as f:
            data = yaml.safe_load(f)

        node = data["nodes"][0]
        assert isinstance(node["next"], dict)
        assert node["next"]["success"] == "step2"
        assert node["next"]["failure"] == "step3"
        assert node["next"]["default"] == "step2"

    def test_generate_yaml_omits_optional_fields_when_none(self, tmp_path):
        """generate_yaml() omits optional fields when they are None or empty."""
        spec = WorkflowSpec(
            name="minimal",
            description="Minimal workflow",
            nodes=[
                {
                    "id": "step1",
                    "name": "Only Step",
                    "prompt": "Do something",
                    # No description, inputs, agent, agent_mode, workflow, outputs, next
                }
            ],
        )

        output_path = tmp_path / "workflow.yaml"
        generate_yaml(spec, output_path)

        with open(output_path) as f:
            data = yaml.safe_load(f)

        node = data["nodes"][0]
        # Required fields should be present
        assert "id" in node
        assert "name" in node
        assert "prompt" in node

        # Optional fields should be omitted or have defaults
        assert node.get("description") is None
        assert node.get("inputs") in [None, {}]
        assert node.get("agent") is None
        assert node.get("agent_mode") is None

    def test_generate_yaml_creates_parent_directories(self, tmp_path):
        """generate_yaml() creates parent directories if they don't exist."""
        output_path = tmp_path / "nested" / "dir" / "workflow.yaml"

        spec = WorkflowSpec(
            name="test",
            description="Test",
            nodes=[{"id": "step1", "name": "Step", "prompt": "Do"}],
        )

        generate_yaml(spec, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_generate_yaml_overwrites_existing_file(self, tmp_path):
        """generate_yaml() overwrites existing file."""
        output_path = tmp_path / "workflow.yaml"

        # Create initial file
        spec1 = WorkflowSpec(
            name="workflow-v1",
            description="Version 1",
            nodes=[{"id": "step1", "name": "V1", "prompt": "Do V1"}],
        )
        generate_yaml(spec1, output_path)

        # Overwrite with new spec
        spec2 = WorkflowSpec(
            name="workflow-v2",
            description="Version 2",
            nodes=[{"id": "step1", "name": "V2", "prompt": "Do V2"}],
        )
        generate_yaml(spec2, output_path)

        # Verify new content
        with open(output_path) as f:
            data = yaml.safe_load(f)

        workflow = data["workflow"]
        assert workflow["name"] == "workflow-v2"
        assert workflow["description"] == "Version 2"


class TestYamlFormat:
    """Tests for YAML formatting and readability."""

    def test_yaml_is_human_readable(self, tmp_path):
        """Generated YAML is clean and human-readable."""
        spec = WorkflowSpec(
            name="readable-workflow",
            description="Should be easy to read",
            nodes=[
                {
                    "id": "step1",
                    "name": "First Step",
                    "prompt": "Do something useful",
                    "outputs": ["result"],
                }
            ],
        )

        output_path = tmp_path / "workflow.yaml"
        generate_yaml(spec, output_path)

        # Read raw YAML text
        yaml_text = output_path.read_text()

        # Verify basic formatting
        assert "name:" in yaml_text
        assert "description:" in yaml_text
        assert "nodes:" in yaml_text
        # Should not have excessive quotes or ugly formatting
        assert yaml_text.count("'") + yaml_text.count('"') < 10  # Minimal quoting
