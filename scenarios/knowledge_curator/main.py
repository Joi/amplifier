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
