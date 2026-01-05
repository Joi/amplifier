"""
Pattern analyzer - learns from review history to improve recommendations.
"""

from collections import Counter
from typing import Any

from ..session.schema import Decision


class PatternAnalyzer:
    """Analyze review history to find patterns and generate insights"""

    def analyze_history(self, decisions: list[Decision]) -> dict[str, Any]:
        """
        Analyze past decisions to find patterns.

        Returns dict with patterns like:
        - action_distribution: How often each action is taken
        - avg_defer_days: Average number of days items are deferred
        - completion_rate: Percentage of items completed
        """
        if not decisions:
            return {}

        # Count actions
        action_counts = Counter(d.action for d in decisions)

        # Calculate defer average
        defer_days = []
        for d in decisions:
            if d.action == "defer" and d.scheduled_date:
                days = (d.scheduled_date - d.timestamp).days
                defer_days.append(days)

        avg_defer = sum(defer_days) / len(defer_days) if defer_days else 7

        patterns = {
            "total_decisions": len(decisions),
            "action_distribution": dict(action_counts),
            "completion_rate": action_counts.get("complete", 0) / len(decisions),
            "defer_rate": action_counts.get("defer", 0) / len(decisions),
            "delete_rate": action_counts.get("delete", 0) / len(decisions),
            "avg_defer_days": round(avg_defer, 1),
        }

        return patterns

    def generate_insights(self, patterns: dict[str, Any]) -> list[str]:
        """
        Generate human-readable insights from patterns.

        Returns list of insight strings.
        """
        if not patterns:
            return []

        insights = []

        # Insight about completion rate
        comp_rate = patterns.get("completion_rate", 0)
        if comp_rate > 0.5:
            insights.append(f"Great job! You completed {comp_rate:.0%} of items reviewed")
        elif comp_rate < 0.2:
            insights.append(f"Only {comp_rate:.0%} completion rate - consider if items are realistic")

        # Insight about deferrals
        defer_rate = patterns.get("defer_rate", 0)
        if defer_rate > 0.5:
            insights.append(f"You deferred {defer_rate:.0%} of items - average {patterns.get('avg_defer_days')} days")

        # Insight about deletions
        delete_rate = patterns.get("delete_rate", 0)
        if delete_rate > 0.3:
            insights.append(f"You deleted {delete_rate:.0%} of items - good pruning!")

        return insights
