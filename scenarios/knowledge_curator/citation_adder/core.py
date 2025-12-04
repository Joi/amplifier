#!/usr/bin/env python3
"""
Citation Adder - Adds citations to markdown files.

Formats and inserts citations in Obsidian-compatible format.
"""

import re
from pathlib import Path
from typing import Any

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


class CitationAdder:
    """Adds citations to markdown files."""

    def __init__(self, citation_style: str = "footnote"):
        """
        Initialize citation adder.

        Args:
            citation_style: 'footnote' or 'inline'
        """
        self.citation_style = citation_style

    async def add_citations(
        self,
        file_path: Path,
        claims: list[dict[str, Any]],
        sources: list[dict[str, Any]],
    ) -> int:
        """
        Add citations to a markdown file.

        Returns:
            Number of citations added.
        """
        if not sources:
            return 0

        content = file_path.read_text(encoding="utf-8")
        citations_added = 0
        footnotes = []

        # Group sources by claim index
        sources_by_claim: dict[int, list[dict]] = {}
        for source in sources:
            idx = source.get("claim_index", 0)
            if idx not in sources_by_claim:
                sources_by_claim[idx] = []
            sources_by_claim[idx].append(source)

        # Find existing footnote numbers
        existing_footnotes = set(re.findall(r"\[\^(\d+)\]", content))
        next_footnote_num = max([int(n) for n in existing_footnotes], default=0) + 1

        # Process each claim with sources
        lines = content.split("\n")
        modified_lines: dict[int, str] = {}  # Track modified lines

        for claim_idx, claim_sources in sources_by_claim.items():
            if claim_idx >= len(claims):
                continue

            claim = claims[claim_idx]
            claim_text = claim.get("text", "")
            line_num = claim.get("line_number", 0)

            # Validate line number
            if line_num <= 0 or line_num > len(lines):
                logger.debug(f"Invalid line number {line_num} for claim: {claim_text[:50]}...")
                continue

            # Get the line (0-indexed)
            line_idx = line_num - 1
            line: str = modified_lines.get(line_idx) or lines[line_idx]

            # Skip if line already has citation markers
            if "[^" in line or "](http" in line:
                logger.debug(f"Line {line_num} already has citations, skipping")
                continue

            # Format citation based on style
            if self.citation_style == "footnote":
                citation_ref = f"[^{next_footnote_num}]"
                footnote_text = self._format_footnote(
                    next_footnote_num,
                    claim_sources[0],  # Use first source
                )
                footnotes.append(footnote_text)
                next_footnote_num += 1
            else:
                citation_ref = self._format_inline(claim_sources[0])

            # Insert citation at end of sentence on this line
            # Look for sentence-ending punctuation
            match = re.search(r"([.!?])(\s|$)", line)
            if match:
                insert_pos = match.start() + 1
                new_line = line[:insert_pos] + citation_ref + line[insert_pos:]
            else:
                # No punctuation found, append to end
                new_line = line.rstrip() + citation_ref

            modified_lines[line_idx] = new_line
            citations_added += 1

        # Apply modifications
        for line_idx, new_line in modified_lines.items():
            lines[line_idx] = new_line
        content = "\n".join(lines)

        # Add footnotes section if using footnote style
        if footnotes and self.citation_style == "footnote":
            # Check if there's already a references section
            if "\n## References\n" not in content and "\n## Notes\n" not in content:
                content += "\n\n## References\n\n"
            content += "\n".join(footnotes) + "\n"

        # Write updated content
        if citations_added > 0:
            file_path.write_text(content, encoding="utf-8")
            logger.info(f"Added {citations_added} citations to {file_path.name}")

        return citations_added

    def _format_footnote(self, num: int, source: dict[str, Any]) -> str:
        """Format a source as a footnote."""
        authors = source.get("authors", ["Unknown"])
        author_str = authors[0] if authors else "Unknown"
        if len(authors) > 1:
            author_str += " et al."

        year = source.get("year", "n.d.")
        title = source.get("title", "Untitled")
        url = source.get("url", "")

        if url:
            return f"[^{num}]: {author_str} ({year}). *{title}*. [{url}]({url})"
        return f"[^{num}]: {author_str} ({year}). *{title}*."

    def _format_inline(self, source: dict[str, Any]) -> str:
        """Format a source as an inline citation."""
        authors = source.get("authors", ["Unknown"])
        author_str = authors[0] if authors else "Unknown"
        year = source.get("year", "n.d.")
        url = source.get("url", "")

        if url:
            return f" ([{author_str} {year}]({url}))"
        return f" ({author_str} {year})"
