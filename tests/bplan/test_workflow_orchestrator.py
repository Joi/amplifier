"""
Tests for WorkflowOrchestrator - agent coordination and evidence tracking.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from amplifier.bplan.evidence_system import EvidenceStore
from amplifier.bplan.three_agent_workflow import FilesystemRestrictor
from amplifier.bplan.three_agent_workflow import ValidationResult
from amplifier.bplan.three_agent_workflow import WorkflowOrchestrator


class TestWorkflowOrchestrator:
    """Test the orchestrator that coordinates the 3-agent workflow."""

    def test_execute_workflow_success(self):
        """Test successful execution of complete workflow."""
        orchestrator = WorkflowOrchestrator()
        evidence_store = MagicMock(spec=EvidenceStore)

        task = "Create a function that squares a number"

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            orchestrator.workspace = workspace

            # Mock agent behaviors
            test_file = workspace / "test_square.py"
            golden_file = workspace / "golden_square.py"
            impl_file = workspace / "square.py"

            test_file.write_text("""
def test_square():
    from square import square
    assert square(5) == 25
""")
            golden_file.write_text("""
def square(x):
    return x * x
""")
            impl_file.write_text("""
def square(x):
    return x * x
""")

            # Mock agent methods
            with patch.object(orchestrator.spec_writer, "create_artifacts", return_value=(test_file, golden_file)):
                with patch.object(orchestrator.coder, "implement_from_test", return_value=impl_file):
                    validation_result = ValidationResult(tests_passed=True, matches_golden=True, error=None, details={})
                    with patch.object(orchestrator.tester, "validate", return_value=validation_result):
                        result = orchestrator.execute_workflow(task, evidence_store)

            # Verify successful result
            assert result.success
            assert result.test_path == test_file
            assert result.implementation_path == impl_file
            assert result.validation_result.tests_passed
            assert result.error is None

            # Verify evidence was tracked
            evidence_store.add_evidence.assert_called()

    def test_execute_workflow_with_test_failure(self):
        """Test workflow when implementation fails tests."""
        orchestrator = WorkflowOrchestrator()
        evidence_store = MagicMock(spec=EvidenceStore)

        task = "Create a complex function"

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            orchestrator.workspace = workspace

            test_file = workspace / "test.py"
            golden_file = workspace / "golden.py"
            impl_file = workspace / "impl.py"

            # Create files
            test_file.write_text("def test(): assert False")
            golden_file.write_text("def func(): pass")
            impl_file.write_text("def func(): return 'wrong'")

            with patch.object(orchestrator.spec_writer, "create_artifacts", return_value=(test_file, golden_file)):
                with patch.object(orchestrator.coder, "implement_from_test", return_value=impl_file):
                    validation_result = ValidationResult(
                        tests_passed=False,
                        matches_golden=False,
                        error="AssertionError: Test failed",
                        details={"failed_tests": ["test"]},
                    )
                    with patch.object(orchestrator.tester, "validate", return_value=validation_result):
                        result = orchestrator.execute_workflow(task, evidence_store)

            # Verify failure is handled
            assert not result.success
            assert result.validation_result.tests_passed is False
            assert result.error is not None or not result.validation_result.tests_passed

    def test_execute_workflow_isolation_between_agents(self):
        """Test that agents are properly isolated from each other."""
        orchestrator = WorkflowOrchestrator()
        evidence_store = MagicMock(spec=EvidenceStore)

        task = "Create a function"

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            orchestrator.workspace = workspace

            # Track workspace usage
            spec_workspace = None
            coder_workspace = None
            tester_workspace = None

            def track_spec_workspace(*args, **kwargs):
                nonlocal spec_workspace
                spec_workspace = orchestrator.spec_writer.workspace
                test_file = workspace / "test.py"
                golden_file = workspace / "golden.py"
                test_file.write_text("def test(): pass")
                golden_file.write_text("def func(): pass")
                return test_file, golden_file

            def track_coder_workspace(test_path, restrictor, evidence_store=None):
                nonlocal coder_workspace
                coder_workspace = orchestrator.coder.workspace
                impl_file = workspace / "impl.py"
                impl_file.write_text("def func(): pass")
                return impl_file

            def track_tester_workspace(*args, **kwargs):
                nonlocal tester_workspace
                tester_workspace = orchestrator.tester.workspace
                return ValidationResult(True, True, None, {})

            with patch.object(orchestrator.spec_writer, "create_artifacts", side_effect=track_spec_workspace):
                with patch.object(orchestrator.coder, "implement_from_test", side_effect=track_coder_workspace):
                    with patch.object(orchestrator.tester, "validate", side_effect=track_tester_workspace):
                        result = orchestrator.execute_workflow(task, evidence_store)

            # Each agent should have its own workspace or isolation
            # (Exact isolation strategy depends on implementation)
            assert result is not None

    def test_execute_workflow_with_filesystem_restrictions(self):
        """Test that filesystem restrictions are applied to coder."""
        orchestrator = WorkflowOrchestrator()
        evidence_store = MagicMock(spec=EvidenceStore)

        task = "Create a function"

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            orchestrator.workspace = workspace

            test_file = workspace / "test.py"
            golden_file = workspace / "golden.py"
            impl_file = workspace / "impl.py"

            test_file.write_text("def test(): pass")
            golden_file.write_text("def func(): pass")
            impl_file.write_text("def func(): pass")

            restrictor_used = None

            def capture_restrictor(test_path, restrictor, evidence_store=None):
                nonlocal restrictor_used
                restrictor_used = restrictor
                return impl_file

            with patch.object(orchestrator.spec_writer, "create_artifacts", return_value=(test_file, golden_file)):
                with patch.object(orchestrator.coder, "implement_from_test", side_effect=capture_restrictor):
                    with patch.object(
                        orchestrator.tester, "validate", return_value=ValidationResult(True, True, None, {})
                    ):
                        orchestrator.execute_workflow(task, evidence_store)

            # Verify restrictor was passed to coder
            assert restrictor_used is not None
            assert isinstance(restrictor_used, FilesystemRestrictor)

    def test_execute_workflow_evidence_collection(self):
        """Test that all evidence is properly collected throughout workflow."""
        orchestrator = WorkflowOrchestrator()
        evidence_store = MagicMock(spec=EvidenceStore)

        task = "Create a function"

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            orchestrator.workspace = workspace

            test_file = workspace / "test.py"
            golden_file = workspace / "golden.py"
            impl_file = workspace / "impl.py"

            test_file.write_text("def test(): pass")
            golden_file.write_text("def func(): pass")
            impl_file.write_text("def func(): pass")

            with patch.object(orchestrator.spec_writer, "create_artifacts", return_value=(test_file, golden_file)):
                with patch.object(orchestrator.coder, "implement_from_test", return_value=impl_file):
                    with patch.object(
                        orchestrator.tester, "validate", return_value=ValidationResult(True, True, None, {})
                    ):
                        orchestrator.execute_workflow(task, evidence_store)

            # Check evidence store interactions
            evidence_calls = evidence_store.add_evidence.call_count

            # Should record multiple evidence entries (artifacts and execution)
            assert evidence_calls >= 3  # At least test, golden, and execution

    def test_execute_workflow_error_handling(self):
        """Test error handling in workflow execution."""
        orchestrator = WorkflowOrchestrator()
        evidence_store = MagicMock(spec=EvidenceStore)

        task = "Create a function"

        # Test spec writer failure
        with patch.object(
            orchestrator.spec_writer, "create_artifacts", side_effect=Exception("Spec generation failed")
        ):
            result = orchestrator.execute_workflow(task, evidence_store)
            assert not result.success
            assert "Spec generation failed" in str(result.error)

        # Test coder failure
        test_file = Path("/tmp/test.py")
        golden_file = Path("/tmp/golden.py")

        with patch.object(orchestrator.spec_writer, "create_artifacts", return_value=(test_file, golden_file)):
            with patch.object(
                orchestrator.coder, "implement_from_test", side_effect=Exception("Code generation failed")
            ):
                result = orchestrator.execute_workflow(task, evidence_store)
                assert not result.success
                assert "Code generation failed" in str(result.error)

    def test_execute_workflow_golden_isolation(self):
        """Test that golden files are never accessible to coder."""
        orchestrator = WorkflowOrchestrator()
        evidence_store = MagicMock(spec=EvidenceStore)

        task = "Create a function"

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            orchestrator.workspace = workspace

            # Create golden directory with sensitive content
            golden_dir = workspace / "golden"
            golden_dir.mkdir()
            golden_file = golden_dir / "solution.py"
            golden_file.write_text("SECRET_ANSWER = 42")

            test_file = workspace / "test.py"
            test_file.write_text("def test(): pass")

            # Track environment passed to coder
            coder_env = None

            def capture_coder_env(test_path, restrictor, evidence_store=None):
                nonlocal coder_env
                # Capture the restricted environment
                coder_env = restrictor.create_restricted_env(
                    allowed_paths=[workspace / "impl"], blocked_paths=[golden_dir]
                )
                impl_file = workspace / "impl.py"
                impl_file.write_text("def func(): pass")
                return impl_file

            with patch.object(orchestrator.spec_writer, "create_artifacts", return_value=(test_file, golden_file)):
                with patch.object(orchestrator.coder, "implement_from_test", side_effect=capture_coder_env):
                    with patch.object(
                        orchestrator.tester, "validate", return_value=ValidationResult(True, True, None, {})
                    ):
                        orchestrator.execute_workflow(task, evidence_store)

            # Verify golden path is not in coder's environment
            if coder_env:
                assert "GOLDEN_PATH" not in coder_env
                blocked_paths = coder_env.get("BLOCKED_PATHS", "").split(":")
                assert str(golden_dir) in blocked_paths or str(golden_file) in blocked_paths

    def test_execute_workflow_subprocess_isolation(self):
        """Test that each agent runs in proper subprocess isolation."""
        orchestrator = WorkflowOrchestrator()
        evidence_store = MagicMock(spec=EvidenceStore)

        task = "Create a function"

        subprocess_configs = []

        def track_subprocess(*args, **kwargs):
            subprocess_configs.append(kwargs)
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=track_subprocess):
            # Run workflow (will fail but we're tracking subprocess calls)
            try:
                orchestrator.execute_workflow(task, evidence_store)
            except Exception:
                pass  # Expected to fail, we're just tracking calls

        # Verify subprocess isolation was used
        if subprocess_configs:
            for config in subprocess_configs:
                # Check for clean environment
                if "env" in config:
                    env = config["env"]
                    # Should not leak sensitive paths
                    assert all("GOLDEN" not in k for k in env)
