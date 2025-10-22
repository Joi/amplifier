"""
Tests for natural language context parser - Phase 6.

TEST-FIRST: Define contract for NL context parsing.
"""

from unittest.mock import patch

import pytest

from amplifier.flow_builder.nl_parser import parse_context


class TestBasicContextParsing:
    """Test basic natural language parsing."""

    @pytest.mark.asyncio
    async def test_parse_context_extracts_single_field(self):
        """Should extract single required field."""
        user_input = "Review the files in src/api/"
        required_fields = ["files"]

        with patch("amplifier.flow_builder.nl_parser.ClaudeSession") as mock_session:
            mock_instance = mock_session.return_value.__aenter__.return_value
            mock_instance.query.return_value.content = '{"files": "src/api/"}'

            result = await parse_context(user_input, required_fields)

            assert result is not None
            assert "files" in result
            assert result["files"] == "src/api/"

    @pytest.mark.asyncio
    async def test_parse_context_extracts_multiple_fields(self):
        """Should extract multiple fields from input."""
        user_input = "Check the authentication in my-app project, focusing on token files"
        required_fields = ["project", "files"]

        with patch("amplifier.flow_builder.nl_parser.ClaudeSession") as mock_session:
            mock_instance = mock_session.return_value.__aenter__.return_value
            mock_instance.query.return_value.content = (
                '{"project": "my-app", "files": "token"}'
            )

            result = await parse_context(user_input, required_fields)

            assert result is not None
            assert result["project"] == "my-app"
            assert result["files"] == "token"

    @pytest.mark.asyncio
    async def test_parse_context_handles_empty_required_fields(self):
        """Should return empty dict when no fields required."""
        user_input = "Just do something"
        required_fields = []

        result = await parse_context(user_input, required_fields)

        assert result == {}


class TestErrorHandling:
    """Test error handling in NL parsing."""

    @pytest.mark.asyncio
    async def test_parse_context_handles_invalid_json(self):
        """Should return None when AI returns invalid JSON."""
        user_input = "Review files"
        required_fields = ["files"]

        with patch("amplifier.flow_builder.nl_parser.ClaudeSession") as mock_session:
            mock_instance = mock_session.return_value.__aenter__.return_value
            mock_instance.query.return_value.content = "This is not JSON"

            result = await parse_context(user_input, required_fields)

            assert result is None

    @pytest.mark.asyncio
    async def test_parse_context_handles_missing_fields(self):
        """Should still parse even if some fields missing."""
        user_input = "Check the auth system"
        required_fields = ["project", "files"]

        with patch("amplifier.flow_builder.nl_parser.ClaudeSession") as mock_session:
            mock_instance = mock_session.return_value.__aenter__.return_value
            # AI only extracted one field
            mock_instance.query.return_value.content = '{"files": "auth"}'

            result = await parse_context(user_input, required_fields)

            assert result is not None
            assert "files" in result


class TestComplexContextParsing:
    """Test complex parsing scenarios."""

    @pytest.mark.asyncio
    async def test_parse_context_handles_nested_values(self):
        """Should handle complex field values."""
        user_input = "Test all Python files in src/ and tests/ directories"
        required_fields = ["files"]

        with patch("amplifier.flow_builder.nl_parser.ClaudeSession") as mock_session:
            mock_instance = mock_session.return_value.__aenter__.return_value
            mock_instance.query.return_value.content = '{"files": "src/**/*.py,tests/**/*.py"}'

            result = await parse_context(user_input, required_fields)

            assert result is not None
            assert "src/**/*.py" in result["files"]

    @pytest.mark.asyncio
    async def test_parse_context_with_special_characters(self):
        """Should handle special characters in extracted values."""
        user_input = "Review files matching pattern *.{js,ts}"
        required_fields = ["pattern"]

        with patch("amplifier.flow_builder.nl_parser.ClaudeSession") as mock_session:
            mock_instance = mock_session.return_value.__aenter__.return_value
            mock_instance.query.return_value.content = '{"pattern": "*.{js,ts}"}'

            result = await parse_context(user_input, required_fields)

            assert result is not None
            assert result["pattern"] == "*.{js,ts}"


class TestPromptConstruction:
    """Test that prompts are constructed correctly."""

    @pytest.mark.asyncio
    async def test_parse_context_includes_required_fields_in_prompt(self):
        """Should include required fields in AI prompt."""
        user_input = "Test something"
        required_fields = ["project", "files", "focus"]

        with patch("amplifier.flow_builder.nl_parser.ClaudeSession") as mock_session:
            mock_instance = mock_session.return_value.__aenter__.return_value
            mock_instance.query.return_value.content = "{}"

            await parse_context(user_input, required_fields)

            # Check that query was called with a prompt containing the fields
            call_args = mock_instance.query.call_args
            prompt = call_args[0][0]
            assert "project" in prompt
            assert "files" in prompt
            assert "focus" in prompt
