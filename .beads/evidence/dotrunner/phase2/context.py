"""
Context interpolation utilities for workflow prompt templates.

This module provides functions to handle variable interpolation in templates,
extract variable names from templates, and validate context completeness.
All functions are pure with no external dependencies.
"""

import re
from typing import Any


class ContextError(Exception):
    """Raised when context interpolation fails due to missing variables.

    Attributes:
        message: Human-readable error message
        missing_vars: List of variable names that were missing from context
        template: The template string that failed to interpolate
    """

    def __init__(self, message: str, missing_vars: list[str], template: str):
        """Initialize ContextError with details about missing variables.

        Args:
            message: Error description
            missing_vars: List of missing variable names
            template: Template that failed interpolation
        """
        super().__init__(message)
        self.missing_vars = missing_vars
        self.template = template


def extract_variables(template: str) -> set[str]:
    """Extract all variable names from a template string.

    Finds all {variable} patterns in the template and returns the unique
    variable names. Variable names must be valid Python identifiers
    (letters, numbers, underscores, not starting with a number).

    Args:
        template: Template string potentially containing {variable} patterns

    Returns:
        Set of unique variable names found in template

    Examples:
        >>> extract_variables("Hello {name}!")
        {'name'}
        >>> extract_variables("Use {a} and {b} for {a}")
        {'a', 'b'}
        >>> extract_variables("No variables here")
        set()
    """
    # Use regex to find all {variable} patterns
    # \w+ matches word characters (letters, numbers, underscore)
    pattern = r"\{(\w+)\}"
    matches = re.findall(pattern, template)
    return set(matches)


def validate_context(template: str, context: dict[str, Any]) -> list[str]:
    """Check if context has all required variables for a template.

    Validates that the provided context dictionary contains values for all
    variables referenced in the template string.

    Args:
        template: Template string containing {variable} patterns
        context: Dictionary of variable names to values

    Returns:
        List of missing variable names (empty if all present)

    Examples:
        >>> validate_context("Use {a}", {"a": 1, "b": 2})
        []
        >>> validate_context("Use {a} and {b}", {"a": 1})
        ['b']
    """
    required_vars = extract_variables(template)
    missing = [var for var in required_vars if var not in context]
    return missing


def interpolate(template: str, context: dict[str, Any]) -> str:
    """Replace {variable} patterns in template with values from context.

    Performs variable substitution in the template string using values from
    the context dictionary. All variables in the template must be present
    in the context or a ContextError is raised.

    Args:
        template: Template string containing {variable} patterns
        context: Dictionary mapping variable names to values

    Returns:
        Template with all variables replaced by their values

    Raises:
        ContextError: If any required variable is missing from context

    Examples:
        >>> interpolate("Hello {name}!", {"name": "World"})
        'Hello World!'
        >>> interpolate("{a} + {b} = {c}", {"a": 1, "b": 2, "c": 3})
        '1 + 2 = 3'
    """
    # First check if all required variables are present
    missing = validate_context(template, context)
    if missing:
        raise ContextError(f"Missing required variables: {missing}", missing_vars=missing, template=template)

    # Perform the interpolation
    result = template
    for var_name, value in context.items():
        # Only replace variables that are actually in the template
        pattern = "{" + var_name + "}"
        if pattern in result:
            # Convert value to string for interpolation
            result = result.replace(pattern, str(value))

    return result
