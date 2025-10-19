"""
Tests for context interpolation utilities.

Tests variable interpolation, extraction, and validation in prompt templates.
"""

import pytest

from ai_working.dotrunner.context import ContextError
from ai_working.dotrunner.context import extract_variables
from ai_working.dotrunner.context import interpolate
from ai_working.dotrunner.context import validate_context


class TestInterpolate:
    """Test prompt template interpolation"""

    def test_interpolate_single_variable(self):
        """Test interpolating a single variable"""
        result = interpolate("Hello {name}", {"name": "World"})
        assert result == "Hello World"

    def test_interpolate_multiple_variables(self):
        """Test interpolating multiple variables"""
        result = interpolate("{a} + {b} = {c}", {"a": 1, "b": 2, "c": 3})
        assert result == "1 + 2 = 3"

    def test_interpolate_in_sentence(self):
        """Test variables embedded in sentences"""
        result = interpolate(
            "Analyze the file at {file_path} for {pattern} patterns",
            {"file_path": "/src/main.py", "pattern": "security"},
        )
        assert result == "Analyze the file at /src/main.py for security patterns"

    def test_interpolate_no_variables(self):
        """Test template with no variables"""
        result = interpolate("Just plain text", {})
        assert result == "Just plain text"

    def test_interpolate_unused_context(self):
        """Test that extra context variables are ignored"""
        result = interpolate("Use {a}", {"a": 1, "b": 2, "c": 3})
        assert result == "Use 1"

    def test_interpolate_missing_variable_raises(self):
        """Test that missing variables raise ContextError"""
        with pytest.raises(ContextError) as exc_info:
            interpolate("Missing {nonexistent}", {})

        error = exc_info.value
        assert "nonexistent" in error.missing_vars
        assert "Missing {nonexistent}" in error.template

    def test_interpolate_some_missing_raises(self):
        """Test error when some variables are present"""
        with pytest.raises(ContextError) as exc_info:
            interpolate("Use {a} and {b} and {c}", {"a": 1, "c": 3})

        error = exc_info.value
        assert "b" in error.missing_vars
        assert len(error.missing_vars) == 1

    def test_interpolate_multiline_template(self):
        """Test interpolating multiline templates"""
        template = """Analyze the code in {file}.

Look for:
1. {pattern1} issues
2. {pattern2} problems

Report findings."""

        result = interpolate(template, {"file": "main.py", "pattern1": "security", "pattern2": "performance"})

        assert "main.py" in result
        assert "security issues" in result
        assert "performance problems" in result

    def test_interpolate_with_numbers(self):
        """Test interpolating numeric values"""
        result = interpolate("Process {count} items", {"count": 42})
        assert result == "Process 42 items"

    def test_interpolate_with_booleans(self):
        """Test interpolating boolean values"""
        result = interpolate("Success: {status}", {"status": True})
        assert result == "Success: True"

    def test_interpolate_same_variable_multiple_times(self):
        """Test variable used multiple times in template"""
        result = interpolate("{var} is {var} is {var}", {"var": "cool"})
        assert result == "cool is cool is cool"


class TestExtractVariables:
    """Test variable extraction from templates"""

    def test_extract_single_variable(self):
        """Test extracting a single variable"""
        vars = extract_variables("Hello {name}")
        assert vars == {"name"}

    def test_extract_multiple_variables(self):
        """Test extracting multiple variables"""
        vars = extract_variables("Use {a} and {b} for {c}")
        assert vars == {"a", "b", "c"}

    def test_extract_no_variables(self):
        """Test template with no variables"""
        vars = extract_variables("Plain text with no vars")
        assert vars == set()

    def test_extract_duplicate_variables(self):
        """Test that duplicate variables appear once"""
        vars = extract_variables("{var} is {var} is {var}")
        assert vars == {"var"}

    def test_extract_from_multiline(self):
        """Test extracting from multiline template"""
        template = """
        Process {file}
        With {config}
        And {options}
        """
        vars = extract_variables(template)
        assert vars == {"file", "config", "options"}

    def test_extract_with_underscores(self):
        """Test variable names with underscores"""
        vars = extract_variables("Use {file_path} and {line_number}")
        assert vars == {"file_path", "line_number"}

    def test_extract_with_numbers(self):
        """Test variable names with numbers"""
        vars = extract_variables("Use {var1} and {var2} and {var3}")
        assert vars == {"var1", "var2", "var3"}


class TestValidateContext:
    """Test context validation against templates"""

    def test_validate_all_present(self):
        """Test validation when all variables present"""
        missing = validate_context("Use {a}", {"a": 1, "b": 2})
        assert missing == []

    def test_validate_all_present_exact_match(self):
        """Test validation with exact context match"""
        missing = validate_context("Use {a} and {b}", {"a": 1, "b": 2})
        assert missing == []

    def test_validate_some_missing(self):
        """Test validation when some variables missing"""
        missing = validate_context("Use {a} and {b}", {"a": 1})
        assert missing == ["b"]

    def test_validate_all_missing(self):
        """Test validation when all variables missing"""
        missing = validate_context("Use {a} and {b}", {})
        assert set(missing) == {"a", "b"}

    def test_validate_no_variables(self):
        """Test validation with no variables in template"""
        missing = validate_context("Plain text", {})
        assert missing == []

    def test_validate_empty_context_with_variables(self):
        """Test validation with empty context and variables"""
        missing = validate_context("Need {x}", {})
        assert missing == ["x"]

    def test_validate_returns_unique_missing(self):
        """Test that duplicate missing vars appear once"""
        missing = validate_context("{var} {var} {var}", {})
        assert missing == ["var"]


class TestContextError:
    """Test ContextError exception"""

    def test_context_error_creation(self):
        """Test creating ContextError"""
        error = ContextError(message="Variables missing", missing_vars=["a", "b"], template="Use {a} and {b}")

        assert str(error) == "Variables missing"
        assert error.missing_vars == ["a", "b"]
        assert error.template == "Use {a} and {b}"

    def test_context_error_from_interpolate(self):
        """Test ContextError raised by interpolate"""
        with pytest.raises(ContextError) as exc_info:
            interpolate("Use {missing}", {})

        e = exc_info.value
        assert "missing" in e.missing_vars
        assert "Use {missing}" in e.template
        assert "missing" in str(e).lower() or "variable" in str(e).lower()
