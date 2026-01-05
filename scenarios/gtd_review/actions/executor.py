"""
Action executor - routes decisions to appropriate data sources for execution.
"""

import logging
from dataclasses import dataclass

from ..session.schema import Decision
from ..sources.base import DataSource
from ..sources.base import ReviewItem

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of executing an action"""

    success: bool
    error: str | None = None


class ActionExecutor:
    """Execute user decisions on appropriate data sources"""

    def __init__(self, sources: dict[str, DataSource]):
        self.sources = sources

    async def execute(self, item: ReviewItem, decision: Decision) -> ExecutionResult:
        """
        Execute decision on appropriate source.
        Returns success/failure status.
        """
        source = self.sources.get(item.source)
        if not source:
            error = f"Unknown source: {item.source}"
            logger.error(error)
            return ExecutionResult(success=False, error=error)

        try:
            # Build kwargs from decision
            kwargs = {}
            if decision.scheduled_date:
                kwargs["scheduled_date"] = decision.scheduled_date
            if decision.priority:
                kwargs["priority"] = decision.priority
            if decision.notes:
                kwargs["notes"] = decision.notes

            # Execute on source
            await source.execute_action(item, decision.action, **kwargs)

            logger.info(f"Executed {decision.action} on {item.id}")
            return ExecutionResult(success=True)

        except Exception as e:
            error = f"Failed to execute {decision.action} on {item.id}: {e}"
            logger.error(error)
            return ExecutionResult(success=False, error=error)
