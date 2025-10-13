"""Buffer management for vi editor."""

from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional


@dataclass
class UndoEntry:
    """Represents an undo/redo operation."""

    operation: str  # 'insert', 'delete', 'replace'
    row: int
    col: int
    text: str  # Text that was inserted/deleted
    old_text: Optional[str] = None  # For replace operations


class Buffer:
    """Manages text content and operations."""

    def __init__(self, content: Optional[List[str]] = None):
        """Initialize the buffer.

        Args:
            content: Initial content as list of lines.
        """
        self._lines: List[str] = content if content is not None else [""]
        self._modified = False
        self._filename: Optional[str] = None
        self._undo_stack: Deque[UndoEntry] = deque(maxlen=1000)
        self._redo_stack: Deque[UndoEntry] = deque(maxlen=1000)
        self._registers: dict[str, str] = {}
        self._marks: dict[str, tuple[int, int]] = {}

    @property
    def lines(self) -> List[str]:
        """Get all lines in the buffer."""
        return self._lines

    @property
    def line_count(self) -> int:
        """Get number of lines in the buffer."""
        return len(self._lines)

    @property
    def modified(self) -> bool:
        """Check if buffer has been modified."""
        return self._modified

    @property
    def filename(self) -> Optional[str]:
        """Get the associated filename."""
        return self._filename

    def set_filename(self, filename: str) -> None:
        """Set the associated filename.

        Args:
            filename: Path to the file.
        """
        self._filename = filename

    def get_line(self, row: int) -> str:
        """Get a specific line.

        Args:
            row: Line number (0-indexed).

        Returns:
            The line text or empty string if out of bounds.
        """
        if 0 <= row < len(self._lines):
            return self._lines[row]
        return ""

    def get_line_length(self, row: int) -> int:
        """Get length of a specific line.

        Args:
            row: Line number (0-indexed).

        Returns:
            Length of the line.
        """
        return len(self.get_line(row))

    def insert_char(self, row: int, col: int, char: str) -> None:
        """Insert a character at position.

        Args:
            row: Row position.
            col: Column position.
            char: Character to insert.
        """
        if 0 <= row < len(self._lines):
            line = self._lines[row]
            self._lines[row] = line[:col] + char + line[col:]
            self._add_undo_entry(UndoEntry("insert", row, col, char))
            self._modified = True
            self._redo_stack.clear()

    def insert_text(self, row: int, col: int, text: str) -> tuple[int, int]:
        """Insert text at position, handling newlines.

        Args:
            row: Row position.
            col: Column position.
            text: Text to insert.

        Returns:
            New cursor position after insertion.
        """
        if not text:
            return (row, col)

        lines = text.split("\n")

        if len(lines) == 1:
            # Single line insertion
            if 0 <= row < len(self._lines):
                line = self._lines[row]
                self._lines[row] = line[:col] + text + line[col:]
                self._add_undo_entry(UndoEntry("insert", row, col, text))
                self._modified = True
                self._redo_stack.clear()
                return (row, col + len(text))
        else:
            # Multi-line insertion
            if 0 <= row < len(self._lines):
                original_line = self._lines[row]
                before = original_line[:col]
                after = original_line[col:]

                # First line
                self._lines[row] = before + lines[0]

                # Middle lines
                for i, line in enumerate(lines[1:-1], 1):
                    self._lines.insert(row + i, line)

                # Last line
                last_row = row + len(lines) - 1
                self._lines.insert(last_row, lines[-1] + after)

                self._add_undo_entry(UndoEntry("insert", row, col, text))
                self._modified = True
                self._redo_stack.clear()

                return (last_row, len(lines[-1]))

        return (row, col)

    def delete_char(self, row: int, col: int) -> Optional[str]:
        """Delete a character at position.

        Args:
            row: Row position.
            col: Column position.

        Returns:
            Deleted character or None.
        """
        if 0 <= row < len(self._lines):
            line = self._lines[row]
            if 0 <= col < len(line):
                deleted = line[col]
                self._lines[row] = line[:col] + line[col + 1 :]
                self._add_undo_entry(UndoEntry("delete", row, col, deleted))
                self._modified = True
                self._redo_stack.clear()
                return deleted
        return None

    def delete_range(self, start_row: int, start_col: int, end_row: int, end_col: int) -> str:
        """Delete a range of text.

        Args:
            start_row: Starting row.
            start_col: Starting column.
            end_row: Ending row.
            end_col: Ending column.

        Returns:
            Deleted text.
        """
        if start_row == end_row:
            # Single line deletion
            if 0 <= start_row < len(self._lines):
                line = self._lines[start_row]
                deleted = line[start_col:end_col]
                self._lines[start_row] = line[:start_col] + line[end_col:]
                self._add_undo_entry(UndoEntry("delete", start_row, start_col, deleted))
                self._modified = True
                self._redo_stack.clear()
                return deleted
        else:
            # Multi-line deletion
            deleted_lines = []

            # First line
            if 0 <= start_row < len(self._lines):
                first_line = self._lines[start_row]
                deleted_lines.append(first_line[start_col:])

                # Middle lines
                for row in range(start_row + 1, min(end_row, len(self._lines))):
                    deleted_lines.append(self._lines[row])

                # Last line
                if end_row < len(self._lines):
                    last_line = self._lines[end_row]
                    deleted_lines.append(last_line[:end_col])

                    # Combine first and last line remnants
                    self._lines[start_row] = first_line[:start_col] + last_line[end_col:]

                    # Delete middle lines
                    for _ in range(end_row - start_row):
                        if start_row + 1 < len(self._lines):
                            del self._lines[start_row + 1]

                deleted = "\n".join(deleted_lines)
                self._add_undo_entry(UndoEntry("delete", start_row, start_col, deleted))
                self._modified = True
                self._redo_stack.clear()
                return deleted

        return ""

    def insert_line(self, row: int, text: str = "") -> None:
        """Insert a new line.

        Args:
            row: Row position to insert at.
            text: Initial text for the line.
        """
        self._lines.insert(row, text)
        self._add_undo_entry(UndoEntry("insert", row, 0, text + "\n"))
        self._modified = True
        self._redo_stack.clear()

    def delete_line(self, row: int) -> Optional[str]:
        """Delete an entire line.

        Args:
            row: Row to delete.

        Returns:
            Deleted line text or None.
        """
        if 0 <= row < len(self._lines):
            deleted = self._lines[row]
            del self._lines[row]
            if not self._lines:  # Keep at least one line
                self._lines.append("")
            self._add_undo_entry(UndoEntry("delete", row, 0, deleted + "\n"))
            self._modified = True
            self._redo_stack.clear()
            return deleted
        return None

    def replace_line(self, row: int, text: str) -> None:
        """Replace an entire line.

        Args:
            row: Row to replace.
            text: New text for the line.
        """
        if 0 <= row < len(self._lines):
            old_text = self._lines[row]
            self._lines[row] = text
            self._add_undo_entry(UndoEntry("replace", row, 0, text, old_text))
            self._modified = True
            self._redo_stack.clear()

    def undo(self) -> Optional[tuple[int, int]]:
        """Undo the last operation.

        Returns:
            Cursor position to restore or None.
        """
        if not self._undo_stack:
            return None

        entry = self._undo_stack.pop()

        if entry.operation == "insert":
            # Undo insertion by deleting
            if "\n" in entry.text:
                # Multi-line insertion
                lines = entry.text.split("\n")
                for i in range(len(lines) - 1):
                    if entry.row < len(self._lines):
                        del self._lines[entry.row]
            else:
                # Single character/line insertion
                line = self._lines[entry.row]
                self._lines[entry.row] = line[: entry.col] + line[entry.col + len(entry.text) :]

        elif entry.operation == "delete":
            # Undo deletion by inserting
            if "\n" in entry.text:
                # Multi-line deletion
                lines = entry.text.split("\n")
                original_line = self._lines[entry.row]
                before = original_line[: entry.col]
                after = original_line[entry.col :]

                self._lines[entry.row] = before + lines[0]
                for i, line in enumerate(lines[1:], 1):
                    self._lines.insert(entry.row + i, line)
                self._lines[entry.row + len(lines) - 1] += after
            else:
                # Single character deletion
                line = self._lines[entry.row]
                self._lines[entry.row] = line[: entry.col] + entry.text + line[entry.col :]

        elif entry.operation == "replace":
            # Undo replacement
            if entry.old_text is not None:
                self._lines[entry.row] = entry.old_text

        self._redo_stack.append(entry)
        self._modified = True
        return (entry.row, entry.col)

    def redo(self) -> Optional[tuple[int, int]]:
        """Redo the last undone operation.

        Returns:
            Cursor position to restore or None.
        """
        if not self._redo_stack:
            return None

        entry = self._redo_stack.pop()

        if entry.operation == "insert":
            # Redo insertion
            if "\n" in entry.text:
                lines = entry.text.split("\n")
                original_line = self._lines[entry.row]
                before = original_line[: entry.col]
                after = original_line[entry.col :]

                self._lines[entry.row] = before + lines[0]
                for i, line in enumerate(lines[1:], 1):
                    self._lines.insert(entry.row + i, line)
                self._lines[entry.row + len(lines) - 1] += after
            else:
                line = self._lines[entry.row]
                self._lines[entry.row] = line[: entry.col] + entry.text + line[entry.col :]

        elif entry.operation == "delete":
            # Redo deletion
            if "\n" in entry.text:
                lines = entry.text.split("\n")
                for _ in range(len(lines) - 1):
                    if entry.row + 1 < len(self._lines):
                        del self._lines[entry.row + 1]
            else:
                line = self._lines[entry.row]
                self._lines[entry.row] = line[: entry.col] + line[entry.col + len(entry.text) :]

        elif entry.operation == "replace":
            # Redo replacement
            self._lines[entry.row] = entry.text

        self._undo_stack.append(entry)
        self._modified = True
        return (entry.row, entry.col)

    def _add_undo_entry(self, entry: UndoEntry) -> None:
        """Add an entry to the undo stack.

        Args:
            entry: Undo entry to add.
        """
        self._undo_stack.append(entry)

    def set_register(self, register: str, content: str) -> None:
        """Set content of a register.

        Args:
            register: Register name (single character).
            content: Content to store.
        """
        self._registers[register] = content

    def get_register(self, register: str) -> Optional[str]:
        """Get content of a register.

        Args:
            register: Register name.

        Returns:
            Register content or None.
        """
        return self._registers.get(register)

    def set_mark(self, mark: str, row: int, col: int) -> None:
        """Set a mark position.

        Args:
            mark: Mark identifier.
            row: Row position.
            col: Column position.
        """
        self._marks[mark] = (row, col)

    def get_mark(self, mark: str) -> Optional[tuple[int, int]]:
        """Get a mark position.

        Args:
            mark: Mark identifier.

        Returns:
            Position tuple or None.
        """
        return self._marks.get(mark)

    def clear(self) -> None:
        """Clear all buffer content."""
        self._lines = [""]
        self._modified = False
        self._undo_stack.clear()
        self._redo_stack.clear()

    def get_text(self) -> str:
        """Get entire buffer as single string.

        Returns:
            Buffer content as string.
        """
        return "\n".join(self._lines)

    def set_text(self, text: str) -> None:
        """Set entire buffer content.

        Args:
            text: New buffer content.
        """
        self._lines = text.split("\n") if text else [""]
        self._modified = True
        self._undo_stack.clear()
        self._redo_stack.clear()
