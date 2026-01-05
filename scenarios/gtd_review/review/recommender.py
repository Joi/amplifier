"""
AI-powered recommendation engine using ClaudeSession.

Provides intelligent suggestions for each review item based on context and history.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Any

from amplifier.ccsdk_toolkit.claude_session import ClaudeSession
from amplifier.ccsdk_toolkit.claude_session import SessionOptions
from amplifier.ccsdk_toolkit.defensive.parse_llm_json import parse_llm_json

from ..session.schema import Decision
from ..sources.base import ReviewItem


@dataclass
class Recommendation:
    """AI recommendation for a review item"""

    action: str  # complete, defer, delete, reschedule, prioritize
    confidence: float  # 0.0-1.0
    reasoning: str
    suggested_date: datetime | None = None
    priority: int | None = None


class AIRecommender:
    """Generate AI-powered recommendations for review items"""

    def __init__(self):
        self.claude_session = None

    async def _get_session(self) -> ClaudeSession:
        """Get or create Claude session"""
        if self.claude_session is None:
            self.claude_session = ClaudeSession(
                SessionOptions(
                    system_prompt="""You are a GTD (Getting Things Done) productivity assistant helping with weekly review.

Your role is to analyze todos, reading items, and calendar events, then recommend actions based on:
- Item age and staleness
- Priority and urgency
- Patterns from past decisions
- Context clues (overdue, deferred multiple times, etc.)

Recommend one of: complete, defer, delete, reschedule, prioritize

Be concise but specific in your reasoning.""",
                    model="claude-haiku",  # Fast, cheap model for recommendations
                )
            )
        return self.claude_session

    async def recommend(
        self, item: ReviewItem, context: dict[str, Any], history: list[Decision] | None = None
    ) -> Recommendation:
        """Generate recommendation for an item"""
        session = await self._get_session()

        # Build prompt
        prompt = self._build_prompt(item, context, history or [])

        # Query Claude
        response = await session.query(prompt)

        # Parse JSON response
        try:
            rec_data = parse_llm_json(response)
        except Exception as e:
            # Fallback: safe default recommendation
            return Recommendation(
                action="defer",
                confidence=0.3,
                reasoning=f"Could not parse AI response: {e}",
                suggested_date=datetime.now() + timedelta(days=7),
            )

        # Create recommendation
        return Recommendation(
            action=rec_data.get("action", "defer"),
            confidence=float(rec_data.get("confidence", 0.5)),
            reasoning=rec_data.get("reasoning", "No reasoning provided"),
            suggested_date=(
                datetime.fromisoformat(rec_data["suggested_date"]) if rec_data.get("suggested_date") else None
            ),
            priority=rec_data.get("priority"),
        )

    def _build_prompt(self, item: ReviewItem, context: dict[str, Any], history: list[Decision]) -> str:
        """Build recommendation prompt"""
        age_days = context.get("age_days", "unknown")
        overdue_days = context.get("overdue_days")

        # Build pattern summary
        pattern_summary = self._summarize_patterns(history)

        prompt = f"""Analyze this item and recommend an action.

ITEM DETAILS:
- Source: {item.source}
- Title: {item.title}
- Description: {item.description or "None"}
- Due: {item.due_date.strftime("%Y-%m-%d") if item.due_date else "None"}
- Priority: {item.priority or "None"}
- Age: {age_days} days
- Tags: {", ".join(item.tags) if item.tags else "None"}

CONTEXT:
{json.dumps(context, indent=2)}

{pattern_summary}

RECOMMEND ONE ACTION:
- complete: Mark as done or obsolete
- defer: Not ready yet, suggest new date
- delete: No longer relevant
- reschedule: Wrong timing, suggest new date
- prioritize: Important but buried, suggest priority level (1=high, 2=medium, 3=low)

Respond ONLY with JSON in this format:
{{
  "action": "defer",
  "confidence": 0.85,
  "reasoning": "One sentence explanation",
  "suggested_date": "2025-01-15T09:00:00" (if defer/reschedule),
  "priority": 1 (if prioritize)
}}"""

        return prompt

    def _summarize_patterns(self, history: list[Decision]) -> str:
        """Summarize patterns from review history"""
        if not history:
            return "PATTERNS: No history available"

        # Count actions
        action_counts = {}
        for decision in history:
            action_counts[decision.action] = action_counts.get(decision.action, 0) + 1

        summary = f"PATTERNS (from {len(history)} past reviews):\n"
        summary += f"- Most common action: {max(action_counts, key=action_counts.get)}\n"
        summary += f"- Defer rate: {action_counts.get('defer', 0) / len(history) * 100:.0f}%"

        return summary

    async def close(self):
        """Clean up Claude session"""
        if self.claude_session:
            await self.claude_session.close()
