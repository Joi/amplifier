"""Test Requirement Matcher - extracts and matches requirements to design outputs."""

from amplifier.bplan.design_review import MatchResult
from amplifier.bplan.design_review import RequirementMatcher


class TestRequirementMatcher:
    """Test requirement extraction and matching."""

    def test_extract_requirements_from_text(self):
        """Test extracting requirements from user text."""
        matcher = RequirementMatcher()

        user_req = """
        Build a TODO application with:
        - User authentication
        - Create, read, update, delete todos
        - Share todos with other users
        - Real-time updates
        """

        requirements = matcher.extract_requirements(user_req)

        assert len(requirements) >= 4
        assert any("authentication" in req.lower() for req in requirements)
        assert any("create" in req.lower() or "crud" in req.lower() for req in requirements)
        assert any("share" in req.lower() for req in requirements)
        assert any("real-time" in req.lower() or "realtime" in req.lower() for req in requirements)

    def test_extract_requirements_handles_various_formats(self):
        """Test extracting requirements from different text formats."""
        matcher = RequirementMatcher()

        # Numbered list format
        user_req = """
        1. System must handle user login
        2. System must store data securely
        3. System must provide API access
        """

        requirements = matcher.extract_requirements(user_req)
        assert len(requirements) >= 3
        assert any("login" in req.lower() for req in requirements)
        assert any("secure" in req.lower() for req in requirements)
        assert any("api" in req.lower() for req in requirements)

    def test_calculate_coverage_full_match(self):
        """Test coverage calculation when all requirements are met."""
        matcher = RequirementMatcher()

        requirements = ["User authentication", "CRUD operations", "Data persistence"]

        design_output = {
            "components": [
                {"name": "AuthService", "purpose": "Handle user authentication"},
                {"name": "TodoService", "purpose": "CRUD operations for todos"},
                {"name": "Database", "purpose": "Data persistence layer"},
            ]
        }

        coverage = matcher.calculate_coverage(requirements, design_output)
        assert coverage >= 0.9  # Should be close to 1.0

    def test_calculate_coverage_partial_match(self):
        """Test coverage calculation with partial requirement matching."""
        matcher = RequirementMatcher()

        requirements = ["User authentication", "Real-time updates", "Email notifications", "Data export"]

        # Design only covers 2 of 4 requirements
        design_output = {
            "components": [
                {"name": "AuthService", "purpose": "User authentication"},
                {"name": "WebSocket", "purpose": "Real-time updates"},
            ]
        }

        coverage = matcher.calculate_coverage(requirements, design_output)
        assert 0.4 <= coverage <= 0.6  # Around 50%

    def test_calculate_coverage_no_match(self):
        """Test coverage calculation when no requirements are met."""
        matcher = RequirementMatcher()

        requirements = ["Machine learning predictions", "Blockchain integration"]

        design_output = {
            "components": [
                {"name": "UIComponent", "purpose": "User interface"},
                {"name": "Database", "purpose": "Data storage"},
            ]
        }

        coverage = matcher.calculate_coverage(requirements, design_output)
        assert coverage < 0.2  # Very low coverage

    def test_match_complete_flow(self):
        """Test the complete matching flow."""
        matcher = RequirementMatcher()

        user_req = """
        Create a blog platform with:
        - User registration and login
        - Create and edit blog posts
        - Comment system
        - Search functionality
        """

        design_output = {
            "overview": "Blog platform with user management and content features",
            "components": [
                {"name": "AuthService", "purpose": "User registration and login"},
                {"name": "PostService", "purpose": "Create, edit, delete blog posts"},
                {"name": "CommentService", "purpose": "Handle comments on posts"},
                {"name": "SearchService", "purpose": "Full-text search functionality"},
            ],
            "data_flow": "User -> Auth -> Posts/Comments -> Database",
        }

        result = matcher.match(user_req, design_output)

        assert isinstance(result, MatchResult)
        assert result.coverage >= 0.8  # Good coverage
        assert len(result.matched_requirements) >= 3
        assert len(result.unmatched_requirements) <= 1
        assert result.extracted_requirements == matcher.extract_requirements(user_req)

    def test_match_identifies_gaps(self):
        """Test that matching identifies missing requirements."""
        matcher = RequirementMatcher()

        user_req = """
        Build a chat application with:
        - Real-time messaging
        - File sharing
        - Video calls
        - End-to-end encryption
        """

        # Design missing video calls and encryption
        design_output = {
            "components": [
                {"name": "ChatService", "purpose": "Real-time messaging"},
                {"name": "FileService", "purpose": "File upload and sharing"},
            ]
        }

        result = matcher.match(user_req, design_output)

        assert result.coverage < 0.6  # Low coverage
        assert len(result.unmatched_requirements) >= 2
        assert any("video" in req.lower() for req in result.unmatched_requirements)
        assert any("encryption" in req.lower() for req in result.unmatched_requirements)

    def test_match_result_structure(self):
        """Test MatchResult dataclass structure."""
        matcher = RequirementMatcher()

        result = matcher.match(user_req="Build something", design_output={"overview": "A system"})

        # Verify MatchResult has required fields
        assert hasattr(result, "coverage")
        assert hasattr(result, "matched_requirements")
        assert hasattr(result, "unmatched_requirements")
        assert hasattr(result, "extracted_requirements")
        assert hasattr(result, "details")

        assert isinstance(result.coverage, float)
        assert 0.0 <= result.coverage <= 1.0
        assert isinstance(result.matched_requirements, list)
        assert isinstance(result.unmatched_requirements, list)
        assert isinstance(result.extracted_requirements, list)
        assert isinstance(result.details, dict)

    def test_stateless_matching(self):
        """Test matcher maintains no state between calls."""
        matcher = RequirementMatcher()

        # First match
        result1 = matcher.match(user_req="Requirement set 1", design_output={"overview": "Design 1"})

        # Second match - should be independent
        result2 = matcher.match(user_req="Requirement set 2", design_output={"overview": "Design 2"})

        # Results should be independent
        assert result1.extracted_requirements != result2.extracted_requirements

        # Matcher should have no instance state
        assert not hasattr(matcher, "_cache")
        assert not hasattr(matcher, "_last_requirements")
