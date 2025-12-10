#!/usr/bin/env python3
"""
Claim Extractor - Extracts verifiable claims from markdown files.

Uses AI to identify statements that would benefit from citations.

Key improvements over simple pattern matching:
1. Pre-filters structural content (tables, links, navigation, frontmatter)
2. Validates that extracted "claims" are actual verifiable assertions
3. Separates prose content from reference/index content
"""

import re
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


class Claim(BaseModel):
    """A claim extracted from a markdown file."""

    text: str
    line_number: int
    context: str  # surrounding text for matching
    confidence: float  # 0-1 how confident this needs a citation
    category: str  # factual, statistical, attribution, etc.


class ClaimList(BaseModel):
    """List of claims from a document."""

    claims: list[Claim]


class ClaimExtractor:
    """Extracts claims needing citations from markdown files.

    Key filtering applied:
    1. Removes structural content (frontmatter, tables, links, navigation)
    2. Focuses on prose paragraphs that contain actual assertions
    3. Validates that matched content is a verifiable claim, not structural
    """

    # Patterns that indicate structural/navigational content (not claims)
    STRUCTURAL_PATTERNS = [
        r"^\s*\|.*\|",  # Table rows
        r"^\s*\|-+",  # Table separators
        r"^\s*#{1,6}\s+",  # Headers
        r"^\s*[-*+]\s+\[\[",  # List items with wiki links
        r"^\s*[-*+]\s+\[.*?\]\(.*?\)",  # List items with markdown links
        r"^---\s*$",  # Horizontal rules / frontmatter delimiters
        r"^\s*```",  # Code blocks
        r"^\s*>\s*\[!",  # Callouts/admonitions
        r"^\s*\[\^",  # Footnote definitions
        r"^\s*\[.*?\]:\s*",  # Reference link definitions
    ]

    # Content that should never be treated as claims
    NON_CLAIM_CONTENT = [
        r"\[\[.*?\|.*?\]\]",  # Wiki links with display text
        r"\[\[.*?\]\]",  # Simple wiki links
        r"`/[a-z-]+`",  # CLI commands
        r"^\s*\|",  # Any table content
        r"^\s*[-*]\s+\*\*.*?\*\*\s*[-–:]",  # Bold list headers like "- **Item**: description"
    ]

    def __init__(self):
        self.agent = None
        self._init_agent()

    def _init_agent(self) -> None:
        """Initialize the AI agent for claim extraction."""
        try:
            self.agent = Agent(
                "claude-3-5-haiku-20241022",
                output_type=ClaimList,
                system_prompt="""You are an expert at identifying claims in text that would benefit from citations.

A claim that needs citation is:
- A factual statement that isn't common knowledge
- A statistic or numerical data
- An attribution to a specific person or source
- A historical fact or event
- A scientific or technical assertion

NOT claims needing citation:
- Opinions clearly stated as such
- Common knowledge ("water boils at 100C")
- Personal experiences or observations
- Questions or hypotheticals
- Claims that already have citations (footnotes, links)

For each claim, provide:
- The exact text of the claim
- The line number where it appears
- Surrounding context (for matching)
- Confidence (0-1) that it needs a citation
- Category: factual, statistical, attribution, historical, scientific, other

Be selective - only flag claims that would genuinely benefit from authoritative sources.""",
            )
        except Exception as e:
            logger.warning(f"Could not initialize AI agent: {e}")
            self.agent = None

    async def extract_claims(self, file_path: Path) -> list[Claim]:
        """Extract claims from a markdown file.

        Applies multiple layers of filtering:
        1. Skip reference/citation-heavy files
        2. Skip index/navigation files
        3. Extract only prose content (remove structural elements)
        4. Validate each claim is a real verifiable assertion
        """
        content = file_path.read_text(encoding="utf-8")

        # Skip files that are mostly citations/references
        if self._is_reference_file(content):
            logger.debug(f"Skipping reference file: {file_path.name}")
            return []

        # Skip index/navigation files - these have links, not claims
        if self._is_index_or_navigation_file(content, file_path):
            logger.debug(f"Skipping index/navigation file: {file_path.name}")
            return []

        # Skip very short files
        if len(content) < 100:
            return []

        # Extract only prose content for claim extraction
        prose_content = self._extract_prose_content(content)

        # If not much prose content, skip
        if len(prose_content) < 100:
            logger.debug(f"Skipping file with minimal prose: {file_path.name}")
            return []

        # If no AI agent, use fallback pattern matching
        if self.agent is None:
            return self._fallback_extraction(prose_content)

        try:
            # Limit content to avoid token limits
            truncated = prose_content[:15000] if len(prose_content) > 15000 else prose_content

            result = await self.agent.run(
                f"Extract claims needing citations from this markdown document:\n\n{truncated}"
            )

            # Validate each claim
            validated_claims = [c for c in result.output.claims if self._is_valid_claim(c.text)]
            if len(validated_claims) < len(result.output.claims):
                logger.debug(
                    f"Filtered {len(result.output.claims) - len(validated_claims)} invalid claims from {file_path.name}"
                )
            return validated_claims
        except Exception as e:
            logger.warning(f"AI extraction failed, using fallback: {e}")
            return self._fallback_extraction(prose_content)

    def _is_reference_file(self, content: str) -> bool:
        """Check if file is primarily references/citations."""
        # Count citation patterns
        footnote_count = len(re.findall(r"\[\^\d+\]", content))
        link_count = len(re.findall(r"\[.*?\]\(.*?\)", content))
        line_count = content.count("\n") + 1

        # If more than 30% of lines have citations, skip
        return (footnote_count + link_count) / max(line_count, 1) > 0.3

    def _is_index_or_navigation_file(self, content: str, file_path: Path) -> bool:
        """Check if file is primarily navigation/index content."""
        # Check filename patterns
        name_lower = file_path.name.lower()
        if any(pat in name_lower for pat in ["index", "readme", "contents", "navigation", "_structure"]):
            return True

        # Check content patterns - high ratio of links to prose
        wiki_links = len(re.findall(r"\[\[.*?\]\]", content))
        markdown_links = len(re.findall(r"\[.*?\]\(.*?\)", content))
        table_rows = len(re.findall(r"^\s*\|.*\|", content, re.MULTILINE))

        # Get approximate prose word count (excluding links and tables)
        prose = re.sub(r"\[\[.*?\]\]|\[.*?\]\(.*?\)|^\s*\|.*\|", "", content, flags=re.MULTILINE)
        word_count = len(prose.split())

        # If more structural elements than prose, it's likely an index
        structural_count = wiki_links + markdown_links + table_rows
        return structural_count > word_count / 10  # More than 1 structural element per 10 words

    def _extract_prose_content(self, content: str) -> str:
        """Extract only prose content, removing structural elements.

        This filters out:
        - YAML frontmatter
        - Tables
        - Navigation links
        - Code blocks
        - Headers (keep header text but mark section)
        """
        lines = content.split("\n")
        prose_lines = []
        in_frontmatter = False
        in_code_block = False

        for i, line in enumerate(lines):
            # Handle frontmatter
            if i == 0 and line.strip() == "---":
                in_frontmatter = True
                continue
            if in_frontmatter:
                if line.strip() == "---":
                    in_frontmatter = False
                continue

            # Handle code blocks
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            # Skip structural patterns
            if any(re.match(pattern, line) for pattern in self.STRUCTURAL_PATTERNS):
                continue

            # Skip lines that are primarily links
            stripped = line.strip()
            if stripped and self._is_primarily_links(stripped):
                continue

            # Keep prose lines
            if stripped:
                prose_lines.append(line)

        return "\n".join(prose_lines)

    def _is_primarily_links(self, line: str) -> bool:
        """Check if a line is primarily composed of links rather than prose."""
        # Remove links and see what's left
        without_wiki_links = re.sub(r"\[\[.*?\]\]", "", line)
        without_md_links = re.sub(r"\[.*?\]\(.*?\)", "", without_wiki_links)
        remaining = without_md_links.strip()

        # If less than 30% of content remains after removing links, it's mostly links
        if len(line) > 0:
            return len(remaining) / len(line) < 0.3
        return True

    def _is_valid_claim(self, claim_text: str) -> bool:
        """Validate that extracted text is actually a claim, not structural content."""
        # Reject if primarily links
        if self._is_primarily_links(claim_text):
            return False

        # Reject if matches non-claim patterns
        for pattern in self.NON_CLAIM_CONTENT:
            if re.search(pattern, claim_text):
                # Allow if there's substantial text around the link
                without_pattern = re.sub(pattern, "", claim_text)
                if len(without_pattern.strip()) < 20:  # Less than 20 chars of actual content
                    return False

        # Reject if it looks like a file path or URL
        if re.search(r"^[\w/-]+\.md$|^https?://|^/[\w/-]+$", claim_text.strip()):
            return False

        # Reject very short claims (likely fragments)
        if len(claim_text.strip()) < 30:
            return False

        # Reject if no verb (likely not a complete sentence/claim)
        # Simple check: must have common verb forms
        verbs = [
            # Being verbs
            "is",
            "are",
            "was",
            "were",
            "been",
            # Auxiliary verbs
            "has",
            "have",
            "had",
            "does",
            "did",
            # Common claim verbs
            "means",
            "requires",
            "includes",
            "indicates",
            "shows",
            "demonstrates",
            "suggests",
            "represents",
            "symbolizes",
            "traces",
            "originates",
            "developed",
            "created",
            "founded",
            "established",
            "wrote",
            # Additional verbs for assertions
            "expresses",
            "defines",
            "describes",
            "emphasizes",
            "explains",
            "refers",
            "states",
            "claims",
            "asserts",
            "argues",
            "believes",
            "considers",
            "holds",
            "maintains",
            "notes",
            "observes",
            "records",
            "reports",
            "says",
            "teaches",
            "used",
            "used",
            "coined",
            "introduced",
            "pioneered",
        ]
        has_verb = any(f" {v} " in claim_text.lower() or claim_text.lower().endswith(f" {v}") for v in verbs)
        if not has_verb:
            return False

        return True

    def _fallback_extraction(self, content: str) -> list[Claim]:
        """Pattern-based extraction when AI is unavailable.

        Enhanced with validation to filter out structural content.
        """
        claims = []
        lines = content.split("\n")

        # General patterns that suggest claims needing citations
        general_patterns = [
            (r"studies show|research indicates|according to", "attribution"),
            (r"\d+%|\d+ percent|statistics show", "statistical"),
            (r"in \d{4}|historically|was founded|was invented", "historical"),
            (r"scientifically|proven that|evidence suggests", "scientific"),
        ]

        # Tea ceremony / Japanese art history patterns
        # More specific patterns to avoid false positives
        tea_ceremony_patterns = [
            # Historical attributions with context - require surrounding text
            (r"(?:was )?made by|(?:was )?created by|(?:was )?owned by", "attribution"),
            (r"provenance[:\s]|originally owned|authenticated by", "attribution"),
            # Historical figures - require context like dates or titles
            (r"(?:tea master|founder|established by)\s+\w+", "historical"),
            (r"(sen no rikyū?|rikyū|sōtan|gengensai|enshu|oribe)", "historical"),
            # Specific verifiable facts with clear structure
            (r"national treasure|important cultural property|designated as", "factual"),
            (r"published in \d{4}|wrote in \d{4}|dated to \d{4}", "historical"),
            # Concepts with clear definitions
            (r"means \"[^\"]+\"|signifies|represents|symbolizes", "philosophical"),
        ]

        # Combine patterns - use tea ceremony patterns first for domain content
        all_patterns = tea_ceremony_patterns + general_patterns

        for i, line in enumerate(lines, 1):
            # Skip structural content
            if any(re.match(pattern, line) for pattern in self.STRUCTURAL_PATTERNS):
                continue

            # Skip lines with existing citations
            if "[^" in line and "]:" not in line:  # Has footnote ref but not a definition
                continue

            # Skip if primarily links
            if self._is_primarily_links(line):
                continue

            for pattern, category in all_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    claim_text = line.strip()

                    # Validate the claim before adding
                    if not self._is_valid_claim(claim_text):
                        continue

                    claims.append(
                        Claim(
                            text=claim_text,
                            line_number=i,
                            context=claim_text[:100],
                            confidence=0.6,  # Lower confidence for pattern matching
                            category=category,
                        )
                    )
                    break  # One match per line

        return claims
