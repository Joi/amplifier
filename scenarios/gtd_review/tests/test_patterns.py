"""Tests for pattern analyzer"""

import sys
from datetime import datetime
from datetime import timedelta
from pathlib import Path

# Add parent directory to path so we can import from scenarios
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scenarios.gtd_review.analytics.patterns import PatternAnalyzer
from scenarios.gtd_review.session.schema import Decision


def test_analyze_history():
    """Test pattern analysis"""
    decisions = [
        Decision(action="complete", timestamp=datetime.now()),
        Decision(action="complete", timestamp=datetime.now()),
        Decision(action="defer", timestamp=datetime.now(), scheduled_date=datetime.now() + timedelta(days=7)),
        Decision(action="defer", timestamp=datetime.now(), scheduled_date=datetime.now() + timedelta(days=14)),
        Decision(action="delete", timestamp=datetime.now()),
    ]

    analyzer = PatternAnalyzer()
    patterns = analyzer.analyze_history(decisions)

    assert patterns["total_decisions"] == 5
    assert patterns["completion_rate"] == 0.4  # 2/5
    assert patterns["defer_rate"] == 0.4  # 2/5
    assert patterns["delete_rate"] == 0.2  # 1/5
    assert patterns["avg_defer_days"] == 10.5  # (7+14)/2


def test_generate_insights():
    """Test insight generation"""
    patterns = {
        "total_decisions": 10,
        "completion_rate": 0.6,
        "defer_rate": 0.3,
        "delete_rate": 0.1,
        "avg_defer_days": 7.0,
    }

    analyzer = PatternAnalyzer()
    insights = analyzer.generate_insights(patterns)

    # Should have completion insight
    assert any("completed 60%" in insight for insight in insights)


def test_empty_history():
    """Test with no history"""
    analyzer = PatternAnalyzer()
    patterns = analyzer.analyze_history([])

    assert patterns == {}

    insights = analyzer.generate_insights(patterns)
    assert insights == []
