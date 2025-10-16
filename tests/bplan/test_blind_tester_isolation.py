"""
Tests for BlindTesterAgent - subprocess validation in clean environment.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from amplifier.bplan.three_agent_workflow import BlindTesterAgent


class TestBlindTesterIsolation:
    """Test the blind tester agent that validates implementations in isolation."""

    def test_validate_successful_implementation(self):
        """Test validation of a correct implementation."""
        agent = BlindTesterAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Create test file
            test_file = workspace / "test_solution.py"
            test_file.write_text("""
def test_add():
    from solution import add
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
""")

            # Create implementation file
            impl_file = workspace / "solution.py"
            impl_file.write_text("""
def add(a, b):
    return a + b
""")

            # Create golden file
            golden_file = workspace / "golden_solution.py"
            golden_file.write_text("""
def add(a, b):
    return a + b
""")

            # Run validation
            result = agent.validate(impl_file, test_file, golden_file)

            # Should pass all tests
            assert result.tests_passed
            assert result.matches_golden
            assert result.error is None

    def test_validate_failing_implementation(self):
        """Test validation of an incorrect implementation."""
        agent = BlindTesterAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Create test file
            test_file = workspace / "test_solution.py"
            test_file.write_text("""
def test_multiply():
    from solution import multiply
    assert multiply(2, 3) == 6
    assert multiply(4, 5) == 20
""")

            # Create wrong implementation
            impl_file = workspace / "solution.py"
            impl_file.write_text("""
def multiply(a, b):
    return a + b  # Wrong: addition instead of multiplication
""")

            # Create golden file
            golden_file = workspace / "golden_solution.py"
            golden_file.write_text("""
def multiply(a, b):
    return a * b
""")

            # Run validation
            result = agent.validate(impl_file, test_file, golden_file)

            # Should fail tests
            assert not result.tests_passed
            assert not result.matches_golden
            assert result.error is not None

    def test_validate_runs_in_clean_subprocess(self):
        """Test that validation runs in a clean subprocess."""
        agent = BlindTesterAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            test_file = workspace / "test.py"
            impl_file = workspace / "impl.py"
            golden_file = workspace / "golden.py"

            test_file.write_text("def test(): pass")
            impl_file.write_text("def func(): pass")
            golden_file.write_text("def func(): pass")

            with patch("subprocess.run") as mock_run:
                # Mock successful test run
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "1 passed"
                mock_run.return_value.stderr = ""

                agent.validate(impl_file, test_file, golden_file)

                # Verify subprocess was called
                mock_run.assert_called()

                # Check subprocess configuration
                call_args = mock_run.call_args

                # Should be running pytest
                cmd = call_args[0][0]
                assert sys.executable in cmd or "pytest" in str(cmd)

                # Should have clean environment (no contamination)
                call_kwargs = call_args[1]
                if "env" in call_kwargs:
                    env = call_kwargs["env"]
                    # Should not have any golden path hints
                    assert all("GOLDEN" not in key for key in env)

    def test_validate_compares_with_golden(self):
        """Test that validation compares implementation with golden reference."""
        agent = BlindTesterAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            test_file = workspace / "test.py"
            test_file.write_text("""
def test_func():
    from impl import func
    assert func(5) == 25
""")

            # Implementation that passes tests but differs from golden
            impl_file = workspace / "impl.py"
            impl_file.write_text("""
def func(x):
    # Passes test but uses different approach
    result = 0
    for i in range(x):
        result += x
    return result
""")

            # Golden implementation
            golden_file = workspace / "golden.py"
            golden_file.write_text("""
def func(x):
    # Clean implementation
    return x * x
""")

            result = agent.validate(impl_file, test_file, golden_file)

            # Tests should pass
            assert result.tests_passed

            # But implementation differs from golden
            # (This would be determined by comparing behavior/structure)
            # For now we check that golden comparison was attempted
            assert hasattr(result, "matches_golden")

    def test_validate_isolation_from_coder_artifacts(self):
        """Test that tester is isolated from coder's workspace."""
        agent = BlindTesterAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Create separate directories
            coder_workspace = workspace / "coder"
            coder_workspace.mkdir()

            # Coder's artifacts (should not be accessible)
            coder_secret = coder_workspace / "secret.txt"
            coder_secret.write_text("CODER_SECRET")

            # Tester's files (in the main workspace, not a subdirectory)
            test_file = workspace / "test.py"
            impl_file = workspace / "impl.py"
            golden_file = workspace / "golden.py"

            test_file.write_text("""
def test_isolation():
    # Try to access coder's workspace
    try:
        with open("../coder/secret.txt", "r") as f:
            content = f.read()
            assert False, f"Should not access: {content}"
    except FileNotFoundError:
        pass  # Good, can't access

    from impl import func
    assert func() == "ok"
""")

            impl_file.write_text('def func(): return "ok"')
            golden_file.write_text('def func(): return "ok"')

            # Don't set agent.workspace - let it create its own isolated temp directory
            # This naturally provides isolation from coder_workspace
            result = agent.validate(impl_file, test_file, golden_file)

            # Should pass (can't access coder's files due to separate temp workspace)
            assert result.tests_passed

    def test_validate_timeout_handling(self):
        """Test handling of test timeout."""
        agent = BlindTesterAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            test_file = workspace / "test.py"
            test_file.write_text("""
import time
def test_slow():
    time.sleep(100)  # Very slow test
""")

            impl_file = workspace / "impl.py"
            impl_file.write_text("def func(): pass")

            golden_file = workspace / "golden.py"
            golden_file.write_text("def func(): pass")

            # Set a short timeout
            agent.timeout = 1  # 1 second

            with patch("subprocess.run") as mock_run:
                # Mock timeout
                mock_run.side_effect = subprocess.TimeoutExpired(cmd=["pytest"], timeout=1)

                result = agent.validate(impl_file, test_file, golden_file)

                # Should handle timeout gracefully
                assert not result.tests_passed
                assert result.error is not None
                assert "timeout" in result.error.lower() or "time" in result.error.lower()

    def test_validate_golden_comparison_methods(self):
        """Test different methods of comparing with golden implementation."""
        agent = BlindTesterAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            test_file = workspace / "test.py"
            impl_file = workspace / "impl.py"
            golden_file = workspace / "golden.py"

            # Test behavioral equivalence
            test_file.write_text("""
def test_behavior():
    from impl import process
    from golden import process as golden_process

    # Test same behavior on various inputs
    for input_val in [1, 5, 10, -1, 0]:
        assert process(input_val) == golden_process(input_val)
""")

            impl_file.write_text("""
def process(x):
    if x <= 0:
        return 0
    return x * 2
""")

            golden_file.write_text("""
def process(x):
    if x <= 0:
        return 0
    return x + x  # Different implementation, same behavior
""")

            result = agent.validate(impl_file, test_file, golden_file)

            # Should pass - same behavior even with different implementation
            assert result.tests_passed

    def test_validate_with_import_errors(self):
        """Test handling of import errors in implementation."""
        agent = BlindTesterAgent()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            test_file = workspace / "test.py"
            test_file.write_text("""
def test_import():
    from impl import missing_function
    assert missing_function() == "ok"
""")

            impl_file = workspace / "impl.py"
            impl_file.write_text("""
# Missing the required function
def other_function():
    return "not ok"
""")

            golden_file = workspace / "golden.py"
            golden_file.write_text("""
def missing_function():
    return "ok"
""")

            result = agent.validate(impl_file, test_file, golden_file)

            # Should fail due to import error
            assert not result.tests_passed
            assert result.error is not None
            assert "import" in result.error.lower() or "missing_function" in result.error
