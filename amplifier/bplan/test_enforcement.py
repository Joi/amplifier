"""
Test-first enforcement utilities.

Ensures tests are written before implementation through subprocess-based verification.
"""

import subprocess
import sys
from pathlib import Path


def get_test_path(module_path: Path) -> Path:
    """
    Calculate the test file path for a given module path.

    Args:
        module_path: Path to the module file (e.g., amplifier/auth.py)

    Returns:
        Path to the corresponding test file (e.g., tests/test_auth.py)

    Examples:
        >>> get_test_path(Path("amplifier/auth.py"))
        PosixPath('tests/test_auth.py')

        >>> get_test_path(Path("amplifier/bplan/executor.py"))
        PosixPath('tests/bplan/test_executor.py')
    """
    # Convert to relative path if absolute
    if module_path.is_absolute():
        # Try to find 'amplifier' in parts and start from there
        parts = module_path.parts
        try:
            amp_idx = parts.index("amplifier")
            module_path = Path(*parts[amp_idx:])
        except ValueError:
            # If 'amplifier' not in path, just use the name
            pass

    # Get the relative path from amplifier/
    parts = module_path.parts

    # Remove 'amplifier' prefix if present
    if parts[0] == "amplifier":
        relative_parts = parts[1:]
    else:
        relative_parts = parts

    # Build test path
    if len(relative_parts) == 1:
        # Top-level module: amplifier/auth.py -> tests/test_auth.py
        module_name = relative_parts[0]
        test_name = f"test_{module_name}"
        return Path("tests") / test_name
    # Nested module: amplifier/bplan/executor.py -> tests/bplan/test_executor.py
    subdir = Path(*relative_parts[:-1])
    module_name = relative_parts[-1]
    test_name = f"test_{module_name}"
    return Path("tests") / subdir / test_name


def check_test_exists(module_path: Path) -> bool:
    """
    Check if a test file exists for the given module.

    Args:
        module_path: Path to the module file

    Returns:
        True if test file exists, False otherwise

    Examples:
        >>> check_test_exists(Path("amplifier/auth.py"))
        True  # if tests/test_auth.py exists
    """
    test_path = get_test_path(module_path)

    # If module_path is absolute, construct absolute test path
    if module_path.is_absolute():
        # Get the base directory (parent of 'amplifier')
        parts = module_path.parts
        try:
            amp_idx = parts.index("amplifier")
            base_dir = Path(*parts[:amp_idx])
            abs_test_path = base_dir / test_path
            return abs_test_path.exists()
        except (ValueError, IndexError):
            # Fallback to relative check
            return test_path.exists()

    # For relative paths, check from current directory
    return test_path.exists()


def generate_test_stub(module_path: Path, spec: str) -> Path:
    """
    Generate a test stub file for a module.

    Args:
        module_path: Path to the module file
        spec: Specification/description of what to test

    Returns:
        Path to the generated test file

    Examples:
        >>> path = generate_test_stub(Path("amplifier/auth.py"), "Authentication tests")
        >>> print(path)
        tests/test_auth.py
    """
    test_path = get_test_path(module_path)

    # Create parent directories if they don't exist
    test_path.parent.mkdir(parents=True, exist_ok=True)

    # Extract module name for imports and class naming
    module_name = module_path.stem  # e.g., 'auth' from 'auth.py'

    # Build import path
    # Convert module_path to import statement
    parts = module_path.parts
    if "amplifier" in parts:
        amp_idx = parts.index("amplifier")
        import_parts = parts[amp_idx:]
        # Remove .py extension
        import_parts = list(import_parts)
        import_parts[-1] = import_parts[-1].replace(".py", "")
        import_path = ".".join(import_parts)
    else:
        import_path = f"amplifier.{module_name}"

    # Generate test stub content
    stub_content = f'''"""
Test suite for {module_name}.

{spec}

These tests should be written BEFORE implementation (test-first development).
REPLACE these placeholder tests with real antagonistic tests.
"""

import pytest

# REPLACE: Import specific functions/classes from the module
# from {import_path} import function_name, ClassName


class Test{module_name.title().replace("_", "")}:
    """Test class for {module_name} module."""

    def test_basic_functionality(self):
        """Test basic functionality of {module_name}."""
        # REPLACE: Write antagonistic tests that verify actual behavior
        # Example: Test with real inputs and verify specific outputs
        pytest.skip("REPLACE with real test")

    def test_edge_cases(self):
        """Test edge cases for {module_name}."""
        # REPLACE: Test boundary conditions and edge cases
        # Example: Empty inputs, very large inputs, invalid inputs
        pytest.skip("REPLACE with real test")

    def test_error_handling(self):
        """Test error handling in {module_name}."""
        # REPLACE: Test that errors are raised appropriately
        # Example: with pytest.raises(ValueError): function(bad_input)
        pytest.skip("REPLACE with real test")
'''

    # Write the stub file
    test_path.write_text(stub_content)

    return test_path


def validate_test_first(module_path: Path) -> bool:
    """
    Validate that tests exist before implementation.

    This function checks if a test file exists for the given module.
    It runs in subprocess isolation to prevent namespace pollution.

    Args:
        module_path: Path to the module file

    Returns:
        True if tests exist, False otherwise

    Examples:
        >>> validate_test_first(Path("amplifier/auth.py"))
        True  # if tests exist
    """
    # Run validation in subprocess to prevent importing the module
    # into the current process
    validation_code = f"""
import sys
from pathlib import Path

# Add current directory to path to ensure imports work
sys.path.insert(0, '{Path.cwd()}')

from amplifier.bplan.test_enforcement import check_test_exists

module_path = Path('{module_path}')
result = check_test_exists(module_path)
sys.exit(0 if result else 1)
"""

    try:
        result = subprocess.run(
            [sys.executable, "-c", validation_code],
            capture_output=True,
            text=True,
            timeout=10,  # Prevent hanging
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        # Treat timeout as validation failure
        return False
    except Exception:
        # Treat any other exception as validation failure
        return False
