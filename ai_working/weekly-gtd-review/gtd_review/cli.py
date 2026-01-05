"""
CLI entry point for GTD review tool.
"""

import asyncio
import logging

import click

from .actions.executor import ActionExecutor
from .analytics.patterns import PatternAnalyzer
from .orchestrator import GTDReviewOrchestrator
from .review.presenter import InteractivePresenter
from .review.recommender import AIRecommender
from .session.manager import SessionManager
from .sources.reading_queue import ReadingQueueSource
from .sources.reminders import RemindersSource

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger("gtd_review")


def create_orchestrator() -> GTDReviewOrchestrator:
    """Factory function to create orchestrator with all dependencies"""

    # Create all the bricks
    session_manager = SessionManager()

    # Data sources
    reminders_source = RemindersSource()
    reading_source = ReadingQueueSource()
    # TODO: Add CalendarSource when ready
    sources = [reminders_source, reading_source]

    # AI and presentation
    recommender = AIRecommender()
    presenter = InteractivePresenter()

    # Execution and analytics
    executor = ActionExecutor({s.name(): s for s in sources})
    analyzer = PatternAnalyzer()

    # Wire it all together
    orchestrator = GTDReviewOrchestrator(
        sources=sources,
        session_manager=session_manager,
        recommender=recommender,
        presenter=presenter,
        executor=executor,
        analyzer=analyzer,
    )

    return orchestrator


@click.command()
@click.option("--resume/--no-resume", default=True, help="Resume previous session if available")
@click.option(
    "--sources",
    default="reminders,reading",
    help="Comma-separated list of sources to review (reminders,reading,calendar)",
)
def main(resume: bool, sources: str):
    """
    Run interactive weekly GTD review.

    Reviews todos, reading queue, and calendar events with AI-powered recommendations.
    """
    logger.info("🗓️  Starting Weekly GTD Review")
    logger.info(f"Resume mode: {resume}")
    logger.info(f"Sources: {sources}")

    try:
        # Create orchestrator
        orchestrator = create_orchestrator()

        # Run review
        asyncio.run(orchestrator.run_review(resume=resume))

    except KeyboardInterrupt:
        logger.info("\n👋 Review paused. Run again to resume.")
    except Exception as e:
        logger.error(f"Review failed: {e}")
        raise


if __name__ == "__main__":
    main()
