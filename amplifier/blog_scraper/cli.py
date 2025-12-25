"""CLI commands for blog scraper."""

import json
import logging
from datetime import datetime
from pathlib import Path

import click

from amplifier.blog_scraper.scraper import scrape_blog

logger = logging.getLogger(__name__)


@click.group("blog")
def cli() -> None:
    """Blog scraper commands for joi.ito.com."""
    pass


@cli.command("scrape")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path.home() / "joi-ito-web-md",
    help="Output directory for markdown files",
)
@click.option(
    "--language",
    "-l",
    type=click.Choice(["en", "jp", "both"]),
    default="both",
    help="Language(s) to scrape",
)
@click.option(
    "--since",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Only scrape posts after this date (YYYY-MM-DD)",
)
@click.option(
    "--max-posts",
    type=int,
    default=None,
    help="Maximum number of posts to scrape (for testing)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def scrape_cmd(
    output: Path,
    language: str,
    since: datetime | None,
    max_posts: int | None,
    verbose: bool,
) -> None:
    """Scrape joi.ito.com blog to markdown files.

    Downloads blog posts and converts them to markdown with YAML frontmatter.
    Supports both English (/weblog/) and Japanese (/jp/archives/) sections.

    Examples:

        # Full scrape (both languages)
        amplifier blog scrape

        # English only, since 2024
        amplifier blog scrape -l en --since 2024-01-01

        # Test with 5 posts
        amplifier blog scrape --max-posts 5

        # Custom output directory
        amplifier blog scrape -o ~/my-blog-backup
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
    )

    # Determine languages
    languages = ["en", "jp"] if language == "both" else [language]

    click.echo("Scraping joi.ito.com blog...")
    click.echo(f"  Output: {output}")
    click.echo(f"  Languages: {', '.join(languages)}")
    if since:
        click.echo(f"  Since: {since.date()}")
    if max_posts:
        click.echo(f"  Max posts: {max_posts}")
    click.echo()

    # Ensure output directory exists
    output.mkdir(parents=True, exist_ok=True)

    # Run scraper
    result = scrape_blog(
        output_dir=output,
        languages=languages,
        since=since,
        max_posts=max_posts,
    )

    # Report results
    click.echo()
    click.echo("=" * 40)
    click.echo("Scrape complete!")
    click.echo(f"  Posts scraped: {result.posts_scraped}")
    click.echo(f"  Posts skipped: {result.posts_skipped}")
    click.echo(f"  Posts failed: {result.posts_failed}")

    if result.errors:
        click.echo()
        click.echo("Errors:")
        for error in result.errors[:10]:  # Show first 10
            click.echo(f"  - {error}")
        if len(result.errors) > 10:
            click.echo(f"  ... and {len(result.errors) - 10} more")


@cli.command("index")
@click.option(
    "--dir",
    "-d",
    "directory",
    type=click.Path(exists=True, path_type=Path),
    default=Path.home() / "joi-ito-web-md",
    help="Directory containing scraped markdown files",
)
def index_cmd(directory: Path) -> None:
    """Generate index.json from scraped markdown files.

    Creates a metadata index of all posts for quick lookup.
    """
    from amplifier.blog_scraper.indexer import generate_index

    click.echo(f"Generating index for {directory}...")
    index = generate_index(directory)

    output_path = directory / "metadata" / "index.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False, default=str)

    click.echo(f"Index saved to {output_path}")
    click.echo(f"  Total posts: {len(index.get('posts', []))}")


if __name__ == "__main__":
    cli()
