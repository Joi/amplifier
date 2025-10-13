"""Tests for visual mode commands."""

import pytest

from vi_editor.commands.motion import MotionHandler
from vi_editor.commands.visual import VisualCommandHandler
from vi_editor.core.buffer import Buffer
from vi_editor.core.cursor import Cursor
from vi_editor.core.mode import Mode, ModeManager
from vi_editor.core.state import EditorState


@pytest.fixture
def editor_state():
    """Create a minimal editor state for testing."""
    buffer = Buffer(["Hello World", "Python is great", "Testing visual mode", "Last line"])
    cursor = Cursor(buffer)
    mode_manager = ModeManager()
    state = EditorState()
    # Replace the default buffer with our test buffer
    state.buffers[0] = buffer
    state.cursor = cursor
    state.mode_manager = mode_manager
    return state


@pytest.fixture
def visual_handler(editor_state):
    """Create a visual command handler for testing."""
    motion_handler = MotionHandler(editor_state)
    return VisualCommandHandler(editor_state, motion_handler)


class TestVisualModeEntry:
    """Test entering visual mode."""

    def test_enter_visual_mode(self, visual_handler, editor_state):
        """Test entering character-wise visual mode."""
        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        assert editor_state.mode_manager.current_mode == Mode.VISUAL
        assert visual_handler.visual_start == (0, 0)
        selection = editor_state.mode_manager.get_visual_selection()
        assert selection == ((0, 0), (0, 0))

    def test_enter_visual_mode_from_middle(self, visual_handler, editor_state):
        """Test entering visual mode from cursor position."""
        editor_state.cursor.set_position(1, 7)
        visual_handler.enter_visual_mode()

        assert visual_handler.visual_start == (1, 7)
        selection = editor_state.mode_manager.get_visual_selection()
        assert selection == ((1, 7), (1, 7))

    def test_exit_visual_mode_with_escape(self, visual_handler, editor_state):
        """Test exiting visual mode with escape."""
        visual_handler.enter_visual_mode()
        result = visual_handler.handle_command("\x1b")

        assert result is True
        assert editor_state.mode_manager.current_mode == Mode.NORMAL
        assert visual_handler.visual_start is None

    def test_exit_visual_mode_with_v(self, visual_handler, editor_state):
        """Test toggling visual mode off with v."""
        visual_handler.enter_visual_mode()
        result = visual_handler.handle_command("v")

        assert result is True
        assert editor_state.mode_manager.current_mode == Mode.NORMAL
        assert visual_handler.visual_start is None


class TestVisualSelection:
    """Test visual selection operations."""

    def test_selection_with_motion_right(self, visual_handler, editor_state):
        """Test extending selection with motion."""
        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        # Move right 5 characters
        for _ in range(5):
            visual_handler.handle_command("l")

        selection = visual_handler.get_selection_range()
        assert selection == ((0, 0), (0, 5))

    def test_selection_with_motion_down(self, visual_handler, editor_state):
        """Test multi-line selection."""
        editor_state.cursor.set_position(0, 5)
        visual_handler.enter_visual_mode()

        # Move down 2 lines
        visual_handler.handle_command("j")
        visual_handler.handle_command("j")

        selection = visual_handler.get_selection_range()
        assert selection[0] == (0, 5)
        assert selection[1][0] == 2  # Row 2

    def test_selection_range_normalization(self, visual_handler, editor_state):
        """Test that selection range is normalized (start before end)."""
        # Start at (2, 5) and move back to (1, 3)
        editor_state.cursor.set_position(2, 5)
        visual_handler.enter_visual_mode()

        # Move up and left
        visual_handler.handle_command("k")
        visual_handler.handle_command("h")
        visual_handler.handle_command("h")

        selection = visual_handler.get_selection_range()
        start, end = selection
        # Verify start comes before end
        assert start[0] < end[0] or (start[0] == end[0] and start[1] <= end[1])

    def test_update_visual_selection(self, visual_handler, editor_state):
        """Test that selection updates as cursor moves."""
        editor_state.cursor.set_position(1, 0)
        visual_handler.enter_visual_mode()

        # Move and update selection
        editor_state.cursor.set_position(1, 10)
        visual_handler.update_visual_selection()

        selection = editor_state.mode_manager.get_visual_selection()
        assert selection == ((1, 0), (1, 10))


class TestVisualDelete:
    """Test deletion operations in visual mode."""

    def test_delete_single_line_selection(self, visual_handler, editor_state):
        """Test deleting a character selection on one line."""
        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        # Select "Hello"
        for _ in range(4):
            visual_handler.handle_command("l")

        visual_handler.handle_command("d")

        assert editor_state.current_buffer.get_line(0) == " World"
        assert editor_state.mode_manager.current_mode == Mode.NORMAL
        assert editor_state.cursor.position == (0, 0)

    def test_delete_multi_line_selection(self, visual_handler, editor_state):
        """Test deleting across multiple lines."""
        editor_state.cursor.set_position(0, 6)  # "World"
        visual_handler.enter_visual_mode()

        # Select to next line
        visual_handler.handle_command("j")
        for _ in range(5):
            visual_handler.handle_command("l")

        visual_handler.handle_command("d")

        # Deleting "World\nPython is gr" leaves "Hello " + "eat" = "Hello eat"
        assert editor_state.current_buffer.get_line(0) == "Hello eat"
        assert editor_state.mode_manager.current_mode == Mode.NORMAL

    def test_delete_stores_in_register(self, visual_handler, editor_state):
        """Test that deleted text is stored in register."""
        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        # Select "Hello"
        for _ in range(4):
            visual_handler.handle_command("l")

        visual_handler.handle_command("d")

        register_content = editor_state.current_buffer.get_register('"')
        assert register_content == "Hello"

    def test_delete_visual_line_mode(self, visual_handler, editor_state):
        """Test deleting in visual line mode."""
        editor_state.cursor.set_position(1, 5)
        editor_state.mode_manager.set_mode(Mode.VISUAL_LINE)
        visual_handler.visual_start = (1, 0)
        editor_state.mode_manager.set_visual_selection((1, 0), (2, 0))

        visual_handler.delete_selection()

        # Lines 1 and 2 should be deleted
        assert editor_state.current_buffer.line_count == 2
        assert editor_state.current_buffer.get_line(0) == "Hello World"
        assert editor_state.current_buffer.get_line(1) == "Last line"


class TestVisualChange:
    """Test change operation in visual mode."""

    def test_change_enters_insert_mode(self, visual_handler, editor_state):
        """Test that change operation enters insert mode."""
        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        # Select "Hello"
        for _ in range(4):
            visual_handler.handle_command("l")

        visual_handler.handle_command("c")

        assert editor_state.mode_manager.current_mode == Mode.INSERT
        assert editor_state.current_buffer.get_line(0) == " World"

    def test_change_deletes_selection(self, visual_handler, editor_state):
        """Test that change deletes the selected text."""
        editor_state.cursor.set_position(1, 0)
        visual_handler.enter_visual_mode()

        # Select "Python"
        for _ in range(5):
            visual_handler.handle_command("l")

        visual_handler.handle_command("c")

        assert editor_state.current_buffer.get_line(1) == " is great"
        register_content = editor_state.current_buffer.get_register('"')
        assert register_content == "Python"


class TestVisualYank:
    """Test yank operation in visual mode."""

    def test_yank_single_line(self, visual_handler, editor_state):
        """Test yanking a single line selection."""
        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        # Select "Hello"
        for _ in range(4):
            visual_handler.handle_command("l")

        visual_handler.handle_command("y")

        # Text should remain
        assert editor_state.current_buffer.get_line(0) == "Hello World"
        # Should be in register
        assert editor_state.current_buffer.get_register('"') == "Hello"
        assert editor_state.current_buffer.get_register("0") == "Hello"
        # Should exit visual mode
        assert editor_state.mode_manager.current_mode == Mode.NORMAL

    def test_yank_multi_line(self, visual_handler, editor_state):
        """Test yanking across multiple lines."""
        editor_state.cursor.set_position(0, 6)  # Start at "World"
        visual_handler.enter_visual_mode()

        # Select down to next line
        visual_handler.handle_command("j")
        for _ in range(5):
            visual_handler.handle_command("l")

        visual_handler.handle_command("y")

        # Text should remain unchanged
        assert editor_state.current_buffer.get_line(0) == "Hello World"
        assert editor_state.current_buffer.get_line(1) == "Python is great"

        # Check register content
        register_content = editor_state.current_buffer.get_register('"')
        assert "World" in register_content
        assert "Python" in register_content

    def test_yank_visual_line_mode(self, visual_handler, editor_state):
        """Test yanking in visual line mode."""
        editor_state.cursor.set_position(1, 5)
        editor_state.mode_manager.set_mode(Mode.VISUAL_LINE)
        visual_handler.visual_start = (1, 0)
        editor_state.mode_manager.set_visual_selection((1, 0), (2, 0))

        visual_handler.yank_selection()

        # Lines should remain
        assert editor_state.current_buffer.get_line(1) == "Python is great"
        assert editor_state.current_buffer.get_line(2) == "Testing visual mode"

        # Register should contain both lines with newline
        register_content = editor_state.current_buffer.get_register('"')
        assert "Python is great\nTesting visual mode\n" == register_content


class TestVisualIndent:
    """Test indent operations in visual mode."""

    def test_indent_single_line(self, visual_handler, editor_state):
        """Test indenting a single line."""
        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        visual_handler.handle_command(">")

        assert editor_state.current_buffer.get_line(0) == "    Hello World"
        assert editor_state.mode_manager.current_mode == Mode.NORMAL

    def test_indent_multiple_lines(self, visual_handler, editor_state):
        """Test indenting multiple lines."""
        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        # Select down two lines
        visual_handler.handle_command("j")
        visual_handler.handle_command("j")

        visual_handler.handle_command(">")

        assert editor_state.current_buffer.get_line(0) == "    Hello World"
        assert editor_state.current_buffer.get_line(1) == "    Python is great"
        assert editor_state.current_buffer.get_line(2) == "    Testing visual mode"

    def test_outdent_single_line(self, visual_handler, editor_state):
        """Test outdenting a single line."""
        # Add indentation first
        editor_state.current_buffer.replace_line(0, "    Hello World")

        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        visual_handler.handle_command("<")

        assert editor_state.current_buffer.get_line(0) == "Hello World"
        assert editor_state.mode_manager.current_mode == Mode.NORMAL

    def test_outdent_multiple_lines(self, visual_handler, editor_state):
        """Test outdenting multiple lines."""
        # Add indentation
        editor_state.current_buffer.replace_line(0, "    Hello World")
        editor_state.current_buffer.replace_line(1, "    Python is great")
        editor_state.current_buffer.replace_line(2, "    Testing visual mode")

        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        visual_handler.handle_command("j")
        visual_handler.handle_command("j")

        visual_handler.handle_command("<")

        assert editor_state.current_buffer.get_line(0) == "Hello World"
        assert editor_state.current_buffer.get_line(1) == "Python is great"
        assert editor_state.current_buffer.get_line(2) == "Testing visual mode"

    def test_outdent_tab_character(self, visual_handler, editor_state):
        """Test outdenting with tab character."""
        editor_state.current_buffer.replace_line(0, "\tHello World")

        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        visual_handler.handle_command("<")

        assert editor_state.current_buffer.get_line(0) == "Hello World"


class TestVisualCaseToggle:
    """Test case toggle operations in visual mode."""

    def test_toggle_case_single_line(self, visual_handler, editor_state):
        """Test toggling case on single line."""
        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        # Select "Hello"
        for _ in range(4):
            visual_handler.handle_command("l")

        visual_handler.handle_command("~")

        assert editor_state.current_buffer.get_line(0) == "hELLO World"
        assert editor_state.mode_manager.current_mode == Mode.NORMAL

    def test_toggle_case_multi_line(self, visual_handler, editor_state):
        """Test toggling case across multiple lines."""
        editor_state.cursor.set_position(0, 6)  # Start at "World"
        visual_handler.enter_visual_mode()

        # Select to next line
        visual_handler.handle_command("j")
        for _ in range(5):
            visual_handler.handle_command("l")

        visual_handler.handle_command("~")

        # "World" -> "wORLD", "Python" -> "pYTHON"
        line0 = editor_state.current_buffer.get_line(0)
        line1 = editor_state.current_buffer.get_line(1)

        assert "wORLD" in line0
        assert "pYTHON" in line1

    def test_toggle_case_visual_line_mode(self, visual_handler, editor_state):
        """Test toggling case in visual line mode."""
        editor_state.cursor.set_position(0, 3)
        editor_state.mode_manager.set_mode(Mode.VISUAL_LINE)
        visual_handler.visual_start = (0, 0)
        editor_state.mode_manager.set_visual_selection((0, 0), (1, 0))

        visual_handler.toggle_case_selection()

        assert editor_state.current_buffer.get_line(0) == "hELLO wORLD"
        assert editor_state.current_buffer.get_line(1) == "pYTHON IS GREAT"

    def test_toggle_case_mixed_content(self, visual_handler, editor_state):
        """Test toggling case with numbers and spaces."""
        editor_state.current_buffer.replace_line(0, "Test 123 Code")
        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()

        # Select entire line
        for _ in range(12):
            visual_handler.handle_command("l")

        visual_handler.handle_command("~")

        # Numbers and spaces unchanged, letters toggled
        assert editor_state.current_buffer.get_line(0) == "tEST 123 cODE"


class TestVisualEdgeCases:
    """Test edge cases in visual mode."""

    def test_selection_on_empty_line(self, visual_handler, editor_state):
        """Test handling empty line in selection."""
        editor_state.current_buffer.insert_line(2, "")  # Insert empty line
        editor_state.cursor.set_position(1, 0)
        visual_handler.enter_visual_mode()

        # Select through empty line
        visual_handler.handle_command("j")
        visual_handler.handle_command("j")

        selection = visual_handler.get_selection_range()
        assert selection is not None
        assert selection[0][0] == 1
        assert selection[1][0] == 3

    def test_visual_operation_at_end_of_buffer(self, visual_handler, editor_state):
        """Test visual operation at the last line."""
        last_line = editor_state.current_buffer.line_count - 1
        editor_state.cursor.set_position(last_line, 0)
        visual_handler.enter_visual_mode()

        # Select to end of line
        line_length = len(editor_state.current_buffer.get_line(last_line))
        for _ in range(line_length - 1):
            visual_handler.handle_command("l")

        visual_handler.handle_command("y")

        assert editor_state.current_buffer.get_register('"') == "Last line"

    def test_no_selection_returns_none(self, visual_handler, editor_state):
        """Test that get_selection_range returns None with no selection."""
        # Don't enter visual mode
        selection = visual_handler.get_selection_range()
        assert selection is None

    def test_delete_at_buffer_end(self, visual_handler, editor_state):
        """Test deleting selection at end of buffer."""
        last_line = editor_state.current_buffer.line_count - 1
        editor_state.cursor.set_position(last_line, 0)
        visual_handler.enter_visual_mode()

        for _ in range(3):
            visual_handler.handle_command("l")

        visual_handler.handle_command("d")

        # Should handle cursor position properly
        assert editor_state.cursor.position[0] == last_line

    def test_yank_then_delete(self, visual_handler, editor_state):
        """Test that yank and delete work sequentially."""
        # Yank "Hello"
        editor_state.cursor.set_position(0, 0)
        visual_handler.enter_visual_mode()
        for _ in range(4):
            visual_handler.handle_command("l")
        visual_handler.handle_command("y")

        yanked = editor_state.current_buffer.get_register("0")

        # Delete "World"
        editor_state.cursor.set_position(0, 6)
        visual_handler.enter_visual_mode()
        for _ in range(4):
            visual_handler.handle_command("l")
        visual_handler.handle_command("d")

        # Yank register "0" should still have "Hello"
        assert yanked == "Hello"
        # Delete register '"' should have "World"
        assert editor_state.current_buffer.get_register('"') == "World"
