"""Tests for the SmartRouter module."""

import json
import tempfile
from pathlib import Path

import pytest

from amplifier.prob_tools.smart_router import (
    QueryFeatures,
    RouteTarget,
    RoutingDecision,
    SmartRouter,
)


class TestQueryFeatures:
    """Tests for QueryFeatures extraction."""

    def test_simple_query(self):
        """Simple queries should have low complexity."""
        features = QueryFeatures.from_query("What is 2+2?")
        assert features.word_count == 3
        assert features.has_question is True
        assert features.has_code is False
        assert features.complexity_score < 0.3

    def test_code_detection(self):
        """Queries with code patterns should be detected."""
        features = QueryFeatures.from_query("def foo(): pass")
        assert features.has_code is True

        features2 = QueryFeatures.from_query("```python\nprint('hello')\n```")
        assert features2.has_code is True

        features3 = QueryFeatures.from_query("How are you today?")
        assert features3.has_code is False

    def test_complexity_scoring(self):
        """Complexity should increase with technical terms and length."""
        simple = QueryFeatures.from_query("Hello")
        complex_query = QueryFeatures.from_query(
            "How do I implement an algorithm to optimize database "
            "performance with async concurrent operations for security?"
        )

        assert complex_query.complexity_score > simple.complexity_score
        assert complex_query.complexity_score >= 0.5

    def test_question_detection(self):
        """Questions should be detected correctly."""
        q1 = QueryFeatures.from_query("What is Python?")
        assert q1.has_question is True

        q2 = QueryFeatures.from_query("How does it work?")
        assert q2.has_question is True

        q3 = QueryFeatures.from_query("Tell me about Python")
        assert q3.has_question is False

    def test_technical_keywords(self):
        """Technical keywords should be extracted."""
        features = QueryFeatures.from_query(
            "Help me debug the authentication algorithm"
        )
        assert "debug" in features.domain_keywords
        assert "authentication" in features.domain_keywords
        assert "algorithm" in features.domain_keywords


class TestSmartRouter:
    """Tests for the SmartRouter class."""

    def test_routing_decision_simple_query(self):
        """Simple queries should route to rules."""
        router = SmartRouter(llm_threshold=0.5)
        decision = router.decide("Hi")

        assert decision.target == RouteTarget.RULES
        assert decision.confidence > 0.5
        assert "rules" in decision.reason.lower()

    def test_routing_decision_complex_query(self):
        """Complex queries should route to LLM."""
        router = SmartRouter(llm_threshold=0.5)
        decision = router.decide(
            "How do I implement a concurrent async algorithm to optimize "
            "database performance with proper authentication and security?"
        )

        assert decision.target == RouteTarget.LLM
        assert decision.confidence > 0.5
        assert "llm" in decision.reason.lower()

    def test_routing_with_code(self):
        """Queries with code should bias toward LLM."""
        router = SmartRouter(llm_threshold=0.5)
        decision = router.decide("Fix this code: ```python\ndef foo(): pass```")

        assert decision.target == RouteTarget.LLM
        assert decision.features.has_code is True

    def test_threshold_adjustment(self):
        """Threshold adjustment should work correctly."""
        router = SmartRouter(llm_threshold=0.5)

        # Increase threshold (more go to rules)
        router.adjust_threshold(0.2)
        assert router.llm_threshold == pytest.approx(0.7)

        # Decrease threshold (more go to LLM)
        router.adjust_threshold(-0.3)
        assert router.llm_threshold == pytest.approx(0.4)

        # Can't go below 0.1
        router.adjust_threshold(-0.5)
        assert router.llm_threshold == pytest.approx(0.1)

        # Can't go above 0.9
        router.adjust_threshold(1.0)
        assert router.llm_threshold == pytest.approx(0.9)

    def test_record_outcome(self):
        """Recording outcomes should work."""
        router = SmartRouter()
        decision = router.decide("Hello")

        router.record_outcome(decision, was_successful=True, feedback_score=0.8)

        assert len(router.history) == 1
        assert router.history[0].was_successful is True
        assert router.history[0].feedback_score == 0.8

    def test_get_stats_empty(self):
        """Stats for empty history should be zeros."""
        router = SmartRouter()
        stats = router.get_stats()

        assert stats["total"] == 0
        assert stats["llm_rate"] == 0.0
        assert stats["success_rate"] == 0.0

    def test_get_stats_with_history(self):
        """Stats should reflect recorded history."""
        router = SmartRouter()

        # Record some outcomes
        simple_decision = router.decide("Hi")
        router.record_outcome(simple_decision, was_successful=True)

        complex_decision = router.decide(
            "Implement async database optimization algorithm"
        )
        router.record_outcome(complex_decision, was_successful=True)
        router.record_outcome(complex_decision, was_successful=False)

        stats = router.get_stats()

        assert stats["total"] == 3
        assert stats["success_rate"] == pytest.approx(2 / 3)

    def test_history_persistence(self):
        """History should persist to file and reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "routing_history.json"

            # Create router and record some outcomes
            router1 = SmartRouter(history_file=history_file)
            decision = router1.decide("Hello")
            router1.record_outcome(decision, was_successful=True)

            assert history_file.exists()

            # Create new router that loads history
            router2 = SmartRouter(history_file=history_file)

            assert len(router2.history) == 1
            assert router2.history[0].was_successful is True


class TestRoutingDecision:
    """Tests for RoutingDecision dataclass."""

    def test_decision_attributes(self):
        """Decision should have all expected attributes."""
        features = QueryFeatures.from_query("Hello")
        decision = RoutingDecision(
            target=RouteTarget.RULES,
            confidence=0.8,
            reason="Simple query",
            features=features,
        )

        assert decision.target == RouteTarget.RULES
        assert decision.confidence == 0.8
        assert decision.reason == "Simple query"
        assert decision.features.word_count == 1


class TestRouteTarget:
    """Tests for RouteTarget enum."""

    def test_enum_values(self):
        """Enum should have expected values."""
        assert RouteTarget.LLM.value == "llm"
        assert RouteTarget.RULES.value == "rules"
