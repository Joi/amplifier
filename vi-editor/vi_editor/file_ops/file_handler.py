"""File handling for vi editor."""

import os
from pathlib import Path
from typing import List

from vi_editor.core.buffer import Buffer


class FileHandler:
    """Handles file read/write operations."""

    def __init__(self, backup_manager=None):
        """Initialize file handler.

        Args:
            backup_manager: Optional BackupManager instance.
        """
        self.backup_manager = backup_manager
        self.encoding = "utf-8"
        self.newline = "\n"

    def read_file(self, filename: str) -> Buffer:
        """Read a file into a buffer.

        Args:
            filename: Path to the file.

        Returns:
            Buffer containing file content.

        Raises:
            FileNotFoundError: If file doesn't exist.
            IOError: If file can't be read.
        """
        path = Path(filename).resolve()

        if not path.exists():
            raise FileNotFoundError(f"File not found: {filename}")

        if not path.is_file():
            raise IOError(f"Not a regular file: {filename}")

        # Read file content
        try:
            with open(path, "r", encoding=self.encoding) as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try binary mode
            with open(path, "rb") as f:
                content = f.read().decode("utf-8", errors="replace")

        # Split into lines
        lines = content.split("\n")

        # Create buffer
        buffer = Buffer(lines)
        buffer.set_filename(str(path))

        # Mark as unmodified since just loaded
        buffer._modified = False

        return buffer

    def write_file(self, filename: str, buffer: Buffer) -> int:
        """Write buffer content to a file.

        Args:
            filename: Path to the file.
            buffer: Buffer to write.

        Returns:
            Number of lines written.

        Raises:
            IOError: If file can't be written.
        """
        path = Path(filename).resolve()

        # Create backup if manager available
        if self.backup_manager and path.exists():
            self.backup_manager.create_backup(str(path))

        # Get buffer content
        content = buffer.get_text()

        # Write to file
        try:
            # Write to temporary file first
            temp_path = path.with_suffix(".tmp")
            with open(temp_path, "w", encoding=self.encoding, newline="") as f:
                f.write(content)

            # Move temp file to actual file
            temp_path.replace(path)

            # Mark buffer as unmodified
            buffer._modified = False

            return buffer.line_count

        except Exception as e:
            # Clean up temp file if exists
            if temp_path.exists():
                temp_path.unlink()
            raise IOError(f"Failed to write file: {str(e)}")

    def write_lines(self, filename: str, lines: List[str]) -> int:
        """Write lines to a file.

        Args:
            filename: Path to the file.
            lines: Lines to write.

        Returns:
            Number of lines written.

        Raises:
            IOError: If file can't be written.
        """
        path = Path(filename).resolve()

        # Join lines
        content = "\n".join(lines)

        # Write to file
        try:
            with open(path, "w", encoding=self.encoding, newline="") as f:
                f.write(content)
            return len(lines)
        except Exception as e:
            raise IOError(f"Failed to write file: {str(e)}")

    def file_exists(self, filename: str) -> bool:
        """Check if a file exists.

        Args:
            filename: Path to check.

        Returns:
            True if file exists, False otherwise.
        """
        return Path(filename).exists()

    def is_writable(self, filename: str) -> bool:
        """Check if a file is writable.

        Args:
            filename: Path to check.

        Returns:
            True if file is writable, False otherwise.
        """
        path = Path(filename)

        if path.exists():
            # Check if existing file is writable
            return os.access(path, os.W_OK)
        else:
            # Check if parent directory is writable
            parent = path.parent
            return parent.exists() and os.access(parent, os.W_OK)

    def is_readable(self, filename: str) -> bool:
        """Check if a file is readable.

        Args:
            filename: Path to check.

        Returns:
            True if file is readable, False otherwise.
        """
        path = Path(filename)
        return path.exists() and os.access(path, os.R_OK)

    def get_file_info(self, filename: str) -> dict:
        """Get information about a file.

        Args:
            filename: Path to the file.

        Returns:
            Dictionary with file information.
        """
        path = Path(filename)

        if not path.exists():
            return {"exists": False, "path": str(path)}

        stat = path.stat()

        return {
            "exists": True,
            "path": str(path.resolve()),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "readable": os.access(path, os.R_OK),
            "writable": os.access(path, os.W_OK),
            "executable": os.access(path, os.X_OK),
        }

    def expand_path(self, filename: str) -> str:
        """Expand a path (handle ~, environment variables).

        Args:
            filename: Path to expand.

        Returns:
            Expanded path.
        """
        # Expand ~ to home directory
        path = os.path.expanduser(filename)

        # Expand environment variables
        path = os.path.expandvars(path)

        # Resolve to absolute path
        path = str(Path(path).resolve())

        return path

    def list_directory(self, dirname: str) -> List[str]:
        """List files in a directory.

        Args:
            dirname: Directory path.

        Returns:
            List of file names.

        Raises:
            NotADirectoryError: If path is not a directory.
        """
        path = Path(dirname)

        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {dirname}")

        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dirname}")

        # List files
        files = []
        for item in path.iterdir():
            if item.is_file():
                files.append(item.name)
            elif item.is_dir():
                files.append(item.name + "/")

        return sorted(files)

    def create_file(self, filename: str) -> None:
        """Create an empty file.

        Args:
            filename: Path to the file.

        Raises:
            IOError: If file can't be created.
        """
        path = Path(filename)

        if path.exists():
            raise IOError(f"File already exists: {filename}")

        try:
            path.touch()
        except Exception as e:
            raise IOError(f"Failed to create file: {str(e)}")
