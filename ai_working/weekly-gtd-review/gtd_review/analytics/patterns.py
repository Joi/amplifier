"""
Pattern Analyzer brick - learns from review history.

Analyzes user decisions to identify patterns and generate insights.
"""

import logging
from collections import Counter
from typing import Any

from ..session.schema import Decision


class PatternAnalyzer:
    """Analyze review patterns to generate insights"""

    def __init__(self):
        self.logger = logging.getLogger("gtd_review.patterns")

    def analyze_history(self, decisions: list[Decision]) -> dict[str, Any]:
        """
        Analyze decision history to identify patterns.

        Args:
            decisions: List of all decisions made

        Returns:
            Dictionary of identified patterns
        """
        if not decisions:
            return {}

        # Count actions
        action_counts = Counter(d.action for d in decisions)

        # Average time to decision (if we tracked review start times)
        # For now, just count decisions

        # Completion rate
        completed = action_counts.get("complete", 0)
        total = len(decisions)
        completion_rate = completed / total if total > 0 else 0

        # Defer rate
        deferred = action_counts.get("defer", 0)
        defer_rate = deferred / total if total > 0 else 0

        # Delete rate
        deleted = action_counts.get("delete", 0)
        delete_rate = deleted / total if total > 0 else 0

        # Common actions
        most_common_action = action_counts.most_common(1)[0][0] if action_counts else None

        # Priority distribution
        priorities = [d.priority for d in decisions if d.priority is not None]
        avg_priority = sum(priorities) / len(priorities) if priorities else None

        return {
            "total_decisions": total,
            "action_distribution": dict(action_counts),
            "completion_rate": completion_rate,
            "defer_rate": defer_rate,
            "delete_rate": delete_rate,
            "most_common_action": most_common_action,
            "avg_priority": avg_priority,
        }

    def generate_insights(self, patterns: dict[str, Any]) -> dict[str, Any]:
        """
        Generate human-readable insights from patterns.

        Args:
            patterns: Output from analyze_history()

        Returns:
            Dictionary of insights for display
        """
        insights = {}

        # Total reviewed
        insights["Total Items Reviewed"] = patterns.get("total_decisions", 0)

        # Action breakdown
        action_dist = patterns.get("action_distribution", {})
        if action_dist:
            for action, count in action_dist.items():
                insights[f"{action.title()} Actions"] = count

        # Rates
        completion_rate = patterns.get("completion_rate", 0)
        insights["Completion Rate"] = f"{completion_rate:.0%}"

        defer_rate = patterns.get("defer_rate", 0)
        insights["Defer Rate"] = f"{defer_rate:.0%}"

        # Interpretation
        if defer_rate > 0.5:
            insights["Note"] = "High defer rate - consider if tasks are well-scoped"
        elif completion_rate > 0.7:
            insights["Note"] = "Great progress! High completion rate"

        return insights
