"""Tests for normal mode operators."""

import pytest

from vi_editor.commands.motion import MotionHandler
from vi_editor.commands.normal import NormalCommandHandler
from vi_editor.core.buffer import Buffer
from vi_editor.core.mode import Mode
from vi_editor.core.state import EditorState


@pytest.fixture
def state():
    """Create a fresh editor state for each test."""
    return EditorState()


@pytest.fixture
def motion_handler(state):
    """Create a motion handler."""
    return MotionHandler(state)


@pytest.fixture
def normal_handler(state, motion_handler):
    """Create a normal command handler."""
    return NormalCommandHandler(state, motion_handler)


class TestDeleteOperator:
    """Test delete operator (d)."""

    def test_delete_word_dw(self, state, normal_handler, motion_handler):
        """Test dw deletes word forward."""
        state.buffers[0] = Buffer(["hello world test"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("d")
        normal_handler.handle_command("w")

        assert state.current_buffer.get_line(0) == "world test"
        assert state.current_buffer.get_register('"') == "hello "

    def test_delete_word_with_count_d3w(self, state, normal_handler):
        """Test d3w deletes three words."""
        state.buffers[0] = Buffer(["one two three four five"])
        state.cursor.set_position(0, 0)

        state.append_count("3")
        normal_handler.handle_command("d")
        normal_handler.handle_command("w")

        assert state.current_buffer.get_line(0) == "four five"

    def test_delete_to_end_of_line_d_dollar(self, state, normal_handler):
        """Test d$ deletes to end of line."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 6)

        normal_handler.handle_command("d")
        normal_handler.handle_command("$")

        assert state.current_buffer.get_line(0) == "hello "
        assert state.current_buffer.get_register('"') == "world"

    def test_delete_to_line_start_d0(self, state, normal_handler):
        """Test d0 deletes to line start."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 5)

        normal_handler.handle_command("d")
        normal_handler.handle_command("0")

        assert state.current_buffer.get_line(0) == " world"
        assert state.current_buffer.get_register('"') == "hello"

    def test_delete_backward_word_db(self, state, normal_handler):
        """Test db deletes backward word."""
        state.buffers[0] = Buffer(["hello world test"])
        state.cursor.set_position(0, 12)

        normal_handler.handle_command("d")
        normal_handler.handle_command("b")

        assert state.current_buffer.get_line(0) == "hello test"

    def test_delete_line_dd(self, state, normal_handler):
        """Test dd deletes entire line."""
        state.buffers[0] = Buffer(["line 1", "line 2", "line 3"])
        state.cursor.set_position(1, 0)

        normal_handler.handle_command("d")
        normal_handler.handle_command("d")

        assert state.current_buffer.line_count == 2
        assert state.current_buffer.get_line(0) == "line 1"
        assert state.current_buffer.get_line(1) == "line 3"
        assert state.current_buffer.get_register('"') == "line 2\n"

    def test_delete_multiple_lines_3dd(self, state, normal_handler):
        """Test 3dd deletes three lines."""
        state.buffers[0] = Buffer(["line 1", "line 2", "line 3", "line 4", "line 5"])
        state.cursor.set_position(1, 0)

        state.append_count("3")
        normal_handler.handle_command("d")
        normal_handler.handle_command("d")

        assert state.current_buffer.line_count == 2
        assert state.current_buffer.get_line(0) == "line 1"
        assert state.current_buffer.get_line(1) == "line 5"

    def test_delete_capital_D(self, state, normal_handler):
        """Test D deletes to end of line."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 6)

        normal_handler.handle_command("D")

        assert state.current_buffer.get_line(0) == "hello "

    def test_delete_at_buffer_end(self, state, normal_handler):
        """Test delete at end of buffer doesn't crash."""
        state.buffers[0] = Buffer(["line 1", "line 2"])
        state.cursor.set_position(1, 0)

        normal_handler.handle_command("d")
        normal_handler.handle_command("w")

        assert state.current_buffer.get_line(1) == "2"

    def test_delete_empty_line(self, state, normal_handler):
        """Test deleting empty line."""
        state.buffers[0] = Buffer(["line 1", "", "line 3"])
        state.cursor.set_position(1, 0)

        normal_handler.handle_command("d")
        normal_handler.handle_command("d")

        assert state.current_buffer.line_count == 2
        assert state.current_buffer.get_line(0) == "line 1"
        assert state.current_buffer.get_line(1) == "line 3"


class TestChangeOperator:
    """Test change operator (c)."""

    def test_change_word_cw(self, state, normal_handler):
        """Test cw changes word and enters insert mode."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("c")
        normal_handler.handle_command("w")

        assert state.current_buffer.get_line(0) == "world"
        assert state.mode_manager.current_mode == Mode.INSERT
        assert state.current_buffer.get_register('"') == "hello "

    def test_change_to_end_c_dollar(self, state, normal_handler):
        """Test c$ changes to end of line."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 6)

        normal_handler.handle_command("c")
        normal_handler.handle_command("$")

        assert state.current_buffer.get_line(0) == "hello "
        assert state.mode_manager.current_mode == Mode.INSERT

    def test_change_line_cc(self, state, normal_handler):
        """Test cc changes entire line."""
        state.buffers[0] = Buffer(["hello world", "line 2"])
        state.cursor.set_position(0, 5)

        normal_handler.handle_command("c")
        normal_handler.handle_command("c")

        assert state.current_buffer.get_line(0) == ""
        assert state.mode_manager.current_mode == Mode.INSERT
        assert state.cursor.position == (0, 0)

    def test_change_multiple_lines_3cc(self, state, normal_handler):
        """Test 3cc changes three lines."""
        state.buffers[0] = Buffer(["line 1", "line 2", "line 3", "line 4"])
        state.cursor.set_position(0, 0)

        state.append_count("3")
        normal_handler.handle_command("c")
        normal_handler.handle_command("c")

        assert state.current_buffer.line_count == 2
        assert state.current_buffer.get_line(0) == ""
        assert state.current_buffer.get_line(1) == "line 4"
        assert state.mode_manager.current_mode == Mode.INSERT

    def test_change_capital_C(self, state, normal_handler):
        """Test C changes to end of line."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 6)

        normal_handler.handle_command("C")

        assert state.current_buffer.get_line(0) == "hello "
        assert state.mode_manager.current_mode == Mode.INSERT

    def test_change_with_count_c3w(self, state, normal_handler):
        """Test c3w changes three words."""
        state.buffers[0] = Buffer(["one two three four"])
        state.cursor.set_position(0, 0)

        state.append_count("3")
        normal_handler.handle_command("c")
        normal_handler.handle_command("w")

        assert state.current_buffer.get_line(0) == "four"
        assert state.mode_manager.current_mode == Mode.INSERT


class TestYankOperator:
    """Test yank operator (y)."""

    def test_yank_word_yw(self, state, normal_handler):
        """Test yw yanks word."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("y")
        normal_handler.handle_command("w")

        assert state.current_buffer.get_line(0) == "hello world"
        assert state.current_buffer.get_register('"') == "hello "
        assert state.mode_manager.current_mode == Mode.NORMAL

    def test_yank_to_end_y_dollar(self, state, normal_handler):
        """Test y$ yanks to end of line."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 6)

        normal_handler.handle_command("y")
        normal_handler.handle_command("$")

        assert state.current_buffer.get_register('"') == "world"

    def test_yank_line_yy(self, state, normal_handler):
        """Test yy yanks entire line."""
        state.buffers[0] = Buffer(["line 1", "line 2"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("y")
        normal_handler.handle_command("y")

        assert state.current_buffer.get_register('"') == "line 1\n"
        assert state.current_buffer.get_register("0") == "line 1\n"

    def test_yank_multiple_lines_3yy(self, state, normal_handler):
        """Test 3yy yanks three lines."""
        state.buffers[0] = Buffer(["line 1", "line 2", "line 3", "line 4"])
        state.cursor.set_position(1, 0)

        state.append_count("3")
        normal_handler.handle_command("y")
        normal_handler.handle_command("y")

        expected = "line 2\nline 3\nline 4\n"
        assert state.current_buffer.get_register('"') == expected
        assert state.cursor.row == 1

    def test_yank_capital_Y(self, state, normal_handler):
        """Test Y yanks entire line (same as yy)."""
        state.buffers[0] = Buffer(["line 1", "line 2"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("Y")

        assert state.current_buffer.get_register('"') == "line 1\n"

    def test_yank_with_motion_y3w(self, state, normal_handler):
        """Test y3w yanks three words."""
        state.buffers[0] = Buffer(["one two three four"])
        state.cursor.set_position(0, 0)

        state.append_count("3")
        normal_handler.handle_command("y")
        normal_handler.handle_command("w")

        assert "one two three " == state.current_buffer.get_register('"')


class TestPutOperator:
    """Test put/paste operators (p, P)."""

    def test_put_after_charwise_p(self, state, normal_handler):
        """Test p pastes after cursor (charwise)."""
        state.buffers[0] = Buffer(["hello world"])
        state.current_buffer.set_register('"', "TEXT")
        state.cursor.set_position(0, 4)

        normal_handler.handle_command("p")

        assert state.current_buffer.get_line(0) == "helloTEXT world"
        assert state.cursor.col == 9

    def test_put_before_charwise_P(self, state, normal_handler):
        """Test P pastes before cursor (charwise)."""
        state.buffers[0] = Buffer(["hello world"])
        state.current_buffer.set_register('"', "TEXT")
        state.cursor.set_position(0, 5)

        normal_handler.handle_command("P")

        assert state.current_buffer.get_line(0) == "helloTEXT world"
        assert state.cursor.col == 5

    def test_put_after_linewise_p(self, state, normal_handler):
        """Test p pastes after line (linewise)."""
        state.buffers[0] = Buffer(["line 1", "line 3"])
        state.current_buffer.set_register('"', "line 2\n")
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("p")

        assert state.current_buffer.line_count == 3
        assert state.current_buffer.get_line(0) == "line 1"
        assert state.current_buffer.get_line(1) == "line 2"
        assert state.current_buffer.get_line(2) == "line 3"

    def test_put_before_linewise_P(self, state, normal_handler):
        """Test P pastes before line (linewise)."""
        state.buffers[0] = Buffer(["line 2", "line 3"])
        state.current_buffer.set_register('"', "line 1\n")
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("P")

        assert state.current_buffer.line_count == 3
        assert state.current_buffer.get_line(0) == "line 1"
        assert state.current_buffer.get_line(1) == "line 2"
        assert state.current_buffer.get_line(2) == "line 3"

    def test_put_with_count_3p(self, state, normal_handler):
        """Test 3p pastes three times."""
        state.buffers[0] = Buffer(["hello"])
        state.current_buffer.set_register('"', "X")
        state.cursor.set_position(0, 4)

        state.append_count("3")
        normal_handler.handle_command("p")

        assert state.current_buffer.get_line(0) == "helloXXX"

    def test_put_empty_register(self, state, normal_handler):
        """Test put with empty register does nothing."""
        state.buffers[0] = Buffer(["hello"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("p")

        assert state.current_buffer.get_line(0) == "hello"

    def test_put_multiline_linewise(self, state, normal_handler):
        """Test putting multiline yanked content."""
        state.buffers[0] = Buffer(["line 1", "line 4"])
        state.current_buffer.set_register('"', "line 2\nline 3\n")
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("p")

        assert state.current_buffer.line_count == 4
        assert state.current_buffer.get_line(0) == "line 1"
        assert state.current_buffer.get_line(1) == "line 2"
        assert state.current_buffer.get_line(2) == "line 3"
        assert state.current_buffer.get_line(3) == "line 4"


class TestUndoRedo:
    """Test undo/redo operators (u, Ctrl-R)."""

    def test_undo_delete_u(self, state, normal_handler):
        """Test u undoes delete."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("d")
        normal_handler.handle_command("w")
        assert state.current_buffer.get_line(0) == "world"

        normal_handler.handle_command("u")
        assert state.current_buffer.get_line(0) == "hello world"

    def test_undo_multiple_times_3u(self, state, normal_handler):
        """Test 3u undoes three times."""
        state.buffers[0] = Buffer(["abc"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("x")
        assert state.current_buffer.get_line(0) == "bc"

        normal_handler.handle_command("x")
        assert state.current_buffer.get_line(0) == "c"

        normal_handler.handle_command("x")
        assert state.current_buffer.get_line(0) == ""

        state.append_count("3")
        normal_handler.handle_command("u")

        assert state.current_buffer.get_line(0) == "abc"

    def test_undo_returns_cursor(self, state, normal_handler):
        """Test undo returns cursor to operation position."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 6)

        normal_handler.handle_command("d")
        normal_handler.handle_command("w")
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("u")

        assert state.cursor.position == (0, 6)

    def test_undo_nothing(self, state, normal_handler):
        """Test undo with nothing to undo."""
        state.buffers[0] = Buffer(["hello"])

        normal_handler.handle_command("u")

        assert state.current_buffer.get_line(0) == "hello"


class TestRepeatCommand:
    """Test repeat command (.)."""

    def test_repeat_delete_dot(self, state, normal_handler):
        """Test . repeats delete command."""
        state.buffers[0] = Buffer(["one two three four"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("d")
        normal_handler.handle_command("w")
        assert state.current_buffer.get_line(0) == "two three four"

        normal_handler.handle_command(".")
        assert state.current_buffer.get_line(0) == "three four"

    def test_repeat_with_count_3_dot(self, state, normal_handler):
        """Test 3. repeats command three times."""
        state.buffers[0] = Buffer(["abcdef"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("x")
        assert state.current_buffer.get_line(0) == "bcdef"

        state.append_count("3")
        normal_handler.handle_command(".")
        assert state.current_buffer.get_line(0) == "ef"

    def test_repeat_change_dot(self, state, normal_handler):
        """Test . repeats change command."""
        state.buffers[0] = Buffer(["one two three"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("c")
        normal_handler.handle_command("w")
        assert state.mode_manager.current_mode == Mode.INSERT

        state.mode_manager.set_mode(Mode.NORMAL)
        state.cursor.set_position(0, 0)

        normal_handler.handle_command(".")
        assert state.mode_manager.current_mode == Mode.INSERT


class TestJoinLines:
    """Test join lines operator (J)."""

    def test_join_lines_J(self, state, normal_handler):
        """Test J joins current and next line."""
        state.buffers[0] = Buffer(["hello", "world"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("J")

        assert state.current_buffer.line_count == 1
        assert state.current_buffer.get_line(0) == "hello world"

    def test_join_multiple_lines_3J(self, state, normal_handler):
        """Test 3J joins three lines."""
        state.buffers[0] = Buffer(["line", "one", "two", "three"])
        state.cursor.set_position(0, 0)

        state.append_count("3")
        normal_handler.handle_command("J")

        assert state.current_buffer.line_count == 2
        assert state.current_buffer.get_line(0) == "line one two"
        assert state.current_buffer.get_line(1) == "three"

    def test_join_with_leading_whitespace(self, state, normal_handler):
        """Test J removes leading whitespace from joined line."""
        state.buffers[0] = Buffer(["hello", "  world"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("J")

        assert state.current_buffer.get_line(0) == "hello world"

    def test_join_at_last_line(self, state, normal_handler):
        """Test J at last line does nothing."""
        state.buffers[0] = Buffer(["line 1", "line 2"])
        state.cursor.set_position(1, 0)

        normal_handler.handle_command("J")

        assert state.current_buffer.line_count == 2


class TestReplaceChar:
    """Test replace character operator (r, R)."""

    def test_replace_single_char_r(self, state, normal_handler):
        """Test r waits for replacement character."""
        state.buffers[0] = Buffer(["hello"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("r")

        assert state.command_buffer == "r"

    def test_enter_replace_mode_R(self, state, normal_handler):
        """Test R enters replace mode."""
        state.buffers[0] = Buffer(["hello"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("R")

        assert state.mode_manager.current_mode == Mode.REPLACE


class TestOperatorEdgeCases:
    """Test operator edge cases."""

    def test_operator_with_backward_motion(self, state, normal_handler):
        """Test operator with backward motion."""
        state.buffers[0] = Buffer(["hello world test"])
        state.cursor.set_position(0, 12)

        normal_handler.handle_command("d")
        normal_handler.handle_command("b")

        assert state.current_buffer.get_line(0) == "hello test"

    def test_operator_at_line_boundaries(self, state, normal_handler):
        """Test operator at line start/end."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("d")
        normal_handler.handle_command("0")

        assert state.current_buffer.get_line(0) == "hello world"

    def test_operator_on_empty_line(self, state, normal_handler):
        """Test operator on empty line."""
        state.buffers[0] = Buffer([""])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("d")
        normal_handler.handle_command("w")

        assert state.current_buffer.get_line(0) == ""

    def test_yank_doesnt_move_cursor(self, state, normal_handler):
        """Test yank doesn't change cursor position."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 6)

        normal_handler.handle_command("y")
        normal_handler.handle_command("w")

        assert state.cursor.position == (0, 6)

    def test_delete_moves_cursor_to_start(self, state, normal_handler):
        """Test delete moves cursor to operation start."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 6)

        normal_handler.handle_command("d")
        normal_handler.handle_command("w")

        assert state.cursor.position == (0, 6)

    def test_invalid_motion_after_operator(self, state, normal_handler):
        """Test invalid motion cancels operator."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("d")
        result = normal_handler.handle_command("z")

        assert result is False
        assert normal_handler.pending_operator is None

    def test_operator_count_and_motion_count(self, state, normal_handler):
        """Test operator count combined with motion count."""
        state.buffers[0] = Buffer(["one two three four five six seven"])
        state.cursor.set_position(0, 0)

        state.append_count("2")
        normal_handler.handle_command("d")
        state.reset_command_state()
        state.append_count("2")
        normal_handler.handle_command("w")

        assert "one two three four " == state.current_buffer.get_register('"')


class TestRegisterIntegration:
    """Test operator integration with registers."""

    def test_delete_stores_in_default_register(self, state, normal_handler):
        """Test delete stores content in default register."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("d")
        normal_handler.handle_command("w")

        assert state.current_buffer.get_register('"') == "hello "

    def test_yank_stores_in_both_registers(self, state, normal_handler):
        """Test yank stores in both unnamed and yank registers."""
        state.buffers[0] = Buffer(["hello"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("y")
        normal_handler.handle_command("y")

        assert state.current_buffer.get_register('"') == "hello\n"
        assert state.current_buffer.get_register("0") == "hello\n"

    def test_delete_overwrites_yank_register(self, state, normal_handler):
        """Test delete overwrites default register but not yank register."""
        state.buffers[0] = Buffer(["hello world"])
        state.cursor.set_position(0, 0)

        normal_handler.handle_command("y")
        normal_handler.handle_command("y")
        yanked = state.current_buffer.get_register("0")

        normal_handler.handle_command("d")
        normal_handler.handle_command("w")

        assert state.current_buffer.get_register('"') == "hello "
        assert state.current_buffer.get_register("0") == yanked
