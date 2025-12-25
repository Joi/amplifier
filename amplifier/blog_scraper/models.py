"""Data models for blog scraper."""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path


@dataclass
class BlogPost:
    """A single blog post with metadata."""

    title: str
    permalink: str
    content_html: str
    content_markdown: str
    date: datetime
    language: str  # "en" or "jp"
    author: str = "Joichi Ito"
    categories: list[str] = field(default_factory=list)
    source_path: str = ""  # Path portion of URL

    def to_frontmatter(self) -> str:
        """Generate YAML frontmatter."""
        categories_str = ", ".join(self.categories) if self.categories else ""
        # Escape quotes in title for YAML
        escaped_title = self.title.replace('"', '\\"')
        extracted_date = datetime.now().strftime("%Y-%m-%d")
        return f"""---
title: "{escaped_title}"
date: {self.date.isoformat()}
permalink: {self.permalink}
language: {self.language}
categories: [{categories_str}]
author: {self.author}
source_path: {self.source_path}
extracted: {extracted_date}
---
"""

    def to_markdown(self) -> str:
        """Generate full markdown with frontmatter."""
        return self.to_frontmatter() + "\n" + self.content_markdown

    def output_path(self, base_dir: Path) -> Path:
        """Generate output file path based on date and language."""
        # Structure: {base}/{lang}/YYYY/MM/slug.md
        slug = self.source_path.rstrip(".html").split("/")[-1]
        return (
            base_dir
            / self.language
            / str(self.date.year)
            / f"{self.date.month:02d}"
            / f"{slug}.md"
        )


@dataclass
class ScrapeResult:
    """Result of a blog scrape operation."""

    posts_scraped: int = 0
    posts_skipped: int = 0
    posts_failed: int = 0
    errors: list[str] = field(default_factory=list)
    output_dir: Path | None = None

    def add_error(self, url: str, error: str) -> None:
        """Record a scrape error."""
        self.errors.append(f"{url}: {error}")
        self.posts_failed += 1
