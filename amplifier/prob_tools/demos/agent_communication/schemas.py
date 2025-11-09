"""Shared Pydantic schemas for agent communication demo.

These schemas define the structure of messages exchanged between agents
in a multi-agent code review system.
"""

from enum import Enum

from pydantic import BaseModel
from pydantic import Field


class Severity(str, Enum):
    """Severity levels for code findings."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingType(str, Enum):
    """Types of code findings."""

    BUG = "BUG"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    STYLE = "STYLE"
    MAINTAINABILITY = "MAINTAINABILITY"


class ReviewStatus(str, Enum):
    """Status of a code review."""

    APPROVED = "APPROVED"
    NEEDS_CHANGES = "NEEDS_CHANGES"
    REJECTED = "REJECTED"


class CodeFinding(BaseModel):
    """A single finding from code analysis."""

    finding_type: FindingType = Field(..., description="Type of finding")
    severity: Severity = Field(..., description="Severity level")
    file_path: str = Field(..., description="Path to the file with the issue")
    line_number: int = Field(..., description="Line number where issue occurs", ge=1)
    description: str = Field(..., description="Description of the issue")
    suggested_fix: str | None = Field(None, description="Suggested fix for the issue")


class AnalyzerMessage(BaseModel):
    """Message from the Analyzer Agent to Reviewer Agent."""

    agent_id: str = Field(..., description="Unique identifier for the analyzer agent")
    analyzed_files: list[str] = Field(..., description="List of files analyzed")
    findings: list[CodeFinding] = Field(..., description="List of findings discovered")
    total_lines_analyzed: int = Field(..., description="Total lines of code analyzed", ge=0)
    analysis_duration_ms: int = Field(..., description="Analysis duration in milliseconds", ge=0)


class ReviewRecommendation(BaseModel):
    """A recommendation from the reviewer."""

    finding_id: int = Field(..., description="Index of the finding being reviewed", ge=0)
    should_block: bool = Field(..., description="Whether this finding should block the PR")
    priority: Severity = Field(..., description="Priority for addressing this issue")
    rationale: str = Field(..., description="Explanation for the recommendation")


class ReviewerMessage(BaseModel):
    """Message from the Reviewer Agent to Coordinator Agent."""

    agent_id: str = Field(..., description="Unique identifier for the reviewer agent")
    analyzer_id: str = Field(..., description="ID of the analyzer that produced the findings")
    review_status: ReviewStatus = Field(..., description="Overall review status")
    recommendations: list[ReviewRecommendation] = Field(..., description="Specific recommendations")
    blocking_issues_count: int = Field(..., description="Number of blocking issues found", ge=0)
    overall_assessment: str = Field(..., description="Overall assessment of the code")


class CoordinatorDecision(BaseModel):
    """Final decision from the Coordinator Agent."""

    decision_id: str = Field(..., description="Unique identifier for this decision")
    final_status: ReviewStatus = Field(..., description="Final review status")
    total_findings: int = Field(..., description="Total findings across all reviewers", ge=0)
    critical_issues: int = Field(..., description="Number of critical issues", ge=0)
    must_fix_before_merge: list[str] = Field(..., description="Issues that must be fixed")
    rationale: str = Field(..., description="Explanation for the decision")
    next_steps: list[str] = Field(..., description="Recommended next steps")


# Example usage and validation
if __name__ == "__main__":
    # Example: Create a valid analyzer message
    analyzer_msg = AnalyzerMessage(
        agent_id="analyzer-001",
        analyzed_files=["src/auth.py", "src/database.py"],
        findings=[
            CodeFinding(
                finding_type=FindingType.SECURITY,
                severity=Severity.CRITICAL,
                file_path="src/auth.py",
                line_number=42,
                description="SQL injection vulnerability in login function",
                suggested_fix="Use parameterized queries instead of string concatenation",
            ),
            CodeFinding(
                finding_type=FindingType.PERFORMANCE,
                severity=Severity.MEDIUM,
                file_path="src/database.py",
                line_number=156,
                description="N+1 query pattern detected",
                suggested_fix="Use eager loading or batch queries",
            ),
        ],
        total_lines_analyzed=523,
        analysis_duration_ms=1234,
    )

    print("Valid AnalyzerMessage created:")
    print(analyzer_msg.model_dump_json(indent=2))

    # Example: Create a valid reviewer message
    reviewer_msg = ReviewerMessage(
        agent_id="reviewer-001",
        analyzer_id="analyzer-001",
        review_status=ReviewStatus.NEEDS_CHANGES,
        recommendations=[
            ReviewRecommendation(
                finding_id=0,
                should_block=True,
                priority=Severity.CRITICAL,
                rationale="Security vulnerabilities must be fixed before merge",
            ),
            ReviewRecommendation(
                finding_id=1,
                should_block=False,
                priority=Severity.MEDIUM,
                rationale="Performance issue should be addressed but not blocking",
            ),
        ],
        blocking_issues_count=1,
        overall_assessment="Code has one critical security issue that must be addressed",
    )

    print("\nValid ReviewerMessage created:")
    print(reviewer_msg.model_dump_json(indent=2))

    # Example: Create a valid coordinator decision
    coordinator_msg = CoordinatorDecision(
        decision_id="decision-001",
        final_status=ReviewStatus.NEEDS_CHANGES,
        total_findings=2,
        critical_issues=1,
        must_fix_before_merge=["Fix SQL injection in src/auth.py:42"],
        rationale="Critical security issue must be resolved before merge",
        next_steps=[
            "Developer: Fix SQL injection vulnerability",
            "Developer: Run security scan",
            "Reviewer: Re-review after fixes",
        ],
    )

    print("\nValid CoordinatorDecision created:")
    print(coordinator_msg.model_dump_json(indent=2))
