"""
Smart LLM Router - Routes queries between expensive LLM and cheap rule-based handlers.

This module implements a heuristic-based router that decides whether a query needs
full LLM processing or can be handled by simpler, cheaper methods.

Design Philosophy:
- Start with simple heuristics that work (ruthless simplicity)
- Learn from outcomes to improve over time
- Can be extended with probabilistic inference later (GenJax) when needed
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import re
import json
from pathlib import Path


class RouteTarget(Enum):
    """Where to route the query."""
    LLM = "llm"  # Full LLM processing (expensive but capable)
    RULES = "rules"  # Rule-based handler (cheap but limited)


@dataclass
class QueryFeatures:
    """Features extracted from a query for routing decision."""
    word_count: int
    has_code: bool
    has_question: bool
    complexity_score: float  # 0.0 to 1.0
    domain_keywords: list[str] = field(default_factory=list)

    @classmethod
    def from_query(cls, query: str) -> "QueryFeatures":
        """Extract features from a query string."""
        words = query.split()
        word_count = len(words)

        # Check for code patterns
        code_patterns = [
            r'```',  # Code blocks
            r'def\s+\w+',  # Python function
            r'class\s+\w+',  # Class definition
            r'import\s+\w+',  # Import statements
            r'function\s+\w+',  # JS function
            r'\w+\s*=\s*\w+',  # Assignment
            r'<\w+>',  # XML/HTML tags
        ]
        has_code = any(re.search(p, query) for p in code_patterns)

        # Check for question patterns
        question_patterns = [
            r'\?$',  # Ends with question mark
            r'^(what|how|why|when|where|who|which|can|could|should|would|is|are|do|does)\b',
        ]
        has_question = any(re.search(p, query, re.IGNORECASE) for p in question_patterns)

        # Calculate complexity score
        complexity = 0.0

        # Length adds complexity
        if word_count > 50:
            complexity += 0.3
        elif word_count > 20:
            complexity += 0.2
        elif word_count > 10:
            complexity += 0.1

        # Code adds complexity significantly
        if has_code:
            complexity += 0.35

        # Technical terms add complexity - more terms = more complex
        technical_terms = [
            'algorithm', 'architecture', 'implementation', 'optimize',
            'refactor', 'debug', 'performance', 'async', 'concurrent',
            'database', 'api', 'security', 'authentication', 'deploy'
        ]
        query_lower = query.lower()
        found_technical = [t for t in technical_terms if t in query_lower]
        # Each technical term adds 0.1, cap at 0.5
        complexity += min(len(found_technical) * 0.1, 0.5)

        # Multi-part questions add complexity
        if query.count('?') > 1:
            complexity += 0.15

        # Cap complexity at 1.0
        complexity = min(complexity, 1.0)

        return cls(
            word_count=word_count,
            has_code=has_code,
            has_question=has_question,
            complexity_score=complexity,
            domain_keywords=found_technical,
        )


@dataclass
class RoutingDecision:
    """The result of a routing decision."""
    target: RouteTarget
    confidence: float  # 0.0 to 1.0
    reason: str
    features: QueryFeatures


@dataclass
class RoutingOutcome:
    """Record of how a routing decision turned out."""
    query_hash: str
    target: RouteTarget
    was_successful: bool
    feedback_score: Optional[float] = None  # User satisfaction if available


class SmartRouter:
    """
    Routes queries between expensive LLM and cheap rule-based handlers.

    Uses heuristic scoring to decide routing, learning from outcomes to improve.

    Example:
        router = SmartRouter()
        decision = router.decide("What is 2+2?")
        if decision.target == RouteTarget.RULES:
            # Use cheap rule-based handler
            pass
        else:
            # Use full LLM
            pass
    """

    def __init__(
        self,
        llm_threshold: float = 0.5,
        history_file: Optional[Path] = None,
    ):
        """
        Initialize the router.

        Args:
            llm_threshold: Complexity score above which queries go to LLM (0.0-1.0)
            history_file: Optional path to persist routing history for learning
        """
        self.llm_threshold = llm_threshold
        self.history_file = history_file
        self.history: list[RoutingOutcome] = []

        # Load history if file exists
        if history_file and history_file.exists():
            self._load_history()

    def decide(self, query: str) -> RoutingDecision:
        """
        Decide where to route a query.

        Args:
            query: The user's query string

        Returns:
            RoutingDecision with target, confidence, and reasoning
        """
        features = QueryFeatures.from_query(query)

        # Calculate routing score
        score = self._calculate_score(features)

        # Make decision
        if score >= self.llm_threshold:
            target = RouteTarget.LLM
            reason = self._explain_llm_decision(features, score)
        else:
            target = RouteTarget.RULES
            reason = self._explain_rules_decision(features, score)

        # Confidence is how far from threshold we are
        distance_from_threshold = abs(score - self.llm_threshold)
        confidence = min(0.5 + distance_from_threshold, 1.0)

        return RoutingDecision(
            target=target,
            confidence=confidence,
            reason=reason,
            features=features,
        )

    def _calculate_score(self, features: QueryFeatures) -> float:
        """
        Calculate a routing score from features.

        Higher score = more likely to need LLM.
        """
        score = 0.0

        # Base complexity contributes directly
        score += features.complexity_score * 0.7

        # Code presence is a strong signal for LLM
        if features.has_code:
            score += 0.3

        # Questions often need reasoning
        if features.has_question:
            score += 0.1

        # Very short queries might be simple
        if features.word_count < 5:
            score -= 0.15

        # Historical success rate adjustment
        success_rate = self._get_success_rate(features)
        if success_rate is not None:
            # If similar queries succeeded with rules, bias toward rules
            score -= (success_rate - 0.5) * 0.2

        # Clamp to valid range
        return max(0.0, min(1.0, score))

    def _get_success_rate(self, features: QueryFeatures) -> Optional[float]:
        """Get historical success rate for similar queries."""
        if not self.history:
            return None

        # Find similar outcomes (simple similarity: same has_code and similar complexity)
        similar = [
            h for h in self.history
            if abs(hash(str(features.has_code)) - hash(str(h.target == RouteTarget.LLM))) < 0.3
        ]

        if not similar:
            return None

        successful = sum(1 for h in similar if h.was_successful)
        return successful / len(similar)

    def _explain_llm_decision(self, features: QueryFeatures, score: float) -> str:
        """Generate explanation for routing to LLM."""
        reasons = []

        if features.complexity_score >= 0.5:
            reasons.append("high complexity")
        if features.has_code:
            reasons.append("contains code")
        if features.domain_keywords:
            reasons.append(f"technical terms: {', '.join(features.domain_keywords[:3])}")
        if features.word_count > 50:
            reasons.append("lengthy query")

        if not reasons:
            reasons.append("overall assessment suggests LLM needed")

        return f"Routing to LLM (score: {score:.2f}): {'; '.join(reasons)}"

    def _explain_rules_decision(self, features: QueryFeatures, score: float) -> str:
        """Generate explanation for routing to rules."""
        reasons = []

        if features.complexity_score < 0.3:
            reasons.append("low complexity")
        if features.word_count < 10:
            reasons.append("short query")
        if not features.has_code:
            reasons.append("no code detected")

        if not reasons:
            reasons.append("simple enough for rule-based handling")

        return f"Routing to rules (score: {score:.2f}): {'; '.join(reasons)}"

    def record_outcome(
        self,
        decision: RoutingDecision,
        was_successful: bool,
        feedback_score: Optional[float] = None,
    ) -> None:
        """
        Record the outcome of a routing decision for learning.

        Args:
            decision: The original routing decision
            was_successful: Whether the handling was successful
            feedback_score: Optional user satisfaction score (0.0-1.0)
        """
        outcome = RoutingOutcome(
            query_hash=str(hash(str(decision.features))),
            target=decision.target,
            was_successful=was_successful,
            feedback_score=feedback_score,
        )
        self.history.append(outcome)

        # Persist if history file configured
        if self.history_file:
            self._save_history()

    def adjust_threshold(self, delta: float) -> None:
        """
        Adjust the LLM threshold.

        Positive delta = more queries go to rules (cost savings)
        Negative delta = more queries go to LLM (quality focus)
        """
        self.llm_threshold = max(0.1, min(0.9, self.llm_threshold + delta))

    def get_stats(self) -> dict:
        """Get routing statistics."""
        if not self.history:
            return {"total": 0, "llm_rate": 0.0, "success_rate": 0.0}

        total = len(self.history)
        llm_count = sum(1 for h in self.history if h.target == RouteTarget.LLM)
        success_count = sum(1 for h in self.history if h.was_successful)

        return {
            "total": total,
            "llm_rate": llm_count / total,
            "rules_rate": (total - llm_count) / total,
            "success_rate": success_count / total,
            "current_threshold": self.llm_threshold,
        }

    def _load_history(self) -> None:
        """Load history from file."""
        if not self.history_file or not self.history_file.exists():
            return

        try:
            with open(self.history_file) as f:
                data = json.load(f)
                self.history = [
                    RoutingOutcome(
                        query_hash=h["query_hash"],
                        target=RouteTarget(h["target"]),
                        was_successful=h["was_successful"],
                        feedback_score=h.get("feedback_score"),
                    )
                    for h in data
                ]
        except (json.JSONDecodeError, KeyError):
            self.history = []

    def _save_history(self) -> None:
        """Save history to file."""
        if not self.history_file:
            return

        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        data = [
            {
                "query_hash": h.query_hash,
                "target": h.target.value,
                "was_successful": h.was_successful,
                "feedback_score": h.feedback_score,
            }
            for h in self.history
        ]

        with open(self.history_file, "w") as f:
            json.dump(data, f, indent=2)
