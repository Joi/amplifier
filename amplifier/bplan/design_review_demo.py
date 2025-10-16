#!/usr/bin/env python3
"""Demo script showing design review in action."""

from amplifier.bplan.design_review import CodeBasedDesignReviewer
from amplifier.bplan.design_review import IndependentValidator
from amplifier.bplan.design_review import RequirementMatcher


def demo_design_review():
    """Demonstrate design review capabilities."""

    # Sample user requirements
    user_requirements = """
    Build a TODO application with:
    - User authentication
    - Create, read, update, delete todos
    - Share todos with other users
    - Real-time updates when todos change
    """

    # Sample design output (good design)
    good_design = {
        "overview": "A collaborative TODO application with real-time sync",
        "components": [
            {"name": "AuthService", "purpose": "Handle user authentication"},
            {"name": "TodoService", "purpose": "CRUD operations for todos"},
            {"name": "ShareService", "purpose": "Manage todo sharing between users"},
            {"name": "WebSocketService", "purpose": "Real-time updates via WebSocket"},
        ],
        "data_flow": "User -> Auth -> TodoService -> Database, WebSocket -> Client",
        "validation": {
            "criteria": ["All CRUD operations work", "Real-time sync functions"],
            "tests": ["Test auth flow", "Test CRUD", "Test sharing", "Test real-time"],
        },
    }

    # Sample design output (incomplete design)
    incomplete_design = {
        "overview": "A basic TODO app",
        "components": [{"name": "TodoService", "purpose": "Manage todos"}],
        # Missing: data_flow, validation, and several required components
    }

    print("=" * 60)
    print("DESIGN REVIEW DEMO")
    print("=" * 60)

    # 1. Code-based structural validation
    print("\n1. CODE-BASED STRUCTURAL VALIDATION")
    print("-" * 40)

    code_reviewer = CodeBasedDesignReviewer()

    print("\nValidating GOOD design:")
    good_result = code_reviewer.validate(user_requirements, good_design)
    print(f"  Passed: {good_result.passed}")
    print(f"  Coverage: {good_result.coverage:.1%}")
    if good_result.issues:
        print(f"  Issues: {good_result.issues}")

    print("\nValidating INCOMPLETE design:")
    incomplete_result = code_reviewer.validate(user_requirements, incomplete_design)
    print(f"  Passed: {incomplete_result.passed}")
    print(f"  Coverage: {incomplete_result.coverage:.1%}")
    print(f"  Issues: {incomplete_result.issues[:2]}...")  # Show first 2 issues

    # 2. Requirement matching
    print("\n2. REQUIREMENT MATCHING")
    print("-" * 40)

    matcher = RequirementMatcher()

    print("\nMatching requirements to GOOD design:")
    good_match = matcher.match(user_requirements, good_design)
    print(f"  Coverage: {good_match.coverage:.1%}")
    print(f"  Matched: {len(good_match.matched_requirements)}/{len(good_match.extracted_requirements)}")
    if good_match.unmatched_requirements:
        print(f"  Unmatched: {good_match.unmatched_requirements}")

    print("\nMatching requirements to INCOMPLETE design:")
    incomplete_match = matcher.match(user_requirements, incomplete_design)
    print(f"  Coverage: {incomplete_match.coverage:.1%}")
    print(f"  Matched: {len(incomplete_match.matched_requirements)}/{len(incomplete_match.extracted_requirements)}")
    print(f"  Unmatched: {incomplete_match.unmatched_requirements[:2]}...")  # Show first 2

    # 3. Independence validation (pollution detection)
    print("\n3. INDEPENDENCE VALIDATION")
    print("-" * 40)

    validator = IndependentValidator()

    # Check clean result
    print("\nChecking CLEAN validation result:")
    clean_context = {"user_requirements": user_requirements, "design_output": good_design}
    clean_report = validator.check_pollution(good_result, clean_context)
    print(f"  Is polluted: {clean_report.is_polluted}")
    print(f"  Confidence: {clean_report.confidence:.1%}")

    # Simulate polluted result
    from amplifier.bplan.design_review import ValidationResult

    polluted_result = ValidationResult(
        passed=False,
        issues=["Missing Redis caching like the previous e-commerce platform"],
        coverage=0.5,
        details={"reasoning": "Unlike the earlier microservices design, this lacks Kubernetes"},
    )

    print("\nChecking POLLUTED validation result:")
    pollution_report = validator.check_pollution(polluted_result, clean_context)
    print(f"  Is polluted: {pollution_report.is_polluted}")
    print(f"  Leaked terms: {pollution_report.leaked_terms}")
    print(f"  Unstated assumptions: {pollution_report.unstated_assumptions[:2]}...")
    print(f"  Confidence: {pollution_report.confidence:.1%}")

    print("\n" + "=" * 60)
    print("Demo complete! The design review system:")
    print("✓ Validates design structure")
    print("✓ Matches requirements to design")
    print("✓ Detects context pollution")
    print("✓ Maintains zero state between validations")
    print("=" * 60)


if __name__ == "__main__":
    demo_design_review()
