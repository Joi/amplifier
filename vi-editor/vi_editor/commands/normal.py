"""Normal mode commands for vi editor."""

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class NormalCommand:
    """Represents a normal mode command."""

    command: str
    count: int = 1
    register: Optional[str] = None
    motion: Optional[str] = None


class NormalCommandHandler:
    """Handles normal mode commands."""

    def __init__(self, state, motion_handler):
        """Initialize normal command handler.

        Args:
            state: EditorState instance.
            motion_handler: MotionHandler instance.
        """
        self.state = state
        self.motion_handler = motion_handler
        self.commands = self._init_commands()
        self.pending_operator = None
        self.operator_count = 1

    def _init_commands(self) -> dict[str, Callable]:
        """Initialize normal mode command mappings."""
        return {
            # Mode changes
            "i": self.enter_insert_mode,
            "I": self.enter_insert_mode_start,
            "a": self.enter_insert_mode_after,
            "A": self.enter_insert_mode_end,
            "o": self.open_line_below,
            "O": self.open_line_above,
            "v": self.enter_visual_mode,
            "V": self.enter_visual_line_mode,
            ":": self.enter_command_mode,
            "R": self.enter_replace_mode,
            # Editing
            "x": self.delete_char,
            "X": self.delete_char_before,
            "s": self.substitute_char,
            "S": self.substitute_line,
            "r": self.replace_char,
            "J": self.join_lines,
            "~": self.toggle_case,
            # Operators
            "d": self.delete_operator,
            "c": self.change_operator,
            "y": self.yank_operator,
            ">": self.indent_operator,
            "<": self.outdent_operator,
            "=": self.format_operator,
            # Line operations
            "dd": self.delete_line,
            "cc": self.change_line,
            "yy": self.yank_line,
            "D": self.delete_to_end,
            "C": self.change_to_end,
            "Y": self.yank_line,
            # Put/Paste
            "p": self.put_after,
            "P": self.put_before,
            # Undo/Redo
            "u": self.undo,
            ".": self.repeat_last,
            # Marks
            "m": self.set_mark,
            "'": self.jump_to_mark_line,
            "`": self.jump_to_mark,
            # Macros
            "q": self.toggle_macro_recording,
            "@": self.play_macro,
            # Search
            "/": self.search_forward,
            "?": self.search_backward,
            "n": self.next_match,
            "N": self.prev_match,
            "*": self.search_word,
            "#": self.search_word_backward,
        }

    def handle_command(self, key: str) -> bool:
        """Handle a normal mode command.

        Args:
            key: The key pressed.

        Returns:
            True if command was handled, False otherwise.
        """
        # Handle count prefix
        if key.isdigit() and key != "0":
            self.state.append_count(key)
            return True
        elif key == "0" and self.state.count_prefix:
            self.state.append_count(key)
            return True

        count = self.state.get_count()

        # Handle pending operator
        if self.pending_operator:
            return self._handle_operator_motion(key, count)

        # Check for operator commands
        if key in ["d", "c", "y", ">", "<", "="]:
            self.pending_operator = key
            self.operator_count = count
            self.state.reset_command_state()
            return True

        # Check for motion commands
        if key in self.motion_handler.motions:
            self.motion_handler.execute_motion(key, count)
            self.state.reset_command_state()
            return True

        # Check for normal commands
        if key in self.commands:
            handler = self.commands[key]
            handler(count)
            self.state.last_command = key
            self.state.reset_command_state()
            return True

        # Check for two-character commands
        combined = self.state.command_buffer + key
        if combined in self.commands:
            handler = self.commands[combined]
            handler(count)
            self.state.last_command = combined
            self.state.reset_command_state()
            return True

        # Build command buffer
        self.state.command_buffer += key

        # Check if buffer could be start of a command
        for cmd in self.commands:
            if cmd.startswith(self.state.command_buffer):
                return True  # Wait for more input

        # Invalid command
        self.state.reset_command_state()
        self.pending_operator = None
        return False

    def _handle_operator_motion(self, key: str, count: int) -> bool:
        """Handle motion after an operator.

        Args:
            key: Motion key.
            count: Motion count.

        Returns:
            True if handled, False otherwise.
        """
        operator = self.pending_operator
        op_count = self.operator_count

        # Handle operator duplication (dd, cc, yy)
        if key == operator:
            if operator == "d":
                self.delete_line(op_count)
            elif operator == "c":
                self.change_line(op_count)
            elif operator == "y":
                self.yank_line(op_count)
            elif operator == ">":
                self.indent_lines(op_count)
            elif operator == "<":
                self.outdent_lines(op_count)

            self.pending_operator = None
            self.state.reset_command_state()
            return True

        # Handle motion
        if key in self.motion_handler.motions:
            start_pos = self.state.cursor.position
            end_pos = self.motion_handler.execute_motion(key, count)

            if end_pos:
                self._apply_operator(operator, start_pos, end_pos, op_count)

            self.pending_operator = None
            self.state.reset_command_state()
            return True

        # Invalid motion
        self.pending_operator = None
        self.state.reset_command_state()
        return False

    def _apply_operator(self, operator: str, start: tuple[int, int], end: tuple[int, int], count: int) -> None:
        """Apply an operator to a range.

        Args:
            operator: The operator character.
            start: Start position.
            end: End position.
            count: Operator count.
        """
        # Ensure start comes before end
        if start[0] > end[0] or (start[0] == end[0] and start[1] > end[1]):
            start, end = end, start

        buffer = self.state.current_buffer

        if operator == "d":
            # Delete range
            text = buffer.delete_range(start[0], start[1], end[0], end[1])
            buffer.set_register('"', text)
            self.state.cursor.set_position(start[0], start[1])

        elif operator == "c":
            # Change range
            text = buffer.delete_range(start[0], start[1], end[0], end[1])
            buffer.set_register('"', text)
            self.state.cursor.set_position(start[0], start[1])
            self.state.mode_manager.set_mode(self.state.mode_manager.Mode.INSERT)

        elif operator == "y":
            # Yank range
            if start[0] == end[0]:
                text = buffer.get_line(start[0])[start[1] : end[1]]
            else:
                lines = []
                lines.append(buffer.get_line(start[0])[start[1] :])
                for row in range(start[0] + 1, end[0]):
                    lines.append(buffer.get_line(row))
                lines.append(buffer.get_line(end[0])[: end[1]])
                text = "\n".join(lines)
            buffer.set_register('"', text)

        elif operator == ">":
            # Indent range
            for row in range(start[0], end[0] + 1):
                line = buffer.get_line(row)
                buffer.replace_line(row, "    " + line)

        elif operator == "<":
            # Outdent range
            for row in range(start[0], end[0] + 1):
                line = buffer.get_line(row)
                if line.startswith("    "):
                    buffer.replace_line(row, line[4:])
                elif line.startswith("\t"):
                    buffer.replace_line(row, line[1:])

    # Mode change commands
    def enter_insert_mode(self, count: int = 1) -> None:
        """Enter insert mode at cursor."""
        from vi_editor.core.mode import Mode

        self.state.mode_manager.set_mode(Mode.INSERT)

    def enter_insert_mode_start(self, count: int = 1) -> None:
        """Enter insert mode at start of line."""
        from vi_editor.core.mode import Mode

        self.state.cursor.move_to_first_non_blank(self.state.current_buffer.get_line(self.state.cursor.row))
        self.state.mode_manager.set_mode(Mode.INSERT)

    def enter_insert_mode_after(self, count: int = 1) -> None:
        """Enter insert mode after cursor."""
        from vi_editor.core.mode import Mode

        line_len = self.state.current_buffer.get_line_length(self.state.cursor.row)
        if self.state.cursor.col < line_len:
            self.state.cursor.move_right(1, line_len)
        self.state.mode_manager.set_mode(Mode.INSERT)

    def enter_insert_mode_end(self, count: int = 1) -> None:
        """Enter insert mode at end of line."""
        from vi_editor.core.mode import Mode

        line_len = self.state.current_buffer.get_line_length(self.state.cursor.row)
        self.state.cursor.move_to_line_end(line_len)
        if line_len > 0:
            self.state.cursor.move_right(1, line_len)
        self.state.mode_manager.set_mode(Mode.INSERT)

    def open_line_below(self, count: int = 1) -> None:
        """Open new line below and enter insert mode."""
        from vi_editor.core.mode import Mode

        buffer = self.state.current_buffer
        cursor = self.state.cursor

        for _ in range(count):
            buffer.insert_line(cursor.row + 1, "")

        cursor.move_down(1, buffer.line_count - 1)
        cursor.move_to_line_start()
        self.state.mode_manager.set_mode(Mode.INSERT)

    def open_line_above(self, count: int = 1) -> None:
        """Open new line above and enter insert mode."""
        from vi_editor.core.mode import Mode

        buffer = self.state.current_buffer
        cursor = self.state.cursor

        for _ in range(count):
            buffer.insert_line(cursor.row, "")

        cursor.move_to_line_start()
        self.state.mode_manager.set_mode(Mode.INSERT)

    def enter_visual_mode(self, count: int = 1) -> None:
        """Enter visual mode."""
        from vi_editor.core.mode import Mode

        self.state.mode_manager.set_mode(Mode.VISUAL)
        self.state.mode_manager.set_visual_selection(self.state.cursor.position, self.state.cursor.position)

    def enter_visual_line_mode(self, count: int = 1) -> None:
        """Enter visual line mode."""
        from vi_editor.core.mode import Mode

        self.state.mode_manager.set_mode(Mode.VISUAL_LINE)
        self.state.mode_manager.set_visual_selection(
            (self.state.cursor.row, 0),
            (self.state.cursor.row, self.state.current_buffer.get_line_length(self.state.cursor.row)),
        )

    def enter_command_mode(self, count: int = 1) -> None:
        """Enter command mode."""
        from vi_editor.core.mode import Mode

        self.state.mode_manager.set_mode(Mode.COMMAND)
        self.state.command_buffer = ":"

    def enter_replace_mode(self, count: int = 1) -> None:
        """Enter replace mode."""
        from vi_editor.core.mode import Mode

        self.state.mode_manager.set_mode(Mode.REPLACE)

    # Editing commands
    def delete_char(self, count: int = 1) -> None:
        """Delete character at cursor."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        deleted = ""
        for _ in range(count):
            char = buffer.delete_char(cursor.row, cursor.col)
            if char:
                deleted += char

        if deleted:
            buffer.set_register('"', deleted)

        # Adjust cursor if at end of line
        line_len = buffer.get_line_length(cursor.row)
        if cursor.col >= line_len and line_len > 0:
            cursor.set_position(cursor.row, line_len - 1)

    def delete_char_before(self, count: int = 1) -> None:
        """Delete character before cursor."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        deleted = ""
        for _ in range(count):
            if cursor.col > 0:
                cursor.move_left()
                char = buffer.delete_char(cursor.row, cursor.col)
                if char:
                    deleted = char + deleted

        if deleted:
            buffer.set_register('"', deleted)

    def substitute_char(self, count: int = 1) -> None:
        """Substitute character at cursor."""
        self.delete_char(count)
        self.enter_insert_mode()

    def substitute_line(self, count: int = 1) -> None:
        """Substitute entire line."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        # Delete line content but keep the line
        line = buffer.get_line(cursor.row)
        buffer.replace_line(cursor.row, "")
        buffer.set_register('"', line)

        cursor.move_to_line_start()
        self.enter_insert_mode()

    def replace_char(self, count: int = 1) -> None:
        """Replace character at cursor (waits for next char)."""
        # This needs to be handled specially in the main input loop
        self.state.command_buffer = "r"

    def join_lines(self, count: int = 1) -> None:
        """Join current line with next line."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        for _ in range(count):
            if cursor.row < buffer.line_count - 1:
                current = buffer.get_line(cursor.row)
                next_line = buffer.get_line(cursor.row + 1)

                # Join with a space if current doesn't end with space
                if current and not current[-1].isspace():
                    joined = current + " " + next_line.lstrip()
                else:
                    joined = current + next_line.lstrip()

                buffer.replace_line(cursor.row, joined)
                buffer.delete_line(cursor.row + 1)

    def toggle_case(self, count: int = 1) -> None:
        """Toggle case of character at cursor."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        for _ in range(count):
            line = buffer.get_line(cursor.row)
            if cursor.col < len(line):
                char = line[cursor.col]
                if char.isupper():
                    new_char = char.lower()
                elif char.islower():
                    new_char = char.upper()
                else:
                    new_char = char

                new_line = line[: cursor.col] + new_char + line[cursor.col + 1 :]
                buffer.replace_line(cursor.row, new_line)

                # Move cursor right
                if cursor.col < len(line) - 1:
                    cursor.move_right()

    # Operators
    def delete_operator(self, count: int = 1) -> None:
        """Delete operator (waits for motion)."""
        self.pending_operator = "d"
        self.operator_count = count

    def change_operator(self, count: int = 1) -> None:
        """Change operator (waits for motion)."""
        self.pending_operator = "c"
        self.operator_count = count

    def yank_operator(self, count: int = 1) -> None:
        """Yank operator (waits for motion)."""
        self.pending_operator = "y"
        self.operator_count = count

    def indent_operator(self, count: int = 1) -> None:
        """Indent operator (waits for motion)."""
        self.pending_operator = ">"
        self.operator_count = count

    def outdent_operator(self, count: int = 1) -> None:
        """Outdent operator (waits for motion)."""
        self.pending_operator = "<"
        self.operator_count = count

    def format_operator(self, count: int = 1) -> None:
        """Format operator (waits for motion)."""
        self.pending_operator = "="
        self.operator_count = count

    # Line operations
    def delete_line(self, count: int = 1) -> None:
        """Delete entire line."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        lines = []
        for _ in range(count):
            if cursor.row < buffer.line_count:
                line = buffer.delete_line(cursor.row)
                if line:
                    lines.append(line)

        if lines:
            buffer.set_register('"', "\n".join(lines) + "\n")

        # Adjust cursor position
        if cursor.row >= buffer.line_count:
            cursor.set_position(buffer.line_count - 1, 0)

        line = buffer.get_line(cursor.row)
        cursor.move_to_first_non_blank(line)

    def change_line(self, count: int = 1) -> None:
        """Change entire line."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        # Delete lines but keep one empty line
        lines = []
        for i in range(count):
            if cursor.row < buffer.line_count:
                if i == 0:
                    # First line - replace with empty
                    line = buffer.get_line(cursor.row)
                    buffer.replace_line(cursor.row, "")
                    lines.append(line)
                else:
                    # Additional lines - delete
                    line = buffer.delete_line(cursor.row)
                    if line:
                        lines.append(line)

        if lines:
            buffer.set_register('"', "\n".join(lines) + "\n")

        cursor.move_to_line_start()
        self.enter_insert_mode()

    def yank_line(self, count: int = 1) -> None:
        """Yank entire line."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        lines = []
        for i in range(count):
            if cursor.row + i < buffer.line_count:
                lines.append(buffer.get_line(cursor.row + i))

        if lines:
            buffer.set_register('"', "\n".join(lines) + "\n")
            buffer.set_register("0", "\n".join(lines) + "\n")

    def delete_to_end(self, count: int = 1) -> None:
        """Delete from cursor to end of line."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        line = buffer.get_line(cursor.row)
        deleted = line[cursor.col :]

        if deleted:
            buffer.replace_line(cursor.row, line[: cursor.col])
            buffer.set_register('"', deleted)

        # Adjust cursor if past end
        line_len = buffer.get_line_length(cursor.row)
        if cursor.col >= line_len and line_len > 0:
            cursor.set_position(cursor.row, line_len - 1)

    def change_to_end(self, count: int = 1) -> None:
        """Change from cursor to end of line."""
        self.delete_to_end(count)
        self.enter_insert_mode_after()

    # Put/Paste
    def put_after(self, count: int = 1) -> None:
        """Put yanked text after cursor."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        text = buffer.get_register('"')
        if not text:
            return

        for _ in range(count):
            if "\n" in text:
                # Line-wise paste
                lines = text.rstrip("\n").split("\n")
                for i, line in enumerate(lines):
                    buffer.insert_line(cursor.row + i + 1, line)
                cursor.move_down(1, buffer.line_count - 1)
                line = buffer.get_line(cursor.row)
                cursor.move_to_first_non_blank(line)
            else:
                # Character-wise paste
                line = buffer.get_line(cursor.row)
                new_line = line[: cursor.col + 1] + text + line[cursor.col + 1 :]
                buffer.replace_line(cursor.row, new_line)
                cursor.move_right(len(text))

    def put_before(self, count: int = 1) -> None:
        """Put yanked text before cursor."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        text = buffer.get_register('"')
        if not text:
            return

        for _ in range(count):
            if "\n" in text:
                # Line-wise paste
                lines = text.rstrip("\n").split("\n")
                for i, line in enumerate(lines):
                    buffer.insert_line(cursor.row + i, line)
                line = buffer.get_line(cursor.row)
                cursor.move_to_first_non_blank(line)
            else:
                # Character-wise paste
                line = buffer.get_line(cursor.row)
                new_line = line[: cursor.col] + text + line[cursor.col :]
                buffer.replace_line(cursor.row, new_line)

    # Undo/Redo
    def undo(self, count: int = 1) -> None:
        """Undo last change."""
        buffer = self.state.current_buffer

        for _ in range(count):
            pos = buffer.undo()
            if pos:
                self.state.cursor.set_position(pos[0], pos[1])
            else:
                break

    def repeat_last(self, count: int = 1) -> None:
        """Repeat last command."""
        if self.state.last_command:
            # Re-execute last command
            for _ in range(count):
                self.handle_command(self.state.last_command)

    # Marks
    def set_mark(self, count: int = 1) -> None:
        """Set a mark (waits for mark character)."""
        self.state.command_buffer = "m"

    def jump_to_mark_line(self, count: int = 1) -> None:
        """Jump to line of mark (waits for mark character)."""
        self.state.command_buffer = "'"

    def jump_to_mark(self, count: int = 1) -> None:
        """Jump to exact mark position (waits for mark character)."""
        self.state.command_buffer = "`"

    # Macros
    def toggle_macro_recording(self, count: int = 1) -> None:
        """Toggle macro recording (waits for register)."""
        if self.state.recording_macro:
            self.state.stop_recording_macro()
        else:
            self.state.command_buffer = "q"

    def play_macro(self, count: int = 1) -> None:
        """Play macro (waits for register)."""
        self.state.command_buffer = "@"

    # Search
    def search_forward(self, count: int = 1) -> None:
        """Start forward search."""
        from vi_editor.core.mode import Mode

        self.state.mode_manager.set_mode(Mode.COMMAND)
        self.state.command_buffer = "/"

    def search_backward(self, count: int = 1) -> None:
        """Start backward search."""
        from vi_editor.core.mode import Mode

        self.state.mode_manager.set_mode(Mode.COMMAND)
        self.state.command_buffer = "?"

    def next_match(self, count: int = 1) -> None:
        """Go to next search match."""
        self.motion_handler.next_search_match(count)

    def prev_match(self, count: int = 1) -> None:
        """Go to previous search match."""
        self.motion_handler.prev_search_match(count)

    def search_word(self, count: int = 1) -> None:
        """Search for word under cursor forward."""
        self.motion_handler.search_word_forward(count)

    def search_word_backward(self, count: int = 1) -> None:
        """Search for word under cursor backward."""
        self.motion_handler.search_word_backward(count)

    # Helper methods
    def indent_lines(self, count: int = 1) -> None:
        """Indent lines."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        for i in range(count):
            if cursor.row + i < buffer.line_count:
                line = buffer.get_line(cursor.row + i)
                buffer.replace_line(cursor.row + i, "    " + line)

    def outdent_lines(self, count: int = 1) -> None:
        """Outdent lines."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        for i in range(count):
            if cursor.row + i < buffer.line_count:
                line = buffer.get_line(cursor.row + i)
                if line.startswith("    "):
                    buffer.replace_line(cursor.row + i, line[4:])
                elif line.startswith("\t"):
                    buffer.replace_line(cursor.row + i, line[1:])
