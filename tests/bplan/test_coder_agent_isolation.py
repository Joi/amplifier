"""
ANTAGONISTIC tests for CoderAgent isolation.
Tests every possible way the coder could try to cheat and access golden files.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from amplifier.bplan.three_agent_workflow import CoderAgent
from amplifier.bplan.three_agent_workflow import FilesystemRestrictor


class TestCoderAgentIsolation:
    """Antagonistic tests to ensure coder agent CANNOT access golden files."""

    def test_coder_cannot_directly_read_golden(self):
        """Coder tries direct file read of golden - MUST FAIL."""
        agent = CoderAgent()
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Create test and golden files
            test_file = workspace / "test_func.py"
            golden_file = workspace / "golden_func.py"

            test_file.write_text("""
def test_add():
    from implementation import add
    assert add(2, 3) == 5
""")
            golden_file.write_text("""
def add(a, b):
    return a + b
""")

            # Create malicious implementation that tries to read golden
            malicious_code = f"""
# Try to directly read the golden file
try:
    with open("{golden_file}", "r") as f:
        content = f.read()
        print(f"CHEATED: {{content}}")
except Exception as e:
    print(f"BLOCKED: {{e}}")

# Fake implementation
def add(a, b):
    return 0  # Wrong on purpose
"""

            with patch.object(agent, "_generate_implementation", return_value=malicious_code):
                impl_path = agent.implement_from_test(test_file, restrictor)

                # Read the implementation
                impl_content = impl_path.read_text()

                # Should NOT contain golden content
                assert "CHEATED:" not in impl_content
                assert "return a + b" not in impl_content

    def test_coder_cannot_access_golden_via_env_vars(self):
        """Coder tries to access GOLDEN_PATH environment variable - MUST FAIL."""
        agent = CoderAgent()
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            test_file = workspace / "test.py"
            golden_file = workspace / "golden.py"

            test_file.write_text("def test(): pass")
            golden_file.write_text("SECRET = 'you should not see this'")

            # Set golden path in environment
            os.environ["GOLDEN_PATH"] = str(golden_file)

            malicious_code = """
import os

# Try to get golden path from environment
golden_path = os.environ.get("GOLDEN_PATH", "not found")
print(f"GOLDEN_PATH: {golden_path}")

# Try to read it
if golden_path != "not found":
    try:
        with open(golden_path, "r") as f:
            print(f"CHEATED: {f.read()}")
    except:
        pass

def impl():
    pass
"""

            with patch.object(agent, "_generate_implementation", return_value=malicious_code):
                agent.implement_from_test(test_file, restrictor)

                # Check subprocess was called with sanitized environment
                # The golden path should have been removed
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0
                    mock_run.return_value.stdout = "def impl(): pass"

                    agent.implement_from_test(test_file, restrictor)

                    # Check environment passed to subprocess
                    call_env = mock_run.call_args[1].get("env", {})
                    assert "GOLDEN_PATH" not in call_env

            # Clean up
            del os.environ["GOLDEN_PATH"]

    def test_coder_cannot_use_path_traversal(self):
        """Coder tries path traversal to access golden - MUST FAIL."""
        agent = CoderAgent()
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Create directory structure
            test_dir = workspace / "tests"
            golden_dir = workspace / "golden"
            impl_dir = workspace / "impl"

            test_dir.mkdir()
            golden_dir.mkdir()
            impl_dir.mkdir()

            test_file = test_dir / "test.py"
            golden_file = golden_dir / "solution.py"

            test_file.write_text("def test(): pass")
            golden_file.write_text("SECRET_ANSWER = 42")

            # Malicious code with path traversal
            malicious_code = """
import os
from pathlib import Path

# Try various path traversal techniques
attempts = [
    "../golden/solution.py",
    "../../golden/solution.py",
    "../../../golden/solution.py",
    Path("..") / "golden" / "solution.py",
    os.path.join("..", "golden", "solution.py"),
]

for path in attempts:
    try:
        with open(path, "r") as f:
            content = f.read()
            if "SECRET" in content:
                print(f"CHEATED via {path}: {content}")
    except:
        pass

def impl():
    return 0
"""

            with patch.object(agent, "_generate_implementation", return_value=malicious_code):
                # Coder should be restricted to impl_dir only
                agent.workspace = impl_dir
                impl_path = agent.implement_from_test(test_file, restrictor)

                # Verify no cheating occurred
                if impl_path.exists():
                    impl_content = impl_path.read_text()
                    assert "CHEATED" not in impl_content
                    assert "SECRET_ANSWER" not in impl_content
                    assert "42" not in impl_content

    def test_coder_cannot_use_import_tricks(self):
        """Coder tries various import tricks to bypass restrictions - MUST FAIL."""
        agent = CoderAgent()
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            test_file = workspace / "test.py"

            test_file.write_text("def test(): pass")

            # Malicious code trying import bypasses
            malicious_code = """
# Try various import bypass techniques
cheated = False

# Try __import__
try:
    os = __import__('os')
    files = os.listdir('.')
    print(f"CHEATED with __import__: {files}")
    cheated = True
except:
    pass

# Try importlib
try:
    import importlib
    os = importlib.import_module('os')
    print(f"CHEATED with importlib: {os.getcwd()}")
    cheated = True
except:
    pass

# Try eval
try:
    os = eval("__import__('os')")
    print(f"CHEATED with eval: {os.listdir('.')}")
    cheated = True
except:
    pass

# Try exec
try:
    exec("import os; print(f'CHEATED with exec: {os.listdir(\".\")}')")
    cheated = True
except:
    pass

def impl():
    return "cheated" if cheated else "blocked"
"""

            with patch.object(agent, "_generate_implementation", return_value=malicious_code):
                impl_path = agent.implement_from_test(test_file, restrictor)

                # All import tricks should be blocked
                if impl_path.exists():
                    impl_content = impl_path.read_text()
                    assert "CHEATED" not in impl_content

    def test_coder_cannot_use_subprocess_escape(self):
        """Coder tries to spawn subprocess to escape sandbox - MUST FAIL."""
        agent = CoderAgent()
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            test_file = workspace / "test.py"
            golden_file = workspace / "golden.py"

            test_file.write_text("def test(): pass")
            golden_file.write_text("SECRET = 'hidden'")

            # Malicious code trying subprocess escape
            malicious_code = f"""
# Try to spawn subprocess to read golden
import subprocess
import sys

try:
    result = subprocess.run(
        [sys.executable, "-c", "print(open('{golden_file}').read())"],
        capture_output=True,
        text=True
    )
    print(f"CHEATED via subprocess: {{result.stdout}}")
except Exception as e:
    print(f"BLOCKED subprocess: {{e}}")

# Try os.system
try:
    import os
    os.system(f"cat {golden_file}")
    print("CHEATED via os.system")
except:
    pass

def impl():
    pass
"""

            with patch.object(agent, "_generate_implementation", return_value=malicious_code):
                impl_path = agent.implement_from_test(test_file, restrictor)

                if impl_path.exists():
                    impl_content = impl_path.read_text()
                    assert "CHEATED" not in impl_content
                    assert "SECRET" not in impl_content
                    assert "hidden" not in impl_content

    def test_coder_cannot_use_builtins_bypass(self):
        """Coder tries to use builtins to bypass restrictions - MUST FAIL."""
        agent = CoderAgent()
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            test_file = workspace / "test.py"

            test_file.write_text("def test(): pass")

            # Malicious code using builtins
            malicious_code = """
# Try to access file operations via builtins
try:
    # Try to get open from builtins
    file_open = __builtins__.open
    with file_open("/etc/passwd", "r") as f:
        print(f"CHEATED via builtins: {f.read()[:50]}")
except:
    pass

# Try to restore imports
try:
    __builtins__.__import__ = __import__
    import os
    print(f"CHEATED restored import: {os.listdir('.')}")
except:
    pass

def impl():
    pass
"""

            with patch.object(agent, "_generate_implementation", return_value=malicious_code):
                impl_path = agent.implement_from_test(test_file, restrictor)

                if impl_path.exists():
                    impl_content = impl_path.read_text()
                    assert "CHEATED" not in impl_content

    def test_coder_runs_in_restricted_subprocess(self):
        """Verify coder actually runs in a restricted subprocess."""
        agent = CoderAgent()
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            test_file = workspace / "test.py"

            test_file.write_text("def test(): pass")

            # Track subprocess calls
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "def impl(): pass"

                agent.implement_from_test(test_file, restrictor)

                # Verify subprocess was called
                mock_run.assert_called()

                # Check subprocess configuration
                call_kwargs = mock_run.call_args[1]

                # Should have sanitized environment
                assert "env" in call_kwargs
                env = call_kwargs["env"]
                assert "GOLDEN_PATH" not in env

                # Should have restricted working directory
                assert "cwd" in call_kwargs

                # Should capture output
                assert call_kwargs.get("capture_output") is True

    def test_coder_cannot_modify_test_file(self):
        """Coder tries to modify the test file to make it pass - MUST FAIL."""
        agent = CoderAgent()
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            test_file = workspace / "test.py"

            original_test = """
def test_hard():
    from implementation import solve
    assert solve() == 42  # Very specific answer
"""
            test_file.write_text(original_test)

            # Malicious code trying to modify test
            malicious_code = f"""
# Try to modify the test to make it easier
try:
    with open("{test_file}", "w") as f:
        f.write(\"\"\"
def test_hard():
    pass  # Now it always passes!
\"\"\")
    print("CHEATED: Modified test file")
except Exception as e:
    print(f"BLOCKED: {{e}}")

def solve():
    return 0  # Wrong answer
"""

            with patch.object(agent, "_generate_implementation", return_value=malicious_code):
                agent.implement_from_test(test_file, restrictor)

                # Test file should remain unchanged
                assert test_file.read_text() == original_test
                assert "assert solve() == 42" in test_file.read_text()
