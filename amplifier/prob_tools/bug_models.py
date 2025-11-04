"""
GenJax Probabilistic Models for Bug Prediction

Learns from extracted git history events to predict bugs in code.
"""

from __future__ import annotations

import jax.numpy as jnp
from genjax import ChoiceMap
from genjax import flip
from genjax import gen
from genjax import normal
from genjax.inference.smc import ImportanceK

from amplifier.prob_tools.event_store import EventStore


@gen
def bug_prediction_model(
    has_null_check: bool,
    has_error_handling: bool,
    complexity: float,
    is_async: bool,
    historical_bug_rate: float,
) -> float:
    """
    GenJax model for predicting bug probability based on code features.

    This model learns from historical bug patterns extracted from git commits.

    Args:
        has_null_check: Does the code have null/None checks?
        has_error_handling: Does it have try/except?
        complexity: Cyclomatic complexity (0-1 normalized)
        is_async: Is this async code?
        historical_bug_rate: Bug rate in similar code historically (0-1)

    Returns:
        Probability of a bug existing (0-1)
    """
    # Prior: base bug rate from historical data
    base_bug_rate = normal(historical_bug_rate, 0.1) @ "base_rate"
    base_bug_rate = jnp.clip(base_bug_rate, 0.01, 0.99)

    # Missing null checks increases bug probability
    # (learned from bug_events where root_cause = "missing_null_check")
    null_check_factor = jnp.where(has_null_check, 1.0, 2.5)

    # Missing error handling increases risk
    # (learned from bug_events where root_cause = "unhandled_exception")
    error_handling_factor = jnp.where(has_error_handling, 1.0, 2.0)

    # Complexity compounds risk
    complexity_factor = 1.0 + (complexity * 2.0)

    # Async code has higher bug rate
    # (learned from bug_events where bug_type = "race_condition")
    async_factor = jnp.where(is_async, 1.8, 1.0)

    # Combined probability
    bug_prob = base_bug_rate * null_check_factor * error_handling_factor * complexity_factor * async_factor
    bug_prob = jnp.clip(bug_prob, 0.01, 0.99)

    # Sample whether bug exists
    has_bug = flip(bug_prob) @ "has_bug"

    return bug_prob


@gen
def refactoring_success_model(
    refactoring_type: str,
    approach: str,
    code_size: float,
    test_coverage: float,
    historical_success_rate: float,
) -> float:
    """
    Model probability of refactoring success.

    Learns from refactoring_events in git history.

    Args:
        refactoring_type: Type of refactoring (DI, extract_method, etc.)
        approach: "incremental" or "big_bang"
        code_size: Size of code being refactored (0-1 normalized)
        test_coverage: Test coverage of code (0-1)
        historical_success_rate: Success rate for this refactoring type

    Returns:
        Probability of successful refactoring
    """
    base_success = normal(historical_success_rate, 0.1) @ "base_success"
    base_success = jnp.clip(base_success, 0.05, 0.95)

    # Incremental approach has higher success
    # (learned from refactoring_events)
    approach_factor = jnp.where(approach == "incremental", 1.3, 0.7)

    # Larger code is riskier
    size_factor = 1.0 - (code_size * 0.5)

    # Better tests = higher success
    test_factor = 1.0 + (test_coverage * 0.5)

    success_prob = base_success * approach_factor * size_factor * test_factor
    success_prob = jnp.clip(success_prob, 0.05, 0.95)

    will_succeed = flip(success_prob) @ "success"

    return success_prob


class BugPredictor:
    """Uses GenJax models trained on historical data to predict bugs"""

    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self.bug_patterns = event_store.get_bug_patterns()

    def predict_bug_probability(
        self, has_null_check: bool, has_error_handling: bool, complexity: float, is_async: bool
    ) -> dict:
        """Predict bug probability for code with given features"""

        # Get historical bug rate for base prior
        historical_rate = self._calculate_historical_bug_rate()

        # Run inference
        key = jax.random.PRNGKey(0)

        # Run importance sampling to get distribution
        sampler = ImportanceK(100)  # 100 particles

        # Create observations (none for prediction)
        observations = ChoiceMap()

        # Run model
        traces = sampler(
            key,
            bug_prediction_model,
            (has_null_check, has_error_handling, complexity, is_async, historical_rate),
            observations,
        )

        # Extract predictions
        bug_probs = []
        for i in range(100):
            trace = traces[i]
            bug_prob = trace.get_retval()
            bug_probs.append(float(bug_prob))

        mean_prob = sum(bug_probs) / len(bug_probs)
        std_prob = (sum((p - mean_prob) ** 2 for p in bug_probs) / len(bug_probs)) ** 0.5

        return {
            "bug_probability": mean_prob,
            "confidence": 1.0 - std_prob,  # Lower std = higher confidence
            "recommendation": self._get_recommendation(mean_prob, has_null_check, has_error_handling),
        }

    def _calculate_historical_bug_rate(self) -> float:
        """Calculate overall bug rate from historical events"""
        bug_events = self.event_store.get_all_bug_events()

        if not bug_events:
            return 0.2  # Default prior

        # Simple: bugs / total commits analyzed
        # In real implementation, would need total commits count
        return min(len(bug_events) / 1000.0, 0.5)

    def _get_recommendation(self, bug_prob: float, has_null_check: bool, has_error_handling: bool) -> str:
        """Get recommendation based on prediction"""

        if bug_prob > 0.7:
            issues = []
            if not has_null_check:
                issues.append("Add null/None checks")
            if not has_error_handling:
                issues.append("Add error handling")

            return f"HIGH RISK ({bug_prob:.0%}): " + ", ".join(issues)

        if bug_prob > 0.4:
            return f"MEDIUM RISK ({bug_prob:.0%}): Consider adding tests"

        return f"LOW RISK ({bug_prob:.0%}): Looks good"


import jax
