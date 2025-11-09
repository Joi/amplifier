"""Test TodoWrite evidence requirement on completion - RED phase tests"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from amplifier.bplan.todowrite_integration import BlockingEnforcer
from amplifier.bplan.todowrite_integration import CompletionValidator
from amplifier.bplan.todowrite_integration import Evidence
from amplifier.bplan.todowrite_integration import EvidenceRequiredTodo
from amplifier.bplan.todowrite_integration import EvidenceStore
from amplifier.bplan.todowrite_integration import EvidenceValidationError
from amplifier.bplan.todowrite_integration import TodoWithEvidence


class TestEvidenceRequiredTodo:
    """Test the EvidenceRequiredTodo dataclass"""

    def test_create_todo_without_evidence(self):
        """Test creating a todo that doesn't require evidence yet"""
        todo = EvidenceRequiredTodo(
            content="Implement feature X", status="pending", activeForm="Implementing feature X", evidence_ids=[]
        )
        assert todo.content == "Implement feature X"
        assert todo.status == "pending"
        assert todo.evidence_ids == []

    def test_create_todo_with_evidence_ids(self):
        """Test creating a todo with pre-attached evidence"""
        todo = EvidenceRequiredTodo(
            content="Fix bug Y",
            status="in_progress",
            activeForm="Fixing bug Y",
            evidence_ids=["test_123", "validation_456"],
        )
        assert len(todo.evidence_ids) == 2
        assert "test_123" in todo.evidence_ids

    def test_add_evidence_to_todo(self):
        """Test adding evidence IDs to an existing todo"""
        todo = EvidenceRequiredTodo(
            content="Refactor module Z", status="in_progress", activeForm="Refactoring module Z", evidence_ids=[]
        )
        todo.evidence_ids.append("golden_789")
        assert "golden_789" in todo.evidence_ids

    def test_todo_requires_evidence_for_completion(self):
        """Test that certain todos are marked as requiring evidence"""
        todo = EvidenceRequiredTodo(
            content="Run tests",
            status="in_progress",
            activeForm="Running tests",
            evidence_ids=[],
            requires_evidence=True,
        )
        assert todo.requires_evidence is True

    def test_todo_optional_evidence(self):
        """Test todos that don't require evidence"""
        todo = EvidenceRequiredTodo(
            content="Update documentation",
            status="in_progress",
            activeForm="Updating documentation",
            evidence_ids=[],
            requires_evidence=False,
        )
        assert todo.requires_evidence is False


class TestCompletionValidator:
    """Test the CompletionValidator class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.evidence_store = EvidenceStore(base_path=Path(self.temp_dir))
        self.validator = CompletionValidator(self.evidence_store)

    def test_validate_with_valid_evidence(self):
        """Test validation passes with valid evidence"""
        # Store real evidence
        evidence = Evidence(
            evidence_id="test_001",
            evidence_type="test_output",
            content="All tests passed: 10/10",
            timestamp=datetime.now(),
            validator_id="test_runner",
            metadata={"tests_passed": 10, "tests_failed": 0},
        )
        self.evidence_store.store_evidence(evidence)

        todo = EvidenceRequiredTodo(
            content="Run unit tests",
            status="in_progress",
            activeForm="Running unit tests",
            evidence_ids=["test_001"],
            requires_evidence=True,
        )

        assert self.validator.validate_completion(todo) is True

    def test_validate_without_evidence_fails(self):
        """Test validation fails when no evidence provided"""
        todo = EvidenceRequiredTodo(
            content="Run integration tests",
            status="in_progress",
            activeForm="Running integration tests",
            evidence_ids=[],
            requires_evidence=True,
        )

        with pytest.raises(EvidenceValidationError) as exc:
            self.validator.validate_completion(todo)
        assert "No evidence provided" in str(exc.value)

    def test_validate_with_invalid_evidence_id(self):
        """Test validation fails with non-existent evidence ID"""
        todo = EvidenceRequiredTodo(
            content="Validate design",
            status="in_progress",
            activeForm="Validating design",
            evidence_ids=["fake_id_999"],
            requires_evidence=True,
        )

        with pytest.raises(EvidenceValidationError) as exc:
            self.validator.validate_completion(todo)
        assert "Evidence not found" in str(exc.value)

    def test_validate_with_empty_evidence_content(self):
        """Test validation fails with empty evidence content"""
        # Store invalid evidence with empty content
        evidence = Evidence(
            evidence_id="empty_001",
            evidence_type="test_output",
            content="",  # Empty content
            timestamp=datetime.now(),
            validator_id="test_runner",
            metadata={},
        )
        self.evidence_store.store_evidence(evidence)

        todo = EvidenceRequiredTodo(
            content="Run tests",
            status="in_progress",
            activeForm="Running tests",
            evidence_ids=["empty_001"],
            requires_evidence=True,
        )

        with pytest.raises(EvidenceValidationError) as exc:
            self.validator.validate_completion(todo)
        assert "Empty evidence content" in str(exc.value)

    def test_validate_multiple_evidence_types(self):
        """Test validation with multiple types of evidence"""
        # Store multiple evidence types
        test_evidence = Evidence(
            evidence_id="test_002",
            evidence_type="test_output",
            content="Tests: 20/20 passed",
            timestamp=datetime.now(),
            validator_id="pytest",
            metadata={"passed": 20},
        )
        self.evidence_store.store_evidence(test_evidence)

        golden_evidence = Evidence(
            evidence_id="golden_002",
            evidence_type="golden_comparison",
            content="Output matches golden file",
            timestamp=datetime.now(),
            validator_id="golden_validator",
            metadata={"match": True},
        )
        self.evidence_store.store_evidence(golden_evidence)

        todo = EvidenceRequiredTodo(
            content="Complete feature with tests",
            status="in_progress",
            activeForm="Completing feature",
            evidence_ids=["test_002", "golden_002"],
            requires_evidence=True,
        )

        assert self.validator.validate_completion(todo) is True

    def test_validate_optional_evidence_todo(self):
        """Test todos that don't require evidence can complete"""
        todo = EvidenceRequiredTodo(
            content="Update README",
            status="in_progress",
            activeForm="Updating README",
            evidence_ids=[],
            requires_evidence=False,
        )

        # Should pass without evidence
        assert self.validator.validate_completion(todo) is True

    def test_validate_weak_evidence_detection(self):
        """Test detection of weak/fake evidence"""
        # Store weak evidence
        weak_evidence = Evidence(
            evidence_id="weak_001",
            evidence_type="test_output",
            content="TODO: Add test results here",  # Fake placeholder
            timestamp=datetime.now(),
            validator_id="fake_runner",
            metadata={},
        )
        self.evidence_store.store_evidence(weak_evidence)

        todo = EvidenceRequiredTodo(
            content="Run comprehensive tests",
            status="in_progress",
            activeForm="Running tests",
            evidence_ids=["weak_001"],
            requires_evidence=True,
        )

        with pytest.raises(EvidenceValidationError) as exc:
            self.validator.validate_completion(todo)
        assert "Weak or placeholder evidence" in str(exc.value)


class TestBlockingEnforcer:
    """Test the BlockingEnforcer class - antagonistic tests"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.evidence_store = EvidenceStore(base_path=Path(self.temp_dir))
        self.validator = CompletionValidator(self.evidence_store)
        self.enforcer = BlockingEnforcer(self.validator)

    def test_enforce_blocks_completion_without_evidence(self):
        """Test that enforcer blocks completion without evidence"""
        todo = EvidenceRequiredTodo(
            content="Deploy to production",
            status="in_progress",
            activeForm="Deploying",
            evidence_ids=[],
            requires_evidence=True,
        )

        # Attempt to complete - should be blocked
        result = self.enforcer.attempt_completion(todo)
        assert result.blocked is True
        assert result.reason == "No evidence provided for completion"
        assert todo.status == "in_progress"  # Status unchanged

    def test_enforce_allows_completion_with_evidence(self):
        """Test that enforcer allows completion with valid evidence"""
        # Store valid evidence
        evidence = Evidence(
            evidence_id="deploy_001",
            evidence_type="validation_result",
            content="All checks passed: security, performance, integration",
            timestamp=datetime.now(),
            validator_id="ci_pipeline",
            metadata={"all_checks": "passed"},
        )
        self.evidence_store.store_evidence(evidence)

        todo = EvidenceRequiredTodo(
            content="Deploy to production",
            status="in_progress",
            activeForm="Deploying",
            evidence_ids=["deploy_001"],
            requires_evidence=True,
        )

        result = self.enforcer.attempt_completion(todo)
        assert result.blocked is False
        assert result.reason == "Evidence validated successfully"
        assert todo.status == "completed"

    def test_enforce_cheating_attempts_blocked(self):
        """Test various cheating attempts are blocked"""
        # Attempt 1: Try to directly modify status
        todo = EvidenceRequiredTodo(
            content="Critical security fix",
            status="in_progress",
            activeForm="Fixing",
            evidence_ids=[],
            requires_evidence=True,
        )

        # Try to cheat by setting status directly
        todo.status = "completed"
        result = self.enforcer.validate_status_change(todo)
        assert result is False  # Change rejected

    def test_enforce_fake_evidence_blocked(self):
        """Test that fake evidence patterns are detected"""
        # Store various fake evidence patterns
        fake_patterns = [
            "Tests passed",  # Too generic
            "All good",  # No details
            "PLACEHOLDER",  # Obvious placeholder
            "TODO: Add results",  # TODO marker
            "...",  # Ellipsis placeholder
            "",  # Empty
        ]

        for i, fake_content in enumerate(fake_patterns):
            evidence = Evidence(
                evidence_id=f"fake_{i}",
                evidence_type="test_output",
                content=fake_content,
                timestamp=datetime.now(),
                validator_id="faker",
                metadata={},
            )
            self.evidence_store.store_evidence(evidence)

            todo = EvidenceRequiredTodo(
                content=f"Task {i}",
                status="in_progress",
                activeForm=f"Working on {i}",
                evidence_ids=[f"fake_{i}"],
                requires_evidence=True,
            )

            result = self.enforcer.attempt_completion(todo)
            assert result.blocked is True, f"Failed to block fake pattern: {fake_content}"

    def test_enforce_bypassing_attempts(self):
        """Test attempts to bypass the evidence system"""
        todo = EvidenceRequiredTodo(
            content="Important task",
            status="in_progress",
            activeForm="Working",
            evidence_ids=[],
            requires_evidence=True,
        )

        # Attempt to bypass by setting requires_evidence to False
        original_flag = todo.requires_evidence
        todo.requires_evidence = False

        # Enforcer should detect tampering
        result = self.enforcer.detect_tampering(todo, original_flag)
        assert result is True  # Tampering detected

    def test_enforce_timing_attacks(self):
        """Test that rapid completion attempts are suspicious"""
        todo = EvidenceRequiredTodo(
            content="Complex refactoring",
            status="pending",
            activeForm="Refactoring",
            evidence_ids=[],
            requires_evidence=True,
            created_at=datetime.now(),
        )

        # Try to complete immediately (suspicious for complex task)
        result = self.enforcer.check_timing_validity(todo)
        assert result is False  # Too fast to be legitimate

    def test_enforce_evidence_recycling_blocked(self):
        """Test that evidence can't be reused across todos"""
        # Store evidence
        evidence = Evidence(
            evidence_id="shared_001",
            evidence_type="test_output",
            content="Tests passed for feature A",
            timestamp=datetime.now(),
            validator_id="pytest",
            metadata={"feature": "A"},
        )
        self.evidence_store.store_evidence(evidence)

        # First todo uses the evidence (valid)
        todo1 = EvidenceRequiredTodo(
            content="Complete feature A",
            status="in_progress",
            activeForm="Completing A",
            evidence_ids=["shared_001"],
            requires_evidence=True,
        )
        result1 = self.enforcer.attempt_completion(todo1)
        assert result1.blocked is False

        # Second todo tries to reuse same evidence (invalid)
        todo2 = EvidenceRequiredTodo(
            content="Complete feature B",  # Different feature!
            status="in_progress",
            activeForm="Completing B",
            evidence_ids=["shared_001"],  # Reusing evidence
            requires_evidence=True,
        )
        result2 = self.enforcer.attempt_completion(todo2)
        assert result2.blocked is True
        assert "Evidence mismatch" in result2.reason


class TestTodoWriteIntegration:
    """Test integration with TodoWrite tool"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.evidence_store = EvidenceStore(base_path=Path(self.temp_dir))
        self.validator = CompletionValidator(self.evidence_store)
        self.enforcer = BlockingEnforcer(self.validator)

    def test_backwards_compatibility(self):
        """Test that regular todos still work without evidence"""
        # Regular todo without evidence requirement
        todo = {"content": "Write documentation", "status": "in_progress", "activeForm": "Writing documentation"}

        # Should work with wrapper
        wrapper = TodoWithEvidence(todo, requires_evidence=False)
        assert wrapper.can_complete() is True

    def test_gradual_adoption_path(self):
        """Test mixing evidence-required and regular todos"""
        todos = [
            EvidenceRequiredTodo(
                content="Run tests",
                status="in_progress",
                activeForm="Running tests",
                evidence_ids=[],
                requires_evidence=True,
            ),
            EvidenceRequiredTodo(
                content="Update docs",
                status="in_progress",
                activeForm="Updating docs",
                evidence_ids=[],
                requires_evidence=False,
            ),
        ]

        # First todo blocked, second allowed
        assert self.enforcer.can_complete_todo(todos[0]) is False
        assert self.enforcer.can_complete_todo(todos[1]) is True

    def test_helper_functions_for_agents(self):
        """Test helper functions agents can use"""
        # Store evidence
        evidence = Evidence(
            evidence_id="helper_001",
            evidence_type="test_output",
            content="All 50 tests passed",
            timestamp=datetime.now(),
            validator_id="pytest",
            metadata={"passed": 50},
        )
        self.evidence_store.store_evidence(evidence)

        # Helper to attach evidence to todo
        todo = EvidenceRequiredTodo(
            content="Complete feature",
            status="in_progress",
            activeForm="Completing",
            evidence_ids=[],
            requires_evidence=True,
        )

        # Use helper to attach evidence
        todo.attach_evidence("helper_001")
        assert "helper_001" in todo.evidence_ids

        # Use helper to validate before completion
        assert todo.validate_for_completion(self.validator) is True

    def test_evidence_types_all_supported(self):
        """Test all evidence types from Phase 1 are supported"""
        evidence_types = [
            ("test_output", "Tests: 100/100 passed"),
            ("validation_result", "All validations successful"),
            ("golden_comparison", "Output matches golden file exactly"),
            ("design_review", "Design approved by architect"),
        ]

        for etype, content in evidence_types:
            evidence = Evidence(
                evidence_id=f"{etype}_001",
                evidence_type=etype,
                content=content,
                timestamp=datetime.now(),
                validator_id=f"{etype}_validator",
                metadata={"type": etype},
            )
            self.evidence_store.store_evidence(evidence)

            todo = EvidenceRequiredTodo(
                content=f"Task requiring {etype}",
                status="in_progress",
                activeForm="Working",
                evidence_ids=[f"{etype}_001"],
                requires_evidence=True,
            )

            assert self.validator.validate_completion(todo) is True

    @patch("amplifier.bplan.todowrite_integration.TodoWrite")
    def test_mock_todowrite_integration(self, mock_todowrite):
        """Test integration with mocked TodoWrite tool"""
        # Setup mock
        mock_tool = Mock()
        mock_todowrite.return_value = mock_tool

        # Create todo that requires evidence
        todo = EvidenceRequiredTodo(
            content="Deploy service",
            status="in_progress",
            activeForm="Deploying",
            evidence_ids=[],
            requires_evidence=True,
        )

        # Attempt completion through mock - should fail
        with pytest.raises(EvidenceValidationError):
            self.enforcer.complete_with_todowrite(todo, mock_tool)

        # Add evidence
        evidence = Evidence(
            evidence_id="deploy_002",
            evidence_type="validation_result",
            content="All deployment checks passed",
            timestamp=datetime.now(),
            validator_id="deploy_validator",
            metadata={"status": "ready"},
        )
        self.evidence_store.store_evidence(evidence)
        todo.evidence_ids.append("deploy_002")

        # Now completion should succeed
        result = self.enforcer.complete_with_todowrite(todo, mock_tool)
        assert result is True
        mock_tool.update_todo.assert_called_once()
