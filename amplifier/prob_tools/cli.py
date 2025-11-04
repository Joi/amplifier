"""
CLI for probabilistic git history analysis
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from amplifier.prob_tools.agent_api import AgentAPI
from amplifier.prob_tools.event_store import EventStore
from amplifier.prob_tools.git_analyzer import GitAnalyzer
from amplifier.prob_tools.llm_extractor import LLMExtractor


@click.group()
def cli():
    """Probabilistic git history analysis and bug prediction"""
    pass


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True, path_type=Path))
@click.option("--limit", "-n", type=int, default=50, help="Number of commits to analyze")
async def extract(repo_path: Path, limit: int):
    """Extract bug patterns from git history using LLM analysis"""

    click.echo(f"🔍 Analyzing last {limit} commits in {repo_path}")

    # Initialize components
    git_analyzer = GitAnalyzer(repo_path)
    llm_extractor = LLMExtractor()
    event_store = EventStore()

    # Get bug fix commits
    click.echo("📋 Finding bug fix commits...")
    bug_commits = git_analyzer.get_bug_fix_commits(limit)
    click.echo(f"   Found {len(bug_commits)} potential bug fixes")

    # Extract events with LLM
    click.echo("\n🤖 Analyzing commits with LLM...")
    bug_events = 0
    refactoring_events = 0

    with click.progressbar(bug_commits, label="Analyzing") as commits:
        for commit in commits:
            # Extract bug event
            bug_event = await llm_extractor.extract_bug_event(commit)
            if bug_event:
                event_store.store_bug_event(bug_event)
                bug_events += 1

            # Extract refactoring event
            refactoring_event = await llm_extractor.extract_refactoring_event(commit)
            if refactoring_event:
                event_store.store_refactoring_event(refactoring_event)
                refactoring_events += 1

    click.echo(f"\n✅ Extracted {bug_events} bug events, {refactoring_events} refactoring events")

    # Show patterns
    patterns = event_store.get_bug_patterns()
    if patterns:
        click.echo("\n📊 Bug Patterns Found:")
        for bug_type, stats in sorted(patterns.items(), key=lambda x: x[1]["count"], reverse=True)[:5]:
            preventable_pct = stats["preventable_pct"] * 100
            click.echo(f"   • {bug_type}: {stats['count']} occurrences ({preventable_pct:.0f}% preventable)")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--function", "-f", help="Specific function to check")
def check(file_path: Path, function: str | None):
    """Check code for bug risk using learned patterns"""

    click.echo(f"🔍 Analyzing {file_path}")

    api = AgentAPI()

    # Get historical context
    patterns = api.get_historical_patterns()
    total_events = patterns["total_bug_events"]

    if total_events == 0:
        click.echo("\n⚠️  No historical data found. Run 'extract' first to learn patterns.")
        return

    click.echo(f"   Using {total_events} bug events from history")

    # Check code
    result = api.check_code_before_commit(str(file_path), function)

    if "error" in result:
        click.echo(f"\n❌ {result['error']}")
        return

    if function:
        # Single function result
        pred = result["prediction"]
        features = result["features"]

        click.echo(f"\n📊 Analysis for {function}():")
        click.echo(f"   Bug probability: {pred['bug_probability']:.1%}")
        click.echo(f"   Confidence: {pred['confidence']:.1%}")
        click.echo("\n   Features:")
        click.echo(f"   • Null checks: {'✓' if features['has_null_check'] else '✗'}")
        click.echo(f"   • Error handling: {'✓' if features['has_error_handling'] else '✗'}")
        click.echo(f"   • Complexity: {features['complexity']:.2f}")
        click.echo(f"   • Async: {'Yes' if features['is_async'] else 'No'}")
        click.echo(f"\n   {pred['recommendation']}")
    else:
        # Multiple functions
        click.echo(f"\n📊 Analyzed {result['functions_analyzed']} functions:")
        for func_result in result["results"][:5]:
            pred = func_result["prediction"]
            risk_level = "🔴" if pred["bug_probability"] > 0.7 else "🟡" if pred["bug_probability"] > 0.4 else "🟢"
            click.echo(f"   {risk_level} {func_result['function']}(): {pred['bug_probability']:.1%} bug probability")


@cli.command()
def patterns():
    """Show learned bug patterns"""

    api = AgentAPI()
    patterns_data = api.get_historical_patterns()

    total_bugs = patterns_data["total_bug_events"]
    total_refactorings = patterns_data["total_refactoring_events"]

    click.echo("📊 Historical Events:")
    click.echo(f"   Bug events: {total_bugs}")
    click.echo(f"   Refactoring events: {total_refactorings}")

    if total_bugs == 0:
        click.echo("\n⚠️  No data found. Run 'extract' first.")
        return

    click.echo("\n🐛 Bug Patterns:")
    patterns = patterns_data["bug_patterns"]

    for bug_type, stats in sorted(patterns.items(), key=lambda x: x[1]["count"], reverse=True):
        click.echo(f"\n   {bug_type}:")
        click.echo(f"   • Count: {stats['count']}")
        click.echo(f"   • Preventable: {stats['preventable_pct']:.0%}")
        if stats["prevention_methods"]:
            methods = set(stats["prevention_methods"])
            click.echo(f"   • Prevention: {', '.join(methods)}")


def main():
    """Entry point that handles async"""
    import sys

    # Check if command needs async
    if len(sys.argv) > 1 and sys.argv[1] == "extract":
        asyncio.run(cli())
    else:
        cli()


if __name__ == "__main__":
    main()
