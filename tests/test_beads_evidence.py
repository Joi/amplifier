"""Test Beads evidence requirement on issue closure - Phase 5 RED tests"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from amplifier.bplan.beads_integration import BeadsClient
from amplifier.bplan.beads_integration import BeadsIssue
from amplifier.bplan.beads_integration import IssueStatus
from amplifier.bplan.beads_integration import IssueType
from amplifier.bplan.todowrite_integration import BlockingEnforcer
from amplifier.bplan.todowrite_integration import CompletionValidator
from amplifier.bplan.todowrite_integration import Evidence
from amplifier.bplan.todowrite_integration import EvidenceStore
from amplifier.bplan.todowrite_integration import EvidenceValidationError


class TestBeadsIssueEvidence:
    """Test evidence tracking for beads issues"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.evidence_store = EvidenceStore(base_path=Path(self.temp_dir))
        self.beads_client = BeadsClient()

    def test_create_issue_with_evidence_field(self):
        """Test that issues can be created with evidence_ids field"""
        issue = BeadsIssue(
            id="test-001",
            title="Implement feature X",
            type=IssueType.FEATURE,
            status=IssueStatus.OPEN,
            evidence_ids=[],
            requires_evidence=True,
        )
        assert hasattr(issue, "evidence_ids")
        assert issue.evidence_ids == []
        assert hasattr(issue, "requires_evidence")
        assert issue.requires_evidence is True

    def test_attach_evidence_to_issue(self):
        """Test attaching evidence to a beads issue"""
        issue = BeadsIssue(
            id="test-002",
            title="Fix bug Y",
            type=IssueType.BUG,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=[],
            requires_evidence=True,
        )

        # Store evidence
        evidence = Evidence(
            evidence_id="test_003",
            evidence_type="test_output",
            content="All tests passed: 15/15",
            timestamp=datetime.now(),
            validator_id="pytest",
            metadata={"passed": 15, "failed": 0},
        )
        self.evidence_store.store_evidence(evidence)

        # Attach evidence to issue
        issue.attach_evidence("test_003")
        assert "test_003" in issue.evidence_ids

    def test_issue_requires_evidence_for_closure(self):
        """Test that certain issues are marked as requiring evidence"""
        feature_issue = BeadsIssue(
            id="test-004",
            title="Add authentication",
            type=IssueType.FEATURE,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=[],
            requires_evidence=True,
        )
        assert feature_issue.requires_evidence is True

        # Chores might not require evidence
        chore_issue = BeadsIssue(
            id="test-005",
            title="Update documentation",
            type=IssueType.CHORE,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=[],
            requires_evidence=False,
        )
        assert chore_issue.requires_evidence is False


class TestBeadsIssueClosureBlocking:
    """Test blocking issue closure without evidence"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.evidence_store = EvidenceStore(base_path=Path(self.temp_dir))
        self.validator = CompletionValidator(self.evidence_store)
        self.enforcer = BlockingEnforcer(self.validator)
        self.beads_client = BeadsClient()

    def test_block_closure_without_evidence(self):
        """Test that issue closure is blocked without evidence"""
        issue = BeadsIssue(
            id="test-006",
            title="Implement critical feature",
            type=IssueType.FEATURE,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=[],
            requires_evidence=True,
        )

        # Attempt to close - should be blocked
        result = self.beads_client.close_with_evidence(issue, self.enforcer)
        assert result.blocked is True
        assert "No evidence provided" in result.reason
        assert issue.status == IssueStatus.IN_PROGRESS  # Status unchanged

    def test_allow_closure_with_valid_evidence(self):
        """Test that issue closure is allowed with valid evidence"""
        # Store valid evidence
        evidence = Evidence(
            evidence_id="deploy_001",
            evidence_type="validation_result",
            content="Deploy feature X: All checks passed - feature tested and deployed successfully",
            timestamp=datetime.now(),
            validator_id="ci_pipeline",
            metadata={"all_checks": "passed"},
        )
        self.evidence_store.store_evidence(evidence)

        issue = BeadsIssue(
            id="test-007",
            title="Deploy feature X",
            type=IssueType.FEATURE,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=["deploy_001"],
            requires_evidence=True,
        )

        result = self.beads_client.close_with_evidence(issue, self.enforcer)
        assert result.blocked is False
        assert result.reason == "Evidence validated successfully"
        assert issue.status == IssueStatus.CLOSED

    def test_block_closure_with_weak_evidence(self):
        """Test that weak evidence patterns are detected and blocked"""
        weak_evidence = Evidence(
            evidence_id="weak_002",
            evidence_type="test_output",
            content="TODO: Add test results here",
            timestamp=datetime.now(),
            validator_id="fake_runner",
            metadata={},
        )
        self.evidence_store.store_evidence(weak_evidence)

        issue = BeadsIssue(
            id="test-008",
            title="Complete feature Z",
            type=IssueType.FEATURE,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=["weak_002"],
            requires_evidence=True,
        )

        result = self.beads_client.close_with_evidence(issue, self.enforcer)
        assert result.blocked is True
        assert "Weak or placeholder evidence" in result.reason


class TestBeadsIssueEvidenceIntegration:
    """Test beads CLI integration with evidence system"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.evidence_store = EvidenceStore(base_path=Path(self.temp_dir))
        self.validator = CompletionValidator(self.evidence_store)
        self.enforcer = BlockingEnforcer(self.validator)
        self.beads_client = BeadsClient()

    def test_beads_client_validates_before_close(self):
        """Test that BeadsClient validates evidence before closing"""
        # Create issue without evidence
        issue = BeadsIssue(
            id="test-009",
            title="Fix security bug",
            type=IssueType.BUG,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=[],
            requires_evidence=True,
        )

        # Attempt close without evidence - should fail
        with pytest.raises(EvidenceValidationError):
            self.beads_client.close_issue_with_validation(issue, self.enforcer)

    def test_beads_client_accepts_valid_evidence(self):
        """Test that BeadsClient accepts and closes with valid evidence"""
        # Store valid evidence
        evidence = Evidence(
            evidence_id="bug_fix_001",
            evidence_type="test_output",
            content="Bug fix verified: all tests passed (20/20)",
            timestamp=datetime.now(),
            validator_id="pytest",
            metadata={"tests_passed": 20},
        )
        self.evidence_store.store_evidence(evidence)

        issue = BeadsIssue(
            id="test-010",
            title="Fix authentication bug",
            type=IssueType.BUG,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=["bug_fix_001"],
            requires_evidence=True,
        )

        result = self.beads_client.close_issue_with_validation(issue, self.enforcer)
        assert result is True
        assert issue.status == IssueStatus.CLOSED

    def test_multiple_evidence_types_for_issue(self):
        """Test that issues can have multiple types of evidence"""
        # Store multiple evidence types
        test_evidence = Evidence(
            evidence_id="test_011",
            evidence_type="test_output",
            content="Tests: 30/30 passed",
            timestamp=datetime.now(),
            validator_id="pytest",
            metadata={"passed": 30},
        )
        self.evidence_store.store_evidence(test_evidence)

        review_evidence = Evidence(
            evidence_id="review_011",
            evidence_type="design_review",
            content="Design approved by architect",
            timestamp=datetime.now(),
            validator_id="architect",
            metadata={"approved": True},
        )
        self.evidence_store.store_evidence(review_evidence)

        issue = BeadsIssue(
            id="test-011",
            title="Complete feature with review",
            type=IssueType.FEATURE,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=["test_011", "review_011"],
            requires_evidence=True,
        )

        result = self.beads_client.close_with_evidence(issue, self.enforcer)
        assert result.blocked is False
        assert issue.status == IssueStatus.CLOSED

    def test_chores_can_close_without_evidence(self):
        """Test that chore issues can close without evidence"""
        issue = BeadsIssue(
            id="test-012",
            title="Update README",
            type=IssueType.CHORE,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=[],
            requires_evidence=False,
        )

        result = self.beads_client.close_with_evidence(issue, self.enforcer)
        assert result.blocked is False
        assert issue.status == IssueStatus.CLOSED


class TestBeadsEvidenceAntagonistic:
    """Antagonistic tests for beads evidence system"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.evidence_store = EvidenceStore(base_path=Path(self.temp_dir))
        self.validator = CompletionValidator(self.evidence_store)
        self.enforcer = BlockingEnforcer(self.validator)
        self.beads_client = BeadsClient()

    def test_block_fake_evidence_patterns(self):
        """Test that various fake evidence patterns are blocked"""
        fake_patterns = [
            "Tests passed",  # Too generic
            "All good",  # No details
            "PLACEHOLDER",  # Obvious placeholder
            "TODO: Add results",  # TODO marker
            "...",  # Ellipsis
        ]

        for i, fake_content in enumerate(fake_patterns):
            evidence = Evidence(
                evidence_id=f"fake_beads_{i}",
                evidence_type="test_output",
                content=fake_content,
                timestamp=datetime.now(),
                validator_id="faker",
                metadata={},
            )
            self.evidence_store.store_evidence(evidence)

            issue = BeadsIssue(
                id=f"test-fake-{i}",
                title=f"Issue {i}",
                type=IssueType.FEATURE,
                status=IssueStatus.IN_PROGRESS,
                evidence_ids=[f"fake_beads_{i}"],
                requires_evidence=True,
            )

            result = self.beads_client.close_with_evidence(issue, self.enforcer)
            assert result.blocked is True, f"Failed to block fake pattern: {fake_content}"

    def test_block_evidence_recycling_across_issues(self):
        """Test that evidence can't be reused across different issues"""
        # Store evidence
        evidence = Evidence(
            evidence_id="shared_002",
            evidence_type="test_output",
            content="Tests passed for feature A",
            timestamp=datetime.now(),
            validator_id="pytest",
            metadata={"feature": "A"},
        )
        self.evidence_store.store_evidence(evidence)

        # First issue uses the evidence (valid)
        issue1 = BeadsIssue(
            id="test-013",
            title="Complete feature A",
            type=IssueType.FEATURE,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=["shared_002"],
            requires_evidence=True,
        )
        result1 = self.beads_client.close_with_evidence(issue1, self.enforcer)
        assert result1.blocked is False

        # Second issue tries to reuse same evidence (invalid)
        issue2 = BeadsIssue(
            id="test-014",
            title="Complete feature B",  # Different feature
            type=IssueType.FEATURE,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=["shared_002"],  # Reusing evidence
            requires_evidence=True,
        )
        result2 = self.beads_client.close_with_evidence(issue2, self.enforcer)
        assert result2.blocked is True
        assert "Evidence mismatch" in result2.reason

    def test_block_tampering_requires_evidence_flag(self):
        """Test detection of requires_evidence flag tampering"""
        issue = BeadsIssue(
            id="test-015",
            title="Important feature",
            type=IssueType.FEATURE,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=[],
            requires_evidence=True,
        )

        # Attempt to bypass by setting requires_evidence to False
        original_flag = issue.requires_evidence
        issue.requires_evidence = False

        # Enforcer should detect tampering
        result = self.enforcer.detect_tampering(issue, original_flag)
        assert result is True  # Tampering detected

    def test_block_empty_evidence_content(self):
        """Test that empty evidence content is blocked"""
        empty_evidence = Evidence(
            evidence_id="empty_beads_001",
            evidence_type="test_output",
            content="",  # Empty
            timestamp=datetime.now(),
            validator_id="test_runner",
            metadata={},
        )
        self.evidence_store.store_evidence(empty_evidence)

        issue = BeadsIssue(
            id="test-016",
            title="Fix bug",
            type=IssueType.BUG,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=["empty_beads_001"],
            requires_evidence=True,
        )

        result = self.beads_client.close_with_evidence(issue, self.enforcer)
        assert result.blocked is True
        assert "Empty evidence content" in result.reason

    def test_block_duplicate_evidence_ids(self):
        """Test that duplicate evidence IDs are detected"""
        evidence = Evidence(
            evidence_id="dup_001",
            evidence_type="test_output",
            content="All tests passed",
            timestamp=datetime.now(),
            validator_id="pytest",
            metadata={},
        )
        self.evidence_store.store_evidence(evidence)

        issue = BeadsIssue(
            id="test-017",
            title="Feature with duplicates",
            type=IssueType.FEATURE,
            status=IssueStatus.IN_PROGRESS,
            evidence_ids=["dup_001", "dup_001"],  # Duplicate!
            requires_evidence=True,
        )

        result = self.beads_client.close_with_evidence(issue, self.enforcer)
        assert result.blocked is True
        assert "Duplicate evidence IDs" in result.reason
