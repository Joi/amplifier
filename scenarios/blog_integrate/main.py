#!/usr/bin/env python3
"""
Blog Integrate - CLI for cross-linking blog extractions with vault content.

Finds matches between extracted entities and vault files.
"""

import sys
from pathlib import Path

import click

from amplifier.utils.logger import get_logger

from .integrator import BlogIntegrator

logger = get_logger(__name__)

# Default paths
DEFAULT_EXTRACTIONS = Path.home() / "switchboard" / "joi-blog" / "extractions"
DEFAULT_VAULT = Path.home() / "switchboard"
DEFAULT_TOPICS = Path.home() / "switchboard" / "joi-blog" / "topics"


@click.command()
@click.option(
    "--extractions-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=DEFAULT_EXTRACTIONS,
    help="Directory containing extraction JSON files",
)
@click.option(
    "--vault-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=DEFAULT_VAULT,
    help="Root switchboard vault directory",
)
@click.option(
    "--topics-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=DEFAULT_TOPICS,
    help="Directory containing blog topic pages",
)
@click.option(
    "--dry-run/--no-dry-run",
    default=True,
    help="Only report matches without modifying files (default: True)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def main(
    extractions_dir: Path,
    vault_dir: Path,
    topics_dir: Path,
    dry_run: bool,
    verbose: bool,
) -> int:
    """Cross-link blog extractions with vault content.

    Finds entities (people, organizations) mentioned in blog posts
    that have matching vault files, and topics that match concepts.

    Generates an integration report with suggested actions.

    Examples:

        # Generate integration report
        python -m scenarios.blog_integrate

        # Apply changes (not just report)
        python -m scenarios.blog_integrate --no-dry-run
    """
    # Setup logging
    if verbose:
        logger.logger.setLevel("DEBUG")

    logger.info("Blog Integrator")
    logger.info(f"  Extractions: {extractions_dir}")
    logger.info(f"  Vault: {vault_dir}")
    logger.info(f"  Topics: {topics_dir}")
    logger.info(f"  Dry run: {dry_run}")
    logger.info("")

    # Run integration
    integrator = BlogIntegrator(
        extractions_dir=extractions_dir,
        vault_dir=vault_dir,
        blog_topics_dir=topics_dir,
    )

    stats = integrator.integrate(dry_run=dry_run)

    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info("Integration Complete")
    logger.info(f"  Extractions processed: {stats['extractions']}")
    logger.info(f"  Entity matches: {stats['entity_matches']}")
    logger.info(f"  Topic matches: {stats['topic_matches']}")
    logger.info("  Report: ~/switchboard/joi-blog/_INTEGRATION_REPORT.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
