"""Tests for the cursor module."""

from vi_editor.core.cursor import Cursor


class TestCursor:
    """Test cases for Cursor class."""

    def test_create_cursor(self):
        """Test creating a cursor."""
        cursor = Cursor()
        assert cursor.row == 0
        assert cursor.col == 0
        assert cursor.position == (0, 0)

    def test_set_position(self):
        """Test setting cursor position."""
        cursor = Cursor()
        cursor.set_position(5, 10)
        assert cursor.row == 5
        assert cursor.col == 10
        assert cursor.position == (5, 10)

    def test_move_up(self):
        """Test moving cursor up."""
        cursor = Cursor(5, 10)
        cursor.move_up(2)
        assert cursor.row == 3
        assert cursor.col == 10

        # Test boundary
        cursor.move_up(10)
        assert cursor.row == 0

    def test_move_down(self):
        """Test moving cursor down."""
        cursor = Cursor(5, 10)
        cursor.move_down(3)
        assert cursor.row == 8

        # Test with max_row
        cursor.move_down(5, max_row=10)
        assert cursor.row == 10

    def test_move_left(self):
        """Test moving cursor left."""
        cursor = Cursor(5, 10)
        cursor.move_left(5)
        assert cursor.col == 5

        # Test boundary
        cursor.move_left(10)
        assert cursor.col == 0

    def test_move_right(self):
        """Test moving cursor right."""
        cursor = Cursor(5, 10)
        cursor.move_right(5)
        assert cursor.col == 15

        # Test with max_col
        cursor.move_right(10, max_col=20)
        assert cursor.col == 20

    def test_move_to_line_start(self):
        """Test moving to line start."""
        cursor = Cursor(5, 10)
        cursor.move_to_line_start()
        assert cursor.col == 0

    def test_move_to_line_end(self):
        """Test moving to line end."""
        cursor = Cursor(5, 10)
        cursor.move_to_line_end(25)
        assert cursor.col == 24  # 0-indexed

    def test_marks(self):
        """Test mark operations."""
        cursor = Cursor()
        cursor.set_position(5, 10)
        cursor.set_mark("a")

        cursor.set_position(10, 20)
        assert cursor.position == (10, 20)

        # Jump back to mark
        success = cursor.jump_to_mark("a")
        assert success
        assert cursor.position == (5, 10)

        # Test non-existent mark
        success = cursor.jump_to_mark("z")
        assert not success
