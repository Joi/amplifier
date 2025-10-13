"""Tests for ex commands."""

from vi_editor.commands.ex import ExCommand, ExCommandHandler
from vi_editor.core.buffer import Buffer
from vi_editor.core.state import EditorState
from vi_editor.file_ops.file_handler import FileHandler


class TestExCommandParsing:
    """Test ex command parsing."""

    def test_parse_simple_command(self):
        """Test parsing simple command without arguments."""
        cmd = ExCommand("w")
        assert cmd.command == "w"
        assert cmd.args == []
        assert cmd.range_start is None
        assert cmd.range_end is None

    def test_parse_command_with_args(self):
        """Test parsing command with arguments."""
        cmd = ExCommand("w testfile.txt")
        assert cmd.command == "w"
        assert cmd.args == ["testfile.txt"]

    def test_parse_command_with_line_range(self):
        """Test parsing command with line range."""
        cmd = ExCommand("1,5d")
        assert cmd.command == "d"
        assert cmd.range_start == 1
        assert cmd.range_end == 5

    def test_parse_command_with_current_line(self):
        """Test parsing command with current line marker."""
        cmd = ExCommand(".s/old/new/")
        assert cmd.command == "s/old/new/"
        assert cmd.range_start == "current"

    def test_parse_command_with_last_line(self):
        """Test parsing command with last line marker."""
        cmd = ExCommand("$d")
        assert cmd.command == "$d"
        assert cmd.range_start is None

    def test_parse_global_substitute(self):
        """Test parsing global substitute command."""
        cmd = ExCommand("%s/old/new/g")
        assert cmd.raw == "%s/old/new/g"


class TestFileCommands:
    """Test file-related ex commands."""

    def test_write_with_filename(self, tmp_path):
        """Test writing buffer to file."""
        state = EditorState()
        state.current_buffer.insert_line(0, "Hello World")
        file_handler = FileHandler()
        handler = ExCommandHandler(state, file_handler)

        filename = tmp_path / "test.txt"
        result = handler.execute(f"w {filename}")

        assert result is True
        assert filename.exists()
        assert filename.read_text() == "Hello World\n"

    def test_write_without_filename(self, tmp_path):
        """Test writing buffer without specifying filename."""
        state = EditorState()
        buffer = Buffer(["Test content"])
        buffer.set_filename(str(tmp_path / "test.txt"))
        state.buffers[0] = buffer
        file_handler = FileHandler()
        handler = ExCommandHandler(state, file_handler)

        result = handler.execute("w")

        assert result is True
        assert (tmp_path / "test.txt").exists()

    def test_write_no_filename_error(self):
        """Test writing without filename when buffer has none."""
        state = EditorState()
        file_handler = FileHandler()
        handler = ExCommandHandler(state, file_handler)

        result = handler.execute("w")

        assert result is False
        assert state.status_message is not None
        assert "No file name" in state.status_message.text

    def test_quit_clean_buffer(self):
        """Test quitting with unmodified buffer."""
        state = EditorState()
        handler = ExCommandHandler(state)

        result = handler.execute("q")

        assert result == "quit"

    def test_quit_modified_buffer_fails(self):
        """Test quitting with modified buffer fails without force."""
        state = EditorState()
        state.current_buffer.insert_char(0, 0, "x")
        handler = ExCommandHandler(state)

        result = handler.execute("q")

        assert result is False
        assert state.status_message is not None
        assert "No write since last change" in state.status_message.text

    def test_force_quit(self):
        """Test force quit without saving."""
        state = EditorState()
        state.current_buffer.insert_char(0, 0, "x")
        handler = ExCommandHandler(state)

        result = handler.execute("q!")

        assert result == "quit"

    def test_write_and_quit(self, tmp_path):
        """Test writing and quitting."""
        state = EditorState()
        buffer = Buffer(["Content"])
        buffer.set_filename(str(tmp_path / "test.txt"))
        state.buffers[0] = buffer
        file_handler = FileHandler()
        handler = ExCommandHandler(state, file_handler)

        result = handler.execute("wq")

        assert result == "quit"
        assert (tmp_path / "test.txt").exists()

    def test_read_file(self, tmp_path):
        """Test reading file into buffer."""
        # Create test file
        test_file = tmp_path / "input.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3")

        state = EditorState()
        file_handler = FileHandler()
        handler = ExCommandHandler(state, file_handler)

        result = handler.execute(f"r {test_file}")

        assert result is True
        assert state.current_buffer.line_count == 4  # Original empty line + 3 read lines
        assert state.current_buffer.get_line(1) == "Line 1"


class TestSubstituteCommands:
    """Test substitute commands."""

    def test_substitute_command_variations(self):
        """Test that substitute command is parsed correctly."""
        cmd = ExCommand("s/World/Python/")
        # The entire substitute pattern is treated as the command
        assert "s/" in cmd.command or cmd.command.startswith("s")

    def test_range_substitute_parsing(self):
        """Test range parsing for substitute."""
        cmd = ExCommand("1,3s/old/new/g")
        assert cmd.range_start == 1
        assert cmd.range_end == 3
        # Command includes pattern since there's no space separator
        assert "s" in cmd.command


class TestDeleteCommands:
    """Test delete commands."""

    def test_delete_current_line(self):
        """Test deleting current line."""
        state = EditorState()
        state.current_buffer.insert_line(0, "Line 1")
        state.current_buffer.insert_line(1, "Line 2")
        state.current_buffer.insert_line(2, "Line 3")
        handler = ExCommandHandler(state)

        result = handler.execute("d")

        assert result is True
        assert state.current_buffer.line_count == 3  # Includes original empty line

    def test_delete_range(self):
        """Test deleting line range."""
        state = EditorState()
        state.current_buffer.insert_line(0, "Line 1")
        state.current_buffer.insert_line(1, "Line 2")
        state.current_buffer.insert_line(2, "Line 3")
        state.current_buffer.insert_line(3, "Line 4")
        handler = ExCommandHandler(state)

        result = handler.execute("1,3d")

        assert result is True
        assert state.current_buffer.line_count == 2


class TestYankPutCommands:
    """Test yank and put commands."""

    def test_yank_current_line(self):
        """Test yanking current line."""
        state = EditorState()
        state.current_buffer.insert_line(0, "Test Line")
        handler = ExCommandHandler(state)

        result = handler.execute("y")

        assert result is True
        assert "Test Line\n" in state.current_buffer.get_register('"')

    def test_yank_range(self):
        """Test yanking line range."""
        state = EditorState()
        state.current_buffer.insert_line(0, "Line 1")
        state.current_buffer.insert_line(1, "Line 2")
        state.current_buffer.insert_line(2, "Line 3")
        handler = ExCommandHandler(state)

        result = handler.execute("1,2y")

        assert result is True
        content = state.current_buffer.get_register('"')
        assert "Line 1" in content
        assert "Line 2" in content

    def test_put_lines(self):
        """Test putting yanked lines."""
        state = EditorState()
        state.current_buffer.set_register('"', "Pasted Line\n")
        handler = ExCommandHandler(state)

        result = handler.execute("put")

        assert result is True
        assert state.current_buffer.get_line(1) == "Pasted Line"


class TestBufferCommands:
    """Test buffer management commands."""

    def test_next_buffer(self):
        """Test switching to next buffer."""
        state = EditorState()
        state.add_buffer(Buffer(["Buffer 2"]))
        handler = ExCommandHandler(state)

        result = handler.execute("bn")

        assert result is True
        assert state.current_buffer_index == 1

    def test_prev_buffer(self):
        """Test switching to previous buffer."""
        state = EditorState()
        state.add_buffer(Buffer(["Buffer 2"]))
        state.switch_buffer(1)
        handler = ExCommandHandler(state)

        result = handler.execute("bp")

        assert result is True
        assert state.current_buffer_index == 0

    def test_delete_buffer(self):
        """Test deleting current buffer."""
        state = EditorState()
        state.add_buffer(Buffer(["Buffer 2"]))
        handler = ExCommandHandler(state)

        result = handler.execute("bd")

        assert result is True
        assert len(state.buffers) == 1

    def test_list_buffers(self):
        """Test listing all buffers."""
        state = EditorState()
        state.add_buffer(Buffer(["Buffer 2"]))
        handler = ExCommandHandler(state)

        result = handler.execute("ls")

        assert result is True
        assert state.status_message is not None


class TestInfoCommands:
    """Test information commands."""

    def test_list_marks(self):
        """Test listing marks."""
        state = EditorState()
        state.current_buffer.set_mark("a", 0, 5)
        handler = ExCommandHandler(state)

        result = handler.execute("marks")

        assert result is True
        assert state.status_message is not None

    def test_list_registers(self):
        """Test listing registers."""
        state = EditorState()
        state.current_buffer.set_register('"', "test content")
        handler = ExCommandHandler(state)

        result = handler.execute("registers")

        assert result is True

    def test_show_help(self):
        """Test showing help."""
        state = EditorState()
        handler = ExCommandHandler(state)

        result = handler.execute("help")

        assert result is True
        assert state.status_message is not None
        assert "Commands" in state.status_message.text or "movement" in state.status_message.text.lower()

    def test_show_version(self):
        """Test showing version."""
        state = EditorState()
        handler = ExCommandHandler(state)

        result = handler.execute("version")

        assert result is True
        assert state.status_message is not None
        assert "Vi Editor" in state.status_message.text


class TestSetCommands:
    """Test set option commands."""

    def test_set_boolean_option(self):
        """Test setting boolean option."""
        state = EditorState()
        handler = ExCommandHandler(state)

        result = handler.execute("set number")

        assert result is True

    def test_set_option_with_value(self):
        """Test setting option with value."""
        state = EditorState()
        handler = ExCommandHandler(state)

        result = handler.execute("set tabstop=4")

        assert result is True

    def test_unset_boolean_option(self):
        """Test unsetting boolean option."""
        state = EditorState()
        handler = ExCommandHandler(state)

        result = handler.execute("set nonumber")

        assert result is True


class TestCommandAbbreviations:
    """Test command abbreviations."""

    def test_quit_abbreviation(self):
        """Test 'q' as abbreviation for 'quit'."""
        state = EditorState()
        handler = ExCommandHandler(state)

        result = handler.execute("quit")

        assert result == "quit"

    def test_write_abbreviation(self, tmp_path):
        """Test 'w' as abbreviation for 'write'."""
        state = EditorState()
        buffer = Buffer(["content"])
        buffer.set_filename(str(tmp_path / "test.txt"))
        state.buffers[0] = buffer
        file_handler = FileHandler()
        handler = ExCommandHandler(state, file_handler)

        result = handler.execute("write")

        assert result is True


class TestErrorHandling:
    """Test error handling in ex commands."""

    def test_unknown_command(self):
        """Test executing unknown command."""
        state = EditorState()
        handler = ExCommandHandler(state)

        result = handler.execute("unknowncmd")

        assert result is False
        assert state.status_message is not None
        assert "Unknown command" in state.status_message.text

    def test_empty_command(self):
        """Test executing empty command."""
        state = EditorState()
        handler = ExCommandHandler(state)

        result = handler.execute("")

        assert result is False

    def test_invalid_substitution_syntax(self):
        """Test invalid substitution syntax."""
        state = EditorState()
        handler = ExCommandHandler(state)

        result = handler.execute("s")

        assert result is False
