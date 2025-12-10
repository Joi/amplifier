#!/usr/bin/env python3
"""
Knowledge Curator - Main CLI and orchestrator.

A Wikipedia-editor style agent that curates knowledge vaults by:
1. Scanning files for uncited claims
2. Searching for authoritative sources
3. Adding citations to files
4. Generating knowledge status reports

Enhanced with metacognitive feedback loops:
- Citation verification ensures sources actually support claims
- Learning from past runs optimizes future searches
- Progressive refinement improves search quality over time
"""

import asyncio
import sys
from pathlib import Path

import click

from amplifier.utils.logger import get_logger

from .citation_adder import CitationAdder
from .citation_rules import load_rules
from .claim_extractor import ClaimExtractor
from .expansion_suggester import ExpansionSuggester
from .expansion_suggester import SuggestionStatus
from .expansion_suggester import SuggestionStore
from .gap_detector import GapDetector
from .gap_reporter import GapReporter
from .learning import CuratorLearning
from .source_searcher import SourceSearcher
from .state import StateManager

logger = get_logger(__name__)

# Default paths
DEFAULT_STATE_DIR = Path.home() / ".data" / "knowledge_curator"
DEFAULT_STATUS_FILE = Path.home() / "switchboard" / "amplifier" / "knowledge-status.json"


async def run_curation(
    vault_path: Path,
    domain: str | None,
    resume: bool,
    report_only: bool,
    state_dir: Path,
    status_file: Path,
    verify_citations: bool = True,
    enable_learning: bool = True,
) -> int:
    """Run the full curation pipeline."""
    logger.info(f"Starting knowledge curation for: {vault_path}")
    if domain:
        logger.info(f"Domain filter: {domain}")

    # Initialize state manager
    state_mgr = StateManager(state_dir)

    # Resume or initialize
    if resume:
        state = state_mgr.load()
        if state is None:
            logger.warning("No existing state to resume, starting fresh")
            state = state_mgr.initialize(str(vault_path), domain)
    else:
        state = state_mgr.initialize(str(vault_path), domain)

    # Initialize pipeline stages
    extractor = ClaimExtractor()
    adder = CitationAdder()
    reporter = GapReporter(status_file)

    # Determine target path
    target_path = vault_path / domain if domain else vault_path

    # Load citation rules from target directory (or use defaults)
    citation_rules = load_rules(target_path)

    # Find markdown files
    md_files = list(target_path.glob("**/*.md"))
    logger.info(f"Found {len(md_files)} markdown files")
    state_mgr.update_stats(total_files=len(md_files))

    if not md_files:
        logger.warning("No markdown files found")
        return 1

    # Stage 1: Scan for claims
    if state.stage == "scan":
        logger.info("Stage 1: Scanning for claims...")
        state_mgr.update_stage("scan")

        for md_file in md_files:
            rel_path = str(md_file.relative_to(vault_path))

            # Skip if already processed
            if rel_path in state.files and state.files[rel_path].claims_extracted:
                continue

            try:
                claims = await extractor.extract_claims(md_file)
                state_mgr.update_file(
                    rel_path,
                    claims_extracted=True,
                    claims=[c.model_dump() for c in claims],
                )
                if claims:
                    state_mgr.update_stats(
                        files_scanned=state.stats["files_scanned"] + 1,
                        files_with_claims=state.stats["files_with_claims"] + 1,
                    )
                else:
                    state_mgr.update_stats(files_scanned=state.stats["files_scanned"] + 1)
                logger.debug(f"  {rel_path}: {len(claims)} claims found")
            except Exception as e:
                logger.error(f"  {rel_path}: Error extracting claims: {e}")
                state_mgr.update_file(rel_path, error=str(e))

        state_mgr.update_stage("search")

    # Stage 2: Search for sources
    if state.stage == "search" and not report_only:
        logger.info("Stage 2: Searching for sources...")
        if verify_citations:
            logger.info("  (with citation verification enabled)")
        if enable_learning:
            logger.info("  (with learning enabled)")

        async with SourceSearcher(
            rules=citation_rules,
            verify_citations=verify_citations,
            enable_learning=enable_learning,
        ) as searcher:
            for rel_path, file_state in state.files.items():
                if not file_state.claims or file_state.sources_found:
                    continue

                try:
                    sources = await searcher.search_sources(file_state.claims)
                    state_mgr.update_file(
                        rel_path,
                        sources_found=True,
                        sources=[s.model_dump() for s in sources],
                    )
                    state_mgr.update_stats(sources_found=state.stats["sources_found"] + len(sources))
                    logger.debug(f"  {rel_path}: {len(sources)} sources found")
                except Exception as e:
                    logger.error(f"  {rel_path}: Error searching sources: {e}")
                    state_mgr.update_file(rel_path, error=str(e))

        state_mgr.update_stage("cite")

    # Stage 3: Add citations
    if state.stage == "cite" and not report_only:
        logger.info("Stage 3: Adding citations...")

        for rel_path, file_state in state.files.items():
            if not file_state.sources or file_state.citations_added:
                continue

            try:
                file_path = vault_path / rel_path
                citations_added = await adder.add_citations(file_path, file_state.claims, file_state.sources)
                state_mgr.update_file(
                    rel_path,
                    citations_added=True,
                    citations_count=citations_added,
                )
                state_mgr.update_stats(citations_added=state.stats["citations_added"] + citations_added)
                logger.debug(f"  {rel_path}: {citations_added} citations added")
            except Exception as e:
                logger.error(f"  {rel_path}: Error adding citations: {e}")
                state_mgr.update_file(rel_path, error=str(e))

        state_mgr.update_stage("report")

    # Stage 4: Generate report
    logger.info("Stage 4: Generating report...")
    await reporter.generate_report(state, vault_path, domain)
    state_mgr.mark_complete()

    # Summary
    logger.info("\n=== Curation Complete ===")
    logger.info(f"Files scanned: {state.stats['files_scanned']}")
    logger.info(f"Files with claims: {state.stats['files_with_claims']}")
    logger.info(f"Sources found: {state.stats['sources_found']}")
    logger.info(f"Citations added: {state.stats['citations_added']}")

    return 0


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--vault",
    "-v",
    type=click.Path(exists=True, path_type=Path),
    default=Path.home() / "switchboard",
    help="Path to knowledge vault",
)
@click.option(
    "--domain",
    "-d",
    type=str,
    default=None,
    help="Specific domain/folder to process (e.g., 'chanoyu/')",
)
@click.option(
    "--resume",
    "-r",
    is_flag=True,
    help="Resume interrupted curation run",
)
@click.option(
    "--report-only",
    is_flag=True,
    help="Generate report without modifying files",
)
@click.option(
    "--state-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_STATE_DIR,
    help="Directory for state files",
)
@click.option(
    "--status-file",
    type=click.Path(path_type=Path),
    default=DEFAULT_STATUS_FILE,
    help="Path to knowledge-status.json",
)
@click.option(
    "--no-verify",
    is_flag=True,
    help="Disable citation verification (faster but less accurate)",
)
@click.option(
    "--no-learning",
    is_flag=True,
    help="Disable learning from outcomes",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
def main(
    ctx: click.Context,
    vault: Path,
    domain: str | None,
    resume: bool,
    report_only: bool,
    state_dir: Path,
    status_file: Path,
    no_verify: bool,
    no_learning: bool,
    verbose: bool,
) -> None:
    """
    Knowledge Curator - Wikipedia-editor style agent for knowledge vaults.

    Processes markdown files to find claims needing citations, searches for
    authoritative sources, and adds citations to files.

    Enhanced with metacognitive feedback loops:
    - Citation verification ensures sources actually support claims
    - Learning from past runs optimizes future searches

    Examples:

        # Process entire vault
        python -m scenarios.knowledge_curator --vault ~/switchboard

        # Process specific domain
        python -m scenarios.knowledge_curator --vault ~/switchboard --domain chanoyu/

        # Resume interrupted run
        python -m scenarios.knowledge_curator --resume

        # Report only (no modifications)
        python -m scenarios.knowledge_curator --report-only

        # Fast mode (no verification)
        python -m scenarios.knowledge_curator --no-verify

        # View learning insights
        python -m scenarios.knowledge_curator learning
    """
    if verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    # Store options in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["vault"] = vault
    ctx.obj["domain"] = domain
    ctx.obj["verbose"] = verbose

    # If no subcommand, run the default curation
    if ctx.invoked_subcommand is None:
        try:
            result = asyncio.run(
                run_curation(
                    vault,
                    domain,
                    resume,
                    report_only,
                    state_dir,
                    status_file,
                    verify_citations=not no_verify,
                    enable_learning=not no_learning,
                )
            )
            ctx.exit(result)
        except KeyboardInterrupt:
            logger.info("\nCuration interrupted. Use --resume to continue.")
            ctx.exit(130)
        except Exception as e:
            logger.error(f"Curation failed: {e}")
            ctx.exit(1)


@main.command()
@click.option(
    "--domain",
    "-d",
    type=str,
    default=None,
    help="Show insights for specific domain",
)
def learning(domain: str | None) -> None:
    """View learning insights from past curation runs.

    Shows which sources work best for different domains,
    verification statistics, and successful search refinements.
    """
    store = CuratorLearning()
    summary = store.get_summary()

    click.echo("\n=== Knowledge Curator Learning Summary ===\n")

    # Overall stats
    vstats = summary["verification_stats"]
    click.echo("Verification Statistics:")
    click.echo(f"  Total verifications: {vstats.get('total', 0)}")
    if vstats.get("total", 0) > 0:
        click.echo(f"  Strong fit rate: {vstats.get('strong_fit_rate', 0):.1%}")
        click.echo(f"  Rejection rate: {vstats.get('rejection_rate', 0):.1%}")
    click.echo(f"  Successful refinements: {summary['total_refinements']}")
    click.echo()

    # Domain-specific insights
    if domain:
        insights = store.get_domain_insights(domain)
        click.echo(f"Domain: {domain}")
        if insights["source_rankings"]:
            click.echo(f"  Best sources: {', '.join(insights['source_rankings'])}")
        click.echo(f"  Total searches: {insights['total_searches']}")
        if insights["successful_refinements"]:
            click.echo("  Recent refinements:")
            for r in insights["successful_refinements"][-3:]:
                click.echo(f"    '{r['original']}' → '{r['refined']}'")
    else:
        click.echo("Domains tracked:")
        for d in summary["domains_tracked"]:
            insights = store.get_domain_insights(d)
            rankings = insights["source_rankings"]
            best = rankings[0] if rankings else "unknown"
            click.echo(f"  {d}: best source = {best}, searches = {insights['total_searches']}")

    click.echo(f"\nLast updated: {summary['last_updated']}")


@main.command()
def reset_learning() -> None:
    """Reset all learning data.

    Clears verification statistics, source rankings, and refinement history.
    """
    from .learning.store import DEFAULT_LEARNING_PATH

    if DEFAULT_LEARNING_PATH.exists():
        DEFAULT_LEARNING_PATH.unlink()
        click.echo("Learning data reset.")
    else:
        click.echo("No learning data to reset.")


@main.command("gaps")
@click.pass_context
@click.option(
    "--stale-months",
    type=int,
    default=6,
    help="Months before content is considered stale",
)
@click.option(
    "--min-words",
    type=int,
    default=100,
    help="Minimum words for a section to be 'complete'",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output JSON file for gap report",
)
@click.option(
    "--type",
    "-t",
    "gap_types",
    multiple=True,
    type=click.Choice(["undefined_concept", "stale_content", "orphan_page", "thin_section"]),
    help="Filter by gap type (can specify multiple)",
)
def gaps(
    ctx: click.Context,
    stale_months: int,
    min_words: int,
    output: Path | None,
    gap_types: tuple[str, ...],
) -> None:
    """Detect knowledge gaps in the vault.

    Tier 1 Detection: Automated gap detection that runs quickly and generates
    reports without modifying files. Designed to run weekly.

    Gap types detected:
    - undefined_concept: Terms mentioned but never explained (P1)
    - stale_content: Files not updated in N months (P1)
    - orphan_page: Files not linked from anywhere (P2)
    - thin_section: Topics with < 100 words (P2)

    Examples:

        # Detect all gaps in chanoyu domain
        python -m scenarios.knowledge_curator gaps --vault ~/switchboard --domain chanoyu/

        # Only show undefined concepts and stale content
        python -m scenarios.knowledge_curator gaps -t undefined_concept -t stale_content

        # Save report to JSON
        python -m scenarios.knowledge_curator gaps --output gaps.json
    """
    import json

    vault = ctx.obj["vault"]
    domain = ctx.obj["domain"]

    click.echo(f"\n{'=' * 60}")
    click.echo("  KNOWLEDGE GAP DETECTION")
    click.echo(f"{'=' * 60}\n")

    target_path = vault / domain if domain else vault
    click.echo(f"Scanning: {target_path}\n")

    # Run detection
    detector = GapDetector(stale_months=stale_months, min_section_words=min_words)
    report = detector.detect_gaps(vault, domain)

    # Filter by type if specified
    if gap_types:
        report.gaps = [g for g in report.gaps if g.type.value in gap_types]

    # Display results
    summary = report.summary
    click.echo(f"Total gaps found: {summary['total']}\n")

    if summary["by_type"]:
        click.echo("By Type:")
        type_icons = {
            "undefined_concept": "🔴",
            "stale_content": "🟡",
            "orphan_page": "🟠",
            "thin_section": "⚪",
        }
        for gap_type, count in sorted(summary["by_type"].items()):
            icon = type_icons.get(gap_type, "•")
            click.echo(f"  {icon} {gap_type}: {count}")

    if summary["by_severity"]:
        click.echo("\nBy Severity:")
        for severity, count in summary["by_severity"].items():
            click.echo(f"  {severity}: {count}")

    # Show top priority gaps
    if report.gaps:
        click.echo(f"\n{'─' * 60}")
        click.echo("Top Priority Gaps:")
        click.echo(f"{'─' * 60}\n")

        # Sort by severity (high first) then by type
        severity_order = {"high": 0, "medium": 1, "low": 2}
        sorted_gaps = sorted(
            report.gaps,
            key=lambda g: (severity_order.get(g.severity.value, 3), g.type.value),
        )

        for gap in sorted_gaps[:15]:
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(gap.severity.value, "•")
            click.echo(f"{severity_icon} [{gap.type.value}] {gap.location.file}")
            click.echo(f"   {gap.description}")
            if gap.location.context:
                click.echo(f'   Context: "{gap.location.context[:60]}..."')
            click.echo()

        if len(report.gaps) > 15:
            click.echo(f"... and {len(report.gaps) - 15} more gaps")

    # Save to JSON if requested
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        click.echo(f"\n📁 Gap report saved to: {output}")

    click.echo(f"\n_Last analysis: {report.generated_at.strftime('%Y-%m-%d %H:%M')}_")


@main.command("suggest")
@click.pass_context
@click.option(
    "--limit",
    "-n",
    type=int,
    default=5,
    help="Maximum number of suggestions to generate",
)
@click.option(
    "--gap-type",
    "-t",
    type=click.Choice(["undefined_concept", "stale_content", "orphan_page", "thin_section"]),
    help="Only suggest for specific gap type",
)
@click.option(
    "--gap-id",
    type=str,
    help="Generate suggestion for specific gap ID",
)
def suggest(
    ctx: click.Context,
    limit: int,
    gap_type: str | None,
    gap_id: str | None,
) -> None:
    """Generate expansion suggestions for detected gaps.

    Researches topics via Tavily and generates actionable suggestions.
    Suggestions are staged for review before application.

    Examples:

        # Generate suggestions for top 5 gaps
        python -m scenarios.knowledge_curator suggest

        # Only suggest for undefined concepts
        python -m scenarios.knowledge_curator suggest -t undefined_concept

        # Generate more suggestions
        python -m scenarios.knowledge_curator suggest -n 10
    """
    vault = ctx.obj["vault"]
    domain = ctx.obj["domain"]

    click.echo(f"\n{'=' * 60}")
    click.echo("  EXPANSION SUGGESTION GENERATION")
    click.echo(f"{'=' * 60}\n")

    # First, detect gaps
    detector = GapDetector()
    report = detector.detect_gaps(vault, domain)

    if not report.gaps:
        click.echo("No gaps found to suggest expansions for.")
        return

    # Filter gaps if specified
    gaps = report.gaps
    if gap_type:
        gaps = [g for g in gaps if g.type.value == gap_type]
    if gap_id:
        gaps = [g for g in gaps if g.id == gap_id]

    if not gaps:
        click.echo("No matching gaps found.")
        return

    click.echo(f"Found {len(gaps)} gaps, generating up to {limit} suggestions...\n")

    # Generate suggestions
    suggester = ExpansionSuggester(vault, domain)
    suggestions = asyncio.run(suggester.suggest_batch(gaps, limit))

    if not suggestions:
        click.echo("Could not generate any suggestions.")
        return

    click.echo(f"\n{'─' * 60}")
    click.echo(f"Generated {len(suggestions)} suggestions:")
    click.echo(f"{'─' * 60}\n")

    for i, s in enumerate(suggestions, 1):
        type_icon = {
            "create_page": "📄",
            "add_section": "📝",
            "update_content": "🔄",
            "add_links": "🔗",
        }.get(s.suggestion_type.value, "•")

        click.echo(f"{i}. {type_icon} {s.title}")
        click.echo(f"   Target: {s.target_file}")
        click.echo(f"   Confidence: {s.confidence:.0%}")
        if s.research_sources:
            click.echo(f"   Sources: {len(s.research_sources)} found")
        click.echo()

    click.echo("✓ Suggestions staged for review. Run 'review' to approve/reject.")


@main.command("review")
@click.pass_context
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="Show all suggestions including approved/rejected",
)
def review(ctx: click.Context, show_all: bool) -> None:
    """Review staged expansion suggestions.

    Interactive review of pending suggestions. For each suggestion you can:
    - [a]pprove: Mark for application
    - [r]eject: Discard suggestion
    - [s]kip: Decide later
    - [v]iew: Show full content
    - [q]uit: Exit review

    Examples:

        # Review pending suggestions
        python -m scenarios.knowledge_curator review

        # Show all suggestions including already reviewed
        python -m scenarios.knowledge_curator review --all
    """
    store = SuggestionStore()

    if show_all:
        suggestions = store.load_all()
    else:
        suggestions = store.load_pending()

    if not suggestions:
        click.echo("\nNo suggestions to review.")
        click.echo("Run 'suggest' command first to generate suggestions.")
        return

    click.echo(f"\n{'=' * 60}")
    click.echo(f"  REVIEW SUGGESTIONS ({len(suggestions)} total)")
    click.echo(f"{'=' * 60}\n")

    for i, s in enumerate(suggestions, 1):
        status_icon = {
            "pending": "⏳",
            "approved": "✅",
            "rejected": "❌",
            "modified": "📝",
            "applied": "✓",
        }.get(s.status.value, "•")

        type_icon = {
            "create_page": "📄",
            "add_section": "📝",
            "update_content": "🔄",
            "add_links": "🔗",
        }.get(s.suggestion_type.value, "•")

        click.echo(f"{'─' * 60}")
        click.echo(f"SUGGESTION {i}/{len(suggestions)} | {status_icon} {s.status.value}")
        click.echo(f"{'─' * 60}")
        click.echo(f"{type_icon} {s.title}")
        click.echo(f"Target: {s.target_file}")
        click.echo(f"Confidence: {s.confidence:.0%}")
        click.echo(f"\nDescription: {s.description}")
        if s.research_sources:
            click.echo("\nSources:")
            for src in s.research_sources[:3]:
                click.echo(f"  - {src[:60]}...")

        click.echo("\nPreview (first 300 chars):")
        click.echo(f"{'─' * 40}")
        click.echo(s.content[:300] + "..." if len(s.content) > 300 else s.content)
        click.echo(f"{'─' * 40}")

        if s.status == SuggestionStatus.PENDING:
            while True:
                action = click.prompt(
                    "\n[a]pprove [r]eject [s]kip [v]iew full [q]uit",
                    type=str,
                    default="s",
                ).lower()

                if action == "a":
                    store.update_status(s.id, SuggestionStatus.APPROVED)
                    click.echo("✅ Approved")
                    break
                if action == "r":
                    store.update_status(s.id, SuggestionStatus.REJECTED)
                    click.echo("❌ Rejected")
                    break
                if action == "s":
                    click.echo("⏭️ Skipped")
                    break
                if action == "v":
                    click.echo(f"\n{'=' * 60}")
                    click.echo("FULL CONTENT:")
                    click.echo(f"{'=' * 60}")
                    click.echo(s.content)
                    click.echo(f"{'=' * 60}\n")
                elif action == "q":
                    click.echo("\nReview session ended.")
                    return
                else:
                    click.echo("Invalid option. Use a/r/s/v/q")
        else:
            click.echo(f"\n(Already {s.status.value})")

        click.echo()

    # Summary
    all_suggestions = store.load_all()
    approved = len([s for s in all_suggestions if s.status == SuggestionStatus.APPROVED])
    rejected = len([s for s in all_suggestions if s.status == SuggestionStatus.REJECTED])
    pending = len([s for s in all_suggestions if s.status == SuggestionStatus.PENDING])

    click.echo(f"\n{'=' * 60}")
    click.echo("REVIEW SUMMARY")
    click.echo(f"{'=' * 60}")
    click.echo(f"✅ Approved: {approved}")
    click.echo(f"❌ Rejected: {rejected}")
    click.echo(f"⏳ Pending: {pending}")

    if approved > 0:
        click.echo(f"\nRun 'apply' to apply {approved} approved suggestions.")


@main.command("apply")
@click.pass_context
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without applying",
)
def apply(ctx: click.Context, dry_run: bool) -> None:
    """Apply approved expansion suggestions to vault.

    Applies all approved suggestions:
    - Creates new pages for undefined concepts
    - Adds sections to thin pages
    - Updates stale content
    - Adds link suggestions

    Examples:

        # Preview what would be applied
        python -m scenarios.knowledge_curator apply --dry-run

        # Apply all approved suggestions
        python -m scenarios.knowledge_curator apply
    """
    vault = ctx.obj["vault"]
    store = SuggestionStore()
    approved = store.load_approved()

    if not approved:
        click.echo("\nNo approved suggestions to apply.")
        click.echo("Run 'review' to approve suggestions first.")
        return

    click.echo(f"\n{'=' * 60}")
    click.echo(f"  APPLYING {len(approved)} SUGGESTIONS")
    if dry_run:
        click.echo("  (DRY RUN - no changes will be made)")
    click.echo(f"{'=' * 60}\n")

    applied = 0
    errors = 0

    for s in approved:
        target_path = vault / s.target_file
        click.echo(f"{'─' * 60}")

        try:
            if s.suggestion_type.value == "create_page":
                click.echo(f"📄 Creating: {s.target_file}")
                if not dry_run:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(s.content, encoding="utf-8")
                    store.update_status(s.id, SuggestionStatus.APPLIED)
                applied += 1

            elif s.suggestion_type.value == "add_section":
                click.echo(f"📝 Appending to: {s.target_file}")
                if target_path.exists():
                    if not dry_run:
                        existing = target_path.read_text(encoding="utf-8")
                        target_path.write_text(existing + "\n\n" + s.content, encoding="utf-8")
                        store.update_status(s.id, SuggestionStatus.APPLIED)
                    applied += 1
                else:
                    click.echo("   ⚠️ File not found, creating instead")
                    if not dry_run:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        target_path.write_text(s.content, encoding="utf-8")
                        store.update_status(s.id, SuggestionStatus.APPLIED)
                    applied += 1

            elif s.suggestion_type.value == "update_content":
                click.echo(f"🔄 Appending update to: {s.target_file}")
                if target_path.exists():
                    if not dry_run:
                        existing = target_path.read_text(encoding="utf-8")
                        target_path.write_text(existing + "\n\n" + s.content, encoding="utf-8")
                        store.update_status(s.id, SuggestionStatus.APPLIED)
                    applied += 1
                else:
                    click.echo("   ⚠️ File not found, skipping")
                    errors += 1

            elif s.suggestion_type.value == "add_links":
                click.echo(f"🔗 Link suggestions for: {s.target_file}")
                click.echo("   (Manual action required - see suggestion content)")
                click.echo(s.content)
                if not dry_run:
                    store.update_status(s.id, SuggestionStatus.APPLIED)
                applied += 1

            if not dry_run:
                click.echo("   ✓ Applied")
            else:
                click.echo("   (would apply)")

        except Exception as e:
            click.echo(f"   ❌ Error: {e}")
            errors += 1

    click.echo(f"\n{'=' * 60}")
    click.echo("APPLY SUMMARY")
    click.echo(f"{'=' * 60}")
    click.echo(f"✓ Applied: {applied}")
    if errors > 0:
        click.echo(f"❌ Errors: {errors}")

    if dry_run:
        click.echo("\n(Dry run - no changes were made)")
        click.echo("Run without --dry-run to apply changes.")


@main.command("verify-existing")
@click.pass_context
@click.option(
    "--limit",
    "-n",
    type=int,
    default=10,
    help="Maximum number of citations to verify",
)
def verify_existing(ctx: click.Context, limit: int) -> None:
    """Verify existing citations in the vault.

    Scans files for existing footnote citations and verifies that
    the cited sources actually support the claims they're attached to.

    This helps identify citations that may be:
    - Tangentially related but not supporting the specific claim
    - From keyword matching but wrong context
    - Outdated or superseded by better sources
    """
    import re

    from .citation_verifier import CitationVerifier

    vault = ctx.obj["vault"]
    domain = ctx.obj["domain"]
    target_path = vault / domain if domain else vault

    click.echo(f"\n=== Verifying Existing Citations in {target_path} ===\n")

    # Find all markdown files
    md_files = list(target_path.glob("**/*.md"))
    click.echo(f"Scanning {len(md_files)} markdown files...\n")

    # Pattern to find footnote citations: text[^1] ... [^1]: Citation info
    footnote_ref_pattern = re.compile(r"([^.!?\n]{20,100})\[\^(\d+)\]")
    footnote_def_pattern = re.compile(r"^\[\^(\d+)\]:\s*(.+)$", re.MULTILINE)

    citations_found: list[dict[str, str]] = []

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Find all footnote definitions
            footnote_defs = {m.group(1): m.group(2) for m in footnote_def_pattern.finditer(content)}

            # Find all footnote references with context
            for match in footnote_ref_pattern.finditer(content):
                claim_context = match.group(1).strip()
                footnote_num = match.group(2)

                if footnote_num in footnote_defs:
                    citations_found.append(
                        {
                            "file": str(md_file.relative_to(vault)),
                            "claim": claim_context,
                            "citation": footnote_defs[footnote_num],
                            "footnote_num": footnote_num,
                        }
                    )
        except Exception as e:
            click.echo(f"  Error reading {md_file}: {e}")

    click.echo(f"Found {len(citations_found)} existing citations\n")

    if not citations_found:
        click.echo("No citations to verify.")
        return

    # Verify up to the limit
    verifier = CitationVerifier()
    to_verify = citations_found[:limit]

    click.echo(f"Verifying {len(to_verify)} citations...\n")

    results = {"strong_fit": 0, "weak_fit": 0, "no_fit": 0, "uncertain": 0}
    problematic: list[dict[str, str]] = []

    for i, cit in enumerate(to_verify, 1):
        click.echo(f"[{i}/{len(to_verify)}] {cit['file']}")
        click.echo(f'  Claim: "{cit["claim"][:60]}..."')
        click.echo(f"  Citation: {cit['citation'][:80]}...")

        result = verifier.verify_citation_fit(
            claim_text=cit["claim"],
            source_title=cit["citation"],
        )

        results[result.outcome.value] += 1

        if result.outcome.value == "strong_fit":
            click.echo(f"  ✓ {result.outcome.value} ({result.confidence:.0%})")
        elif result.outcome.value == "weak_fit":
            click.echo(f"  ~ {result.outcome.value} ({result.confidence:.0%}): {result.explanation}")
        elif result.outcome.value == "no_fit":
            click.echo(f"  ✗ {result.outcome.value} ({result.confidence:.0%}): {result.explanation}")
            problematic.append({**cit, "reason": result.explanation})
        else:
            click.echo(f"  ? {result.outcome.value} ({result.confidence:.0%})")

        click.echo()

    # Summary
    click.echo("\n=== Verification Summary ===\n")
    click.echo(f"Strong fit (good citations): {results['strong_fit']}")
    click.echo(f"Weak fit (partial support): {results['weak_fit']}")
    click.echo(f"No fit (problematic): {results['no_fit']}")
    click.echo(f"Uncertain: {results['uncertain']}")

    if problematic:
        click.echo("\n=== Problematic Citations ===\n")
        for p in problematic:
            click.echo(f"File: {p['file']}")
            click.echo(f"  Claim: {p['claim'][:60]}...")
            click.echo(f"  Citation: {p['citation'][:60]}...")
            click.echo(f"  Issue: {p['reason']}")
            click.echo()


@main.command("audit-citations")
@click.pass_context
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output JSON file for audit results",
)
@click.option(
    "--skip-verify",
    is_flag=True,
    help="Skip AI verification (faster, uses heuristics only)",
)
def audit_citations(ctx: click.Context, output: Path | None, skip_verify: bool) -> None:
    """Comprehensive audit of all citations in the vault.

    Scans all files and categorizes citations as:
    - GOOD: Strong fit, keeps
    - WEAK: Partial support, review recommended
    - BAD: No fit, should be removed
    - STRUCTURAL: Attached to non-claim content (tables, links, etc.)

    Outputs a detailed report and optionally saves to JSON for cleanup.
    """
    import json
    import re

    from .citation_verifier import CitationVerifier

    vault = ctx.obj["vault"]
    domain = ctx.obj["domain"]
    target_path = vault / domain if domain else vault

    click.echo(f"\n{'=' * 60}")
    click.echo(f"  CITATION AUDIT: {target_path}")
    click.echo(f"{'=' * 60}\n")

    # Patterns for detecting structural content
    structural_patterns = [
        r"^\s*\|.*\|",  # Table rows
        r"\[\[.*?\]\]",  # Wiki links
        r"\[.*?\]\(.*?\)",  # Markdown links
        r"^#+\s+",  # Headers
        r"^\s*[-*]\s+\[\[",  # List items with links
        r"`[^`]+`",  # Inline code
        r"^```",  # Code blocks
    ]

    # Find all markdown files
    md_files = list(target_path.glob("**/*.md"))
    click.echo(f"Scanning {len(md_files)} markdown files...\n")

    # Pattern to find footnote citations
    footnote_ref_pattern = re.compile(r"([^\n]{0,150})\[\^(\d+)\]")
    footnote_def_pattern = re.compile(r"^\[\^(\d+)\]:\s*(.+)$", re.MULTILINE)

    all_citations: list[dict] = []
    files_with_citations = 0

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            rel_path = str(md_file.relative_to(vault))

            # Find all footnote definitions
            footnote_defs = {m.group(1): m.group(2) for m in footnote_def_pattern.finditer(content)}

            if not footnote_defs:
                continue

            files_with_citations += 1

            # Find all footnote references with context
            for match in footnote_ref_pattern.finditer(content):
                context = match.group(1).strip()
                footnote_num = match.group(2)

                if footnote_num not in footnote_defs:
                    continue

                citation_text = footnote_defs[footnote_num]

                # Detect if context is structural
                is_structural = any(re.search(pat, context) for pat in structural_patterns)

                # Quick heuristic checks for obviously bad citations
                obviously_bad_keywords = [
                    "venture capital",
                    "machine learning",
                    "neural network",
                    "stock market",
                    "cryptocurrency",
                    "blockchain",
                    "social media",
                    "covid",
                    "pandemic",
                    "climate change",
                    "deep learning",
                    "reinforcement learning",
                    "natural language processing",
                    "computer vision",
                    "autonomous vehicle",
                    "robotics",
                    "quantum computing",
                    "sunfish",
                    "ocean",
                    "marine biology",
                ]

                citation_lower = citation_text.lower()
                is_obviously_bad = any(kw in citation_lower for kw in obviously_bad_keywords)

                # Check for good Japanese tea ceremony indicators
                good_indicators = [
                    "茶",  # cha (tea)
                    "chanoyu",
                    "tea ceremony",
                    "rikyū",
                    "rikyu",
                    "wabi",
                    "sabi",
                    "matcha",
                    "kaiseki",
                    "茶道",  # sadō
                    "裏千家",  # urasenke
                    "表千家",  # omotesenke
                ]
                has_good_indicator = any(ind in citation_lower or ind in citation_text for ind in good_indicators)

                all_citations.append(
                    {
                        "file": rel_path,
                        "footnote_num": footnote_num,
                        "context": context[:100],
                        "citation": citation_text,
                        "is_structural": is_structural,
                        "is_obviously_bad": is_obviously_bad,
                        "has_good_indicator": has_good_indicator,
                        "category": None,  # Will be set after verification
                        "confidence": None,
                        "reason": None,
                    }
                )

        except Exception as e:
            click.echo(f"  Error reading {md_file}: {e}")

    click.echo(f"Found {len(all_citations)} citations in {files_with_citations} files\n")

    if not all_citations:
        click.echo("No citations to audit.")
        return

    # Categorize citations
    results = {
        "good": [],
        "weak": [],
        "bad": [],
        "structural": [],
        "uncertain": [],
    }

    # First pass: categorize by heuristics
    for cit in all_citations:
        if cit["is_structural"]:
            cit["category"] = "structural"
            cit["reason"] = "Attached to structural content (table, link, header)"
            results["structural"].append(cit)
        elif cit["is_obviously_bad"]:
            cit["category"] = "bad"
            cit["reason"] = "Contains obviously unrelated keywords"
            results["bad"].append(cit)
        elif cit["has_good_indicator"]:
            cit["category"] = "good"
            cit["reason"] = "Contains tea ceremony related terms"
            results["good"].append(cit)
        else:
            cit["category"] = "uncertain"
            results["uncertain"].append(cit)

    # Second pass: verify uncertain citations with AI (unless skipped)
    if not skip_verify and results["uncertain"]:
        click.echo(f"Verifying {len(results['uncertain'])} uncertain citations with AI...\n")
        verifier = CitationVerifier()

        for i, cit in enumerate(results["uncertain"][:50], 1):  # Limit to 50 for speed
            click.echo(f"  [{i}/{min(len(results['uncertain']), 50)}] {cit['file']}...", nl=False)

            result = verifier.verify_citation_fit(
                claim_text=cit["context"],
                source_title=cit["citation"],
            )

            cit["confidence"] = result.confidence

            if result.outcome.value == "strong_fit":
                cit["category"] = "good"
                cit["reason"] = result.explanation
                results["good"].append(cit)
                click.echo(" ✓")
            elif result.outcome.value == "weak_fit":
                cit["category"] = "weak"
                cit["reason"] = result.explanation
                results["weak"].append(cit)
                click.echo(" ~")
            elif result.outcome.value == "no_fit":
                cit["category"] = "bad"
                cit["reason"] = result.explanation
                results["bad"].append(cit)
                click.echo(" ✗")
            else:
                click.echo(" ?")

        # Remove verified from uncertain
        results["uncertain"] = [c for c in results["uncertain"] if c["category"] == "uncertain"]

    # Print summary
    click.echo(f"\n{'=' * 60}")
    click.echo("  AUDIT SUMMARY")
    click.echo(f"{'=' * 60}\n")

    click.echo(f"✓ Good citations:        {len(results['good']):>4}")
    click.echo(f"~ Weak citations:         {len(results['weak']):>4}")
    click.echo(f"✗ Bad citations:          {len(results['bad']):>4}")
    click.echo(f"⚠ Structural citations:   {len(results['structural']):>4}")
    click.echo(f"? Uncertain:              {len(results['uncertain']):>4}")
    click.echo(f"{'─' * 40}")
    click.echo(f"  Total:                  {len(all_citations):>4}")

    # Print bad citations by file
    if results["bad"] or results["structural"]:
        click.echo(f"\n{'=' * 60}")
        click.echo("  CITATIONS TO REMOVE")
        click.echo(f"{'=' * 60}\n")

        # Group by file
        by_file: dict[str, list] = {}
        for cit in results["bad"] + results["structural"]:
            if cit["file"] not in by_file:
                by_file[cit["file"]] = []
            by_file[cit["file"]].append(cit)

        for file_path, cits in sorted(by_file.items()):
            click.echo(f"📄 {file_path}")
            for cit in cits:
                marker = "✗" if cit["category"] == "bad" else "⚠"
                click.echo(f"  {marker} [^{cit['footnote_num']}]: {cit['citation'][:60]}...")
                click.echo(f"      Reason: {cit['reason'][:70]}")
            click.echo()

    # Save to JSON if requested
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        audit_data = {
            "vault": str(vault),
            "domain": domain,
            "summary": {
                "good": len(results["good"]),
                "weak": len(results["weak"]),
                "bad": len(results["bad"]),
                "structural": len(results["structural"]),
                "uncertain": len(results["uncertain"]),
                "total": len(all_citations),
            },
            "to_remove": results["bad"] + results["structural"],
            "all_citations": all_citations,
        }
        with open(output, "w", encoding="utf-8") as f:
            json.dump(audit_data, f, indent=2, ensure_ascii=False)
        click.echo(f"\n📁 Audit results saved to: {output}")


@main.command("cleanup-citations")
@click.pass_context
@click.option(
    "--audit-file",
    "-a",
    type=click.Path(exists=True, path_type=Path),
    help="Use audit JSON file instead of re-scanning",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without making changes",
)
@click.option(
    "--include-structural",
    is_flag=True,
    default=True,
    help="Also remove citations attached to structural content",
)
@click.option(
    "--include-weak",
    is_flag=True,
    help="Also remove weak citations (more aggressive)",
)
def cleanup_citations(
    ctx: click.Context,
    audit_file: Path | None,
    dry_run: bool,
    include_structural: bool,
    include_weak: bool,
) -> None:
    """Remove bad citations from vault files.

    By default removes:
    - Citations marked as "bad" (no fit)
    - Citations attached to structural content

    Use --include-weak to also remove weak citations.
    Use --dry-run to preview changes without modifying files.
    """
    import json
    import re

    vault = ctx.obj["vault"]
    domain = ctx.obj["domain"]
    target_path = vault / domain if domain else vault

    click.echo(f"\n{'=' * 60}")
    click.echo(f"  CITATION CLEANUP: {target_path}")
    click.echo(f"{'=' * 60}\n")

    if dry_run:
        click.echo("🔍 DRY RUN - No files will be modified\n")

    # Load citations to remove
    if audit_file:
        with open(audit_file, encoding="utf-8") as f:
            audit_data = json.load(f)
        to_remove = audit_data.get("to_remove", [])
        if include_weak:
            to_remove.extend([c for c in audit_data.get("all_citations", []) if c.get("category") == "weak"])
    else:
        # Run quick audit
        click.echo("Running quick audit (use --audit-file for cached results)...\n")
        ctx.invoke(audit_citations, output=Path("/tmp/citation_audit.json"), skip_verify=True)
        with open("/tmp/citation_audit.json", encoding="utf-8") as f:
            audit_data = json.load(f)
        to_remove = audit_data.get("to_remove", [])

    if not to_remove:
        click.echo("No citations to remove!")
        return

    # Group by file
    by_file: dict[str, list] = {}
    for cit in to_remove:
        file_path = cit["file"]
        if not include_structural and cit.get("category") == "structural":
            continue
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(cit)

    total_removed = 0
    files_modified = 0

    for rel_path, citations in sorted(by_file.items()):
        file_path = vault / rel_path
        if not file_path.exists():
            click.echo(f"⚠ File not found: {rel_path}")
            continue

        content = file_path.read_text(encoding="utf-8")
        original_content = content
        footnotes_to_remove = {cit["footnote_num"] for cit in citations}

        click.echo(f"📄 {rel_path}")

        for fn_num in footnotes_to_remove:
            # Remove footnote references [^N]
            ref_pattern = re.compile(rf"\[\^{fn_num}\](?!:)")
            ref_count = len(ref_pattern.findall(content))
            content = ref_pattern.sub("", content)

            # Remove footnote definitions [^N]: ...
            def_pattern = re.compile(rf"^\[\^{fn_num}\]:.*$\n?", re.MULTILINE)
            def_count = len(def_pattern.findall(content))
            content = def_pattern.sub("", content)

            if ref_count or def_count:
                cit = next((c for c in citations if c["footnote_num"] == fn_num), None)
                reason = cit["reason"][:50] if cit else "unknown"
                click.echo(f"  ✓ Removed [^{fn_num}] ({ref_count} refs, {def_count} defs) - {reason}")
                total_removed += 1

        # Clean up multiple blank lines
        content = re.sub(r"\n{3,}", "\n\n", content)

        if content != original_content:
            files_modified += 1
            if not dry_run:
                file_path.write_text(content, encoding="utf-8")
            else:
                click.echo("  (would save changes)")

        click.echo()

    # Summary
    click.echo(f"{'=' * 60}")
    click.echo("  CLEANUP SUMMARY")
    click.echo(f"{'=' * 60}\n")

    if dry_run:
        click.echo(f"Would remove {total_removed} citations from {files_modified} files")
        click.echo("\nRun without --dry-run to apply changes")
    else:
        click.echo(f"Removed {total_removed} citations from {files_modified} files")


if __name__ == "__main__":
    sys.exit(main())
