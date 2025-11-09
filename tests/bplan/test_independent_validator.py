"""Test Independent Validator - detects context pollution and leaked information."""

from amplifier.bplan.design_review import IndependentValidator
from amplifier.bplan.design_review import PollutionReport
from amplifier.bplan.design_review import ValidationResult


class TestIndependentValidator:
    """Test context pollution detection and independence validation."""

    def test_pollution_report_structure(self):
        """Test PollutionReport dataclass structure."""
        report = PollutionReport(is_polluted=False, leaked_terms=[], unstated_assumptions=[], confidence=0.95)

        assert report.is_polluted is False
        assert report.leaked_terms == []
        assert report.unstated_assumptions == []
        assert report.confidence == 0.95

    def test_detect_leaked_terms(self):
        """Test detection of terms that shouldn't be in validation."""
        validator = IndependentValidator()

        # Validation result contains terms not in allowed set
        result = ValidationResult(
            passed=True,
            issues=[],
            coverage=0.9,
            details={
                "reasoning": "Design uses Redis for caching and Kafka for messaging",
                "components_found": ["Redis cache", "Kafka queue", "PostgreSQL"],
            },
        )

        # User requirements never mentioned Redis or Kafka
        allowed_terms = {"cache", "messaging", "database", "postgresql"}

        leaked = validator.detect_leaked_terms(result, allowed_terms)

        assert "redis" in [term.lower() for term in leaked]
        assert "kafka" in [term.lower() for term in leaked]
        assert len(leaked) >= 2

    def test_detect_no_leaked_terms(self):
        """Test when no terms are leaked."""
        validator = IndependentValidator()

        result = ValidationResult(
            passed=True,
            issues=[],
            coverage=0.9,
            details={"reasoning": "Design implements caching and messaging as required"},
        )

        allowed_terms = {"cache", "caching", "messaging", "design", "implements", "required"}

        leaked = validator.detect_leaked_terms(result, allowed_terms)
        assert leaked == []

    def test_check_pollution_clean(self):
        """Test pollution check on clean validation."""
        validator = IndependentValidator()

        result = ValidationResult(
            passed=True, issues=[], coverage=0.85, details={"matched_requirements": ["User auth", "Data storage"]}
        )

        context = {
            "user_requirements": "Build app with user auth and data storage",
            "design_output": {"components": ["AuthService", "Database"]},
        }

        report = validator.check_pollution(result, context)

        assert isinstance(report, PollutionReport)
        assert report.is_polluted is False
        assert len(report.leaked_terms) == 0
        assert len(report.unstated_assumptions) == 0
        assert report.confidence > 0.8

    def test_check_pollution_detects_external_context(self):
        """Test pollution check detects external context leakage."""
        validator = IndependentValidator()

        # Result mentions things not in the provided context
        result = ValidationResult(
            passed=False,
            issues=["Missing microservices architecture from previous design"],
            coverage=0.5,
            details={
                "reasoning": "Unlike the earlier Redis-based solution, this lacks caching",
                "comparison": "Previous iteration had better performance",
            },
        )

        context = {"user_requirements": "Build a simple TODO app", "design_output": {"components": ["TodoService"]}}

        report = validator.check_pollution(result, context)

        assert report.is_polluted is True
        assert len(report.leaked_terms) > 0
        assert any("redis" in term.lower() for term in report.leaked_terms)
        assert any("previous" in term.lower() or "earlier" in term.lower() for term in report.unstated_assumptions)

    def test_check_pollution_detects_unstated_assumptions(self):
        """Test detection of assumptions not stated in requirements."""
        validator = IndependentValidator()

        result = ValidationResult(
            passed=True,
            issues=[],
            coverage=0.9,
            details={
                "assumptions": [
                    "System will handle millions of users",
                    "Needs distributed architecture",
                    "Must integrate with AWS services",
                ]
            },
        )

        context = {"user_requirements": "Build a blog website", "design_output": {"overview": "Simple blog"}}

        report = validator.check_pollution(result, context)

        assert len(report.unstated_assumptions) >= 2
        assert any("millions" in assumption.lower() for assumption in report.unstated_assumptions)
        assert any("aws" in assumption.lower() for assumption in report.unstated_assumptions)

    def test_stateless_validation(self):
        """Test validator maintains no state between calls."""
        validator = IndependentValidator()

        # First result - clean
        result1 = ValidationResult(passed=True, issues=[], coverage=0.8, details={"test": "1"})

        # Second result - with pollution indicators
        result2 = ValidationResult(
            passed=False,
            issues=["Error - unlike previous version"],
            coverage=0.3,
            details={"test": "2", "comparison": "worse than before"},
        )

        # Check pollution for both
        report1 = validator.check_pollution(result1, {"context": "1"})
        report2 = validator.check_pollution(result2, {"context": "2"})

        # Validator should have no state
        assert not hasattr(validator, "_history")
        assert not hasattr(validator, "_cache")
        assert not hasattr(validator, "_previous_result")

        # Reports should be independent - second should detect pollution
        assert report1.is_polluted is False
        assert report2.is_polluted is True  # Has "previous" and "before" references

    def test_confidence_scoring(self):
        """Test confidence scoring in pollution detection."""
        validator = IndependentValidator()

        # High confidence - clear pollution
        result_polluted = ValidationResult(
            passed=False,
            issues=["This is like the Redis system from project X"],
            coverage=0.5,
            details={"external_refs": ["project X", "system Y"]},
        )

        report_high = validator.check_pollution(
            result_polluted, {"user_requirements": "Build app", "design_output": {}}
        )

        assert report_high.is_polluted is True
        assert report_high.confidence > 0.8

        # Low confidence - ambiguous case
        result_ambiguous = ValidationResult(
            passed=True, issues=[], coverage=0.7, details={"notes": "Standard implementation"}
        )

        report_low = validator.check_pollution(
            result_ambiguous, {"user_requirements": "Build standard app", "design_output": {}}
        )

        assert report_low.confidence < report_high.confidence
