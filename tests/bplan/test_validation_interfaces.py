"""Tests for Validation Interfaces - Core Evidence System"""

import shutil
import tempfile
from pathlib import Path
from typing import Protocol

import pytest

from amplifier.bplan.evidence_system import EvidenceStore
from amplifier.bplan.evidence_system import ValidationInterface


class TestValidationInterface:
    """Test the ValidationInterface protocol"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def evidence_store(self, temp_dir):
        """Create an EvidenceStore for testing"""
        return EvidenceStore(base_dir=temp_dir)

    def test_validation_interface_is_protocol(self):
        """Test that ValidationInterface is a Protocol"""
        assert issubclass(ValidationInterface, Protocol)

    def test_validation_interface_methods_defined(self):
        """Test that required methods are defined in protocol"""
        # Check that the protocol defines the expected methods
        assert hasattr(ValidationInterface, "validate_code")
        assert hasattr(ValidationInterface, "validate_design")

    def test_concrete_validator_implementation(self, temp_dir, evidence_store):
        """Test implementing a concrete validator"""

        class ConcreteValidator:
            """A concrete implementation of ValidationInterface"""

            def validate_code(self, code_path: Path, evidence_store: EvidenceStore) -> str:
                """Validate code and store evidence"""
                # Simple validation: check if file exists and is Python
                if not code_path.exists():
                    return "failure: file not found"

                if code_path.suffix != ".py":
                    return "failure: not a Python file"

                # Store validation evidence
                evidence = evidence_store.add_evidence(
                    type="code_validation",
                    content={
                        "file": str(code_path),
                        "exists": True,
                        "is_python": True,
                    },
                    validator_id="concrete_validator",
                )
                return evidence.id

            def validate_design(self, spec_path: Path, evidence_store: EvidenceStore) -> str:
                """Validate design specification"""
                # Simple validation: check if spec file exists
                if not spec_path.exists():
                    return "failure: spec not found"

                # Store validation evidence
                evidence = evidence_store.add_evidence(
                    type="design_validation",
                    content={
                        "spec": str(spec_path),
                        "exists": True,
                    },
                    validator_id="concrete_validator",
                )
                return evidence.id

        # Create instance and test
        validator = ConcreteValidator()

        # Create test files
        code_file = temp_dir / "test.py"
        code_file.write_text("print('hello')")

        spec_file = temp_dir / "spec.md"
        spec_file.write_text("# Specification")

        # Validate code
        code_result = validator.validate_code(code_file, evidence_store)
        assert len(code_result) == 36  # UUID length
        assert code_result != "failure"

        # Validate design
        design_result = validator.validate_design(spec_file, evidence_store)
        assert len(design_result) == 36  # UUID length
        assert design_result != "failure"

        # Verify evidence was stored
        code_evidence = evidence_store.get_evidence(code_result)
        assert code_evidence.type == "code_validation"
        assert code_evidence.content["is_python"] is True

        design_evidence = evidence_store.get_evidence(design_result)
        assert design_evidence.type == "design_validation"
        assert design_evidence.content["exists"] is True

    def test_validator_with_nonexistent_file(self, temp_dir, evidence_store):
        """Test validator behavior with non-existent files"""

        class SimpleValidator:
            def validate_code(self, code_path: Path, evidence_store: EvidenceStore) -> str:
                if not code_path.exists():
                    return "failure: file not found"
                return "success"

            def validate_design(self, spec_path: Path, evidence_store: EvidenceStore) -> str:
                if not spec_path.exists():
                    return "failure: spec not found"
                return "success"

        validator = SimpleValidator()
        fake_path = temp_dir / "nonexistent.py"

        result = validator.validate_code(fake_path, evidence_store)
        assert result == "failure: file not found"

    def test_multiple_validators_can_coexist(self, temp_dir, evidence_store):
        """Test that multiple validators can implement the interface"""

        class ValidatorA:
            def validate_code(self, code_path: Path, evidence_store: EvidenceStore) -> str:
                evidence = evidence_store.add_evidence(
                    type="code_validation",
                    content={"validator": "A", "file": str(code_path)},
                    validator_id="validator_a",
                )
                return evidence.id

            def validate_design(self, spec_path: Path, evidence_store: EvidenceStore) -> str:
                evidence = evidence_store.add_evidence(
                    type="design_validation",
                    content={"validator": "A", "spec": str(spec_path)},
                    validator_id="validator_a",
                )
                return evidence.id

        class ValidatorB:
            def validate_code(self, code_path: Path, evidence_store: EvidenceStore) -> str:
                evidence = evidence_store.add_evidence(
                    type="code_validation",
                    content={"validator": "B", "file": str(code_path)},
                    validator_id="validator_b",
                )
                return evidence.id

            def validate_design(self, spec_path: Path, evidence_store: EvidenceStore) -> str:
                evidence = evidence_store.add_evidence(
                    type="design_validation",
                    content={"validator": "B", "spec": str(spec_path)},
                    validator_id="validator_b",
                )
                return evidence.id

        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("code")

        # Both validators should work
        val_a = ValidatorA()
        val_b = ValidatorB()

        result_a = val_a.validate_code(test_file, evidence_store)
        result_b = val_b.validate_code(test_file, evidence_store)

        # Different validators produce different evidence
        assert result_a != result_b

        evidence_a = evidence_store.get_evidence(result_a)
        evidence_b = evidence_store.get_evidence(result_b)

        assert evidence_a.content["validator"] == "A"
        assert evidence_b.content["validator"] == "B"

    def test_validator_error_handling(self, temp_dir, evidence_store):
        """Test validator error handling patterns"""

        class ErrorHandlingValidator:
            def validate_code(self, code_path: Path, evidence_store: EvidenceStore) -> str:
                try:
                    # Simulate validation that might fail
                    if not code_path.exists():
                        raise FileNotFoundError(f"Code file not found: {code_path}")

                    with open(code_path) as f:
                        content = f.read()
                        if "error" in content:
                            raise ValueError("Code contains errors")

                    # Success case
                    evidence = evidence_store.add_evidence(
                        type="code_validation",
                        content={"status": "success", "file": str(code_path)},
                        validator_id="error_handler",
                    )
                    return evidence.id

                except FileNotFoundError:
                    return "failure: file_not_found"
                except ValueError as e:
                    return f"failure: {str(e)}"
                except Exception as e:
                    return f"failure: unexpected_{str(e)}"

            def validate_design(self, spec_path: Path, evidence_store: EvidenceStore) -> str:
                # Similar error handling for design validation
                if not spec_path.exists():
                    return "failure: spec_not_found"
                return "success"

        validator = ErrorHandlingValidator()

        # Test file not found
        result = validator.validate_code(temp_dir / "missing.py", evidence_store)
        assert result == "failure: file_not_found"

        # Test validation failure
        error_file = temp_dir / "error.py"
        error_file.write_text("this has error in it")
        result = validator.validate_code(error_file, evidence_store)
        assert "failure:" in result
        assert "errors" in result

        # Test success case
        good_file = temp_dir / "good.py"
        good_file.write_text("print('hello')")
        result = validator.validate_code(good_file, evidence_store)
        assert len(result) == 36  # UUID length

    def test_validator_with_complex_evidence(self, temp_dir, evidence_store):
        """Test validator storing complex evidence structures"""

        class ComplexValidator:
            def validate_code(self, code_path: Path, evidence_store: EvidenceStore) -> str:
                # Collect comprehensive validation data
                stats = {}
                with open(code_path) as f:
                    content = f.read()
                    lines = content.splitlines()
                    stats["total_lines"] = len(lines)
                    stats["non_empty_lines"] = len([line for line in lines if line.strip()])
                    stats["imports"] = [line for line in lines if line.startswith("import") or line.startswith("from")]
                    stats["functions"] = [line for line in lines if line.strip().startswith("def ")]
                    stats["classes"] = [line for line in lines if line.strip().startswith("class ")]

                # Store detailed evidence
                evidence = evidence_store.add_evidence(
                    type="code_validation",
                    content={
                        "file": str(code_path),
                        "statistics": stats,
                        "validation_rules": [
                            "line_count",
                            "import_analysis",
                            "structure_detection",
                        ],
                        "passed": True,
                    },
                    validator_id="complex_validator",
                )
                return evidence.id

            def validate_design(self, spec_path: Path, evidence_store: EvidenceStore) -> str:
                # Simple implementation for protocol compliance
                evidence = evidence_store.add_evidence(
                    type="design_validation", content={"spec": str(spec_path)}, validator_id="complex_validator"
                )
                return evidence.id

        # Create a Python file with various elements
        code_file = temp_dir / "complex.py"
        code_file.write_text(
            """import os
from pathlib import Path

class MyClass:
    def method1(self):
        pass

def function1():
    return True

def function2():
    return False
"""
        )

        validator = ComplexValidator()
        result = validator.validate_code(code_file, evidence_store)

        # Verify complex evidence was stored correctly
        evidence = evidence_store.get_evidence(result)
        assert evidence.content["statistics"]["total_lines"] == 12
        assert len(evidence.content["statistics"]["functions"]) == 3  # Three def statements (including method)
        assert len(evidence.content["statistics"]["classes"]) == 1  # One class definition
        assert len(evidence.content["statistics"]["imports"]) == 2  # Two import lines
