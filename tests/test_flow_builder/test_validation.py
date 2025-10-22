"""
Tests for workflow validation module.

Following TEST-FIRST discipline: These tests define the contract (studs)
for the validation module before implementation.
"""

from pathlib import Path

import pytest

from amplifier.flow_builder.validation import WorkflowSpec
from amplifier.flow_builder.validation import validate_workflow


class TestWorkflowValidation:
    """Tests for workflow validation using DotRunner's validate()."""

    def test_validate_uses_dotrunner(self, tmp_path):
        """validate_workflow() uses DotRunner's Workflow.validate()."""
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

        errors = validate_workflow(spec)

        # Valid workflow should have no errors
        assert errors == []

    def test_validate_catches_empty_nodes(self):
        """validate_workflow() catches workflows with no nodes."""
        spec = WorkflowSpec(name="empty-workflow", description="No nodes", nodes=[])

        errors = validate_workflow(spec)

        assert len(errors) > 0
        assert any("at least one node" in err.lower() for err in errors)

    def test_validate_catches_duplicate_node_ids(self):
        """validate_workflow() catches duplicate node IDs."""
        spec = WorkflowSpec(
            name="dup-workflow",
            description="Duplicate IDs",
            nodes=[
                {"id": "step1", "name": "First", "prompt": "Do A"},
                {"id": "step1", "name": "Second", "prompt": "Do B"},  # Duplicate ID
            ],
        )

        errors = validate_workflow(spec)

        assert len(errors) > 0
        assert any("duplicate" in err.lower() for err in errors)

    def test_validate_catches_invalid_next_reference(self):
        """validate_workflow() catches next references to nonexistent nodes."""
        spec = WorkflowSpec(
            name="bad-ref-workflow",
            description="Invalid reference",
            nodes=[
                {
                    "id": "step1",
                    "name": "First",
                    "prompt": "Do A",
                    "next": "nonexistent",  # Invalid reference
                }
            ],
        )

        errors = validate_workflow(spec)

        assert len(errors) > 0
        assert any("nonexistent" in err.lower() for err in errors)

    def test_validate_catches_circular_dependencies(self):
        """validate_workflow() detects circular dependencies."""
        spec = WorkflowSpec(
            name="circular-workflow",
            description="Circular deps",
            nodes=[
                {"id": "step1", "name": "First", "prompt": "Do A", "next": "step2"},
                {"id": "step2", "name": "Second", "prompt": "Do B", "next": "step1"},  # Circular
            ],
        )

        errors = validate_workflow(spec)

        assert len(errors) > 0
        assert any("circular" in err.lower() or "cycle" in err.lower() for err in errors)

    def test_validate_accepts_valid_linear_workflow(self):
        """validate_workflow() accepts valid linear workflows."""
        spec = WorkflowSpec(
            name="linear-workflow",
            description="Valid linear",
            nodes=[
                {"id": "step1", "name": "First", "prompt": "Do A", "next": "step2"},
                {"id": "step2", "name": "Second", "prompt": "Do B", "next": "step3"},
                {"id": "step3", "name": "Third", "prompt": "Do C"},
            ],
        )

        errors = validate_workflow(spec)

        assert errors == []

    def test_validate_accepts_conditional_routing(self):
        """validate_workflow() accepts valid conditional routing."""
        spec = WorkflowSpec(
            name="conditional-workflow",
            description="Valid conditional",
            nodes=[
                {
                    "id": "step1",
                    "name": "First",
                    "prompt": "Do A",
                    "outputs": ["status"],
                    "next": {"success": "step2", "failure": "step3", "default": "step2"},
                },
                {"id": "step2", "name": "Success path", "prompt": "Handle success"},
                {"id": "step3", "name": "Failure path", "prompt": "Handle failure"},
            ],
        )

        errors = validate_workflow(spec)

        assert errors == []


class TestWorkflowSpecDataClass:
    """Tests for WorkflowSpec data structure."""

    def test_workflow_spec_has_required_fields(self):
        """WorkflowSpec has name, description, and nodes fields."""
        spec = WorkflowSpec(
            name="test-workflow", description="Test description", nodes=[{"id": "step1", "name": "Step", "prompt": "Do"}]
        )

        assert spec.name == "test-workflow"
        assert spec.description == "Test description"
        assert len(spec.nodes) == 1

    def test_workflow_spec_has_optional_version(self):
        """WorkflowSpec has optional version field."""
        spec = WorkflowSpec(
            name="test", description="Test", nodes=[{"id": "s1", "name": "S", "prompt": "Do"}], version="2.0.0"
        )

        assert spec.version == "2.0.0"

    def test_workflow_spec_has_optional_context(self):
        """WorkflowSpec has optional context field."""
        spec = WorkflowSpec(
            name="test",
            description="Test",
            nodes=[{"id": "s1", "name": "S", "prompt": "Do"}],
            context={"project": "myapp"},
        )

        assert spec.context == {"project": "myapp"}
