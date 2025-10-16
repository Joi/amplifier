"""Test Antagonistic Validation - ensures truly independent review with no context pollution."""

from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from amplifier.bplan.design_review import IndependentValidator
from amplifier.bplan.design_review import LLMDesignReviewer
from amplifier.bplan.design_review import ValidationResult


class TestAntagonisticValidation:
    """Test antagonistic validation to ensure zero context pollution."""

    @pytest.mark.asyncio
    async def test_llm_reviewer_polluted_context_detection(self):
        """Test that LLM reviewer with polluted context gets detected."""
        with patch("amplifier.bplan.design_review.Agent") as mock_ai:
            # Simulate a polluted LLM that references previous validations
            mock_agent = AsyncMock()

            call_count = 0
            previous_project = None

            async def mock_run_polluted(prompt):
                nonlocal call_count, previous_project
                call_count += 1

                response = Mock()
                if call_count == 1:
                    previous_project = "E-commerce platform"
                    response.data = {
                        "passed": True,
                        "issues": [],
                        "semantic_coverage": 0.9,
                        "reasoning": f"Design for {previous_project} looks good",
                    }
                else:
                    # Polluted response - references previous validation
                    response.data = {
                        "passed": False,
                        "issues": [f"Unlike the {previous_project}, this lacks payment integration"],
                        "semantic_coverage": 0.5,
                        "reasoning": f"Compared to the previous {previous_project} design...",
                    }
                return response

            mock_agent.run.side_effect = mock_run_polluted
            mock_ai.return_value = mock_agent

            reviewer = LLMDesignReviewer()
            validator = IndependentValidator()

            # First validation
            await reviewer.validate_async(
                user_req="Build an e-commerce platform", design_output={"overview": "E-commerce with payments"}
            )

            # Second validation - different project
            result2 = await reviewer.validate_async(
                user_req="Build a blog website", design_output={"overview": "Simple blog"}
            )

            # Check for pollution in second result
            context2 = {"user_requirements": "Build a blog website", "design_output": {"overview": "Simple blog"}}

            pollution_report = validator.check_pollution(result2, context2)

            # Should detect pollution
            assert pollution_report.is_polluted is True
            assert any(
                "e-commerce" in term.lower() or "payment" in term.lower() for term in pollution_report.leaked_terms
            )

    @pytest.mark.asyncio
    async def test_llm_reviewer_clean_context_passes(self):
        """Test that LLM reviewer with clean context passes pollution check."""
        with patch("amplifier.bplan.design_review.Agent") as mock_ai:
            # Simulate a clean LLM that doesn't reference other contexts
            mock_agent = AsyncMock()

            async def mock_run_clean(prompt):
                response = Mock()
                if "blog" in prompt.lower():
                    response.data = {
                        "passed": True,
                        "issues": [],
                        "semantic_coverage": 0.85,
                        "reasoning": "Blog design includes all required components",
                    }
                else:
                    response.data = {
                        "passed": True,
                        "issues": [],
                        "semantic_coverage": 0.9,
                        "reasoning": "Design meets stated requirements",
                    }
                return response

            mock_agent.run.side_effect = mock_run_clean
            mock_ai.return_value = mock_agent

            reviewer = LLMDesignReviewer()
            validator = IndependentValidator()

            # Multiple validations
            result1 = await reviewer.validate_async(
                user_req="Build a TODO app", design_output={"overview": "TODO application"}
            )

            result2 = await reviewer.validate_async(
                user_req="Build a blog website", design_output={"overview": "Blog platform"}
            )

            # Check both for pollution
            context1 = {"user_requirements": "Build a TODO app", "design_output": {"overview": "TODO application"}}

            context2 = {"user_requirements": "Build a blog website", "design_output": {"overview": "Blog platform"}}

            report1 = validator.check_pollution(result1, context1)
            report2 = validator.check_pollution(result2, context2)

            # Both should be clean
            assert report1.is_polluted is False
            assert report2.is_polluted is False
            assert len(report1.leaked_terms) == 0
            assert len(report2.leaked_terms) == 0

    def test_biased_review_prevention(self):
        """Test that biased reviews are detected and prevented."""
        validator = IndependentValidator()

        # Biased result that assumes specific technology stack
        biased_result = ValidationResult(
            passed=False,
            issues=[
                "Should use React instead of Vue",
                "Missing Docker configuration",
                "No Kubernetes deployment files",
            ],
            coverage=0.4,
            details={
                "tech_assumptions": ["React", "Docker", "Kubernetes"],
                "reasoning": "Modern apps need containerization",
            },
        )

        # Simple requirements that don't specify technology
        context = {
            "user_requirements": "Build a simple web interface",
            "design_output": {"components": ["WebUI", "API"]},
        }

        report = validator.check_pollution(biased_result, context)

        # Should detect bias as unstated assumptions
        assert len(report.unstated_assumptions) > 0
        assert any(
            "react" in assumption.lower() or "docker" in assumption.lower() or "kubernetes" in assumption.lower()
            for assumption in report.unstated_assumptions
        )

    def test_isolation_across_sessions(self):
        """Test complete isolation between validation sessions."""
        # Create multiple validators to ensure no shared state
        validator1 = IndependentValidator()
        validator2 = IndependentValidator()

        result1 = ValidationResult(
            passed=True, issues=[], coverage=0.9, details={"project": "Project A", "tech": "Python"}
        )

        result2 = ValidationResult(
            passed=True, issues=[], coverage=0.85, details={"project": "Project B", "tech": "JavaScript"}
        )

        context1 = {"user_requirements": "Python web app", "design_output": {"language": "Python"}}

        context2 = {"user_requirements": "JavaScript frontend", "design_output": {"language": "JavaScript"}}

        # Check with different validators
        report1 = validator1.check_pollution(result1, context1)
        report2 = validator2.check_pollution(result2, context2)

        # Both should be independent and clean
        assert report1.is_polluted is False
        assert report2.is_polluted is False

        # Validators should not share any state
        assert validator1 is not validator2
        assert not hasattr(validator1, "_shared_state")
        assert not hasattr(validator2, "_shared_state")

    @pytest.mark.asyncio
    async def test_fresh_llm_instance_per_validation(self):
        """Test that each validation uses a fresh LLM instance."""
        with patch("amplifier.bplan.design_review.Agent") as mock_ai:
            instances_created = []

            def track_instance(*args, **kwargs):
                instance = Mock()
                instance.run = AsyncMock(
                    return_value=Mock(data={"passed": True, "issues": [], "semantic_coverage": 0.9, "reasoning": "OK"})
                )
                instances_created.append(instance)
                return instance

            mock_ai.side_effect = track_instance

            reviewer = LLMDesignReviewer()

            # Multiple validations
            await reviewer.validate_async("Req 1", {"design": "1"})
            await reviewer.validate_async("Req 2", {"design": "2"})
            await reviewer.validate_async("Req 3", {"design": "3"})

            # Should create fresh instance each time
            assert len(instances_created) >= 3
            # Verify they're different instances
            assert instances_created[0] is not instances_created[1]
            assert instances_created[1] is not instances_created[2]

    def test_pollution_detection_sensitivity(self):
        """Test pollution detection catches subtle context leaks."""
        validator = IndependentValidator()

        # Subtle pollution - references to iteration/version
        subtle_result = ValidationResult(
            passed=True,
            issues=[],
            coverage=0.8,
            details={
                "notes": "This iteration improves on the last one",
                "comparison": "Better than v1",
                "references": "See previous implementation",
            },
        )

        context = {"user_requirements": "Build initial version", "design_output": {"version": "1.0"}}

        report = validator.check_pollution(subtle_result, context)

        # Should catch subtle references to other contexts
        assert len(report.unstated_assumptions) > 0 or len(report.leaked_terms) > 0
        assert report.confidence > 0.5  # Some confidence in detection
