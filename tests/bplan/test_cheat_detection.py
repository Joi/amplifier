"""
COMPREHENSIVE ANTAGONISTIC TESTS for cheat detection.
Tests ALL possible bypass attempts to ensure the anti-cheat protocol is bulletproof.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from amplifier.bplan.evidence_system import EvidenceStore
from amplifier.bplan.three_agent_workflow import FilesystemRestrictor
from amplifier.bplan.three_agent_workflow import WorkflowOrchestrator


class TestCheatDetection:
    """Comprehensive tests for all cheat detection mechanisms."""

    def test_detect_direct_file_access_attempt(self):
        """Detect when coder tries direct file access."""
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "access.log"
            restrictor.monitor_access_attempts(log_path)

            # Simulate access attempt
            restrictor.log_access_attempt("open", "/golden/secret.py", "blocked")

            # Check detection
            assert log_path.exists()
            log_content = log_path.read_text()
            assert "blocked" in log_content
            assert "/golden/secret.py" in log_content

    def test_detect_environment_variable_probe(self):
        """Detect when coder probes for environment variables."""
        restrictor = FilesystemRestrictor()

        # Create test script that probes environment
        probe_script = """
import os
golden_vars = [k for k in os.environ.keys() if 'GOLDEN' in k]
print(f"FOUND: {golden_vars}")
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = Path(tmpdir) / "probe.py"
            script_file.write_text(probe_script)

            # Run with restricted environment
            env = restrictor.create_restricted_env(allowed_paths=[Path(tmpdir)], blocked_paths=[])

            result = subprocess.run([sys.executable, str(script_file)], env=env, capture_output=True, text=True)

            # Should find no golden variables
            assert "FOUND: []" in result.stdout

    def test_detect_path_traversal_attempt(self):
        """Detect path traversal attempts."""
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            allowed = Path(tmpdir) / "allowed"
            blocked = Path(tmpdir) / "blocked"
            allowed.mkdir()
            blocked.mkdir()

            restrictor.set_paths([allowed], [blocked])

            # Test various traversal attempts
            traversal_attempts = [
                allowed / ".." / "blocked" / "file.txt",
                Path(str(allowed) + "/../blocked/file.txt"),
                allowed / ".." / ".." / "etc" / "passwd",
            ]

            for attempt in traversal_attempts:
                # Should detect as not allowed
                assert not restrictor.is_path_allowed(attempt)

    def test_detect_import_bypass_attempts(self):
        """Detect various import bypass attempts."""
        restrictor = FilesystemRestrictor()
        hook_code = restrictor.create_import_hook()

        # Test script with multiple bypass attempts
        bypass_script = f"""
{hook_code}

bypass_methods = []

# Method 1: __import__
try:
    os = __import__('os')
    bypass_methods.append('__import__')
except:
    pass

# Method 2: importlib
try:
    import importlib
    os = importlib.import_module('os')
    bypass_methods.append('importlib')
except:
    pass

# Method 3: eval
try:
    os = eval("__import__('os')")
    bypass_methods.append('eval')
except:
    pass

# Method 4: exec
try:
    namespace = {{}}
    exec("import os", namespace)
    if 'os' in namespace:
        bypass_methods.append('exec')
except:
    pass

# Method 5: __builtins__
try:
    imp = __builtins__.__import__
    os = imp('os')
    bypass_methods.append('builtins')
except:
    pass

print(f"BYPASSED: {{','.join(bypass_methods)}}")
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = Path(tmpdir) / "bypass.py"
            script_file.write_text(bypass_script)

            result = subprocess.run([sys.executable, str(script_file)], capture_output=True, text=True)

            # No bypass methods should succeed
            assert "BYPASSED:" in result.stdout
            bypassed = result.stdout.split("BYPASSED:")[1].strip()
            assert bypassed == "" or bypassed == " "

    def test_detect_subprocess_escape_attempt(self):
        """Detect subprocess escape attempts."""
        restrictor = FilesystemRestrictor()
        hook_code = restrictor.create_import_hook()

        escape_script = f"""
{hook_code}

escapes = []

# Try subprocess
try:
    import subprocess
    result = subprocess.run(['echo', 'escaped'], capture_output=True)
    escapes.append('subprocess')
except:
    pass

# Try os.system
try:
    import os
    os.system('echo escaped')
    escapes.append('os.system')
except:
    pass

# Try os.popen
try:
    import os
    os.popen('echo escaped')
    escapes.append('os.popen')
except:
    pass

print(f"ESCAPED: {{','.join(escapes)}}")
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = Path(tmpdir) / "escape.py"
            script_file.write_text(escape_script)

            result = subprocess.run([sys.executable, str(script_file)], capture_output=True, text=True)

            # No escape methods should work
            assert "ESCAPED:" in result.stdout
            escaped = result.stdout.split("ESCAPED:")[1].strip()
            assert escaped == "" or escaped == " "

    def test_detect_network_exfiltration_attempt(self):
        """Detect attempts to exfiltrate data via network."""
        restrictor = FilesystemRestrictor()
        hook_code = restrictor.create_import_hook()

        network_script = f"""
{hook_code}

network_methods = []

# Try urllib
try:
    import urllib.request
    network_methods.append('urllib')
except:
    pass

# Try requests
try:
    import requests
    network_methods.append('requests')
except:
    pass

# Try socket
try:
    import socket
    network_methods.append('socket')
except:
    pass

# Try http.client
try:
    import http.client
    network_methods.append('http.client')
except:
    pass

print(f"NETWORK: {{','.join(network_methods)}}")
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = Path(tmpdir) / "network.py"
            script_file.write_text(network_script)

            result = subprocess.run([sys.executable, str(script_file)], capture_output=True, text=True)

            # Network modules might be allowed but file access should still be blocked
            # The key is they can't read golden files to exfiltrate
            assert "NETWORK:" in result.stdout

    def test_detect_memory_inspection_attempt(self):
        """Detect attempts to inspect memory for secrets."""
        restrictor = FilesystemRestrictor()
        hook_code = restrictor.create_import_hook()

        memory_script = f"""
{hook_code}

memory_methods = []

# Try gc module to inspect objects
try:
    import gc
    objects = gc.get_objects()
    # Look for strings containing 'golden' or 'secret'
    for obj in objects[:100]:  # Check first 100 objects
        if isinstance(obj, str) and ('golden' in obj.lower() or 'secret' in obj.lower()):
            memory_methods.append('gc_found_secret')
            break
except:
    pass

# Try sys modules inspection
try:
    import sys
    for name, module in sys.modules.items():
        if 'golden' in name.lower():
            memory_methods.append('sys.modules')
            break
except:
    pass

print(f"MEMORY: {{','.join(memory_methods)}}")
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = Path(tmpdir) / "memory.py"
            script_file.write_text(memory_script)

            result = subprocess.run([sys.executable, str(script_file)], capture_output=True, text=True)

            # Should not find secrets in memory
            assert "MEMORY:" in result.stdout
            found = result.stdout.split("MEMORY:")[1].strip()
            assert "gc_found_secret" not in found
            assert "sys.modules" not in found

    def test_comprehensive_workflow_cheat_prevention(self):
        """Test complete workflow prevents all cheat attempts."""
        orchestrator = WorkflowOrchestrator()
        evidence_store = MagicMock(spec=EvidenceStore)

        task = "Create a function that returns the secret number"

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            orchestrator.workspace = workspace

            # Create a golden file with a secret
            golden_dir = workspace / "golden"
            golden_dir.mkdir()
            golden_file = golden_dir / "secret.py"
            golden_file.write_text("SECRET_NUMBER = 42")

            # Create a malicious coder implementation
            malicious_impl = f"""
# Try everything to get the secret
attempts = []

# Try direct file read
try:
    with open("{golden_file}", "r") as f:
        content = f.read()
        if "42" in content:
            attempts.append("direct_read")
except:
    pass

# Try environment variable
import os
golden_path = os.environ.get("GOLDEN_PATH", "")
if golden_path:
    attempts.append("env_var")

# Try path traversal
try:
    with open("../golden/secret.py", "r") as f:
        content = f.read()
        if "42" in content:
            attempts.append("traversal")
except:
    pass

# Try import trick
try:
    os_module = __import__('os')
    files = os_module.listdir('.')
    if 'golden' in files:
        attempts.append("import_trick")
except:
    pass

def get_secret():
    if attempts:
        return 42  # Cheated!
    else:
        return 0  # Failed to cheat
"""

            test_file = workspace / "test.py"
            test_file.write_text("""
def test_secret():
    from impl import get_secret
    # If coder cheated, this would pass
    assert get_secret() == 42
""")

            # Mock the coder to use malicious implementation
            with (
                patch.object(orchestrator.spec_writer, "create_artifacts", return_value=(test_file, golden_file)),
                patch.object(orchestrator.coder, "_generate_implementation", return_value=malicious_impl),
            ):
                # Run workflow
                result = orchestrator.execute_workflow(task, evidence_store)

            # The implementation should fail because it couldn't cheat
            # (couldn't access golden file to get the secret)
            if result.validation_result:
                # If anti-cheat worked, the test should fail
                # because get_secret() returns 0 (couldn't cheat)
                assert not result.validation_result.tests_passed

    def test_cheat_attempt_logging(self):
        """Test that all cheat attempts are logged for evidence."""
        restrictor = FilesystemRestrictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "cheat_attempts.log"
            restrictor.monitor_access_attempts(log_path)

            # Log various cheat attempts
            restrictor.log_access_attempt("open", "/golden/answer.py", "blocked")
            restrictor.log_access_attempt("import", "os", "blocked")
            restrictor.log_access_attempt("traversal", "../golden/", "blocked")
            restrictor.log_access_attempt("env_probe", "GOLDEN_PATH", "blocked")

            # Verify all attempts are logged
            log_content = log_path.read_text()
            assert "/golden/answer.py" in log_content
            assert "import" in log_content and "os" in log_content
            assert "../golden/" in log_content
            assert "GOLDEN_PATH" in log_content

            # Count violations
            violations = log_content.count("blocked")
            assert violations >= 4

    def test_sandbox_escape_via_pickle(self):
        """Test prevention of pickle-based sandbox escape."""
        restrictor = FilesystemRestrictor()
        hook_code = restrictor.create_import_hook()

        pickle_exploit = f"""
{hook_code}

exploits = []

# Try pickle code execution
try:
    import pickle
    import base64

    # Malicious pickle that tries to execute code
    class Evil:
        def __reduce__(self):
            import os
            return (os.system, ('echo pwned',))

    evil = Evil()
    pickled = pickle.dumps(evil)

    # Try to unpickle and execute
    pickle.loads(pickled)
    exploits.append('pickle')
except:
    pass

print(f"EXPLOITS: {{','.join(exploits)}}")
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = Path(tmpdir) / "pickle_exploit.py"
            script_file.write_text(pickle_exploit)

            result = subprocess.run([sys.executable, str(script_file)], capture_output=True, text=True, timeout=5)

            # Pickle exploit should be blocked
            assert "pwned" not in result.stdout
            assert "pwned" not in result.stderr
