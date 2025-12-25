#!/usr/bin/env python3
"""
Blog Synthesize - CLI for aggregating blog extractions into topic pages.

Processes JSON extraction files and creates navigable topic structure.
"""

import sys
from pathlib import Path

import click

from amplifier.utils.logger import get_logger

from .synthesizer import BlogSynthesizer

logger = get_logger(__name__)

# Default paths
DEFAULT_EXTRACTIONS = Path.home() / "switchboard" / "joi-blog" / "extractions"
DEFAULT_OUTPUT = Path.home() / "switchboard" / "joi-blog"


@click.command()
@click.option(
    "--extractions-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=DEFAULT_EXTRACTIONS,
    help="Directory containing extraction JSON files",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_OUTPUT,
    help="Output directory for topic pages (joi-blog root)",
)
@click.option(
    "--min-posts",
    type=int,
    default=3,
    help="Minimum posts required for a topic page",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def main(
    extractions_dir: Path,
    output_dir: Path,
    min_posts: int,
    verbose: bool,
) -> int:
    """Synthesize blog extractions into topic pages.

    Aggregates topic data from extraction JSON files and generates:
    - Topic pages (topics/{topic}.md) for each topic with >= min-posts
    - Topic index (topics/_INDEX.md) with navigation by count and era
    - Manifest (_MANIFEST.json) with corpus statistics

    Examples:

        # Synthesize with defaults
        python -m scenarios.blog_synthesize

        # Require at least 5 posts per topic
        python -m scenarios.blog_synthesize --min-posts 5
    """
    # Setup logging
    if verbose:
        logger.logger.setLevel("DEBUG")

    logger.info("Blog Synthesizer")
    logger.info(f"  Extractions: {extractions_dir}")
    logger.info(f"  Output: {output_dir}")
    logger.info(f"  Min posts per topic: {min_posts}")
    logger.info("")

    # Check extractions exist
    extraction_count = len(list(extractions_dir.glob("**/*.json")))
    if extraction_count == 0:
        logger.error("No extraction files found!")
        logger.error("Run 'python -m scenarios.blog_extract' first")
        return 1

    logger.info(f"Found {extraction_count} extraction files")

    # Run synthesis
    synthesizer = BlogSynthesizer(
        extractions_dir=extractions_dir,
        output_dir=output_dir,
        min_posts=min_posts,
    )

    stats = synthesizer.synthesize()

    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info("Synthesis Complete")
    logger.info(f"  Extractions processed: {stats['extractions']}")
    logger.info(f"  Total unique topics: {stats['topics_total']}")
    logger.info(f"  Topic pages generated: {stats['topics_generated']}")
    logger.info(f"  Output: {output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
