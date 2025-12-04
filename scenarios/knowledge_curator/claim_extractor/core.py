#!/usr/bin/env python3
"""
Claim Extractor - Extracts verifiable claims from markdown files.

Uses AI to identify statements that would benefit from citations.
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
    """Extracts claims needing citations from markdown files."""

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
        """Extract claims from a markdown file."""
        content = file_path.read_text(encoding="utf-8")

        # Skip files that are mostly citations/references
        if self._is_reference_file(content):
            logger.debug(f"Skipping reference file: {file_path.name}")
            return []

        # Skip very short files
        if len(content) < 100:
            return []

        # If no AI agent, use fallback pattern matching
        if self.agent is None:
            return self._fallback_extraction(content)

        try:
            # Limit content to avoid token limits
            truncated = content[:15000] if len(content) > 15000 else content

            result = await self.agent.run(
                f"Extract claims needing citations from this markdown document:\n\n{truncated}"
            )
            return result.output.claims
        except Exception as e:
            logger.warning(f"AI extraction failed, using fallback: {e}")
            return self._fallback_extraction(content)

    def _is_reference_file(self, content: str) -> bool:
        """Check if file is primarily references/citations."""
        # Count citation patterns
        footnote_count = len(re.findall(r"\[\^\d+\]", content))
        link_count = len(re.findall(r"\[.*?\]\(.*?\)", content))
        line_count = content.count("\n") + 1

        # If more than 30% of lines have citations, skip
        return (footnote_count + link_count) / max(line_count, 1) > 0.3

    def _fallback_extraction(self, content: str) -> list[Claim]:
        """Pattern-based extraction when AI is unavailable."""
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
        tea_ceremony_patterns = [
            # Historical attributions and provenance
            (r"made by|created by|owned by|held by|passed to|given to|formerly", "attribution"),
            (r"provenance:|originally owned|box by|authenticated", "attribution"),
            # Historical figures and dates
            (r"era|period|generation|founder|master", "historical"),
            (r"(1[4-9]\d{2}|20[0-2]\d)[-–]?(1[4-9]\d{2}|20[0-2]\d)?", "historical"),  # Years 1400-2029
            # Tea ceremony specific terminology indicating verifiable claims
            (r"urasenke|omotesenke|sansenke|mushanokoji", "factual"),
            (r"rikyu|sotan|senso|gengensai|enshu|oribe|sekishu", "historical"),
            (r"raku|hagi|bizen|shigaraki|karatsu|takatori|ohi", "factual"),
            (r"meibutsu|karamono|wamono", "factual"),
            # Art/material attributions
            (r"technique:|style:|material:|clay:", "factual"),
            (r"national treasure|important cultural property", "factual"),
            # Zen/philosophical claims
            (r"zen meaning|symbolism:|represents|signifies", "philosophical"),
        ]

        # Combine patterns - use tea ceremony patterns first for domain content
        all_patterns = tea_ceremony_patterns + general_patterns

        for i, line in enumerate(lines, 1):
            # Skip headers, code blocks, existing citations, table headers
            if line.startswith("#") or line.startswith("```") or "[^" in line:
                continue
            if line.startswith("|") and "---" in line:
                continue

            for pattern, category in all_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    claims.append(
                        Claim(
                            text=line.strip(),
                            line_number=i,
                            context=line.strip()[:100],
                            confidence=0.6,  # Lower confidence for pattern matching
                            category=category,
                        )
                    )
                    break  # One match per line

        return claims
