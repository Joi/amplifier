"""Tests for agent interface - CLI and API access to evidence system"""

import tempfile
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

from amplifier.bplan.agent_interface import AgentAPI
from amplifier.bplan.evidence_system import EvidenceStore as BaseEvidenceStore


class TestAgentAPI:
    """Test the Python API for agents"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.evidence_dir = Path(self.temp_dir)
        self.api = AgentAPI(evidence_dir=self.evidence_dir)

    def test_api_initialization(self):
        """Test API initializes correctly"""
        assert self.api.evidence_dir == self.evidence_dir
        assert self.api.evidence_store is not None
        assert self.api.validator is not None
        assert self.api.enforcer is not None

    def test_check_evidence_exists(self):
        """Test checking for existing evidence"""
        # Add evidence using the base store method
        evidence = self.api.evidence_store.add_evidence(
            type="test_output",
            content={"text": "All tests passed: 10/10", "metadata": {"passed": 10}},
            validator_id="pytest",
        )

        # Check it exists using the returned evidence ID
        result = self.api.check_evidence(evidence.id)
        assert result["exists"] is True
        assert result["valid"] is True
        assert "test_output" in result["details"]

    def test_check_evidence_not_exists(self):
        """Test checking for non-existent evidence"""
        result = self.api.check_evidence("fake_id")
        assert result["exists"] is False
        assert result["valid"] is False
        assert "not found" in result["details"]

    def test_validate_todo_completion_with_evidence(self):
        """Test validating todo with valid evidence"""
        # Add evidence using the base store method
        evidence = self.api.evidence_store.add_evidence(
            type="test_output",
            content={"text": "Feature implementation: all tests passed", "metadata": {}},
            validator_id="pytest",
        )

        # Validate todo
        result = self.api.validate_todo_completion(
            content="Implement feature",
            evidence_ids=[evidence.id],
            requires_evidence=True,
        )
        assert result["can_complete"] is True
        assert "validated successfully" in result["reason"]

    def test_validate_todo_completion_without_evidence(self):
        """Test validating todo without required evidence"""
        result = self.api.validate_todo_completion(
            content="Implement feature",
            evidence_ids=[],
            requires_evidence=True,
        )
        assert result["can_complete"] is False
        assert "No evidence provided" in result["reason"]

    def test_validate_todo_completion_no_evidence_required(self):
        """Test validating todo that doesn't require evidence"""
        result = self.api.validate_todo_completion(
            content="Update documentation",
            evidence_ids=[],
            requires_evidence=False,
        )
        assert result["can_complete"] is True

    def test_validate_code_with_mock_orchestrator(self):
        """Test code validation with mocked orchestrator"""
        with patch("amplifier.bplan.agent_interface.WorkflowOrchestrator") as mock_orch:
            # Mock the workflow result
            mock_result = Mock()
            mock_result.passed = True
            mock_result.evidence = Mock()
            mock_result.evidence.id = "code_001"
            mock_result.details = "Code validated"
            mock_result.cheating_detected = False

            mock_instance = Mock()
            mock_instance.execute_workflow.return_value = mock_result
            mock_orch.return_value = mock_instance

            # Test validation
            result = self.api.validate_code("Implement function X")

            assert result["passed"] is True
            assert result["evidence_id"] == "code_001"
            assert result["cheating_detected"] is False

    def test_validate_code_failure(self):
        """Test code validation failure"""
        with patch("amplifier.bplan.agent_interface.WorkflowOrchestrator") as mock_orch:
            # Mock orchestrator to raise exception
            mock_instance = Mock()
            mock_instance.execute_workflow.side_effect = Exception("Validation failed")
            mock_orch.return_value = mock_instance

            result = self.api.validate_code("Implement function X")

            assert result["passed"] is False
            assert result["evidence_id"] is None
            assert "Validation failed" in result["message"]


class TestAgentAPIEdgeCases:
    """Test edge cases and error handling"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.evidence_dir = Path(self.temp_dir)
        self.api = AgentAPI(evidence_dir=self.evidence_dir)

    def test_validate_todo_with_weak_evidence(self):
        """Test that weak evidence is rejected"""
        # Add weak evidence using the base store method
        evidence = self.api.evidence_store.add_evidence(
            type="test_output",
            content={"text": "TODO: Add test results", "metadata": {}},
            validator_id="fake",
        )

        result = self.api.validate_todo_completion(
            content="Complete task",
            evidence_ids=[evidence.id],
            requires_evidence=True,
        )
        assert result["can_complete"] is False
        assert "placeholder" in result["reason"].lower() or "weak" in result["reason"].lower()

    def test_validate_todo_with_mismatched_evidence(self):
        """Test that mismatched evidence is rejected"""
        # Add evidence about feature A using the base store method
        evidence = self.api.evidence_store.add_evidence(
            type="test_output",
            content={"text": "Tests passed for feature A module", "metadata": {}},
            validator_id="pytest",
        )

        # Try to use it for feature B
        result = self.api.validate_todo_completion(
            content="Complete feature B module",
            evidence_ids=[evidence.id],
            requires_evidence=True,
        )
        assert result["can_complete"] is False
        assert "mismatch" in result["reason"].lower()

    def test_check_evidence_with_unavailable_store(self):
        """Test checking evidence when store is unavailable"""
        # Create API with non-existent directory that can't be created
        with patch.object(BaseEvidenceStore, "__init__") as mock_init:
            mock_init.side_effect = PermissionError("Cannot create directory")

            # This should handle the error gracefully
            try:
                api = AgentAPI(evidence_dir=Path("/nonexistent/path"))
                result = api.check_evidence("test_id")
                # Should return "not found" even if store unavailable
                assert result["exists"] is False
            except PermissionError:
                # Also acceptable if it propagates
                pass


class TestAgentAPIIntegration:
    """Integration tests with real evidence store"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.evidence_dir = Path(self.temp_dir)
        self.api = AgentAPI(evidence_dir=self.evidence_dir)

    def test_full_todo_workflow(self):
        """Test complete todo validation workflow"""
        # 1. Add evidence using the base store method
        evidence = self.api.evidence_store.add_evidence(
            type="test_output",
            content={
                "text": "Workflow test: all 20 tests passed successfully",
                "metadata": {"tests": 20, "passed": 20},
            },
            validator_id="pytest",
        )

        # 2. Check evidence exists
        check_result = self.api.check_evidence(evidence.id)
        assert check_result["exists"] is True

        # 3. Validate todo can complete
        validate_result = self.api.validate_todo_completion(
            content="Complete workflow test",
            evidence_ids=[evidence.id],
            requires_evidence=True,
        )
        assert validate_result["can_complete"] is True

    def test_multiple_evidence_validation(self):
        """Test validation with multiple pieces of evidence"""
        # Store multiple evidence types using add_evidence
        test_evidence = self.api.evidence_store.add_evidence(
            type="test_output",
            content={"text": "Tests passed: 30/30", "metadata": {}},
            validator_id="pytest",
        )

        review_evidence = self.api.evidence_store.add_evidence(
            type="design_review",
            content={"text": "Design review approved by architect", "metadata": {}},
            validator_id="architect",
        )

        # Validate with both
        result = self.api.validate_todo_completion(
            content="Complete feature with tests and review",
            evidence_ids=[test_evidence.id, review_evidence.id],
            requires_evidence=True,
        )
        assert result["can_complete"] is True
