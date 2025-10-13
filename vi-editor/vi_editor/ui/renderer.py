"""Rendering engine for vi editor."""

from typing import Tuple

from vi_editor.core.mode import Mode


class Renderer:
    """Renders the editor display."""

    def __init__(self, terminal, state):
        """Initialize renderer.

        Args:
            terminal: Terminal instance.
            state: EditorState instance.
        """
        self.terminal = terminal
        self.state = state
        self.last_cursor_row = 0
        self.last_cursor_col = 0

    def render(self) -> None:
        """Render the complete editor display."""
        # Get terminal size
        height, width = self.terminal.get_size()

        # Update viewport size in state
        self.state.viewport_height = height - 2  # Reserve for status and command lines
        self.state.viewport_width = width

        # Adjust viewport to keep cursor visible
        self.state.adjust_viewport()

        # Clear and render
        self.terminal.clear_screen()

        # Render buffer content
        self._render_buffer(height - 2, width)

        # Render status line
        self._render_status_line(height - 2, width)

        # Render command line
        self._render_command_line(height - 1, width)

        # Position cursor
        self._position_cursor()

    def _render_buffer(self, max_rows: int, width: int) -> None:
        """Render the buffer content.

        Args:
            max_rows: Maximum number of rows to render.
            width: Terminal width.
        """
        buffer = self.state.current_buffer
        cursor = self.state.cursor
        viewport_start = self.state.viewport_row

        # Get visual selection if in visual mode
        visual_start = None
        visual_end = None
        if self.state.mode_manager.is_visual_mode():
            selection = self.state.mode_manager.get_visual_selection()
            if selection:
                visual_start, visual_end = selection
                # Ensure start comes before end
                if visual_start[0] > visual_end[0] or (
                    visual_start[0] == visual_end[0] and visual_start[1] > visual_end[1]
                ):
                    visual_start, visual_end = visual_end, visual_start

        # Render each visible line
        for screen_row in range(max_rows):
            buffer_row = viewport_start + screen_row

            if buffer_row < buffer.line_count:
                # Get line content
                line = buffer.get_line(buffer_row)

                # Render line number if enabled
                line_display = ""
                col_offset = 0

                if self.state.get_config("number"):
                    line_num = f"{buffer_row + 1:4} "
                    self.terminal.write(line_num, screen_row, 0)
                    col_offset = len(line_num)

                # Render line content with visual selection
                if visual_start and visual_end:
                    line_display = self._render_line_with_selection(
                        line, buffer_row, visual_start, visual_end, width - col_offset
                    )
                    self.terminal.write(line_display, screen_row, col_offset)
                else:
                    # Truncate line to fit width
                    if len(line) > width - col_offset:
                        line_display = line[: width - col_offset - 1] + ">"
                    else:
                        line_display = line

                    self.terminal.write(line_display, screen_row, col_offset)
            else:
                # Empty line indicator
                self.terminal.write_styled("~", "34", screen_row, 0)  # Blue color

    def _render_line_with_selection(
        self, line: str, row: int, visual_start: Tuple[int, int], visual_end: Tuple[int, int], max_width: int
    ) -> str:
        """Render a line with visual selection highlighting.

        Args:
            line: Line content.
            row: Line row number.
            visual_start: Start of visual selection.
            visual_end: End of visual selection.
            max_width: Maximum line width.

        Returns:
            Rendered line string.
        """
        result = []

        # Visual line mode - highlight entire line
        if self.state.mode == Mode.VISUAL_LINE:
            if visual_start[0] <= row <= visual_end[0]:
                # Highlight entire line
                self.terminal.set_color(fg=30, bg=47)  # Black on white
                result.append(line[:max_width])
                self.terminal.reset_style()
            else:
                result.append(line[:max_width])

        # Character visual mode
        else:
            for col, char in enumerate(line):
                if col >= max_width:
                    break

                # Check if this character is in selection
                in_selection = False

                if row == visual_start[0] == visual_end[0]:
                    # Selection on single line
                    in_selection = visual_start[1] <= col <= visual_end[1]
                elif row == visual_start[0]:
                    # First line of selection
                    in_selection = col >= visual_start[1]
                elif row == visual_end[0]:
                    # Last line of selection
                    in_selection = col <= visual_end[1]
                elif visual_start[0] < row < visual_end[0]:
                    # Middle line of selection
                    in_selection = True

                if in_selection:
                    # Highlight character
                    self.terminal.write_styled(char, "30;47")  # Black on white
                else:
                    self.terminal.write(char)

        return "".join(result)

    def _render_status_line(self, row: int, width: int) -> None:
        """Render the status line.

        Args:
            row: Row position for status line.
            width: Terminal width.
        """
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        # Build status components
        left_parts = []
        right_parts = []

        # Mode indicator
        mode_str = self._get_mode_string()
        if mode_str:
            left_parts.append(f"-- {mode_str} --")

        # File name and status
        filename = buffer.filename or "[No Name]"
        if buffer.modified:
            filename += " [+]"
        left_parts.append(filename)

        # Position info
        line_num = cursor.row + 1
        col_num = cursor.col + 1
        percent = int((cursor.row / max(1, buffer.line_count - 1)) * 100) if buffer.line_count > 1 else 100
        right_parts.append(f"{line_num},{col_num}")
        right_parts.append(f"{percent}%")

        # Build status line
        left = " ".join(left_parts)
        right = "  ".join(right_parts)
        padding = width - len(left) - len(right) - 2
        if padding < 0:
            padding = 0

        status = f" {left}{' ' * padding}{right} "[:width]

        # Render with inverse colors
        self.terminal.write_styled(status, "7", row, 0)  # Inverse video

    def _render_command_line(self, row: int, width: int) -> None:
        """Render the command line.

        Args:
            row: Row position for command line.
            width: Terminal width.
        """
        # Clear the line first
        self.terminal.clear_line()
        self.terminal.move_cursor(row, 0)

        # Show status message if present
        if self.state.status_message:
            msg = self.state.status_message.text[:width]
            if self.state.status_message.type == "error":
                self.terminal.write_styled(msg, "31")  # Red
            elif self.state.status_message.type == "warning":
                self.terminal.write_styled(msg, "33")  # Yellow
            else:
                self.terminal.write(msg)

        # Show command buffer if in command mode
        elif self.state.mode_manager.current_mode in (Mode.COMMAND, Mode.EX):
            cmd = self.state.command_buffer[:width]
            self.terminal.write(cmd)

        # Show search pattern if searching
        elif self.state.command_buffer and self.state.command_buffer[0] in ["/", "?"]:
            search = self.state.command_buffer[:width]
            self.terminal.write(search)

        # Show pending operator/command
        elif hasattr(self.state, "pending_operator") and self.state.pending_operator:
            self.terminal.write(f"{self.state.pending_operator}")

        # Show count prefix if present
        elif self.state.count_prefix:
            self.terminal.write(self.state.count_prefix)

    def _position_cursor(self) -> None:
        """Position the terminal cursor."""
        cursor = self.state.cursor

        # Calculate screen position
        screen_row = cursor.row - self.state.viewport_row
        screen_col = cursor.col

        # Account for line numbers
        if self.state.get_config("number"):
            screen_col += 5  # Line number width

        # Ensure cursor is within viewport
        height, width = self.terminal.get_size()
        screen_row = max(0, min(screen_row, height - 3))
        screen_col = max(0, min(screen_col, width - 1))

        # Set cursor style based on mode
        if self.state.mode_manager.is_insert_mode():
            self.terminal.set_cursor_style("bar")
        elif self.state.mode == Mode.REPLACE:
            self.terminal.set_cursor_style("underline")
        else:
            self.terminal.set_cursor_style("block")

        # Position cursor
        self.terminal.move_cursor(screen_row, screen_col)
        self.terminal.show_cursor()

        # Store last position
        self.last_cursor_row = screen_row
        self.last_cursor_col = screen_col

    def _get_mode_string(self) -> str:
        """Get the mode indicator string.

        Returns:
            Mode string for status line.
        """
        mode = self.state.mode_manager.current_mode

        if mode == Mode.INSERT:
            return "INSERT"
        elif mode == Mode.REPLACE:
            return "REPLACE"
        elif mode == Mode.VISUAL:
            return "VISUAL"
        elif mode == Mode.VISUAL_LINE:
            return "VISUAL LINE"
        elif mode == Mode.VISUAL_BLOCK:
            return "VISUAL BLOCK"
        elif mode == Mode.COMMAND or mode == Mode.EX:
            return ""  # Command shown in command line
        else:
            return ""  # Normal mode - no indicator

    def refresh_line(self, row: int) -> None:
        """Refresh a single line.

        Args:
            row: Buffer row to refresh.
        """
        # Calculate screen row
        screen_row = row - self.state.viewport_row
        if screen_row < 0 or screen_row >= self.state.viewport_height:
            return  # Line not visible

        # Clear line
        self.terminal.move_cursor(screen_row, 0)
        self.terminal.clear_line()

        # Re-render line
        buffer = self.state.current_buffer
        line = buffer.get_line(row)

        col_offset = 0
        if self.state.get_config("number"):
            line_num = f"{row + 1:4} "
            self.terminal.write(line_num)
            col_offset = len(line_num)

        # Render line content
        width = self.terminal.width
        if len(line) > width - col_offset:
            line = line[: width - col_offset - 1] + ">"

        self.terminal.write(line)

    def refresh_status(self) -> None:
        """Refresh just the status line."""
        height = self.terminal.height
        self._render_status_line(height - 2, self.terminal.width)
        self._position_cursor()

    def refresh_command(self) -> None:
        """Refresh just the command line."""
        height = self.terminal.height
        self._render_command_line(height - 1, self.terminal.width)
        self._position_cursor()
