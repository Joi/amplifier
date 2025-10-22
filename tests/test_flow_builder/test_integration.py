"""
End-to-end integration tests for Phase 1.

Tests the entire flow: CLI → YAML generation → DotRunner validation
"""

import subprocess
from pathlib import Path

import yaml

from ai_working.dotrunner.workflow import Workflow


class TestPhase1Integration:
    """End-to-end tests for Phase 1 functionality."""

    def test_end_to_end_workflow_creation(self, tmp_path):
        """Complete flow: build spec → validate → generate YAML → load with DotRunner."""
        from amplifier.flow_builder.generator import generate_yaml
        from amplifier.flow_builder.interrogation import build_minimal_workflow
        from amplifier.flow_builder.validation import validate_workflow

        # Step 1: Build minimal workflow
        spec = build_minimal_workflow(
            name="test-workflow",
            description="End-to-end test workflow",
            node_name="Process Data",
            node_prompt="Process the input data and generate results",
            agent="zen-architect",
            agent_mode="ANALYZE",
            outputs=["results", "status"],
        )

        # Step 2: Validate with DotRunner
        errors = validate_workflow(spec)
        assert errors == []

        # Step 3: Generate YAML
        output_path = tmp_path / "test-workflow.yaml"
        generate_yaml(spec, output_path)

        assert output_path.exists()

        # Step 4: Load with DotRunner
        workflow = Workflow.from_yaml(output_path)

        assert workflow.name == "test-workflow"
        assert workflow.description == "End-to-end test workflow"
        assert len(workflow.nodes) == 1

        node = workflow.nodes[0]
        assert node.name == "Process Data"
        assert node.prompt == "Process the input data and generate results"
        assert node.agent == "zen-architect"
        assert node.agent_mode == "ANALYZE"
        assert node.outputs == ["results", "status"]

    def test_generated_yaml_is_valid_dotrunner_format(self, tmp_path):
        """Generated YAML can be loaded by DotRunner."""
        from amplifier.flow_builder.generator import generate_yaml
        from amplifier.flow_builder.interrogation import build_minimal_workflow

        spec = build_minimal_workflow(
            name="simple-task",
            description="A simple task",
            node_name="Execute Task",
            node_prompt="Execute the task",
        )

        output_path = tmp_path / "simple-task.yaml"
        generate_yaml(spec, output_path)

        # Load with DotRunner (should not raise)
        workflow = Workflow.from_yaml(output_path)

        # Validate with DotRunner
        errors = workflow.validate()
        assert errors == []

    def test_all_modules_work_together(self, tmp_path):
        """All Phase 1 modules integrate correctly."""
        from amplifier.flow_builder.discovery import scan_agents
        from amplifier.flow_builder.generator import generate_yaml
        from amplifier.flow_builder.interrogation import build_minimal_workflow
        from amplifier.flow_builder.validation import validate_workflow

        # Create fake agents directory
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        agent_file = agents_dir / "test-agent.toml"
        agent_file.write_text('description = "Test agent"')

        # Scan agents
        agents = scan_agents(agents_dir)
        assert len(agents) == 1
        assert agents[0].name == "test-agent"

        # Build workflow using discovered agent
        spec = build_minimal_workflow(
            name="agent-workflow",
            description="Workflow using discovered agent",
            node_name="Task",
            node_prompt="Do task",
            agent=agents[0].name,
        )

        # Validate
        errors = validate_workflow(spec)
        assert errors == []

        # Generate YAML
        output_path = tmp_path / "agent-workflow.yaml"
        generate_yaml(spec, output_path)

        # Load with DotRunner
        workflow = Workflow.from_yaml(output_path)
        assert workflow.nodes[0].agent == "test-agent"

    def test_validation_catches_real_errors(self):
        """Validation correctly catches workflow errors using DotRunner."""
        from amplifier.flow_builder.validation import WorkflowSpec
        from amplifier.flow_builder.validation import validate_workflow

        # Create invalid workflow (empty nodes)
        spec = WorkflowSpec(name="invalid", description="Invalid workflow", nodes=[])

        errors = validate_workflow(spec)

        # Should have validation errors
        assert len(errors) > 0
        assert any("node" in err.lower() for err in errors)

    def test_yaml_format_matches_dotrunner_examples(self, tmp_path):
        """Generated YAML format matches DotRunner's expected format."""
        from amplifier.flow_builder.generator import generate_yaml
        from amplifier.flow_builder.interrogation import build_minimal_workflow

        spec = build_minimal_workflow(
            name="example-workflow",
            description="Example workflow",
            node_name="Example Node",
            node_prompt="Do example task",
            outputs=["result"],
        )

        output_path = tmp_path / "example.yaml"
        generate_yaml(spec, output_path)

        # Load and check structure
        with open(output_path) as f:
            data = yaml.safe_load(f)

        # Check required top-level fields (DotRunner format)
        assert "workflow" in data
        assert "nodes" in data

        # Check workflow info
        workflow = data["workflow"]
        assert "name" in workflow
        assert "description" in workflow
        assert "version" in workflow

        # Check node structure
        assert len(data["nodes"]) == 1
        node = data["nodes"][0]

        assert "id" in node
        assert "name" in node
        assert "prompt" in node
        assert "outputs" in node

    def test_full_coverage_of_phase_1_modules(self):
        """Verify all Phase 1 modules are present and importable."""
        # This test ensures all modules exist and can be imported
        from amplifier.flow_builder import cli
        from amplifier.flow_builder import discovery
        from amplifier.flow_builder import generator
        from amplifier.flow_builder import interrogation
        from amplifier.flow_builder import validation

        # Verify key functions exist
        assert hasattr(discovery, "scan_agents")
        assert hasattr(validation, "validate_workflow")
        assert hasattr(generator, "generate_yaml")
        assert hasattr(interrogation, "build_minimal_workflow")
        assert hasattr(cli, "cli")
