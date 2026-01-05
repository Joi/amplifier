"""
Action Executor brick - executes user decisions across data sources.
"""

import logging
from dataclasses import dataclass

from ..session.schema import Decision
from ..sources.base import DataSource
from ..sources.base import ReviewItem


@dataclass
class ExecutionResult:
    """Result of executing an action"""

    success: bool
    error: str | None = None


class ActionExecutor:
    """Execute decisions across different data sources"""

    def __init__(self, sources: dict[str, DataSource]):
        self.sources = sources
        self.logger = logging.getLogger("gtd_review.executor")

    async def execute(self, item: ReviewItem, decision: Decision) -> ExecutionResult:
        """
        Execute a user decision on an item.

        Args:
            item: The review item
            decision: The user's decision

        Returns:
            ExecutionResult with success status
        """
        # Get the source
        source = self.sources.get(item.source)
        if not source:
            return ExecutionResult(
                success=False,
                error=f"Unknown source: {item.source}",
            )

        try:
            # Build kwargs from decision
            kwargs = {}
            if decision.scheduled_date:
                kwargs["scheduled_date"] = decision.scheduled_date
            if decision.priority is not None:
                kwargs["priority"] = decision.priority
            if decision.notes:
                kwargs["notes"] = decision.notes

            # Execute the action
            await source.execute_action(item, decision.action, **kwargs)

            self.logger.info(f"Executed {decision.action} on {item.source}:{item.id}")

            return ExecutionResult(success=True)

        except Exception as e:
            self.logger.error(f"Failed to execute {decision.action} on {item.id}: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
            )
