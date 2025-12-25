#!/usr/bin/env python3
"""
Blog Extract - CLI for extracting topics and entities from blog posts.

Processes markdown blog posts and extracts structured metadata using AI.
"""

import json
import sys
import time
from pathlib import Path

import click
import yaml

from amplifier.utils.logger import get_logger

from .extractor import BlogExtractor
from .models import BlogExtraction

logger = get_logger(__name__)

# Default paths
DEFAULT_SOURCE = Path.home() / "joi-ito-web-md"
DEFAULT_OUTPUT = Path.home() / "switchboard" / "joi-blog" / "extractions"


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}

    end_marker = content.find("---", 3)
    if end_marker == -1:
        return {}

    try:
        frontmatter = content[3:end_marker].strip()
        return yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError:
        return {}


def get_output_path(post_path: Path, source_dir: Path, output_dir: Path) -> Path:
    """Get output path for extraction JSON, mirroring source structure."""
    relative = post_path.relative_to(source_dir)
    # Change extension to .json
    output_path = output_dir / relative.with_suffix(".json")
    return output_path


def discover_posts(
    source_dir: Path,
    language: str | None = None,
) -> list[Path]:
    """Discover all blog posts in source directory.

    Args:
        source_dir: Directory containing blog posts
        language: Filter by language (en, jp, or None for all)

    Returns:
        List of paths to markdown files
    """
    posts = []

    if language == "en":
        search_dirs = [source_dir / "en"]
    elif language == "jp":
        search_dirs = [source_dir / "jp"]
    else:
        search_dirs = [source_dir / "en", source_dir / "jp"]

    for search_dir in search_dirs:
        if search_dir.exists():
            posts.extend(search_dir.glob("**/*.md"))

    # Sort by path for consistent ordering
    return sorted(posts)


def count_existing(output_dir: Path) -> int:
    """Count existing extraction files."""
    if not output_dir.exists():
        return 0
    return len(list(output_dir.glob("**/*.json")))


@click.command()
@click.option(
    "--source-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=DEFAULT_SOURCE,
    help="Directory containing blog markdown files",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_OUTPUT,
    help="Directory for extraction JSON files",
)
@click.option(
    "--language",
    type=click.Choice(["en", "jp", "all"]),
    default="all",
    help="Filter by language",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Maximum posts to process (for testing)",
)
@click.option(
    "--resume/--no-resume",
    default=True,
    help="Skip already-extracted posts (default: True)",
)
@click.option(
    "--delay",
    type=float,
    default=0.5,
    help="Delay between API calls in seconds",
)
@click.option(
    "--model",
    type=str,
    default="claude-sonnet-4-20250514",
    help="Claude model to use",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be processed without calling AI",
)
def main(
    source_dir: Path,
    output_dir: Path,
    language: str,
    limit: int | None,
    resume: bool,
    delay: float,
    model: str,
    verbose: bool,
    dry_run: bool,
) -> int:
    """Extract topics and entities from blog posts using AI.

    Processes markdown blog posts from joi.ito.com and extracts:
    - Topic tags (3-7 per post)
    - Named entities (people, organizations, places)
    - Summary (1-2 sentences)
    - Key quotes

    Results are saved as JSON files mirroring the source structure.

    Examples:

        # Extract all posts (resume from where we left off)
        python -m scenarios.blog_extract

        # Extract English posts only, limit to 50 for testing
        python -m scenarios.blog_extract --language en --limit 50

        # Dry run to see what would be processed
        python -m scenarios.blog_extract --dry-run

        # Force re-extraction of all posts
        python -m scenarios.blog_extract --no-resume
    """
    # Setup logging
    if verbose:
        logger.logger.setLevel("DEBUG")

    # Resolve language filter
    lang_filter = None if language == "all" else language

    # Discover posts
    logger.info(f"Discovering posts in {source_dir}...")
    posts = discover_posts(source_dir, lang_filter)
    total_posts = len(posts)
    logger.info(f"Found {total_posts} posts")

    # Filter already-extracted if resume mode
    if resume:
        existing = count_existing(output_dir)
        logger.info(f"Found {existing} existing extractions")

        # Filter to only unprocessed
        unprocessed = []
        for post in posts:
            output_path = get_output_path(post, source_dir, output_dir)
            if not output_path.exists():
                unprocessed.append(post)
        posts = unprocessed
        logger.info(f"Remaining to process: {len(posts)}")

    # Apply limit
    if limit:
        posts = posts[:limit]
        logger.info(f"Limited to {len(posts)} posts")

    if not posts:
        logger.info("No posts to process!")
        return 0

    # Dry run mode
    if dry_run:
        logger.info("\n=== DRY RUN ===")
        logger.info(f"Would process {len(posts)} posts:")
        for i, post in enumerate(posts[:20]):
            logger.info(f"  {i + 1}. {post.relative_to(source_dir)}")
        if len(posts) > 20:
            logger.info(f"  ... and {len(posts) - 20} more")
        return 0

    # Initialize extractor
    extractor = BlogExtractor(model=model)

    # Process posts
    logger.info(f"\nProcessing {len(posts)} posts...")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Model: {model}")
    logger.info(f"Delay: {delay}s between requests")
    logger.info("")

    processed = 0
    failed = 0
    start_time = time.time()

    for i, post in enumerate(posts):
        try:
            # Parse frontmatter
            content = post.read_text(encoding="utf-8")
            metadata = parse_frontmatter(content)

            # Skip if no title (likely not a real post)
            if not metadata.get("title"):
                logger.debug(f"Skipping {post.name}: no title")
                continue

            # Extract
            logger.info(f"[{i + 1}/{len(posts)}] {metadata.get('title', post.name)[:60]}...")

            extraction = extractor.extract(post, metadata)

            if extraction:
                # Save to output
                output_path = get_output_path(post, source_dir, output_dir)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    json.dumps(extraction.to_dict(), indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                processed += 1
                logger.debug(f"  Topics: {', '.join(extraction.topics[:5])}")
            else:
                failed += 1
                logger.warning(f"  Failed to extract")

            # Rate limiting
            if i < len(posts) - 1:
                time.sleep(delay)

        except KeyboardInterrupt:
            logger.info("\n\nInterrupted! Progress saved.")
            break
        except Exception as e:
            logger.error(f"Error processing {post.name}: {e}")
            failed += 1

    # Summary
    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 50)
    logger.info("Extraction Complete")
    logger.info(f"  Processed: {processed}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Time: {elapsed:.1f}s ({elapsed / max(processed, 1):.1f}s per post)")
    logger.info(f"  Output: {output_dir}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
