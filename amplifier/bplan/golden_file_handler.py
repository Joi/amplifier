"""Golden File Handler for the Core Evidence System"""

import difflib
import hashlib
import re
from pathlib import Path


class GoldenFileHandler:
    """Handler for golden file generation, comparison, and reproduction"""

    def __init__(self, base_dir: Path) -> None:
        """Initialize the handler with a base directory

        Args:
            base_dir: Base directory for storing golden files
        """
        self.base_dir = Path(base_dir)
        self.golden_dir = self.base_dir / "golden"
        self.golden_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, content: bytes, name: str) -> Path:
        """Generate a new golden file with content

        Args:
            content: Binary content to store
            name: Base name for the golden file

        Returns:
            Path to the created golden file
        """
        # Calculate hash of content for uniqueness
        content_hash = hashlib.sha256(content).hexdigest()[:8]

        # Sanitize the name to remove problematic characters
        safe_name = self._sanitize_filename(name)

        # Create filename with hash
        filename = f"{safe_name}_{content_hash}.golden"
        golden_path = self.golden_dir / filename

        # Write content to file
        with open(golden_path, "wb") as f:
            f.write(content)

        return golden_path

    def compare(self, content: bytes, golden_path: Path) -> bool:
        """Compare content with a golden file

        Args:
            content: Binary content to compare
            golden_path: Path to the golden file

        Returns:
            True if content matches, False otherwise

        Raises:
            FileNotFoundError: If golden file doesn't exist
        """
        if not golden_path.exists():
            raise FileNotFoundError(f"Golden file not found: {golden_path}")

        with open(golden_path, "rb") as f:
            golden_content = f.read()

        return content == golden_content

    def get_diff(self, content: bytes, golden_path: Path) -> str:
        """Get the difference between content and golden file

        Args:
            content: Binary content to compare
            golden_path: Path to the golden file

        Returns:
            String representation of the diff, empty if identical

        Raises:
            FileNotFoundError: If golden file doesn't exist
        """
        if not golden_path.exists():
            raise FileNotFoundError(f"Golden file not found: {golden_path}")

        with open(golden_path, "rb") as f:
            golden_content = f.read()

        # If content is identical, return empty string
        if content == golden_content:
            return ""

        try:
            # Try to decode as text for readable diff
            content_lines = content.decode("utf-8", errors="replace").splitlines(keepends=True)
            golden_lines = golden_content.decode("utf-8", errors="replace").splitlines(keepends=True)

            # Generate unified diff
            diff = difflib.unified_diff(
                golden_lines,
                content_lines,
                fromfile=str(golden_path),
                tofile="new_content",
                lineterm="",
            )

            return "".join(diff)

        except Exception:
            # For binary content, just indicate they differ
            return f"Binary files differ: {len(golden_content)} bytes (golden) vs {len(content)} bytes (new)"

    def reproduce(self, golden_path: Path) -> bytes:
        """Reproduce content from a golden file

        Args:
            golden_path: Path to the golden file

        Returns:
            Binary content from the golden file

        Raises:
            FileNotFoundError: If golden file doesn't exist
        """
        if not golden_path.exists():
            raise FileNotFoundError(f"Golden file not found: {golden_path}")

        with open(golden_path, "rb") as f:
            return f.read()

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a filename to remove problematic characters

        Args:
            name: Original filename

        Returns:
            Sanitized filename safe for filesystem
        """
        # Replace problematic characters with underscores
        # Keep alphanumeric, dash, underscore, and dot
        safe_name = re.sub(r"[^a-zA-Z0-9\-_.]", "_", name)

        # Remove consecutive underscores
        safe_name = re.sub(r"_{2,}", "_", safe_name)

        # Trim underscores from start and end
        safe_name = safe_name.strip("_")

        # Ensure we have a valid name
        if not safe_name:
            safe_name = "golden_file"

        return safe_name
