"""
Tests for multi-node interrogation (Phase 2.1).

Following TEST-FIRST discipline.
Phase 2: Still NO AI - just collect 2-5 nodes via input()
"""

from amplifier.flow_builder.interrogation import interrogate_multi_node


class TestMultiNodeInterrogation:
    """Tests for collecting multiple nodes."""

    def test_interrogate_multi_node_collects_multiple_nodes(self, monkeypatch):
        """interrogate_multi_node() collects 2-5 nodes from user."""
        inputs = [
            "my-workflow",  # name
            "Multi-step workflow",  # description
            "3",  # number of nodes
            "Step 1",  # node 1 name
            "Do first thing",  # node 1 prompt
            "",  # node 1 agent (skip)
            "",  # node 1 outputs (skip)
            "Step 2",  # node 2 name
            "Do second thing",  # node 2 prompt
            "",  # agent
            "data",  # outputs
            "Step 3",  # node 3 name
            "Do third thing",  # node 3 prompt
            "",  # agent
            "",  # outputs
        ]
        monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

        spec = interrogate_multi_node()

        assert spec.name == "my-workflow"
        assert spec.description == "Multi-step workflow"
        assert len(spec.nodes) == 3
        assert spec.nodes[0]["name"] == "Step 1"
        assert spec.nodes[1]["name"] == "Step 2"
        assert spec.nodes[2]["name"] == "Step 3"

    def test_interrogate_validates_node_count(self, monkeypatch):
        """interrogate_multi_node() validates node count is 1-5."""
        inputs = [
            "test",
            "Test",
            "10",  # invalid (too many)
            "3",  # valid
            "Node 1", "Prompt 1", "", "",
            "Node 2", "Prompt 2", "", "",
            "Node 3", "Prompt 3", "", "",
        ]
        monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

        spec = interrogate_multi_node()

        # Should have asked again and accepted valid count
        assert len(spec.nodes) == 3

    def test_interrogate_creates_linear_chain_by_default(self, monkeypatch):
        """interrogate_multi_node() links nodes linearly by default."""
        inputs = [
            "test",
            "Test",
            "3",
            "A", "Do A", "", "",
            "B", "Do B", "", "",
            "C", "Do C", "", "",
        ]
        monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

        spec = interrogate_multi_node()

        # Nodes should be chained: A → B → C
        assert spec.nodes[0]["next"] == "b"
        assert spec.nodes[1]["next"] == "c"
        assert spec.nodes[2].get("next") is None  # Last node

    def test_interrogate_parses_outputs(self, monkeypatch):
        """interrogate_multi_node() parses comma-separated outputs."""
        inputs = [
            "test",
            "Test",
            "2",
            "Step 1", "Prompt 1", "", "data, status",
            "Step 2", "Prompt 2", "", "",
        ]
        monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

        spec = interrogate_multi_node()

        assert spec.nodes[0]["outputs"] == ["data", "status"]

    def test_interrogate_handles_agent_selection(self, monkeypatch):
        """interrogate_multi_node() accepts agent names."""
        inputs = [
            "test",
            "Test",
            "2",
            "Step 1", "Prompt 1", "zen-architect", "",
            "Step 2", "Prompt 2", "", "",
        ]
        monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

        spec = interrogate_multi_node()

        assert spec.nodes[0].get("agent") == "zen-architect"
        assert spec.nodes[1].get("agent") is None
