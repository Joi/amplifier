"""Tests for motion commands."""

import pytest

from vi_editor.commands.motion import MotionHandler
from vi_editor.core.buffer import Buffer
from vi_editor.core.state import EditorState


@pytest.fixture
def editor_state():
    """Create a basic editor state for testing."""
    state = EditorState()
    return state


@pytest.fixture
def editor_with_text():
    """Create editor with sample text."""
    state = EditorState()
    lines = [
        "hello world",
        "foo bar baz",
        "",
        "test line",
        "another test",
    ]
    state.buffers[0] = Buffer(lines)
    return state


@pytest.fixture
def editor_with_punctuation():
    """Create editor with punctuation for word motion tests."""
    state = EditorState()
    lines = [
        "foo-bar_baz.qux",
        "word1, word2; word3!",
        "test(foo)bar[baz]",
    ]
    state.buffers[0] = Buffer(lines)
    return state


@pytest.fixture
def editor_with_paragraphs():
    """Create editor with paragraphs."""
    state = EditorState()
    lines = [
        "First paragraph line 1.",
        "First paragraph line 2.",
        "",
        "Second paragraph line 1.",
        "Second paragraph line 2.",
        "",
        "",
        "Third paragraph.",
    ]
    state.buffers[0] = Buffer(lines)
    return state


@pytest.fixture
def editor_with_sentences():
    """Create editor with sentences."""
    state = EditorState()
    lines = [
        "First sentence. Second sentence! Third sentence?",
        "Another line. More text.",
    ]
    state.buffers[0] = Buffer(lines)
    return state


@pytest.fixture
def editor_with_brackets():
    """Create editor with matching brackets."""
    state = EditorState()
    lines = [
        "function(arg1, arg2) {",
        "    if (condition) {",
        "        array[index]",
        "    }",
        "}",
    ]
    state.buffers[0] = Buffer(lines)
    return state


class TestBasicMotions:
    """Test basic h/j/k/l motions."""

    def test_move_left(self, editor_state):
        """Test h (left) motion."""
        editor_state.cursor.set_position(0, 5)
        handler = MotionHandler(editor_state)

        row, col = handler.move_left()
        assert (row, col) == (0, 4)

    def test_move_left_with_count(self, editor_state):
        """Test 3h motion."""
        editor_state.cursor.set_position(0, 5)
        handler = MotionHandler(editor_state)

        row, col = handler.move_left(3)
        assert (row, col) == (0, 2)

    def test_move_left_at_boundary(self, editor_state):
        """Test h at start of line."""
        editor_state.cursor.set_position(0, 0)
        handler = MotionHandler(editor_state)

        row, col = handler.move_left()
        assert (row, col) == (0, 0)

    def test_move_right(self, editor_with_text):
        """Test l (right) motion."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_right()
        assert (row, col) == (0, 1)

    def test_move_right_with_count(self, editor_with_text):
        """Test 3l motion."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_right(3)
        assert (row, col) == (0, 3)

    def test_move_right_at_boundary(self, editor_with_text):
        """Test l at end of line (normal mode)."""
        editor_with_text.cursor.set_position(0, 10)  # "hello world" = 11 chars, max is 10
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_right()
        assert (row, col) == (0, 10)

    def test_move_down(self, editor_with_text):
        """Test j (down) motion."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_down()
        assert row == 1

    def test_move_down_with_count(self, editor_with_text):
        """Test 3j motion."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_down(3)
        assert row == 3

    def test_move_down_at_boundary(self, editor_with_text):
        """Test j at last line."""
        editor_with_text.cursor.set_position(4, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_down()
        assert row == 4

    def test_move_up(self, editor_with_text):
        """Test k (up) motion."""
        editor_with_text.cursor.set_position(3, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_up()
        assert row == 2

    def test_move_up_with_count(self, editor_with_text):
        """Test 3k motion."""
        editor_with_text.cursor.set_position(4, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_up(3)
        assert row == 1

    def test_move_up_at_boundary(self, editor_with_text):
        """Test k at first line."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_up()
        assert row == 0


class TestWordMotions:
    """Test w/b/e word motions."""

    def test_word_forward_basic(self, editor_with_text):
        """Test w motion basic case."""
        editor_with_text.cursor.set_position(0, 0)  # "hello world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_word_forward()
        assert (row, col) == (0, 6)  # Start of "world"

    def test_word_forward_with_count(self, editor_with_text):
        """Test 2w motion."""
        editor_with_text.cursor.set_position(0, 0)  # "hello world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_word_forward(2)
        assert row == 1  # Moved to next line

    def test_word_forward_across_lines(self, editor_with_text):
        """Test w crossing line boundaries."""
        editor_with_text.cursor.set_position(0, 6)  # "world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_word_forward()
        assert row == 1  # Next line
        assert col == 0  # Start of "foo"

    def test_word_forward_with_punctuation(self, editor_with_punctuation):
        """Test w with punctuation (treats as separate words)."""
        editor_with_punctuation.cursor.set_position(0, 0)  # "foo-bar_baz.qux"
        handler = MotionHandler(editor_with_punctuation)

        # w should move to "-"
        row, col = handler.move_word_forward()
        assert (row, col) == (0, 3)  # At "-"

    def test_WORD_forward_basic(self, editor_with_punctuation):
        """Test W motion (whitespace-separated)."""
        editor_with_punctuation.cursor.set_position(0, 0)  # "foo-bar_baz.qux"
        handler = MotionHandler(editor_with_punctuation)

        row, col = handler.move_WORD_forward()
        # W skips entire WORD including punctuation
        assert row == 1  # Next line

    def test_word_backward_basic(self, editor_with_text):
        """Test b motion basic case."""
        editor_with_text.cursor.set_position(0, 6)  # "world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_word_backward()
        assert (row, col) == (0, 0)  # Start of "hello"

    def test_word_backward_with_count(self, editor_with_text):
        """Test 2b motion."""
        editor_with_text.cursor.set_position(1, 8)  # "foo bar baz"
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_word_backward(2)
        assert (row, col) == (1, 0)  # Start of "foo"

    def test_word_backward_across_lines(self, editor_with_text):
        """Test b crossing line boundaries."""
        editor_with_text.cursor.set_position(1, 0)  # Start of line 2
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_word_backward()
        assert row == 0  # Previous line
        assert col == 6  # Start of "world"

    def test_WORD_backward_basic(self, editor_with_punctuation):
        """Test B motion (whitespace-separated)."""
        editor_with_punctuation.cursor.set_position(1, 7)  # "word1, word2; word3!"
        handler = MotionHandler(editor_with_punctuation)

        row, col = handler.move_WORD_backward()
        assert col == 0  # Start of line

    def test_word_end_basic(self, editor_with_text):
        """Test e motion basic case."""
        editor_with_text.cursor.set_position(0, 0)  # "hello world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_word_end()
        assert (row, col) == (0, 4)  # End of "hello"

    def test_word_end_with_count(self, editor_with_text):
        """Test 2e motion."""
        editor_with_text.cursor.set_position(0, 0)  # "hello world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_word_end(2)
        assert (row, col) == (0, 10)  # End of "world"

    def test_word_end_across_lines(self, editor_with_text):
        """Test e crossing line boundaries."""
        editor_with_text.cursor.set_position(0, 10)  # End of "world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_word_end()
        assert row == 1  # Next line
        assert col == 2  # End of "foo"

    def test_WORD_end_basic(self, editor_with_punctuation):
        """Test E motion (whitespace-separated)."""
        editor_with_punctuation.cursor.set_position(0, 0)  # "foo-bar_baz.qux"
        handler = MotionHandler(editor_with_punctuation)

        row, col = handler.move_WORD_end()
        assert col == 14  # End of entire WORD


class TestLineMotions:
    """Test 0/^/$ line motions."""

    def test_line_start(self, editor_with_text):
        """Test 0 motion."""
        editor_with_text.cursor.set_position(0, 5)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_line_start()
        assert (row, col) == (0, 0)

    def test_first_non_blank(self, editor_state):
        """Test ^ motion."""
        editor_state.buffers[0] = Buffer(["    indented line"])
        editor_state.cursor.set_position(0, 10)
        handler = MotionHandler(editor_state)

        row, col = handler.move_first_non_blank()
        assert (row, col) == (0, 4)  # First non-space char

    def test_first_non_blank_all_spaces(self, editor_state):
        """Test ^ on line with only spaces."""
        editor_state.buffers[0] = Buffer(["     "])
        editor_state.cursor.set_position(0, 3)
        handler = MotionHandler(editor_state)

        row, col = handler.move_first_non_blank()
        assert (row, col) == (0, 0)  # Stays at start

    def test_line_end(self, editor_with_text):
        """Test $ motion."""
        editor_with_text.cursor.set_position(0, 0)  # "hello world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_line_end()
        assert (row, col) == (0, 10)  # Last char

    def test_line_end_with_count(self, editor_with_text):
        """Test 2$ motion (move to end of next line)."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_line_end(2)
        assert row == 1  # Second line
        assert col == 10  # End of "foo bar baz"


class TestParagraphMotions:
    """Test { and } paragraph motions."""

    def test_paragraph_forward(self, editor_with_paragraphs):
        """Test } motion."""
        editor_with_paragraphs.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_paragraphs)

        row, col = handler.move_paragraph_forward()
        assert row == 2  # Blank line after first paragraph

    def test_paragraph_forward_with_count(self, editor_with_paragraphs):
        """Test 2} motion."""
        editor_with_paragraphs.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_paragraphs)

        row, col = handler.move_paragraph_forward(2)
        assert row == 5  # Blank line after second paragraph

    def test_paragraph_backward(self, editor_with_paragraphs):
        """Test { motion."""
        editor_with_paragraphs.cursor.set_position(4, 0)
        handler = MotionHandler(editor_with_paragraphs)

        row, col = handler.move_paragraph_backward()
        assert row == 3  # Start of second paragraph

    def test_paragraph_backward_with_count(self, editor_with_paragraphs):
        """Test 2{ motion."""
        editor_with_paragraphs.cursor.set_position(7, 0)
        handler = MotionHandler(editor_with_paragraphs)

        row, col = handler.move_paragraph_backward(2)
        assert row == 3  # Start of second paragraph


class TestSentenceMotions:
    """Test ( and ) sentence motions."""

    def test_sentence_forward(self, editor_with_sentences):
        """Test ) motion."""
        editor_with_sentences.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_sentences)

        row, col = handler.move_sentence_forward()
        assert col == 16  # After "First sentence. "

    def test_sentence_forward_with_count(self, editor_with_sentences):
        """Test 2) motion."""
        editor_with_sentences.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_sentences)

        row, col = handler.move_sentence_forward(2)
        assert col == 36  # After "Second sentence! "

    def test_sentence_backward(self, editor_with_sentences):
        """Test ( motion."""
        editor_with_sentences.cursor.set_position(0, 30)
        handler = MotionHandler(editor_with_sentences)

        row, col = handler.move_sentence_backward()
        assert col == 16  # After previous sentence end


class TestCharacterSearch:
    """Test f/F/t/T character search motions."""

    def test_find_char_forward(self, editor_with_text):
        """Test f motion."""
        editor_with_text.cursor.set_position(0, 0)  # "hello world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.find_char_forward(1, "w")
        assert (row, col) == (0, 6)

    def test_find_char_forward_with_count(self, editor_with_text):
        """Test 2fl motion."""
        editor_with_text.cursor.set_position(0, 0)  # "hello world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.find_char_forward(2, "l")
        assert (row, col) == (0, 3)  # Second 'l'

    def test_find_char_forward_not_found(self, editor_with_text):
        """Test f when character not found."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.find_char_forward(1, "z")
        assert (row, col) == (0, 0)  # Stays at current position

    def test_find_char_backward(self, editor_with_text):
        """Test F motion."""
        editor_with_text.cursor.set_position(0, 10)  # "hello world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.find_char_backward(1, "o")
        assert (row, col) == (0, 7)  # 'o' in "world"

    def test_till_char_forward(self, editor_with_text):
        """Test t motion."""
        editor_with_text.cursor.set_position(0, 0)  # "hello world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.till_char_forward(1, "w")
        assert (row, col) == (0, 5)  # One before 'w'

    def test_till_char_backward(self, editor_with_text):
        """Test T motion."""
        editor_with_text.cursor.set_position(0, 10)  # "hello world"
        handler = MotionHandler(editor_with_text)

        row, col = handler.till_char_backward(1, "h")
        assert (row, col) == (0, 1)  # One after 'h'

    def test_repeat_char_search(self, editor_with_text):
        """Test ; motion (repeat last search)."""
        editor_with_text.cursor.set_position(0, 0)  # "hello world"
        handler = MotionHandler(editor_with_text)

        # First search
        handler.find_char_forward(1, "l")
        # Repeat
        row, col = handler.repeat_char_search()
        assert (row, col) == (0, 3)  # Next 'l'

    def test_reverse_char_search(self, editor_with_text):
        """Test , motion (reverse last search)."""
        editor_with_text.cursor.set_position(0, 0)  # "hello world"
        handler = MotionHandler(editor_with_text)

        # Forward search
        handler.find_char_forward(1, "l")
        assert editor_with_text.cursor.col == 2
        # Reverse
        row, col = handler.reverse_char_search()
        assert col < 2  # Moved backward


class TestBracketMatching:
    """Test % bracket matching motion."""

    def test_matching_parentheses(self, editor_with_brackets):
        """Test % on opening paren."""
        editor_with_brackets.cursor.set_position(0, 8)  # "function("
        handler = MotionHandler(editor_with_brackets)

        row, col = handler.move_matching_bracket()
        assert (row, col) == (0, 18)  # Closing paren

    def test_matching_braces(self, editor_with_brackets):
        """Test % on opening brace."""
        editor_with_brackets.cursor.set_position(0, 20)  # "{"
        handler = MotionHandler(editor_with_brackets)

        row, col = handler.move_matching_bracket()
        assert (row, col) == (4, 0)  # Closing brace

    def test_matching_brackets(self, editor_with_brackets):
        """Test % on square brackets."""
        editor_with_brackets.cursor.set_position(2, 13)  # "array["
        handler = MotionHandler(editor_with_brackets)

        row, col = handler.move_matching_bracket()
        assert (row, col) == (2, 19)  # Closing bracket

    def test_matching_backward(self, editor_with_brackets):
        """Test % on closing bracket."""
        editor_with_brackets.cursor.set_position(4, 0)  # "}"
        handler = MotionHandler(editor_with_brackets)

        row, col = handler.move_matching_bracket()
        assert (row, col) == (0, 20)  # Opening brace

    def test_matching_nested(self, editor_with_brackets):
        """Test % with nested brackets."""
        editor_with_brackets.cursor.set_position(1, 7)  # Inner "("
        handler = MotionHandler(editor_with_brackets)

        row, col = handler.move_matching_bracket()
        assert (row, col) == (1, 17)  # Matching closing paren


class TestJumpMotions:
    """Test gg/G/H/M/L jump motions."""

    def test_goto_first_line(self, editor_with_text):
        """Test gg motion."""
        editor_with_text.cursor.set_position(3, 5)
        handler = MotionHandler(editor_with_text)

        row, col = handler.handle_g_motion("g", 1)
        assert row == 0

    def test_goto_line(self, editor_with_text):
        """Test 3G motion."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_to_line(3)
        assert row == 2  # 3rd line (0-indexed)

    def test_goto_last_line(self, editor_with_text):
        """Test G motion (no count)."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_to_line(None)
        assert row == 4  # Last line

    def test_goto_line_beyond_buffer(self, editor_with_text):
        """Test 100G motion (beyond buffer)."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_to_line(100)
        assert row == 4  # Last line


class TestSearchMotions:
    """Test * and # search motions."""

    def test_search_word_forward(self, editor_state):
        """Test * motion."""
        editor_state.buffers[0] = Buffer(
            [
                "hello world",
                "hello again",
                "goodbye hello",
            ]
        )
        editor_state.cursor.set_position(0, 0)  # On "hello"
        handler = MotionHandler(editor_state)

        row, col = handler.search_word_forward()
        assert row == 1  # Next "hello"
        assert col == 0

    def test_search_word_backward(self, editor_state):
        """Test # motion."""
        editor_state.buffers[0] = Buffer(
            [
                "hello world",
                "hello again",
                "goodbye hello",
            ]
        )
        editor_state.cursor.set_position(1, 0)  # On second "hello"
        handler = MotionHandler(editor_state)

        row, col = handler.search_word_backward()
        assert row == 0  # First "hello"
        assert col == 0

    def test_search_word_forward_with_count(self, editor_state):
        """Test 2* motion."""
        editor_state.buffers[0] = Buffer(
            [
                "test word",
                "test again",
                "test more",
            ]
        )
        editor_state.cursor.set_position(0, 0)  # On "test"
        handler = MotionHandler(editor_state)

        row, col = handler.search_word_forward(2)
        assert row == 2  # Third occurrence


class TestMotionWithEmptyLines:
    """Test motions on empty or nearly-empty lines."""

    def test_word_forward_on_empty_line(self, editor_with_text):
        """Test w motion on empty line."""
        editor_with_text.cursor.set_position(2, 0)  # Empty line
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_word_forward()
        assert row == 3  # Moves to next line with content

    def test_line_end_on_empty_line(self, editor_with_text):
        """Test $ on empty line."""
        editor_with_text.cursor.set_position(2, 0)  # Empty line
        handler = MotionHandler(editor_with_text)

        row, col = handler.move_line_end()
        assert (row, col) == (2, 0)  # Stays at position 0


class TestMotionEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_motion_at_end_of_buffer(self, editor_with_text):
        """Test motions at end of buffer."""
        editor_with_text.cursor.set_position(4, 10)
        handler = MotionHandler(editor_with_text)

        # Try to move down - should stay
        row, col = handler.move_down()
        assert row == 4

        # Try to move word forward - should handle gracefully
        row, col = handler.move_word_forward()
        assert row == 4

    def test_motion_on_single_char_line(self, editor_state):
        """Test motions on single character line."""
        editor_state.buffers[0] = Buffer(["a"])
        editor_state.cursor.set_position(0, 0)
        handler = MotionHandler(editor_state)

        # Word forward should not crash
        row, col = handler.move_word_forward()
        assert row == 0

    def test_count_overflow(self, editor_with_text):
        """Test very large count."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        # 1000j should stop at last line
        row, col = handler.move_down(1000)
        assert row == 4

    def test_word_motion_whitespace_only(self, editor_state):
        """Test word motion on line with only whitespace."""
        editor_state.buffers[0] = Buffer(["     ", "word"])
        editor_state.cursor.set_position(0, 0)
        handler = MotionHandler(editor_state)

        row, col = handler.move_word_forward()
        assert row == 1  # Moves to next line


class TestMotionExecuteInterface:
    """Test the execute_motion interface."""

    def test_execute_motion_basic(self, editor_with_text):
        """Test execute_motion with basic motion."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        result = handler.execute_motion("w")
        assert result is not None
        assert result[0] == 0
        assert result[1] == 6  # Start of "world"

    def test_execute_motion_with_count(self, editor_with_text):
        """Test execute_motion with count."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        result = handler.execute_motion("l", count=3)
        assert result == (0, 3)

    def test_execute_motion_with_arg(self, editor_with_text):
        """Test execute_motion with argument (f/t commands)."""
        editor_with_text.cursor.set_position(0, 0)
        handler = MotionHandler(editor_with_text)

        result = handler.execute_motion("f", count=1, arg="w")
        assert result == (0, 6)

    def test_execute_motion_g_prefix(self, editor_with_text):
        """Test execute_motion with g prefix."""
        editor_with_text.cursor.set_position(3, 5)
        handler = MotionHandler(editor_with_text)

        result = handler.execute_motion("g", count=1, arg="g")
        assert result[0] == 0  # First line

    def test_execute_motion_invalid(self, editor_with_text):
        """Test execute_motion with invalid motion."""
        handler = MotionHandler(editor_with_text)

        result = handler.execute_motion("@")
        assert result is None
