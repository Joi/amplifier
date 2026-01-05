"""
Weekly GTD Review Tool

AI-powered weekly review system that integrates with reading queue, todos, and calendar.
Provides intelligent recommendations and helps maintain a clean GTD system.

Public Interface:
- run_review(): Main entry point for interactive review
"""

__all__ = ["run_review"]


async def run_review():
    """Run interactive weekly review"""
    # Import here to avoid circular dependencies and allow tests to run
    from .review.orchestrator import ReviewOrchestrator

    orchestrator = ReviewOrchestrator()
    await orchestrator.run()
