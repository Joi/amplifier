#!/usr/bin/env python3
"""
Learning Store - Persistent memory for metacognitive feedback loops.

This enables the curator to learn from past runs:
- Which sources work best for which domains
- How accurate our relevance predictions are
- What search refinements succeeded
- Overall verification statistics
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_LEARNING_PATH = Path.home() / ".data" / "knowledge_curator" / "learning.json"


class SearchOutcome(BaseModel):
    """Record of a search attempt outcome."""

    domain: str
    source_api: str  # semantic_scholar, crossref, arxiv, cinii
    query: str
    success: bool  # Did we find usable sources?
    verified_fit: bool | None = None  # Did verification confirm the fit?
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class VerificationRecord(BaseModel):
    """Record of a verification outcome."""

    claim_hash: str  # Hash of claim text for deduplication
    source_title: str
    outcome: str  # strong_fit, weak_fit, no_fit, uncertain
    confidence: float
    domain: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class CalibrationStats(BaseModel):
    """Statistics on prediction accuracy."""

    total_predictions: int = 0
    correct_predictions: int = 0
    accuracy: float = 0.0
    by_confidence_bucket: dict[str, dict[str, int]] = Field(default_factory=dict)


class LearningData(BaseModel):
    """Persistent learning data structure."""

    # Domain → Source API → success rate
    domain_source_success: dict[str, dict[str, float]] = Field(default_factory=dict)

    # Raw counts for computing success rates
    domain_source_counts: dict[str, dict[str, dict[str, int]]] = Field(default_factory=dict)

    # Verification outcomes aggregated
    verification_stats: dict[str, int] = Field(
        default_factory=lambda: {
            "strong_fit": 0,
            "weak_fit": 0,
            "no_fit": 0,
            "uncertain": 0,
        }
    )

    # Search refinements that worked
    successful_refinements: list[dict[str, str]] = Field(default_factory=list)

    # Last updated timestamp
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())


class CuratorLearning:
    """Persistent memory for curator metacognitive feedback.

    This store enables the curator to:
    1. Learn which sources work best for which domains
    2. Track verification outcomes to calibrate relevance scoring
    3. Remember successful search refinements
    4. Build a feedback loop that improves over time
    """

    def __init__(self, path: Path = DEFAULT_LEARNING_PATH):
        self.path = path
        self.data = self._load_or_create()

    def _load_or_create(self) -> LearningData:
        """Load existing learning data or create new."""
        if self.path.exists():
            try:
                with open(self.path) as f:
                    raw_data = json.load(f)
                return LearningData(**raw_data)
            except Exception as e:
                logger.warning(f"Failed to load learning data: {e}, starting fresh")
                return LearningData()
        return LearningData()

    def _save(self) -> None:
        """Save learning data to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data.last_updated = datetime.now().isoformat()
        with open(self.path, "w") as f:
            json.dump(self.data.model_dump(), f, indent=2)

    def record_search_outcome(
        self,
        domain: str,
        source_api: str,
        success: bool,
        verified_fit: bool | None = None,
    ) -> None:
        """Record outcome of a search attempt.

        Args:
            domain: Domain being searched (e.g., "chanoyu", "machine_learning")
            source_api: Which API was used (semantic_scholar, crossref, etc.)
            success: Did the search return usable results?
            verified_fit: If verification ran, did it confirm the fit?
        """
        # Initialize nested dicts if needed
        if domain not in self.data.domain_source_counts:
            self.data.domain_source_counts[domain] = {}
        if source_api not in self.data.domain_source_counts[domain]:
            self.data.domain_source_counts[domain][source_api] = {"success": 0, "total": 0, "verified": 0}

        # Update counts
        counts = self.data.domain_source_counts[domain][source_api]
        counts["total"] += 1
        if success:
            counts["success"] += 1
        if verified_fit:
            counts["verified"] += 1

        # Recompute success rate
        if domain not in self.data.domain_source_success:
            self.data.domain_source_success[domain] = {}

        # Weight verified successes more highly
        effective_success = counts["success"] + (counts["verified"] * 0.5)
        self.data.domain_source_success[domain][source_api] = effective_success / counts["total"]

        self._save()

    def record_verification(
        self,
        claim_text: str,
        source_title: str,
        outcome: str,
        confidence: float,
        domain: str | None = None,
    ) -> None:
        """Record a verification outcome.

        Args:
            claim_text: The claim that was being verified
            source_title: Title of the source
            outcome: Verification outcome (strong_fit, weak_fit, no_fit, uncertain)
            confidence: Confidence in the outcome
            domain: Domain if known
        """
        # Update aggregate stats
        if outcome in self.data.verification_stats:
            self.data.verification_stats[outcome] += 1

        self._save()
        logger.debug(f"Recorded verification: {outcome} ({confidence:.2f}) for '{source_title[:30]}...'")

    def record_successful_refinement(
        self,
        original_query: str,
        refined_query: str,
        domain: str | None = None,
    ) -> None:
        """Record a search refinement that succeeded.

        Args:
            original_query: The query that failed to find good sources
            refined_query: The refined query that worked
            domain: Domain if known
        """
        self.data.successful_refinements.append(
            {
                "original": original_query,
                "refined": refined_query,
                "domain": domain or "unknown",
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Keep only last 100 refinements
        if len(self.data.successful_refinements) > 100:
            self.data.successful_refinements = self.data.successful_refinements[-100:]

        self._save()

    def get_best_sources_for_domain(self, domain: str) -> list[str]:
        """Get source APIs ranked by success rate for a domain.

        Args:
            domain: The domain to get sources for

        Returns:
            List of source API names, best first
        """
        if domain not in self.data.domain_source_success:
            return []

        sources = self.data.domain_source_success[domain]
        # Sort by success rate descending
        ranked = sorted(sources.items(), key=lambda x: x[1], reverse=True)
        return [name for name, _ in ranked]

    def get_verification_stats(self) -> dict[str, int | float]:
        """Get aggregate verification statistics.

        Returns:
            Dictionary with verification outcome counts and rates
        """
        stats: dict[str, int | float] = dict(self.data.verification_stats)
        total = sum(self.data.verification_stats.values())

        if total > 0:
            stats["total"] = total
            stats["strong_fit_rate"] = self.data.verification_stats["strong_fit"] / total
            stats["rejection_rate"] = self.data.verification_stats["no_fit"] / total
        else:
            stats["total"] = 0
            stats["strong_fit_rate"] = 0.0
            stats["rejection_rate"] = 0.0

        return stats

    def get_domain_insights(self, domain: str) -> dict[str, Any]:
        """Get insights for a specific domain.

        Args:
            domain: Domain to analyze

        Returns:
            Dictionary with domain-specific insights
        """
        insights: dict[str, Any] = {
            "domain": domain,
            "source_rankings": self.get_best_sources_for_domain(domain),
            "total_searches": 0,
            "successful_refinements": [],
        }

        if domain in self.data.domain_source_counts:
            for _source, counts in self.data.domain_source_counts[domain].items():
                insights["total_searches"] += counts["total"]

        # Get refinements for this domain
        insights["successful_refinements"] = [r for r in self.data.successful_refinements if r.get("domain") == domain][
            -5:
        ]  # Last 5

        return insights

    def suggest_search_order(self, domain: str, default_order: list[str]) -> list[str]:
        """Suggest optimal search order based on learned success rates.

        Args:
            domain: The domain being searched
            default_order: Default order from configuration

        Returns:
            Reordered list of sources, best first
        """
        learned_order = self.get_best_sources_for_domain(domain)

        if not learned_order:
            return default_order

        # Merge: learned order first, then any defaults not in learned
        result = learned_order.copy()
        for source in default_order:
            if source not in result:
                result.append(source)

        return result

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all learning data.

        Returns:
            Dictionary with overall learning summary
        """
        return {
            "domains_tracked": list(self.data.domain_source_success.keys()),
            "verification_stats": self.get_verification_stats(),
            "total_refinements": len(self.data.successful_refinements),
            "last_updated": self.data.last_updated,
        }
