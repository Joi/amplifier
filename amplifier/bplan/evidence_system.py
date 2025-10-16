"""Core Evidence System - Evidence Storage and Validation Interfaces"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Protocol


@dataclass
class Evidence:
    """Evidence data structure for storing validation results"""

    id: str  # UUID
    type: str  # 'code_validation', 'design_validation', etc.
    content: dict[str, Any]  # Evidence data
    timestamp: datetime
    validator_id: str
    checksum: str  # SHA256 for integrity


class EvidenceStore:
    """File-based storage for evidence with integrity verification"""

    def __init__(self, base_dir: Path) -> None:
        """Initialize the evidence store with a base directory

        Args:
            base_dir: Base directory for storing evidence files
        """
        self.base_dir = Path(base_dir)
        self.evidence_dir = self.base_dir / "evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def add_evidence(self, type: str, content: dict[str, Any], validator_id: str) -> Evidence:
        """Add new evidence to the store

        Args:
            type: Type of evidence (e.g., 'code_validation')
            content: Evidence data to store
            validator_id: ID of the validator that created this evidence

        Returns:
            Evidence object with generated ID and checksum
        """
        evidence_id = str(uuid.uuid4())
        timestamp = datetime.now()

        # Create evidence object
        evidence = Evidence(
            id=evidence_id,
            type=type,
            content=content,
            timestamp=timestamp,
            validator_id=validator_id,
            checksum="",  # Will be calculated
        )

        # Calculate checksum
        evidence.checksum = self._calculate_checksum(evidence)

        # Save to file
        self._save_evidence(evidence)

        return evidence

    def get_evidence(self, evidence_id: str) -> Evidence:
        """Retrieve evidence by ID

        Args:
            evidence_id: UUID of the evidence to retrieve

        Returns:
            Evidence object

        Raises:
            FileNotFoundError: If evidence file doesn't exist
            KeyError: If evidence file is missing required fields
            json.JSONDecodeError: If evidence file is not valid JSON
        """
        evidence_path = self.evidence_dir / f"{evidence_id}.json"

        if not evidence_path.exists():
            raise FileNotFoundError(f"Evidence not found: {evidence_id}")

        with open(evidence_path) as f:
            data = json.load(f)

        # Reconstruct Evidence object
        evidence = Evidence(
            id=data["id"],
            type=data["type"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            validator_id=data["validator_id"],
            checksum=data["checksum"],
        )

        return evidence

    def list_evidence(self, type: str | None = None) -> list[Evidence]:
        """List all evidence, optionally filtered by type

        Args:
            type: Optional type filter

        Returns:
            List of Evidence objects
        """
        evidence_list = []

        for evidence_file in self.evidence_dir.glob("*.json"):
            try:
                evidence_id = evidence_file.stem
                evidence = self.get_evidence(evidence_id)

                if type is None or evidence.type == type:
                    evidence_list.append(evidence)
            except (FileNotFoundError, KeyError, json.JSONDecodeError):
                # Skip corrupted or invalid files
                continue

        return evidence_list

    def verify_integrity(self, evidence_id: str) -> bool:
        """Verify the integrity of evidence using its checksum

        Args:
            evidence_id: UUID of the evidence to verify

        Returns:
            True if checksum matches, False if corrupted

        Raises:
            FileNotFoundError: If evidence doesn't exist
        """
        evidence = self.get_evidence(evidence_id)
        expected_checksum = evidence.checksum

        # Recalculate checksum
        evidence.checksum = ""  # Clear for recalculation
        actual_checksum = self._calculate_checksum(evidence)

        return expected_checksum == actual_checksum

    def _save_evidence(self, evidence: Evidence) -> None:
        """Save evidence to a JSON file

        Args:
            evidence: Evidence object to save
        """
        evidence_path = self.evidence_dir / f"{evidence.id}.json"

        data = {
            "id": evidence.id,
            "type": evidence.type,
            "content": evidence.content,
            "timestamp": evidence.timestamp.isoformat(),
            "validator_id": evidence.validator_id,
            "checksum": evidence.checksum,
        }

        with open(evidence_path, "w") as f:
            json.dump(data, f, indent=2)

    def _calculate_checksum(self, evidence: Evidence) -> str:
        """Calculate SHA256 checksum for evidence

        Args:
            evidence: Evidence object (checksum field is ignored)

        Returns:
            Hex digest of SHA256 hash
        """
        # Create a copy without checksum for calculation
        data = {
            "id": evidence.id,
            "type": evidence.type,
            "content": evidence.content,
            "timestamp": evidence.timestamp.isoformat(),
            "validator_id": evidence.validator_id,
        }

        # Serialize to JSON with sorted keys for consistency
        json_str = json.dumps(data, sort_keys=True)

        # Calculate SHA256
        return hashlib.sha256(json_str.encode()).hexdigest()


class ValidationInterface(Protocol):
    """Protocol defining the validation interface that validators must implement"""

    def validate_code(self, code_path: Path, evidence_store: EvidenceStore) -> str:
        """Validate code and store evidence

        Args:
            code_path: Path to the code file to validate
            evidence_store: Store for saving validation evidence

        Returns:
            Evidence ID if successful, or error string starting with "failure:"
        """
        ...

    def validate_design(self, spec_path: Path, evidence_store: EvidenceStore) -> str:
        """Validate design specification and store evidence

        Args:
            spec_path: Path to the specification file to validate
            evidence_store: Store for saving validation evidence

        Returns:
            Evidence ID if successful, or error string starting with "failure:"
        """
        ...
