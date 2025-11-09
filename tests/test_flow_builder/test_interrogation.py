"""
Tests for basic interrogation module.

Following TEST-FIRST discipline: These tests define the contract (studs)
for the interrogation module before implementation.

Phase 1 interrogation is SIMPLE - just helper functions, no AI.
"""

from amplifier.flow_builder.interrogation import build_minimal_workflow


class TestBuildMinimalWorkflow:
    """Tests for building minimal workflows from user input."""

    def test_build_minimal_workflow_creates_spec(self):
        """build_minimal_workflow() creates WorkflowSpec from basic inputs."""
        spec = build_minimal_workflow(
            name="test-workflow",
            description="Test workflow",
            node_name="First Step",
            node_prompt="Do something",
        )

        assert spec.name == "test-workflow"
        assert spec.description == "Test workflow"
        assert len(spec.nodes) == 1
        assert spec.nodes[0]["name"] == "First Step"
        assert spec.nodes[0]["prompt"] == "Do something"

    def test_build_minimal_workflow_generates_node_id(self):
        """build_minimal_workflow() generates node ID from name."""
        spec = build_minimal_workflow(
            name="test",
            description="Test",
            node_name="My Step Name",
            node_prompt="Prompt",
        )

        # Node ID should be slug of name
        assert spec.nodes[0]["id"] == "my-step-name"

    def test_build_minimal_workflow_sets_default_version(self):
        """build_minimal_workflow() sets version to 1.0.0 by default."""
        spec = build_minimal_workflow(
            name="test",
            description="Test",
            node_name="Step",
            node_prompt="Prompt",
        )

        assert spec.version == "1.0.0"

    def test_build_minimal_workflow_accepts_optional_agent(self):
        """build_minimal_workflow() accepts optional agent parameter."""
        spec = build_minimal_workflow(
            name="test",
            description="Test",
            node_name="Step",
            node_prompt="Prompt",
            agent="zen-architect",
        )

        assert spec.nodes[0].get("agent") == "zen-architect"

    def test_build_minimal_workflow_accepts_optional_agent_mode(self):
        """build_minimal_workflow() accepts optional agent_mode parameter."""
        spec = build_minimal_workflow(
            name="test",
            description="Test",
            node_name="Step",
            node_prompt="Prompt",
            agent_mode="ANALYZE",
        )

        assert spec.nodes[0].get("agent_mode") == "ANALYZE"

    def test_build_minimal_workflow_accepts_optional_outputs(self):
        """build_minimal_workflow() accepts optional outputs parameter."""
        spec = build_minimal_workflow(
            name="test",
            description="Test",
            node_name="Step",
            node_prompt="Prompt",
            outputs=["result", "status"],
        )

        assert spec.nodes[0].get("outputs") == ["result", "status"]

    def test_build_minimal_workflow_creates_valid_single_node(self):
        """build_minimal_workflow() creates valid single-node workflow."""
        spec = build_minimal_workflow(
            name="simple",
            description="Simple workflow",
            node_name="Only Step",
            node_prompt="Do the thing",
        )

        # Should have exactly one node
        assert len(spec.nodes) == 1

        # Node should have required fields
        node = spec.nodes[0]
        assert "id" in node
        assert "name" in node
        assert "prompt" in node

        # Should be valid (no next field for single node)
        assert node.get("next") is None


class TestNodeIdGeneration:
    """Tests for node ID generation from names."""

    def test_node_id_lowercases_name(self):
        """Node IDs are lowercase."""
        spec = build_minimal_workflow(
            name="test",
            description="Test",
            node_name="UPPERCASE NAME",
            node_prompt="Prompt",
        )

        assert spec.nodes[0]["id"] == "uppercase-name"

    def test_node_id_replaces_spaces_with_hyphens(self):
        """Node IDs replace spaces with hyphens."""
        spec = build_minimal_workflow(
            name="test",
            description="Test",
            node_name="Multi Word Name",
            node_prompt="Prompt",
        )

        assert spec.nodes[0]["id"] == "multi-word-name"

    def test_node_id_removes_special_characters(self):
        """Node IDs remove special characters."""
        spec = build_minimal_workflow(
            name="test",
            description="Test",
            node_name="Name with @#$% chars!",
            node_prompt="Prompt",
        )

        # Should only keep alphanumeric and hyphens
        assert spec.nodes[0]["id"] == "name-with-chars"

    def test_node_id_handles_multiple_spaces(self):
        """Node IDs collapse multiple spaces to single hyphen."""
        spec = build_minimal_workflow(
            name="test",
            description="Test",
            node_name="Name    with    spaces",
            node_prompt="Prompt",
        )

        assert spec.nodes[0]["id"] == "name-with-spaces"
