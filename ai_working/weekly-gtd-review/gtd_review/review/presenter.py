"""
Interactive Presenter brick - displays items and gets user input.

Uses rich for beautiful CLI presentation.
"""

import logging
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from ..session.schema import Decision
from ..sources.base import ReviewItem
from .recommender import Recommendation


class InteractivePresenter:
    """Present review items and gather user decisions"""

    def __init__(self):
        self.console = Console()
        self.logger = logging.getLogger("gtd_review.presenter")

    def present_item(
        self,
        item: ReviewItem,
        recommendation: Recommendation,
        context: dict[str, Any],
        current_index: int,
        total_items: int,
    ) -> Decision | None:
        """
        Present an item to the user and get their decision.

        Returns:
            Decision if user made a choice
            None if user chose to skip
        """
        # Clear screen for clean presentation
        self.console.clear()

        # Show progress
        self._show_progress(current_index, total_items)

        # Show the item
        self._show_item(item, context)

        # Show AI recommendation
        self._show_recommendation(recommendation)

        # Get user decision
        decision = self._get_user_decision(recommendation)

        return decision

    def _show_progress(self, current: int, total: int):
        """Show review progress"""
        progress_text = Text()
        progress_text.append("Review Progress: ", style="bold")
        progress_text.append(f"{current}/{total}", style="cyan")
        progress_text.append(f" ({(current / total) * 100:.0f}%)", style="dim")

        self.console.print(progress_text)
        self.console.print()

    def _show_item(self, item: ReviewItem, context: dict[str, Any]):
        """Display the review item"""
        # Create item panel
        content = []

        # Title
        title = Text(item.title, style="bold yellow")
        content.append(title)

        # Description
        if item.description:
            content.append(Text())
            content.append(Text(item.description, style="white"))

        # Metadata
        content.append(Text())
        metadata = []

        if item.due_date:
            overdue = (datetime.now() - item.due_date).days
            due_text = f"Due: {item.due_date.strftime('%Y-%m-%d')}"
            if overdue > 0:
                due_text += f" (overdue {overdue} days)"
                metadata.append(Text(due_text, style="red"))
            else:
                metadata.append(Text(due_text, style="green"))

        if item.priority:
            metadata.append(Text(f"Priority: {item.priority}", style="cyan"))

        if item.tags:
            metadata.append(Text(f"Tags: {', '.join(item.tags)}", style="blue"))

        if item.url:
            metadata.append(Text(f"URL: {item.url}", style="dim"))

        # Context info
        if context.get("age_days"):
            metadata.append(Text(f"Age: {context['age_days']} days", style="dim"))

        for meta in metadata:
            content.append(meta)

        panel = Panel(
            Text.assemble(*[c if isinstance(c, Text) else Text(str(c)) for c in content]),
            title=f"[bold cyan]{item.source.upper()}[/bold cyan]",
            border_style="cyan",
        )

        self.console.print(panel)
        self.console.print()

    def _show_recommendation(self, rec: Recommendation):
        """Display AI recommendation"""
        # Confidence color
        if rec.confidence >= 0.7:
            conf_style = "green"
        elif rec.confidence >= 0.4:
            conf_style = "yellow"
        else:
            conf_style = "red"

        # Create recommendation panel
        content = []
        content.append(Text("Action: ", style="bold") + Text(rec.action.upper(), style="bold green"))
        content.append(Text(f"Reasoning: {rec.reasoning}", style="white"))
        content.append(Text(f"Confidence: {rec.confidence:.0%}", style=conf_style))

        if rec.suggested_date:
            content.append(Text(f"Suggested date: {rec.suggested_date}", style="cyan"))

        if rec.suggested_priority:
            content.append(Text(f"Suggested priority: {rec.suggested_priority}", style="cyan"))

        panel = Panel(
            Text.assemble(*[c if isinstance(c, Text) else Text(str(c) + "\n") for c in content]),
            title="[bold magenta]AI Recommendation[/bold magenta]",
            border_style="magenta",
        )

        self.console.print(panel)
        self.console.print()

    def _get_user_decision(self, recommendation: Recommendation) -> Decision | None:
        """Get user's decision"""
        # Show options
        self.console.print("[bold]What would you like to do?[/bold]")
        self.console.print("  [green]1.[/green] Complete")
        self.console.print("  [yellow]2.[/yellow] Defer to next week")
        self.console.print("  [red]3.[/red] Delete")
        self.console.print("  [cyan]4.[/cyan] Reschedule")
        self.console.print("  [blue]5.[/blue] Change priority")
        self.console.print("  [dim]s.[/dim] Skip for now")
        self.console.print("  [dim]q.[/dim] Quit review")
        self.console.print()

        # Get choice
        choice = Prompt.ask(
            "Your choice",
            choices=["1", "2", "3", "4", "5", "s", "q"],
            default="1" if recommendation.action == "complete" else "2",
        )

        if choice == "q":
            raise KeyboardInterrupt()

        if choice == "s":
            return None

        # Map choice to action
        action_map = {
            "1": "complete",
            "2": "defer",
            "3": "delete",
            "4": "reschedule",
            "5": "prioritize",
        }

        action = action_map[choice]

        # Get additional details
        scheduled_date = None
        priority = None
        notes = None

        if action in ["defer", "reschedule"]:
            date_str = Prompt.ask(
                "Schedule for when? (YYYY-MM-DD or 'next week')",
                default=recommendation.suggested_date or "next week",
            )
            if date_str == "next week":
                # Calculate next week
                from datetime import timedelta

                scheduled_date = datetime.now() + timedelta(days=7)
            else:
                try:
                    scheduled_date = datetime.fromisoformat(date_str)
                except ValueError:
                    self.console.print("[red]Invalid date format, using next week[/red]")
                    scheduled_date = datetime.now() + timedelta(days=7)

        if action == "prioritize":
            priority_str = Prompt.ask(
                "Priority (1-5, 1=highest)",
                default=str(recommendation.suggested_priority or 3),
            )
            try:
                priority = int(priority_str)
            except ValueError:
                priority = 3

        # Optional notes
        notes = Prompt.ask("Add notes (optional)", default="")

        return Decision(
            action=action,
            timestamp=datetime.now(),
            scheduled_date=scheduled_date,
            priority=priority,
            notes=notes if notes else None,
        )

    def show_insights(self, insights: dict[str, Any]):
        """Display insights at end of review"""
        self.console.clear()

        # Create insights table
        table = Table(title="Review Insights", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        for key, value in insights.items():
            table.add_row(key.replace("_", " ").title(), str(value))

        self.console.print(table)
        self.console.print()

        # Summary message
        self.console.print(
            Panel(
                "[bold green]Weekly review complete![/bold green]\n\n"
                "Your decisions have been saved and will be synced to your systems.",
                border_style="green",
            )
        )
