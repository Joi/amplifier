"""
Test workflow and node data models.

Tests FIRST (RED phase) - These tests will fail until implementation is complete.
"""

from dataclasses import asdict
from pathlib import Path

import pytest

from ai_working.dotrunner.workflow import Node

# Import will fail until we create workflow.py
from ai_working.dotrunner.workflow import Workflow


class TestNodeDataclass:
    """Test Node dataclass creation and validation"""

    def test_node_minimal_creation(self):
        """Test creating node with only required fields"""
        node = Node(id="test-node", name="Test Node", prompt="Test prompt")

        assert node.id == "test-node"
        assert node.name == "Test Node"
        assert node.prompt == "Test prompt"
        assert node.agent is None  # Default (None means use generic AI)
        assert node.agent_mode is None  # Default
        assert node.outputs == []  # Default
        assert node.next is None  # Default
        assert node.retry_on_failure == 1  # Default
        assert node.type is None  # Default

    def test_node_full_creation(self):
        """Test creating node with all fields"""
        node = Node(
            id="full-node",
            name="Full Node",
            prompt="Full prompt",
            agent="zen-architect",
            outputs=["result1", "result2"],
            next="next-node",
            retry_on_failure=3,
            type="terminal",
        )

        assert node.id == "full-node"
        assert node.agent == "zen-architect"
        assert node.outputs == ["result1", "result2"]
        assert node.next == "next-node"
        assert node.retry_on_failure == 3
        assert node.type == "terminal"

    def test_node_conditional_next(self):
        """Test node with conditional next"""
        node = Node(
            id="conditional-node",
            name="Conditional",
            prompt="Check condition",
            next=[{"when": "{result} == true", "goto": "node-a"}, {"default": "node-b"}],
        )

        assert isinstance(node.next, list)
        assert len(node.next) == 2
        assert node.next[0]["when"] == "{result} == true"
        assert node.next[1]["default"] == "node-b"

    def test_node_to_dict(self):
        """Test converting node to dictionary"""
        node = Node(id="test", name="Test", prompt="Prompt", outputs=["out1"])

        node_dict = asdict(node)
        assert node_dict["id"] == "test"
        assert node_dict["name"] == "Test"
        assert node_dict["prompt"] == "Prompt"
        assert node_dict["outputs"] == ["out1"]


class TestWorkflowDataclass:
    """Test Workflow dataclass creation and validation"""

    def test_workflow_minimal_creation(self):
        """Test creating workflow with only required fields"""
        nodes = [Node(id="node1", name="Node 1", prompt="Prompt 1"), Node(id="node2", name="Node 2", prompt="Prompt 2")]

        workflow = Workflow(name="test-workflow", description="Test workflow", nodes=nodes)

        assert workflow.name == "test-workflow"
        assert workflow.description == "Test workflow"
        assert len(workflow.nodes) == 2
        assert workflow.context == {}  # Default empty dict

    def test_workflow_with_context(self):
        """Test creating workflow with global context"""
        nodes = [Node(id="node1", name="Node 1", prompt="Prompt 1")]

        workflow = Workflow(
            name="context-workflow",
            description="With context",
            nodes=nodes,
            context={"key1": "value1", "key2": "value2"},
        )

        assert workflow.context == {"key1": "value1", "key2": "value2"}

    def test_workflow_to_dict(self):
        """Test converting workflow to dictionary"""
        nodes = [Node(id="node1", name="Node 1", prompt="Prompt 1")]
        workflow = Workflow(name="test", description="Test", nodes=nodes)

        workflow_dict = asdict(workflow)
        assert workflow_dict["name"] == "test"
        assert workflow_dict["description"] == "Test"
        assert len(workflow_dict["nodes"]) == 1
        assert workflow_dict["nodes"][0]["id"] == "node1"


class TestWorkflowGetNode:
    """Test workflow node lookup functionality"""

    def test_get_node_by_id_found(self):
        """Test finding node by ID"""
        nodes = [
            Node(id="node1", name="Node 1", prompt="Prompt 1"),
            Node(id="node2", name="Node 2", prompt="Prompt 2"),
            Node(id="node3", name="Node 3", prompt="Prompt 3"),
        ]

        workflow = Workflow(name="test", description="Test", nodes=nodes)

        node = workflow.get_node("node2")
        assert node is not None
        assert node.id == "node2"
        assert node.name == "Node 2"

    def test_get_node_by_id_not_found(self):
        """Test looking up non-existent node"""
        nodes = [Node(id="node1", name="Node 1", prompt="Prompt 1")]

        workflow = Workflow(name="test", description="Test", nodes=nodes)

        node = workflow.get_node("nonexistent")
        assert node is None

    def test_get_first_node(self):
        """Test getting first node (for workflow execution start)"""
        nodes = [Node(id="first", name="First", prompt="First"), Node(id="second", name="Second", prompt="Second")]

        workflow = Workflow(name="test", description="Test", nodes=nodes)

        first = workflow.nodes[0]
        assert first.id == "first"


class TestWorkflowValidation:
    """Test workflow validation logic"""

    def test_validate_empty_workflow(self):
        """Test validation catches empty workflow"""
        workflow = Workflow(name="empty", description="Empty workflow", nodes=[])

        errors = workflow.validate()
        assert len(errors) > 0
        assert "at least one node" in errors[0]

    def test_validate_duplicate_node_ids(self):
        """Test validation catches duplicate node IDs"""
        nodes = [
            Node(id="node1", name="Node 1", prompt="Prompt 1"),
            Node(id="node1", name="Node 1 Duplicate", prompt="Prompt 2"),
        ]

        workflow = Workflow(name="test", description="Test", nodes=nodes)

        errors = workflow.validate()
        assert len(errors) > 0
        assert "duplicate" in errors[0].lower()

    def test_validate_invalid_node_reference(self):
        """Test validation catches invalid node references in next"""
        nodes = [
            Node(id="node1", name="Node 1", prompt="Prompt 1", next="nonexistent"),
            Node(id="node2", name="Node 2", prompt="Prompt 2"),
        ]

        workflow = Workflow(name="test", description="Test", nodes=nodes)

        errors = workflow.validate()
        assert len(errors) > 0
        assert "nonexistent" in errors[0]

    def test_validate_circular_dependency_simple(self):
        """Test validation catches simple circular dependency"""
        nodes = [
            Node(id="node1", name="Node 1", prompt="Prompt 1", next="node2"),
            Node(id="node2", name="Node 2", prompt="Prompt 2", next="node1"),
        ]

        workflow = Workflow(name="test", description="Test", nodes=nodes)

        errors = workflow.validate()
        assert len(errors) > 0
        assert "circular" in errors[0].lower()

    def test_validate_valid_workflow(self):
        """Test validation passes for valid workflow"""
        nodes = [
            Node(id="node1", name="Node 1", prompt="Prompt 1", next="node2"),
            Node(id="node2", name="Node 2", prompt="Prompt 2", type="terminal"),
        ]

        workflow = Workflow(name="test", description="Test", nodes=nodes)

        # Should not raise
        workflow.validate()


class TestWorkflowFromYAML:
    """Test loading workflow from YAML file"""

    def test_from_yaml_simple_linear(self, tmp_path):
        """Test loading simple linear workflow from YAML"""
        yaml_content = """workflow:
  name: "simple-test"
  description: "Simple test workflow"

nodes:
  - id: "node1"
    name: "First Node"
    prompt: "Do something"

  - id: "node2"
    name: "Second Node"
    prompt: "Do something else"
"""
        yaml_file = tmp_path / "test_workflow.yaml"
        yaml_file.write_text(yaml_content)

        workflow = Workflow.from_yaml(yaml_file)

        assert workflow.name == "simple-test"
        assert workflow.description == "Simple test workflow"
        assert len(workflow.nodes) == 2
        assert workflow.nodes[0].id == "node1"
        assert workflow.nodes[1].id == "node2"

    def test_from_yaml_with_context(self, tmp_path):
        """Test loading workflow with global context"""
        yaml_content = """workflow:
  name: "context-test"
  description: "With context"
  context:
    key1: "value1"
    key2: "value2"

nodes:
  - id: "node1"
    name: "Node"
    prompt: "Use {key1}"
"""
        yaml_file = tmp_path / "test_workflow.yaml"
        yaml_file.write_text(yaml_content)

        workflow = Workflow.from_yaml(yaml_file)

        assert workflow.context["key1"] == "value1"
        assert workflow.context["key2"] == "value2"

    def test_from_yaml_invalid_file(self):
        """Test loading from nonexistent file"""
        with pytest.raises(FileNotFoundError):
            Workflow.from_yaml(Path("/nonexistent/file.yaml"))

    def test_from_yaml_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML syntax"""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("invalid: yaml: syntax: [")

        with pytest.raises(ValueError, match="Invalid YAML"):
            Workflow.from_yaml(yaml_file)

    def test_from_yaml_missing_required_fields(self, tmp_path):
        """Test loading YAML with missing required fields"""
        yaml_content = """workflow:
  name: "incomplete"
  # Missing description and nodes
"""
        yaml_file = tmp_path / "incomplete.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="Missing required field"):
            Workflow.from_yaml(yaml_file)
