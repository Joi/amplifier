"""Test Design Reviewer - validates designs with zero context pollution."""

from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from amplifier.bplan.design_review import CodeBasedDesignReviewer
from amplifier.bplan.design_review import DesignReviewer
from amplifier.bplan.design_review import LLMDesignReviewer
from amplifier.bplan.design_review import ValidationResult


class TestValidationResult:
    """Test the ValidationResult dataclass."""

    def test_validation_result_structure(self):
        """Test ValidationResult has required fields."""
        result = ValidationResult(passed=True, issues=[], coverage=0.95, details={"key": "value"})

        assert result.passed is True
        assert result.issues == []
        assert result.coverage == 0.95
        assert result.details == {"key": "value"}

    def test_validation_result_with_issues(self):
        """Test ValidationResult can hold issues."""
        issues = ["Missing error handling", "No rate limiting"]
        result = ValidationResult(passed=False, issues=issues, coverage=0.6, details={})

        assert result.passed is False
        assert len(result.issues) == 2
        assert "Missing error handling" in result.issues


class TestCodeBasedDesignReviewer:
    """Test code-based structural validation."""

    def test_validates_required_sections(self):
        """Test it checks for required design sections."""
        reviewer = CodeBasedDesignReviewer()

        # Missing required sections
        design = {
            "overview": "Some overview"
            # Missing: components, data_flow, validation
        }

        result = reviewer.validate(user_req="Build a TODO app", design_output=design)

        assert result.passed is False
        assert any("components" in issue.lower() for issue in result.issues)
        assert any("data_flow" in issue.lower() for issue in result.issues)
        assert result.coverage < 1.0

    def test_validates_complete_design(self):
        """Test it passes valid complete designs."""
        reviewer = CodeBasedDesignReviewer()

        design = {
            "overview": "A TODO application",
            "components": [
                {"name": "TodoStore", "purpose": "Manage todos"},
                {"name": "TodoUI", "purpose": "User interface"},
            ],
            "data_flow": "User -> UI -> Store -> Database",
            "validation": {
                "criteria": ["All todos saved", "UI responsive"],
                "tests": ["Test CRUD operations", "Test UI updates"],
            },
        }

        result = reviewer.validate(user_req="Build a TODO app", design_output=design)

        assert result.passed is True
        assert result.issues == []
        assert result.coverage >= 0.8

    def test_stateless_operation(self):
        """Test reviewer maintains no state between calls."""
        reviewer = CodeBasedDesignReviewer()

        # First validation
        design1 = {"overview": "Design 1"}
        result1 = reviewer.validate("Req 1", design1)

        # Second validation - should be independent
        design2 = {"overview": "Design 2"}
        result2 = reviewer.validate("Req 2", design2)

        # Results should be independent
        assert result1.details.get("design_id") != result2.details.get("design_id")

        # Reviewer should have no instance state that persists
        assert not hasattr(reviewer, "_last_design")
        assert not hasattr(reviewer, "_cache")


class TestLLMDesignReviewer:
    """Test LLM-based semantic validation."""

    @pytest.mark.asyncio
    async def test_creates_fresh_context_each_call(self):
        """Test LLM reviewer uses fresh context for each validation."""
        with patch("amplifier.bplan.design_review.Agent") as mock_ai:
            mock_agent = AsyncMock()
            mock_response = Mock()
            mock_response.data = {
                "passed": True,
                "issues": [],
                "semantic_coverage": 0.9,
                "reasoning": "Design matches requirements",
            }
            mock_agent.run.return_value = mock_response
            mock_ai.return_value = mock_agent

            reviewer = LLMDesignReviewer()

            # First call
            await reviewer.validate_async(user_req="Build app 1", design_output={"overview": "App 1 design"})

            # Second call - should use fresh context
            await reviewer.validate_async(user_req="Build app 2", design_output={"overview": "App 2 design"})

            # Verify fresh agent calls (no shared context)
            assert mock_agent.run.call_count == 2

            # Check calls had different prompts
            call1_prompt = mock_agent.run.call_args_list[0][0][0]
            call2_prompt = mock_agent.run.call_args_list[1][0][0]
            assert "Build app 1" in call1_prompt
            assert "Build app 2" in call2_prompt
            assert "Build app 1" not in call2_prompt

    @pytest.mark.asyncio
    async def test_no_context_pollution_between_sessions(self):
        """Test no information leaks between validation sessions."""
        with patch("amplifier.bplan.design_review.Agent") as mock_ai:
            # Setup mock to simulate context pollution detection
            call_count = 0

            async def mock_run(prompt):
                nonlocal call_count
                call_count += 1

                response = Mock()
                # If context was polluted, previous terms would appear
                if "secret_term_xyz" in prompt and call_count > 1:
                    # This should NOT happen
                    response.data = {
                        "passed": False,
                        "issues": ["Context pollution detected"],
                        "semantic_coverage": 0,
                        "reasoning": "Found leaked context",
                    }
                else:
                    response.data = {
                        "passed": True,
                        "issues": [],
                        "semantic_coverage": 0.9,
                        "reasoning": "Clean validation",
                    }
                return response

            mock_agent = AsyncMock()
            mock_agent.run.side_effect = mock_run
            mock_ai.return_value = mock_agent

            reviewer = LLMDesignReviewer()

            # First validation with sensitive term
            await reviewer.validate_async(
                user_req="Build app with secret_term_xyz", design_output={"overview": "Design 1"}
            )

            # Second validation - should NOT see secret_term_xyz
            result2 = await reviewer.validate_async(
                user_req="Build different app", design_output={"overview": "Design 2"}
            )

            # Second result should be clean (no pollution)
            assert result2.passed is True
            assert "pollution" not in str(result2.issues).lower()

    def test_sync_validate_wrapper(self):
        """Test synchronous validate method wraps async properly."""
        with patch("amplifier.bplan.design_review.asyncio.run") as mock_run:
            mock_run.return_value = ValidationResult(passed=True, issues=[], coverage=0.9, details={})

            reviewer = LLMDesignReviewer()
            result = reviewer.validate(user_req="Build app", design_output={"overview": "Design"})

            assert result.passed is True
            mock_run.assert_called_once()


class TestDesignReviewerProtocol:
    """Test the DesignReviewer protocol interface."""

    def test_protocol_compliance(self):
        """Test both reviewers implement the protocol."""
        # Code-based reviewer
        code_reviewer = CodeBasedDesignReviewer()
        assert hasattr(code_reviewer, "validate")
        assert callable(code_reviewer.validate)

        # LLM reviewer
        llm_reviewer = LLMDesignReviewer()
        assert hasattr(llm_reviewer, "validate")
        assert callable(llm_reviewer.validate)

        # Both should be DesignReviewer instances
        assert isinstance(code_reviewer, DesignReviewer)
        assert isinstance(llm_reviewer, DesignReviewer)
