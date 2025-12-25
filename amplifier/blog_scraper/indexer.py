"""Index generator for scraped blog posts."""

import re
from datetime import datetime
from pathlib import Path

import yaml


def generate_index(directory: Path) -> dict:
    """Generate a metadata index from scraped markdown files.

    Args:
        directory: Root directory containing en/ and jp/ subdirectories

    Returns:
        Dictionary with posts metadata
    """
    posts = []

    for md_file in directory.glob("**/*.md"):
        # Skip README and other non-post files
        if md_file.name.lower() in ["readme.md", "index.md"]:
            continue

        metadata = extract_frontmatter(md_file)
        if metadata:
            posts.append(metadata)

    # Sort by date descending
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)

    return {
        "generated": datetime.now().isoformat(),
        "total_posts": len(posts),
        "posts": posts,
    }


def extract_frontmatter(file_path: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file.

    Args:
        file_path: Path to markdown file

    Returns:
        Dictionary with frontmatter fields, or None if parsing fails
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Match YAML frontmatter (between --- markers)
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None

    try:
        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            return None

        # Add file path for reference
        frontmatter["file_path"] = str(file_path)

        return frontmatter
    except yaml.YAMLError:
        return None
