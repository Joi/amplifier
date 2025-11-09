"""Design Review Module - Independent validation with zero context pollution.

This module provides both code-based and LLM-based design validation with
strict isolation to prevent context pollution between validations.
"""

import asyncio
import json
import re
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Protocol
from typing import runtime_checkable

from pydantic import BaseModel
from pydantic_ai import Agent


@dataclass
class ValidationResult:
    """Result of a design validation."""

    passed: bool
    issues: list[str]
    coverage: float  # 0.0 to 1.0
    details: dict[str, Any]


@dataclass
class MatchResult:
    """Result of requirement matching."""

    coverage: float
    matched_requirements: list[str]
    unmatched_requirements: list[str]
    extracted_requirements: list[str]
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PollutionReport:
    """Report on context pollution detection."""

    is_polluted: bool
    leaked_terms: list[str]
    unstated_assumptions: list[str]
    confidence: float  # 0.0 to 1.0


@runtime_checkable
class DesignReviewer(Protocol):
    """Protocol for design reviewers."""

    def validate(self, user_req: str, design_output: dict) -> ValidationResult:
        """Validate a design against user requirements."""
        ...


class CodeBasedDesignReviewer:
    """Code-based structural validation of designs."""

    def validate(self, user_req: str, design_output: dict) -> ValidationResult:
        """Validate design structure and completeness.

        Args:
            user_req: User requirements text
            design_output: Design output dictionary

        Returns:
            ValidationResult with structural validation
        """
        issues = []
        required_sections = ["overview", "components", "data_flow", "validation"]
        present_sections = []

        # Check required sections
        for section in required_sections:
            if section not in design_output or not design_output[section]:
                issues.append(f"Missing required section: {section}")
            else:
                present_sections.append(section)

        # Calculate coverage
        coverage = len(present_sections) / len(required_sections)

        # Additional validation for components
        if "components" in design_output:
            components = design_output["components"]
            if isinstance(components, list):
                for comp in components:
                    if not isinstance(comp, dict):
                        issues.append(f"Invalid component format: {comp}")
                    elif "name" not in comp or "purpose" not in comp:
                        issues.append(f"Component missing name or purpose: {comp}")
            else:
                issues.append("Components should be a list")
                coverage *= 0.5

        # Ensure statelessness - generate unique ID for this validation
        import uuid

        design_id = str(uuid.uuid4())

        return ValidationResult(
            passed=len(issues) == 0 and coverage >= 0.8,
            issues=issues,
            coverage=coverage,
            details={
                "design_id": design_id,
                "sections_present": present_sections,
                "sections_missing": [s for s in required_sections if s not in present_sections],
            },
        )


class LLMDesignReviewResponse(BaseModel):
    """Response structure for LLM design review."""

    passed: bool
    issues: list[str]
    semantic_coverage: float
    reasoning: str


class LLMDesignReviewer:
    """LLM-based semantic validation of designs."""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        """Initialize with model name only - no persistent state."""
        self.model = model
        # Note: No agent stored as instance variable to ensure fresh context

    async def validate_async(self, user_req: str, design_output: dict) -> ValidationResult:
        """Asynchronously validate design semantics using fresh LLM context.

        Args:
            user_req: User requirements text
            design_output: Design output dictionary

        Returns:
            ValidationResult with semantic validation
        """
        # Create fresh agent for each validation - ensures zero context pollution
        agent = Agent(
            model=self.model,
            result_type=LLMDesignReviewResponse,
            system=(
                "You are a design validator. Analyze if the design meets the requirements. "
                "Focus ONLY on the provided requirements and design. "
                "Do NOT reference any previous validations or external context."
            ),
        )

        # Build isolated prompt
        prompt = f"""
        Validate this design against the user requirements.

        User Requirements:
        {user_req}

        Design Output:
        {json.dumps(design_output, indent=2)}

        Analyze:
        1. Does the design address all stated requirements?
        2. Are there any missing components?
        3. What is the coverage percentage (0-1)?

        Respond with validation results. Base your analysis ONLY on what is provided above.
        """

        # Run validation with fresh context
        response = await agent.run(prompt)

        # Handle both real responses and mock responses
        if hasattr(response.data, "passed"):
            # Real Pydantic model response
            passed = response.data.passed
            issues = response.data.issues
            coverage = response.data.semantic_coverage
            reasoning = response.data.reasoning
        else:
            # Mock dict response for testing
            passed = response.data["passed"]
            issues = response.data["issues"]
            coverage = response.data["semantic_coverage"]
            reasoning = response.data["reasoning"]

        return ValidationResult(
            passed=passed,
            issues=issues,
            coverage=coverage,
            details={"reasoning": reasoning, "model": self.model, "validation_type": "semantic"},
        )

    def validate(self, user_req: str, design_output: dict) -> ValidationResult:
        """Synchronous wrapper for async validation.

        Args:
            user_req: User requirements text
            design_output: Design output dictionary

        Returns:
            ValidationResult with semantic validation
        """
        return asyncio.run(self.validate_async(user_req, design_output))


class RequirementMatcher:
    """Extract and match requirements to design outputs."""

    def extract_requirements(self, text: str) -> list[str]:
        """Extract individual requirements from user text.

        Args:
            text: User requirements text

        Returns:
            List of extracted requirement strings
        """
        requirements = []

        # Extract bullet points
        bullet_pattern = r"[-•*]\s*([^\n]+)"
        bullets = re.findall(bullet_pattern, text)
        requirements.extend(bullets)

        # Extract numbered items
        numbered_pattern = r"\d+\.\s*([^\n]+)"
        numbered = re.findall(numbered_pattern, text)
        requirements.extend(numbered)

        # If no structured format, split by common requirement keywords
        if not requirements:
            # Look for requirement indicators
            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                if (
                    any(
                        keyword in line.lower()
                        for keyword in ["must", "should", "need", "require", "build", "create", "implement"]
                    )
                    and len(line) > 10
                ):  # Filter out too-short lines
                    requirements.append(line)

        # Clean and deduplicate
        requirements = [req.strip() for req in requirements if req.strip()]
        return list(dict.fromkeys(requirements))  # Preserve order, remove duplicates

    def calculate_coverage(self, requirements: list[str], design_output: dict) -> float:
        """Calculate how much of requirements are covered by design.

        Args:
            requirements: List of requirement strings
            design_output: Design output dictionary

        Returns:
            Coverage score between 0.0 and 1.0
        """
        if not requirements:
            return 1.0

        # Convert design to searchable text
        design_text = json.dumps(design_output).lower()

        matched = 0
        for req in requirements:
            # Check if key terms from requirement appear in design
            req_terms = {word.lower() for word in req.split() if len(word) > 3 and word.isalnum()}

            if req_terms:
                # Count how many requirement terms appear in design
                terms_found = sum(1 for term in req_terms if term in design_text)
                if terms_found >= len(req_terms) * 0.5:  # At least 50% of terms
                    matched += 1

        return matched / len(requirements)

    def match(self, user_req: str, design_output: dict) -> MatchResult:
        """Match requirements to design output.

        Args:
            user_req: User requirements text
            design_output: Design output dictionary

        Returns:
            MatchResult with coverage and gap analysis
        """
        # Extract requirements
        requirements = self.extract_requirements(user_req)

        # Calculate coverage
        coverage = self.calculate_coverage(requirements, design_output)

        # Identify matched vs unmatched
        design_text = json.dumps(design_output).lower()
        matched_reqs = []
        unmatched_reqs = []

        for req in requirements:
            req_terms = {word.lower() for word in req.split() if len(word) > 3 and word.isalnum()}

            if req_terms:
                terms_found = sum(1 for term in req_terms if term in design_text)
                if terms_found >= len(req_terms) * 0.5:
                    matched_reqs.append(req)
                else:
                    unmatched_reqs.append(req)
            else:
                unmatched_reqs.append(req)

        return MatchResult(
            coverage=coverage,
            matched_requirements=matched_reqs,
            unmatched_requirements=unmatched_reqs,
            extracted_requirements=requirements,
            details={
                "total_requirements": len(requirements),
                "matched_count": len(matched_reqs),
                "unmatched_count": len(unmatched_reqs),
            },
        )


class IndependentValidator:
    """Validate independence and detect context pollution."""

    def detect_leaked_terms(self, result: ValidationResult, allowed_terms: set[str]) -> list[str]:
        """Detect terms in validation that aren't in allowed set.

        Args:
            result: Validation result to check
            allowed_terms: Set of terms that should appear

        Returns:
            List of leaked/unexpected terms
        """
        # Extract all text from result
        result_text = json.dumps(result.issues) + json.dumps(result.details)

        # Extract words from result
        words = re.findall(r"\b[a-zA-Z]+\b", result_text.lower())
        result_terms = set(words)

        # Common words to ignore
        common_words = {
            "the",
            "and",
            "or",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "a",
            "an",
            "to",
            "for",
            "from",
            "with",
            "without",
            "on",
            "in",
            "at",
            "by",
            "up",
            "down",
            "missing",
            "lacks",
            "unlike",
            "design",
            "uses",
            "found",
            "components",
            "reasoning",
            "validation",
            "passed",
            "issues",
        }

        # Normalize allowed terms
        normalized_allowed = {term.lower() for term in allowed_terms}
        normalized_allowed.update(common_words)

        # Find leaked terms
        leaked = []
        for term in result_terms:
            if term not in normalized_allowed and len(term) > 3:
                # Check for specific technology terms that indicate pollution
                if term in ["redis", "kafka", "docker", "kubernetes", "react", "vue"]:
                    leaked.append(term)
                # Check for references to other contexts
                elif (
                    term in ["previous", "earlier", "iteration", "platform", "commerce", "payment", "integration"]
                    and term not in normalized_allowed
                ):
                    # Check if these terms are genuinely leaked (not in context)
                    leaked.append(term)

        return list(set(leaked))  # Deduplicate

    def check_pollution(self, result: ValidationResult, context: dict) -> PollutionReport:
        """Check if validation result contains pollution from other contexts.

        Args:
            result: Validation result to check
            context: Current validation context

        Returns:
            PollutionReport with pollution analysis
        """
        leaked_terms = []
        unstated_assumptions = []

        # Extract context terms
        context_text = json.dumps(context).lower()
        context_words = set(re.findall(r"\b[a-zA-Z]+\b", context_text))

        # Check for leaked terms
        potential_leaks = self.detect_leaked_terms(result, context_words)
        leaked_terms.extend(potential_leaks)

        # Check for references to other contexts
        result_text = json.dumps(result.issues) + json.dumps(result.details)

        # Look for comparison/reference patterns
        pollution_patterns = [
            r"previous\s+\w+",
            r"earlier\s+\w+",
            r"unlike\s+the\s+\w+",
            r"compared\s+to\s+\w+",
            r"from\s+project\s+\w+",
            r"last\s+\w+",
            r"iteration",
            r"version\s+\d+",
            r"v\d+",
        ]

        for pattern in pollution_patterns:
            matches = re.findall(pattern, result_text.lower())
            if matches:
                unstated_assumptions.extend(matches)

        # Check for technology assumptions not in requirements
        tech_assumptions = ["react", "vue", "docker", "kubernetes", "redis", "kafka", "aws"]
        for tech in tech_assumptions:
            if tech in result_text.lower() and tech not in context_text:
                unstated_assumptions.append(f"Assumes {tech}")

        # Check details for assumptions
        if "assumptions" in result.details:
            assumptions = result.details["assumptions"]
            if isinstance(assumptions, list):
                for assumption in assumptions:
                    assumption_lower = assumption.lower()
                    # Check if assumption contains terms not in context
                    if any(
                        term in assumption_lower for term in ["millions", "distributed", "aws", "cloud", "scale"]
                    ) and not any(
                        term in context_text for term in ["millions", "distributed", "aws", "cloud", "scale"]
                    ):
                        unstated_assumptions.append(assumption)

        # Calculate confidence
        confidence = 0.5  # Base confidence

        if leaked_terms:
            confidence += 0.2
        if unstated_assumptions:
            confidence += 0.3
        if len(leaked_terms) > 3 or len(unstated_assumptions) > 2:
            confidence = min(confidence + 0.2, 1.0)

        # Determine if polluted
        is_polluted = len(leaked_terms) > 0 or len(unstated_assumptions) > 0

        # For clean results, high confidence means we're confident it's clean
        if not is_polluted:
            confidence = 0.9  # High confidence in cleanliness

        return PollutionReport(
            is_polluted=is_polluted,
            leaked_terms=list(set(leaked_terms)),
            unstated_assumptions=list(set(unstated_assumptions)),
            confidence=confidence,
        )
