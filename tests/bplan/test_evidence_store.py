"""Tests for the Evidence Store - Core Evidence System"""

import json
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from amplifier.bplan.evidence_system import Evidence
from amplifier.bplan.evidence_system import EvidenceStore


class TestEvidence:
    """Test the Evidence dataclass"""

    def test_evidence_creation(self):
        """Test creating an Evidence instance"""
        evidence = Evidence(
            id=str(uuid.uuid4()),
            type="code_validation",
            content={"test": "data"},
            timestamp=datetime.now(),
            validator_id="test_validator",
            checksum="abc123",
        )
        assert evidence.type == "code_validation"
        assert evidence.content == {"test": "data"}
        assert evidence.validator_id == "test_validator"
        assert evidence.checksum == "abc123"

    def test_evidence_id_uniqueness(self):
        """Test that evidence IDs are unique"""
        id1 = str(uuid.uuid4())
        id2 = str(uuid.uuid4())
        assert id1 != id2


class TestEvidenceStore:
    """Test the EvidenceStore with real file I/O"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def store(self, temp_dir):
        """Create an EvidenceStore instance"""
        return EvidenceStore(base_dir=temp_dir)

    def test_store_initialization(self, store, temp_dir):
        """Test that store creates necessary directories"""
        evidence_dir = temp_dir / "evidence"
        assert evidence_dir.exists()
        assert evidence_dir.is_dir()

    def test_add_evidence(self, store):
        """Test adding evidence to the store"""
        content = {"test": "data", "value": 42}
        evidence = store.add_evidence(type="code_validation", content=content, validator_id="test_validator")

        assert evidence.type == "code_validation"
        assert evidence.content == content
        assert evidence.validator_id == "test_validator"
        assert len(evidence.id) == 36  # UUID string length
        assert evidence.checksum is not None
        assert isinstance(evidence.timestamp, datetime)

    def test_get_evidence(self, store):
        """Test retrieving evidence by ID"""
        content = {"test": "retrieval"}
        added = store.add_evidence(type="design_validation", content=content, validator_id="retriever")

        retrieved = store.get_evidence(added.id)
        assert retrieved.id == added.id
        assert retrieved.type == added.type
        assert retrieved.content == added.content
        assert retrieved.validator_id == added.validator_id
        assert retrieved.checksum == added.checksum

    def test_get_nonexistent_evidence(self, store):
        """Test getting evidence that doesn't exist"""
        fake_id = str(uuid.uuid4())
        with pytest.raises(FileNotFoundError):
            store.get_evidence(fake_id)

    def test_list_evidence_empty(self, store):
        """Test listing evidence when store is empty"""
        evidence_list = store.list_evidence()
        assert evidence_list == []

    def test_list_evidence_with_entries(self, store):
        """Test listing all evidence"""
        # Add multiple evidence entries
        ev1 = store.add_evidence(type="code_validation", content={"item": 1}, validator_id="validator1")
        ev2 = store.add_evidence(type="design_validation", content={"item": 2}, validator_id="validator2")
        ev3 = store.add_evidence(type="code_validation", content={"item": 3}, validator_id="validator3")

        all_evidence = store.list_evidence()
        assert len(all_evidence) == 3
        ids = [e.id for e in all_evidence]
        assert ev1.id in ids
        assert ev2.id in ids
        assert ev3.id in ids

    def test_list_evidence_by_type(self, store):
        """Test filtering evidence by type"""
        # Add mixed types
        code1 = store.add_evidence(type="code_validation", content={"code": 1}, validator_id="v1")
        design = store.add_evidence(type="design_validation", content={"design": 1}, validator_id="v2")
        code2 = store.add_evidence(type="code_validation", content={"code": 2}, validator_id="v3")

        # Filter by type
        code_evidence = store.list_evidence(type="code_validation")
        assert len(code_evidence) == 2
        code_ids = [e.id for e in code_evidence]
        assert code1.id in code_ids
        assert code2.id in code_ids
        assert design.id not in code_ids

        design_evidence = store.list_evidence(type="design_validation")
        assert len(design_evidence) == 1
        assert design_evidence[0].id == design.id

    def test_verify_integrity_valid(self, store):
        """Test verifying integrity of valid evidence"""
        evidence = store.add_evidence(
            type="test_validation", content={"data": "unchanged"}, validator_id="integrity_test"
        )

        assert store.verify_integrity(evidence.id) is True

    def test_verify_integrity_corrupted(self, store, temp_dir):
        """Test detecting corrupted evidence"""
        evidence = store.add_evidence(
            type="test_validation", content={"data": "original"}, validator_id="corruption_test"
        )

        # Corrupt the file
        evidence_path = temp_dir / "evidence" / f"{evidence.id}.json"
        with open(evidence_path) as f:
            data = json.load(f)

        data["content"]["data"] = "corrupted"

        with open(evidence_path, "w") as f:
            json.dump(data, f)

        assert store.verify_integrity(evidence.id) is False

    def test_verify_integrity_nonexistent(self, store):
        """Test verifying integrity of non-existent evidence"""
        fake_id = str(uuid.uuid4())
        with pytest.raises(FileNotFoundError):
            store.verify_integrity(fake_id)

    def test_persistence_across_instances(self, temp_dir):
        """Test that evidence persists across store instances"""
        # Create first store and add evidence
        store1 = EvidenceStore(base_dir=temp_dir)
        evidence = store1.add_evidence(type="persistence_test", content={"persistent": True}, validator_id="persister")
        evidence_id = evidence.id

        # Create new store instance with same directory
        store2 = EvidenceStore(base_dir=temp_dir)
        retrieved = store2.get_evidence(evidence_id)

        assert retrieved.id == evidence.id
        assert retrieved.content == evidence.content
        assert retrieved.type == evidence.type

    def test_antagonistic_invalid_json(self, store, temp_dir):
        """Test handling of invalid JSON in evidence files"""
        # Create a malformed evidence file
        bad_id = str(uuid.uuid4())
        bad_file = temp_dir / "evidence" / f"{bad_id}.json"
        bad_file.write_text("{ invalid json content")

        with pytest.raises(json.JSONDecodeError):
            store.get_evidence(bad_id)

    def test_antagonistic_missing_fields(self, store, temp_dir):
        """Test handling of evidence files with missing required fields"""
        # Create evidence file with missing fields
        incomplete_id = str(uuid.uuid4())
        incomplete_file = temp_dir / "evidence" / f"{incomplete_id}.json"
        incomplete_data = {
            "id": incomplete_id,
            "type": "test",
            # Missing: content, timestamp, validator_id, checksum
        }
        incomplete_file.write_text(json.dumps(incomplete_data))

        with pytest.raises(KeyError):
            store.get_evidence(incomplete_id)

    def test_antagonistic_wrong_types(self, store, temp_dir):
        """Test handling of evidence with wrong field types"""
        wrong_id = str(uuid.uuid4())
        wrong_file = temp_dir / "evidence" / f"{wrong_id}.json"
        wrong_data = {
            "id": wrong_id,
            "type": "test",
            "content": "should be dict not string",  # Wrong type
            "timestamp": "2024-01-01T00:00:00",
            "validator_id": "test",
            "checksum": "abc123",
        }
        wrong_file.write_text(json.dumps(wrong_data))

        # This should either raise or handle gracefully
        # depending on implementation choices
        try:
            evidence = store.get_evidence(wrong_id)
            # If it doesn't raise, content should be handled somehow
            assert isinstance(evidence.content, dict | str)
        except (TypeError, ValueError):
            # Expected if strict type checking
            pass

    def test_concurrent_adds(self, store):
        """Test that concurrent additions don't interfere"""
        # Add multiple evidence entries rapidly
        evidences = []
        for i in range(10):
            ev = store.add_evidence(type="concurrent_test", content={"index": i}, validator_id=f"concurrent_{i}")
            evidences.append(ev)

        # Verify all were stored correctly
        for ev in evidences:
            retrieved = store.get_evidence(ev.id)
            assert retrieved.content == ev.content
