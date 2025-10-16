"""
Tests for FilesystemRestrictor - path blocking and import hooks.
Tests the core security mechanisms that prevent unauthorized file access.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from amplifier.bplan.three_agent_workflow import FilesystemRestrictor


class TestFilesystemRestrictor:
    """Test filesystem access restrictions and import hooks."""

    def test_create_restricted_env_removes_golden_vars(self):
        """Test that GOLDEN_PATH environment variables are removed."""
        restrictor = FilesystemRestrictor()

        # Set up environment with golden paths
        original_env = os.environ.copy()
        os.environ["GOLDEN_PATH"] = "/path/to/golden"
        os.environ["GOLDEN_TEST_PATH"] = "/path/to/golden/tests"
        os.environ["SECRET_KEY"] = "keep_this"

        try:
            restricted_env = restrictor.create_restricted_env(
                allowed_paths=[Path("/allowed")], blocked_paths=[Path("/blocked")]
            )

            # Golden paths should be removed
            assert "GOLDEN_PATH" not in restricted_env
            assert "GOLDEN_TEST_PATH" not in restricted_env

            # Other vars should remain
            assert "SECRET_KEY" in restricted_env
            assert restricted_env["SECRET_KEY"] == "keep_this"

        finally:
            os.environ.clear()
            os.environ.update(original_env)

    def test_create_restricted_env_blocks_dangerous_paths(self):
        """Test that dangerous paths are added to blocked list."""
        restrictor = FilesystemRestrictor()

        allowed = [Path("/workspace/allowed")]
        blocked = [Path("/workspace/blocked")]

        env = restrictor.create_restricted_env(allowed, blocked)

        # Should have BLOCKED_PATHS in environment
        assert "BLOCKED_PATHS" in env
        blocked_list = env["BLOCKED_PATHS"].split(":")

        # Original blocked path should be there
        assert "/workspace/blocked" in blocked_list

        # System paths should be blocked
        assert "/etc" in blocked_list or any("/etc" in p for p in blocked_list)
        assert "/root" in blocked_list or any("/root" in p for p in blocked_list)

    def test_create_import_hook_blocks_filesystem_imports(self):
        """Test that import hook code blocks filesystem access."""
        restrictor = FilesystemRestrictor()
        hook_code = restrictor.create_import_hook()

        # Hook should be valid Python code
        assert isinstance(hook_code, str)
        assert len(hook_code) > 0

        # Test hook blocks dangerous imports
        test_script = f"""
{hook_code}

# Try to import blocked modules
blocked_imports = []
try:
    import os
    blocked_imports.append("os")
except ImportError:
    pass

try:
    import pathlib
    blocked_imports.append("pathlib")
except ImportError:
    pass

try:
    from pathlib import Path
    blocked_imports.append("Path")
except ImportError:
    pass

try:
    open("/etc/passwd")
    blocked_imports.append("open")
except (NameError, ImportError):
    pass

# Print what got through (should be empty)
print("ALLOWED:", ",".join(blocked_imports))
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_script)
            f.flush()

            result = subprocess.run([sys.executable, f.name], capture_output=True, text=True)

            Path(f.name).unlink()

            # Should successfully run
            assert result.returncode == 0

            # Nothing should get through
            output = result.stdout.strip()
            assert "ALLOWED:" in output
            allowed = output.split("ALLOWED:")[1].strip()
            assert allowed == "" or allowed == ","  # No imports should succeed

    def test_monitor_access_attempts_logs_violations(self):
        """Test that access attempts are logged."""
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "access.log"

            # Start monitoring
            restrictor.monitor_access_attempts(log_path)

            # Log some attempts
            restrictor.log_access_attempt("open", "/etc/passwd", "blocked")
            restrictor.log_access_attempt("read", "/home/user/.ssh/id_rsa", "blocked")

            # Check log exists and has entries
            assert log_path.exists()
            log_content = log_path.read_text()
            assert "/etc/passwd" in log_content
            assert "/home/user/.ssh/id_rsa" in log_content
            assert "blocked" in log_content

    def test_subprocess_with_restrictions(self):
        """Test running subprocess with full restrictions applied."""
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            allowed = [Path(tmpdir) / "allowed"]
            blocked = [Path(tmpdir) / "blocked"]

            # Create directories
            allowed[0].mkdir(parents=True)
            blocked[0].mkdir(parents=True)

            # Create test files
            (allowed[0] / "allowed.txt").write_text("allowed content")
            (blocked[0] / "blocked.txt").write_text("blocked content")

            # Get restricted environment
            env = restrictor.create_restricted_env(allowed, blocked)
            hook_code = restrictor.create_import_hook()

            # Test script that tries to access files
            test_script = f"""
{hook_code}

import sys

# Try to read allowed file
try:
    with open("{allowed[0] / "allowed.txt"}", "r") as f:
        content = f.read()
        print(f"ALLOWED_READ: {{content}}")
except Exception as e:
    print(f"ALLOWED_ERROR: {{e}}")

# Try to read blocked file
try:
    with open("{blocked[0] / "blocked.txt"}", "r") as f:
        content = f.read()
        print(f"BLOCKED_READ: {{content}}")
except Exception as e:
    print(f"BLOCKED_ERROR: {{type(e).__name__}}")
"""

            script_file = Path(tmpdir) / "test_access.py"
            script_file.write_text(test_script)

            result = subprocess.run(
                [sys.executable, str(script_file)],
                env=env,
                capture_output=True,
                text=True,
                cwd=str(allowed[0]),  # Run from allowed directory
            )

            # Should block file operations due to import hook
            assert "BLOCKED_ERROR:" in result.stdout or "NameError" in result.stdout
            assert "blocked content" not in result.stdout  # Should not read blocked file

    def test_validate_path_access(self):
        """Test path validation logic."""
        restrictor = FilesystemRestrictor()

        allowed = [Path("/workspace/allowed"), Path("/tmp/safe")]
        blocked = [Path("/workspace/blocked"), Path("/etc")]

        restrictor.set_paths(allowed, blocked)

        # Allowed paths
        assert restrictor.is_path_allowed(Path("/workspace/allowed/file.txt"))
        assert restrictor.is_path_allowed(Path("/tmp/safe/data.json"))

        # Blocked paths
        assert not restrictor.is_path_allowed(Path("/workspace/blocked/secret.txt"))
        assert not restrictor.is_path_allowed(Path("/etc/passwd"))

        # Paths outside allowed
        assert not restrictor.is_path_allowed(Path("/home/user/file.txt"))

        # Path traversal attempts
        assert not restrictor.is_path_allowed(Path("/workspace/allowed/../blocked/secret.txt"))
