"""
AI Recommender brick - generates recommendations using Claude.

Uses Claude Haiku for fast, cost-effective recommendations.
"""

import logging
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent

from ..session.schema import Decision
from ..sources.base import ReviewItem


@dataclass
class Recommendation:
    """AI recommendation for a review item"""

    action: str  # complete, defer, delete, reschedule, prioritize
    reasoning: str
    confidence: float  # 0-1
    suggested_date: str | None = None
    suggested_priority: int | None = None


class AIRecommender:
    """Generate AI-powered recommendations for review items"""

    def __init__(self):
        self.logger = logging.getLogger("gtd_review.recommender")
        self.agent = Agent(
            "claude-3-5-haiku-20241022",
            system_prompt=self._get_system_prompt(),
        )

    def _get_system_prompt(self) -> str:
        """System prompt for the AI agent"""
        return """You are a GTD (Getting Things Done) productivity assistant helping with weekly reviews.

Your job is to recommend actions for todo items, reading queue entries, and calendar events.

Available actions:
- complete: Mark as done (if already completed or no longer relevant)
- defer: Postpone to next week or later
- delete: Remove entirely (if obsolete or not actionable)
- reschedule: Change the due date
- prioritize: Adjust the priority level

Consider:
- How long the item has been pending
- Whether it's overdue and by how much
- The user's past decisions on similar items
- Urgency vs importance

Respond with:
1. Recommended action
2. Brief reasoning (1-2 sentences)
3. Confidence level (0-1)
4. Suggested date (if rescheduling/deferring)
5. Suggested priority (if prioritizing)

Be concise and actionable."""

    async def recommend(
        self,
        item: ReviewItem,
        context: dict[str, Any],
        history: list[Decision],
    ) -> Recommendation:
        """
        Generate recommendation for an item.

        Args:
            item: The item to review
            context: Additional context from the data source
            history: Past decisions for pattern learning
        """
        # Build prompt
        prompt = self._build_prompt(item, context, history)

        try:
            # Get recommendation from AI
            result = await self.agent.run(prompt)
            response_text = result.data

            # Parse the response
            recommendation = self._parse_response(response_text)
            return recommendation

        except Exception as e:
            self.logger.error(f"AI recommendation failed: {e}")
            # Return safe default
            return Recommendation(
                action="defer",
                reasoning="Unable to generate recommendation. Suggest manual review.",
                confidence=0.0,
            )

    def _build_prompt(
        self,
        item: ReviewItem,
        context: dict[str, Any],
        history: list[Decision],
    ) -> str:
        """Build the prompt for AI recommendation"""
        parts = [
            "# Item to Review",
            f"Title: {item.title}",
            f"Source: {item.source}",
        ]

        if item.description:
            parts.append(f"Description: {item.description}")

        if item.due_date:
            parts.append(f"Due date: {item.due_date}")

        if item.priority:
            parts.append(f"Priority: {item.priority}")

        if item.tags:
            parts.append(f"Tags: {', '.join(item.tags)}")

        # Add context
        parts.append("\n# Context")
        for key, value in context.items():
            if value is not None:
                parts.append(f"{key}: {value}")

        # Add relevant history
        if history:
            parts.append("\n# Recent Similar Decisions")
            # Show last 5 decisions
            for decision in history[-5:]:
                parts.append(f"- {decision.action}: {decision.notes or 'no notes'}")

        parts.append("\n# Your Recommendation")

        return "\n".join(parts)

    def _parse_response(self, response: str) -> Recommendation:
        """
        Parse AI response into Recommendation.

        Expected format:
        Action: [action]
        Reasoning: [reasoning]
        Confidence: [0-1]
        Suggested date: [date or None]
        Suggested priority: [int or None]
        """
        lines = response.strip().split("\n")
        action = "defer"
        reasoning = "No reasoning provided"
        confidence = 0.5
        suggested_date = None
        suggested_priority = None

        for line in lines:
            line = line.strip()
            if line.lower().startswith("action:"):
                action = line.split(":", 1)[1].strip().lower()
            elif line.lower().startswith("reasoning:"):
                reasoning = line.split(":", 1)[1].strip()
            elif line.lower().startswith("confidence:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except ValueError:
                    confidence = 0.5
            elif line.lower().startswith("suggested date:"):
                date_str = line.split(":", 1)[1].strip()
                if date_str.lower() not in ["none", "n/a", ""]:
                    suggested_date = date_str
            elif line.lower().startswith("suggested priority:"):
                try:
                    priority_str = line.split(":", 1)[1].strip()
                    if priority_str.lower() not in ["none", "n/a", ""]:
                        suggested_priority = int(priority_str)
                except ValueError:
                    suggested_priority = None

        return Recommendation(
            action=action,
            reasoning=reasoning,
            confidence=confidence,
            suggested_date=suggested_date,
            suggested_priority=suggested_priority,
        )

    async def close(self):
        """Clean up resources"""
        # pydantic_ai handles cleanup automatically
        pass
