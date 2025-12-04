#!/usr/bin/env python3
"""
Knowledge Curator - Main CLI and orchestrator.

A Wikipedia-editor style agent that curates knowledge vaults by:
1. Scanning files for uncited claims
2. Searching for authoritative sources
3. Adding citations to files
4. Generating knowledge status reports
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

        async with SourceSearcher(rules=citation_rules) as searcher:
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


@click.command()
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
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
def main(
    vault: Path,
    domain: str | None,
    resume: bool,
    report_only: bool,
    state_dir: Path,
    status_file: Path,
    verbose: bool,
) -> int:
    """
    Knowledge Curator - Wikipedia-editor style agent for knowledge vaults.

    Processes markdown files to find claims needing citations, searches for
    authoritative sources, and adds citations to files.

    Examples:

        # Process entire vault
        python -m scenarios.knowledge_curator --vault ~/switchboard

        # Process specific domain
        python -m scenarios.knowledge_curator --vault ~/switchboard --domain chanoyu/

        # Resume interrupted run
        python -m scenarios.knowledge_curator --resume

        # Report only (no modifications)
        python -m scenarios.knowledge_curator --report-only
    """
    if verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    try:
        return asyncio.run(run_curation(vault, domain, resume, report_only, state_dir, status_file))
    except KeyboardInterrupt:
        logger.info("\nCuration interrupted. Use --resume to continue.")
        return 130
    except Exception as e:
        logger.error(f"Curation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
