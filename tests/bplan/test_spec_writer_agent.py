"""
Tests for SpecWriterAgent - artifact creation and test generation.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from amplifier.bplan.evidence_system import EvidenceStore
from amplifier.bplan.three_agent_workflow import SpecWriterAgent


class TestSpecWriterAgent:
    """Test the spec writer agent that creates test and golden artifacts."""

    def test_create_artifacts_basic_task(self):
        """Test creating artifacts for a simple task."""
        agent = SpecWriterAgent()
        evidence_store = MagicMock(spec=EvidenceStore)

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            agent.workspace = workspace

            task = "Create a function that adds two numbers"

            # Mock LLM response for test generation
            test_content = '''"""
Test for add function.
"""

def test_add():
    """Test addition of two numbers."""
    from implementation import add

    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
'''

            golden_content = '''"""
Golden reference implementation.
"""

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''

            with patch.object(agent, "_generate_test", return_value=test_content):
                with patch.object(agent, "_generate_golden", return_value=golden_content):
                    test_path, golden_path = agent.create_artifacts(task, evidence_store)

            # Verify paths exist
            assert test_path.exists()
            assert golden_path.exists()

            # Verify content
            assert "def test_add():" in test_path.read_text()
            assert "def add(a: int, b: int)" in golden_path.read_text()

            # Verify paths are in workspace
            assert test_path.parent == workspace
            assert golden_path.parent == workspace

            # Verify evidence was recorded
            evidence_store.add_evidence.assert_called()

    def test_create_artifacts_complex_task(self):
        """Test creating artifacts for a complex task with multiple requirements."""
        agent = SpecWriterAgent()
        evidence_store = MagicMock(spec=EvidenceStore)

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            agent.workspace = workspace

            task = """Create a Calculator class with the following methods:
            - add(a, b): returns sum
            - subtract(a, b): returns difference
            - multiply(a, b): returns product
            - divide(a, b): returns quotient, raises ValueError if b is 0
            """

            test_content = '''"""
Test for Calculator class.
"""
import pytest

def test_calculator():
    """Test Calculator operations."""
    from implementation import Calculator

    calc = Calculator()

    # Test addition
    assert calc.add(5, 3) == 8

    # Test subtraction
    assert calc.subtract(10, 4) == 6

    # Test multiplication
    assert calc.multiply(3, 7) == 21

    # Test division
    assert calc.divide(10, 2) == 5.0

    # Test division by zero
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        calc.divide(10, 0)
'''

            golden_content = '''"""
Golden Calculator implementation.
"""

class Calculator:
    """Calculator with basic operations."""

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
'''

            with patch.object(agent, "_generate_test", return_value=test_content):
                with patch.object(agent, "_generate_golden", return_value=golden_content):
                    test_path, golden_path = agent.create_artifacts(task, evidence_store)

            # Verify complex test structure
            test_text = test_path.read_text()
            assert "class Calculator" in golden_path.read_text()
            assert "calc.add(" in test_text
            assert "calc.divide(" in test_text
            assert "pytest.raises(ValueError" in test_text

    def test_create_artifacts_with_evidence_tracking(self):
        """Test that artifacts are properly tracked in evidence store."""
        agent = SpecWriterAgent()
        evidence_store = MagicMock(spec=EvidenceStore)

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            agent.workspace = workspace

            task = "Create a simple function"

            with patch.object(agent, "_generate_test", return_value="def test(): pass"):
                with patch.object(agent, "_generate_golden", return_value="def func(): pass"):
                    test_path, golden_path = agent.create_artifacts(task, evidence_store)

            # Verify evidence calls
            calls = evidence_store.add_evidence.call_args_list
            assert len(calls) >= 2  # At least test and golden artifacts

            # Check evidence types
            for call in calls:
                if len(call) > 1 and call[1].get("type") == "artifact":
                    content = call[1].get("content", {})
                    artifact_type = content.get("artifact_type", "")
                    assert "test" in artifact_type or "golden" in artifact_type

    def test_workspace_isolation(self):
        """Test that agent creates isolated workspace for artifacts."""
        agent = SpecWriterAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            agent.workspace = workspace

            # Workspace should be used for all artifacts
            assert agent.workspace == workspace

            # Create subdirectories for organization
            test_dir = workspace / "tests"
            golden_dir = workspace / "golden"
            test_dir.mkdir(parents=True)
            golden_dir.mkdir(parents=True)

            agent.test_dir = test_dir
            agent.golden_dir = golden_dir

            assert agent.test_dir.exists()
            assert agent.golden_dir.exists()
            assert agent.test_dir.parent == workspace
            assert agent.golden_dir.parent == workspace

    def test_artifact_naming_convention(self):
        """Test that artifacts follow naming conventions."""
        agent = SpecWriterAgent()
        evidence_store = MagicMock(spec=EvidenceStore)

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            agent.workspace = workspace

            task = "Create array utilities"

            with patch.object(agent, "_generate_test", return_value="def test(): pass"):
                with patch.object(agent, "_generate_golden", return_value="def func(): pass"):
                    test_path, golden_path = agent.create_artifacts(task, evidence_store)

            # Test file should start with test_
            assert test_path.name.startswith("test_")
            assert test_path.suffix == ".py"

            # Golden file should indicate it's golden/reference
            assert "golden" in golden_path.name or "reference" in golden_path.name
            assert golden_path.suffix == ".py"

    def test_handle_generation_failure(self):
        """Test handling of LLM generation failures."""
        agent = SpecWriterAgent()
        evidence_store = MagicMock(spec=EvidenceStore)

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            agent.workspace = workspace

            task = "Create something"

            # Mock generation failure
            with patch.object(agent, "_generate_test", side_effect=Exception("LLM failed")):
                with pytest.raises(Exception, match="LLM failed"):
                    agent.create_artifacts(task, evidence_store)

            # Verify no partial artifacts left behind
            assert len(list(workspace.glob("*.py"))) == 0
