"""Recovery management for vi editor."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class RecoveryManager:
    """Manages crash recovery and swap files."""

    def __init__(self, recovery_dir: Optional[str] = None):
        """Initialize recovery manager.

        Args:
            recovery_dir: Directory for recovery files (default: ~/.vi_recovery).
        """
        if recovery_dir:
            self.recovery_dir = Path(recovery_dir)
        else:
            self.recovery_dir = Path.home() / ".vi_recovery"

        # Create recovery directory if it doesn't exist
        self.recovery_dir.mkdir(parents=True, exist_ok=True)

        self.swap_suffix = ".swp"
        self.recovery_suffix = ".rec"

    def create_swap_file(self, filename: str) -> Optional[str]:
        """Create a swap file for a buffer.

        Args:
            filename: Original filename.

        Returns:
            Path to swap file or None if failed.
        """
        source = Path(filename)
        swap_name = f".{source.name}{self.swap_suffix}"
        swap_path = source.parent / swap_name

        try:
            # Create swap file
            swap_path.touch()
            return str(swap_path)
        except Exception:
            # Try recovery directory as fallback
            try:
                swap_path = self.recovery_dir / swap_name
                swap_path.touch()
                return str(swap_path)
            except Exception:
                return None

    def update_swap_file(self, swap_file: str, buffer_content: str) -> bool:
        """Update swap file with buffer content.

        Args:
            swap_file: Path to swap file.
            buffer_content: Current buffer content.

        Returns:
            True if successful, False otherwise.
        """
        swap_path = Path(swap_file)

        try:
            with open(swap_path, "w", encoding="utf-8") as f:
                f.write(buffer_content)
            return True
        except Exception:
            return False

    def remove_swap_file(self, swap_file: str) -> bool:
        """Remove a swap file.

        Args:
            swap_file: Path to swap file.

        Returns:
            True if successful, False otherwise.
        """
        swap_path = Path(swap_file)

        if not swap_path.exists():
            return True

        try:
            swap_path.unlink()
            return True
        except Exception:
            return False

    def find_swap_file(self, filename: str) -> Optional[str]:
        """Find swap file for a given file.

        Args:
            filename: Original filename.

        Returns:
            Path to swap file or None if not found.
        """
        source = Path(filename)
        swap_name = f".{source.name}{self.swap_suffix}"

        # Check in same directory
        swap_path = source.parent / swap_name
        if swap_path.exists():
            return str(swap_path)

        # Check in recovery directory
        swap_path = self.recovery_dir / swap_name
        if swap_path.exists():
            return str(swap_path)

        return None

    def check_recovery_needed(self, filename: str) -> bool:
        """Check if recovery is needed for a file.

        Args:
            filename: Original filename.

        Returns:
            True if swap file exists, False otherwise.
        """
        return self.find_swap_file(filename) is not None

    def recover_from_swap(self, swap_file: str) -> Optional[str]:
        """Recover content from swap file.

        Args:
            swap_file: Path to swap file.

        Returns:
            Recovered content or None if failed.
        """
        swap_path = Path(swap_file)

        if not swap_path.exists():
            return None

        try:
            with open(swap_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    def save_recovery_info(self, filename: str, info: Dict[str, Any]) -> bool:
        """Save recovery information.

        Args:
            filename: Original filename.
            info: Recovery information to save.

        Returns:
            True if successful, False otherwise.
        """
        source = Path(filename)
        recovery_name = f"{source.name}{self.recovery_suffix}"
        recovery_path = self.recovery_dir / recovery_name

        try:
            # Add timestamp
            info["timestamp"] = datetime.now().isoformat()
            info["original_file"] = str(source.resolve())

            with open(recovery_path, "w") as f:
                json.dump(info, f, indent=2)
            return True
        except Exception:
            return False

    def load_recovery_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load recovery information.

        Args:
            filename: Original filename.

        Returns:
            Recovery information or None if not found.
        """
        source = Path(filename)
        recovery_name = f"{source.name}{self.recovery_suffix}"
        recovery_path = self.recovery_dir / recovery_name

        if not recovery_path.exists():
            return None

        try:
            with open(recovery_path, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def clean_recovery_files(self, filename: str) -> None:
        """Clean all recovery files for a given file.

        Args:
            filename: Original filename.
        """
        # Remove swap file
        swap_file = self.find_swap_file(filename)
        if swap_file:
            self.remove_swap_file(swap_file)

        # Remove recovery info
        source = Path(filename)
        recovery_name = f"{source.name}{self.recovery_suffix}"
        recovery_path = self.recovery_dir / recovery_name

        if recovery_path.exists():
            try:
                recovery_path.unlink()
            except Exception:
                pass

    def list_recoverable_files(self) -> list[str]:
        """List all files that can be recovered.

        Returns:
            List of original filenames that have recovery files.
        """
        recoverable = []

        # Check swap files in recovery directory
        for swap_file in self.recovery_dir.glob(f"*{self.swap_suffix}"):
            # Extract original filename
            original_name = swap_file.name[1 : -len(self.swap_suffix)]
            recoverable.append(original_name)

        # Check recovery info files
        for rec_file in self.recovery_dir.glob(f"*{self.recovery_suffix}"):
            try:
                with open(rec_file, "r") as f:
                    info = json.load(f)
                    if "original_file" in info:
                        recoverable.append(info["original_file"])
            except Exception:
                pass

        return list(set(recoverable))  # Remove duplicates
