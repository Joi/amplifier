"""Cursor management for vi editor."""

from typing import Optional


class Cursor:
    """Manages cursor position and movement."""

    def __init__(self, row: int = 0, col: int = 0):
        """Initialize the cursor.

        Args:
            row: Initial row position.
            col: Initial column position.
        """
        self._row = row
        self._col = col
        self._desired_col = col  # For vertical movement
        self._mark_positions: dict[str, tuple[int, int]] = {}

    @property
    def row(self) -> int:
        """Get current row."""
        return self._row

    @property
    def col(self) -> int:
        """Get current column."""
        return self._col

    @property
    def position(self) -> tuple[int, int]:
        """Get current position as tuple."""
        return (self._row, self._col)

    def set_position(self, row: int, col: int) -> None:
        """Set cursor position.

        Args:
            row: Row to move to.
            col: Column to move to.
        """
        self._row = max(0, row)
        self._col = max(0, col)
        self._desired_col = self._col

    def move_to(self, row: int, col: int) -> None:
        """Move cursor to specific position.

        Args:
            row: Target row.
            col: Target column.
        """
        self.set_position(row, col)

    def move_up(self, count: int = 1) -> None:
        """Move cursor up by count lines.

        Args:
            count: Number of lines to move up.
        """
        self._row = max(0, self._row - count)

    def move_down(self, count: int = 1, max_row: int = None) -> None:
        """Move cursor down by count lines.

        Args:
            count: Number of lines to move down.
            max_row: Maximum row limit.
        """
        new_row = self._row + count
        if max_row is not None:
            new_row = min(new_row, max_row)
        self._row = new_row

    def move_left(self, count: int = 1) -> None:
        """Move cursor left by count columns.

        Args:
            count: Number of columns to move left.
        """
        self._col = max(0, self._col - count)
        self._desired_col = self._col

    def move_right(self, count: int = 1, max_col: int = None) -> None:
        """Move cursor right by count columns.

        Args:
            count: Number of columns to move right.
            max_col: Maximum column limit.
        """
        new_col = self._col + count
        if max_col is not None:
            new_col = min(new_col, max_col)
        self._col = new_col
        self._desired_col = self._col

    def move_to_line_start(self) -> None:
        """Move cursor to start of current line."""
        self._col = 0
        self._desired_col = 0

    def move_to_line_end(self, line_length: int) -> None:
        """Move cursor to end of current line.

        Args:
            line_length: Length of the current line.
        """
        self._col = max(0, line_length - 1)
        self._desired_col = self._col

    def move_to_first_non_blank(self, line: str) -> None:
        """Move to first non-blank character in line.

        Args:
            line: The current line text.
        """
        for i, char in enumerate(line):
            if not char.isspace():
                self._col = i
                self._desired_col = i
                return
        # If all spaces, stay at beginning
        self._col = 0
        self._desired_col = 0

    def adjust_column_for_line(self, line_length: int) -> None:
        """Adjust column position for current line length.

        Args:
            line_length: Length of the current line.
        """
        if line_length == 0:
            self._col = 0
        else:
            # Try to maintain desired column for vertical movement
            self._col = min(self._desired_col, line_length - 1)

    def set_mark(self, mark: str) -> None:
        """Set a mark at current position.

        Args:
            mark: Mark identifier (single character).
        """
        self._mark_positions[mark] = (self._row, self._col)

    def get_mark(self, mark: str) -> Optional[tuple[int, int]]:
        """Get position of a mark.

        Args:
            mark: Mark identifier.

        Returns:
            Position tuple or None if mark not set.
        """
        return self._mark_positions.get(mark)

    def jump_to_mark(self, mark: str) -> bool:
        """Jump to a previously set mark.

        Args:
            mark: Mark identifier.

        Returns:
            True if mark exists and jump successful, False otherwise.
        """
        position = self.get_mark(mark)
        if position:
            self._row, self._col = position
            self._desired_col = self._col
            return True
        return False

    def clear_marks(self) -> None:
        """Clear all marks."""
        self._mark_positions.clear()
