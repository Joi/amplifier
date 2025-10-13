"""Tests for the buffer module."""

from vi_editor.core.buffer import Buffer


class TestBuffer:
    """Test cases for Buffer class."""

    def test_create_empty_buffer(self):
        """Test creating an empty buffer."""
        buffer = Buffer()
        assert buffer.line_count == 1
        assert buffer.get_line(0) == ""
        assert not buffer.modified

    def test_create_buffer_with_content(self):
        """Test creating a buffer with initial content."""
        lines = ["Hello", "World", "Test"]
        buffer = Buffer(lines)
        assert buffer.line_count == 3
        assert buffer.get_line(0) == "Hello"
        assert buffer.get_line(1) == "World"
        assert buffer.get_line(2) == "Test"

    def test_insert_char(self):
        """Test inserting a character."""
        buffer = Buffer(["Hello"])
        buffer.insert_char(0, 5, "!")
        assert buffer.get_line(0) == "Hello!"
        assert buffer.modified

    def test_delete_char(self):
        """Test deleting a character."""
        buffer = Buffer(["Hello"])
        deleted = buffer.delete_char(0, 4)
        assert deleted == "o"
        assert buffer.get_line(0) == "Hell"
        assert buffer.modified

    def test_insert_line(self):
        """Test inserting a new line."""
        buffer = Buffer(["Line 1", "Line 3"])
        buffer.insert_line(1, "Line 2")
        assert buffer.line_count == 3
        assert buffer.get_line(0) == "Line 1"
        assert buffer.get_line(1) == "Line 2"
        assert buffer.get_line(2) == "Line 3"

    def test_delete_line(self):
        """Test deleting a line."""
        buffer = Buffer(["Line 1", "Line 2", "Line 3"])
        deleted = buffer.delete_line(1)
        assert deleted == "Line 2"
        assert buffer.line_count == 2
        assert buffer.get_line(0) == "Line 1"
        assert buffer.get_line(1) == "Line 3"

    def test_undo(self):
        """Test undo operation."""
        buffer = Buffer(["Hello"])
        buffer.insert_char(0, 5, "!")
        assert buffer.get_line(0) == "Hello!"

        pos = buffer.undo()
        assert pos == (0, 5)
        assert buffer.get_line(0) == "Hello"

    def test_redo(self):
        """Test redo operation."""
        buffer = Buffer(["Hello"])
        buffer.insert_char(0, 5, "!")
        buffer.undo()

        pos = buffer.redo()
        assert pos == (0, 5)
        assert buffer.get_line(0) == "Hello!"

    def test_registers(self):
        """Test register operations."""
        buffer = Buffer()
        buffer.set_register('"', "test content")
        assert buffer.get_register('"') == "test content"
        assert buffer.get_register("x") is None

    def test_marks(self):
        """Test mark operations."""
        buffer = Buffer()
        buffer.set_mark("a", 5, 10)
        mark = buffer.get_mark("a")
        assert mark == (5, 10)
        assert buffer.get_mark("b") is None
