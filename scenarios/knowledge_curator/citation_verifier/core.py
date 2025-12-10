#!/usr/bin/env python3
"""
Citation Verifier - Validates that found sources actually support claims.

This is the first metacognitive feedback loop: Critic-Creator pattern.
Instead of blindly accepting sources based on relevance_score, we verify
that the source actually supports the claim using AI evaluation.
"""

import os
from enum import Enum
from typing import Any

from anthropic import Anthropic
from pydantic import BaseModel

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


class VerificationOutcome(str, Enum):
    """Result of verifying a citation-claim match."""

    STRONG_FIT = "strong_fit"  # Source clearly supports the claim
    WEAK_FIT = "weak_fit"  # Source partially/tangentially supports
    NO_FIT = "no_fit"  # Source doesn't actually support this claim
    UNCERTAIN = "uncertain"  # Can't determine from available info


class VerificationResult(BaseModel):
    """Result of citation verification."""

    outcome: VerificationOutcome
    confidence: float  # 0-1 how confident in this assessment
    explanation: str  # Brief explanation of why
    suggested_refinement: str | None = None  # If NO_FIT, suggest better search terms


class CitationVerifier:
    """Validates that found sources actually support claims.

    The core metacognitive question: "Does this source ACTUALLY support this claim?"

    This catches false positives from keyword-based matching, where a source
    might have relevant terms but discuss a completely different context.
    """

    def __init__(self, model: str = "claude-3-5-haiku-20241022", api_key: str | None = None):
        self.model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client: Anthropic | None = None

    @property
    def client(self) -> Anthropic:
        if self._client is None:
            if not self._api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY not found. Set the environment variable or pass api_key to CitationVerifier."
                )
            self._client = Anthropic(api_key=self._api_key)
        return self._client

    def verify_citation_fit(
        self,
        claim_text: str,
        source_title: str,
        source_abstract: str | None = None,
        source_authors: list[str] | None = None,
        source_year: int | None = None,
    ) -> VerificationResult:
        """Verify that a source actually supports the given claim.

        Args:
            claim_text: The claim that needs citation
            source_title: Title of the found source
            source_abstract: Abstract if available (improves accuracy)
            source_authors: Author names if available
            source_year: Publication year if available

        Returns:
            VerificationResult with outcome, confidence, and explanation
        """
        # Build source context
        source_info = f"Title: {source_title}"
        if source_authors:
            source_info += f"\nAuthors: {', '.join(source_authors[:3])}"
        if source_year:
            source_info += f"\nYear: {source_year}"
        if source_abstract:
            source_info += f"\nAbstract: {source_abstract[:500]}..."

        prompt = f"""Evaluate whether this academic source actually supports the given claim.

CLAIM TO VERIFY:
"{claim_text}"

SOURCE INFORMATION:
{source_info}

Analyze carefully:
1. Does the source title/abstract indicate it discusses the same topic as the claim?
2. Is the source about the same domain, context, and meaning?
3. Would citing this source genuinely support the claim?

Be strict - a source about "tea" doesn't support a claim about "Japanese tea ceremony" unless it specifically covers that context.

Respond with a JSON object:
{{
    "outcome": "strong_fit" | "weak_fit" | "no_fit" | "uncertain",
    "confidence": 0.0-1.0,
    "explanation": "Brief reason for this assessment",
    "suggested_refinement": "If no_fit, suggest better search terms, else null"
}}

Only output the JSON, nothing else."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            content_block = response.content[0]
            if not hasattr(content_block, "text"):
                raise ValueError("Unexpected response format from API")
            result_text = content_block.text.strip()  # type: ignore[union-attr]

            # Handle markdown code blocks
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            import json

            result_data = json.loads(result_text)

            return VerificationResult(
                outcome=VerificationOutcome(result_data["outcome"]),
                confidence=float(result_data["confidence"]),
                explanation=result_data["explanation"],
                suggested_refinement=result_data.get("suggested_refinement"),
            )

        except Exception as e:
            logger.warning(f"Verification failed: {e}")
            # Default to uncertain on error
            return VerificationResult(
                outcome=VerificationOutcome.UNCERTAIN,
                confidence=0.3,
                explanation=f"Verification error: {str(e)[:50]}",
                suggested_refinement=None,
            )

    def suggest_search_refinement(
        self,
        claim_text: str,
        failed_sources: list[dict[str, Any]],
    ) -> str | None:
        """Given sources that didn't fit, suggest better search terms.

        This is part of the progressive refinement pattern - learn from
        what didn't work to improve the next search.
        """
        if not failed_sources:
            return None

        failed_titles = "\n".join(f"- {s.get('title', 'Unknown')}" for s in failed_sources[:5])

        prompt = f"""A search for citations to support this claim found sources that don't actually fit:

CLAIM:
"{claim_text}"

SOURCES FOUND (but don't support the claim):
{failed_titles}

The found sources were off-topic or wrong context. Suggest better search terms
that would find sources specifically supporting this claim.

Output only the refined search query (5-10 words), nothing else."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )
            content_block = response.content[0]
            if not hasattr(content_block, "text"):
                return None
            return content_block.text.strip()  # type: ignore[union-attr]
        except Exception as e:
            logger.warning(f"Refinement suggestion failed: {e}")
            return None

    def batch_verify(
        self,
        claim_text: str,
        sources: list[dict[str, Any]],
    ) -> list[tuple[dict[str, Any], VerificationResult]]:
        """Verify multiple sources for a single claim.

        Returns list of (source, verification_result) tuples, sorted by fit quality.
        """
        results = []
        for source in sources:
            result = self.verify_citation_fit(
                claim_text=claim_text,
                source_title=source.get("title", ""),
                source_abstract=source.get("abstract"),
                source_authors=source.get("authors"),
                source_year=source.get("year"),
            )
            results.append((source, result))

        # Sort by outcome quality (strong > weak > uncertain > no_fit)
        # and then by confidence
        outcome_order = {
            VerificationOutcome.STRONG_FIT: 0,
            VerificationOutcome.WEAK_FIT: 1,
            VerificationOutcome.UNCERTAIN: 2,
            VerificationOutcome.NO_FIT: 3,
        }

        results.sort(key=lambda x: (outcome_order[x[1].outcome], -x[1].confidence))
        return results
