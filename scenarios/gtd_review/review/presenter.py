"""
Interactive presentation layer using rich for beautiful CLI output.

Presents items to user with AI recommendations and captures their decisions.
"""

from datetime import datetime
from datetime import timedelta

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ..session.schema import Decision
from ..sources.base import ReviewItem
from .recommender import Recommendation


class InteractivePresenter:
    """Present items interactively and capture user decisions"""

    def __init__(self):
        self.console = Console()

    def present_item(
        self, item: ReviewItem, recommendation: Recommendation, context: dict, index: int, total: int
    ) -> Decision | None:
        """
        Display item with AI recommendation and prompt for decision.
        Returns user's decision or None if skipped.
        """
        # Clear screen and show header
        self.console.clear()
        self.console.rule("[bold blue]Weekly GTD Review", style="blue")
        self.console.print(f"\n[dim]Item {index}/{total} from {item.source}[/dim]\n")

        # Create item display panel
        item_content = f"[bold]{item.title}[/bold]\n\n"

        if item.description:
            item_content += f"{item.description}\n\n"

        # Add metadata
        metadata_table = Table(show_header=False, box=None)
        if item.due_date:
            overdue = (datetime.now() - item.due_date).days if item.due_date < datetime.now() else None
            due_str = item.due_date.strftime("%Y-%m-%d")
            if overdue and overdue > 0:
                due_str += f" [red](Overdue by {overdue} days)[/red]"
            metadata_table.add_row("Due:", due_str)

        if item.priority:
            priority_map = {1: "[red]High[/red]", 2: "[yellow]Medium[/yellow]", 3: "[green]Low[/green]"}
            metadata_table.add_row("Priority:", priority_map.get(item.priority, "Unknown"))

        if item.tags:
            metadata_table.add_row("Tags:", ", ".join(item.tags))

        if context.get("age_days"):
            metadata_table.add_row("Age:", f"{context['age_days']} days")

        if item.url:
            metadata_table.add_row("URL:", f"[link]{item.url}[/link]")

        item_content += metadata_table.__str__()

        self.console.print(Panel(item_content, title=f"[bold]{item.source.upper()}[/bold]", border_style="blue"))

        # Show AI recommendation
        confidence_color = (
            "green" if recommendation.confidence > 0.7 else "yellow" if recommendation.confidence > 0.4 else "red"
        )
        rec_content = f"[bold]Action:[/bold] {recommendation.action}\n"
        rec_content += (
            f"[bold]Confidence:[/bold] [{confidence_color}]{recommendation.confidence:.0%}[/{confidence_color}]\n"
        )
        rec_content += f"[bold]Reasoning:[/bold] {recommendation.reasoning}\n"

        if recommendation.suggested_date:
            rec_content += f"[bold]Suggested Date:[/bold] {recommendation.suggested_date.strftime('%Y-%m-%d')}\n"

        if recommendation.priority:
            priority_map = {1: "High", 2: "Medium", 3: "Low"}
            rec_content += f"[bold]Suggested Priority:[/bold] {priority_map.get(recommendation.priority, 'Unknown')}"

        self.console.print(Panel(rec_content, title="[bold]AI Recommendation[/bold]", border_style="green"))

        # Prompt for action
        self.console.print("\n[bold]What would you like to do?[/bold]")
        choice = Prompt.ask(
            "Action",
            choices=["complete", "defer", "delete", "skip", "quit"],
            default=recommendation.action if recommendation.action != "reschedule" else "defer",
        )

        if choice == "quit":
            raise KeyboardInterrupt("User quit review")

        if choice == "skip":
            # Return None to indicate skip
            return None

        # Build decision
        decision = Decision(action=choice, timestamp=datetime.now())

        # Get additional details based on action
        if choice == "defer":
            days = Prompt.ask("Defer for how many days?", default="7")
            decision.scheduled_date = datetime.now() + timedelta(days=int(days))
            notes = Prompt.ask("Notes (optional)", default="")
            decision.notes = notes if notes else None

        elif choice == "prioritize":
            priority = Prompt.ask("Priority", choices=["1", "2", "3"], default="1")
            decision.priority = int(priority)

        return decision

    def show_insights(self, insights: list[str]):
        """Display insights at end of review"""
        self.console.clear()
        self.console.rule("[bold blue]Review Complete!", style="blue")

        if insights:
            self.console.print("\n[bold]Insights from your review:[/bold]\n")
            for insight in insights:
                self.console.print(f"  • {insight}")
        else:
            self.console.print("\n[dim]No insights generated this time.[/dim]")

        self.console.print("\n[green]Weekly review complete![/green]\n")
