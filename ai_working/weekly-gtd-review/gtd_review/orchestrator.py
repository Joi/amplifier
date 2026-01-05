"""
Orchestrator - coordinates the entire weekly GTD review workflow.

This is the "main" component that wires all the bricks together:
- Session management
- Data source loading
- AI recommendations
- Interactive presentation
- Decision execution
- Pattern analysis
"""

import logging

from .actions.executor import ActionExecutor
from .analytics.patterns import PatternAnalyzer
from .review.presenter import InteractivePresenter
from .review.recommender import AIRecommender
from .session.manager import SessionManager
from .session.schema import SessionState
from .sources.base import DataSource
from .sources.base import ReviewItem


class GTDReviewOrchestrator:
    """Coordinate the entire review workflow"""

    def __init__(
        self,
        sources: list[DataSource],
        session_manager: SessionManager,
        recommender: AIRecommender,
        presenter: InteractivePresenter,
        executor: ActionExecutor,
        analyzer: PatternAnalyzer,
    ):
        self.sources = {s.name(): s for s in sources}
        self.session_manager = session_manager
        self.recommender = recommender
        self.presenter = presenter
        self.executor = executor
        self.analyzer = analyzer
        self.logger = logging.getLogger("gtd_review.orchestrator")

    async def run_review(self, resume: bool = True) -> None:
        """
        Main workflow:
        1. Load or create session
        2. Load items from all sources
        3. For each item:
           a. Get AI recommendation
           b. Present to user
           c. Execute decision
           d. Save progress
        4. Generate insights at end
        5. Mark session complete
        """
        try:
            # Stage 1: Session setup
            session = await self._setup_session(resume)

            # Stage 2: Load all items
            all_items = await self._load_all_items()

            # Stage 3: Filter to unreviewed items
            remaining = [item for item in all_items if item.id not in session.reviewed_items]

            if not remaining:
                self.logger.info("No items to review!")
                return

            self.logger.info(f"Found {len(remaining)} items to review")

            # Stage 4: Review loop
            await self._review_loop(session, remaining)

            # Stage 5: Final insights
            await self._show_insights(session)

            # Stage 6: Complete session
            session.completed = True
            self.session_manager.save_progress(session)

        except KeyboardInterrupt:
            self.logger.info("\n⏸️  Review paused. Run again with --resume to continue.")
        except Exception as e:
            self.logger.error(f"Review failed: {e}")
            raise
        finally:
            # Clean up
            await self.recommender.close()

    async def _setup_session(self, resume: bool) -> SessionState:
        """Set up or resume session"""
        if resume and self.session_manager.can_resume():
            session = self.session_manager.get_latest_session()
            self.logger.info(f"📝 Resuming session from {session.current_source}")
            return session
        session = self.session_manager.create_session()
        self.logger.info(f"🆕 Starting new review session: {session.session_id}")
        return session

    async def _load_all_items(self) -> list[ReviewItem]:
        """Load items from all data sources"""
        all_items = []

        for source_name, source in self.sources.items():
            try:
                self.logger.info(f"Loading items from {source_name}...")
                items = await source.load_items()
                all_items.extend(items)
                self.logger.info(f"  Found {len(items)} items from {source_name}")
            except Exception as e:
                self.logger.error(f"Failed to load from {source_name}: {e}")
                self.logger.warning(f"Skipping {source_name}, continuing with other sources")
                continue

        return all_items

    async def _review_loop(self, session: SessionState, items: list[ReviewItem]) -> None:
        """Main review loop - process each item"""
        for index, item in enumerate(items, 1):
            try:
                # Update session position
                session.current_source = item.source
                session.current_index = index

                # Get source for context
                source = self.sources.get(item.source)
                if not source:
                    self.logger.error(f"Unknown source: {item.source}")
                    continue

                # Get AI recommendation
                context = source.get_context(item)
                history = list(session.decisions.values())

                self.logger.info(f"Getting AI recommendation for {item.id}...")
                recommendation = await self.recommender.recommend(item, context, history)

                # Present to user
                decision = self.presenter.present_item(item, recommendation, context, index, len(items))

                # Handle skip
                if decision is None:
                    self.logger.info(f"Skipped {item.id}")
                    continue

                # Execute decision
                result = await self.executor.execute(item, decision)

                if not result.success:
                    self.logger.error(f"Failed to execute: {result.error}")
                    # Ask user if they want to retry
                    continue

                # Save progress immediately
                self.session_manager.mark_reviewed(session, item.id, decision)

            except KeyboardInterrupt:
                # User wants to pause
                raise
            except Exception as e:
                self.logger.error(f"Error processing {item.id}: {e}")
                # Continue with next item
                continue

    async def _show_insights(self, session: SessionState) -> None:
        """Generate and show insights"""
        patterns = self.analyzer.analyze_history(list(session.decisions.values()))
        insights = self.analyzer.generate_insights(patterns)
        self.presenter.show_insights(insights)
