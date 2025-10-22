"""
Tests for routing logic (Phase 2.2).

Following TEST-FIRST discipline.
Phase 2: Support conditional routing in workflows
"""

from amplifier.flow_builder.interrogation import set_conditional_routing
from amplifier.flow_builder.validation import WorkflowSpec


class TestConditionalRouting:
    """Tests for conditional routing support."""

    def test_set_conditional_routing_updates_node(self):
        """set_conditional_routing() updates a node's next field with routing dict."""
        spec = WorkflowSpec(
            name="test",
            description="Test",
            nodes=[
                {"id": "router", "name": "Router", "prompt": "Route"},
                {"id": "path-a", "name": "Path A", "prompt": "Handle A"},
                {"id": "path-b", "name": "Path B", "prompt": "Handle B"},
            ],
        )

        spec = set_conditional_routing(
            spec=spec,
            node_id="router",
            routing={
                "success": "path-a",
                "failure": "path-b",
                "default": "path-a",
            },
        )

        router_node = spec.nodes[0]
        assert isinstance(router_node["next"], dict)
        assert router_node["next"]["success"] == "path-a"
        assert router_node["next"]["failure"] == "path-b"
        assert router_node["next"]["default"] == "path-a"

    def test_set_conditional_routing_finds_node_by_id(self):
        """set_conditional_routing() finds correct node by ID."""
        spec = WorkflowSpec(
            name="test",
            description="Test",
            nodes=[
                {"id": "step1", "name": "Step 1", "prompt": "Do 1"},
                {"id": "router", "name": "Router", "prompt": "Route"},
                {"id": "step3", "name": "Step 3", "prompt": "Do 3"},
            ],
        )

        spec = set_conditional_routing(
            spec=spec,
            node_id="router",
            routing={"default": "step3"},
        )

        # Only middle node should be updated
        assert "next" not in spec.nodes[0] or isinstance(spec.nodes[0].get("next"), str)
        assert isinstance(spec.nodes[1]["next"], dict)

    def test_set_conditional_routing_validates_target_nodes_exist(self):
        """set_conditional_routing() validates that target nodes exist."""
        spec = WorkflowSpec(
            name="test",
            description="Test",
            nodes=[
                {"id": "router", "name": "Router", "prompt": "Route"},
                {"id": "existing", "name": "Exists", "prompt": "Handle"},
            ],
        )

        # Should raise or return error if target doesn't exist
        try:
            spec = set_conditional_routing(
                spec=spec,
                node_id="router",
                routing={
                    "success": "nonexistent",
                    "default": "existing",
                },
            )
            # If no exception, validation should fail
            from amplifier.flow_builder.validation import validate_workflow

            errors = validate_workflow(spec)
            assert len(errors) > 0
            assert any("nonexistent" in err.lower() for err in errors)
        except ValueError as e:
            # Acceptable: function validates immediately
            assert "nonexistent" in str(e).lower()

    def test_conditional_routing_workflow_validates(self):
        """Workflows with conditional routing pass DotRunner validation."""
        spec = WorkflowSpec(
            name="conditional-test",
            description="Test conditional routing",
            nodes=[
                {
                    "id": "validator",
                    "name": "Validate Input",
                    "prompt": "Check if input is valid",
                    "outputs": ["is_valid"],
                    "next": {
                        "success": "process",
                        "failure": "error-handler",
                        "default": "process",
                    },
                },
                {
                    "id": "process",
                    "name": "Process Data",
                    "prompt": "Process the validated data",
                },
                {
                    "id": "error-handler",
                    "name": "Handle Error",
                    "prompt": "Handle validation failure",
                },
            ],
        )

        from amplifier.flow_builder.validation import validate_workflow

        errors = validate_workflow(spec)
        assert errors == []
