"""Visual mode commands for vi editor."""

from typing import Optional, Tuple


class VisualCommand:
    """Represents a visual mode command."""

    def __init__(self, command: str):
        """Initialize visual command.

        Args:
            command: The command string.
        """
        self.command = command


class VisualCommandHandler:
    """Handles visual mode commands."""

    def __init__(self, state, motion_handler):
        """Initialize visual command handler.

        Args:
            state: EditorState instance.
            motion_handler: MotionHandler instance.
        """
        self.state = state
        self.motion_handler = motion_handler
        self.visual_start: Optional[Tuple[int, int]] = None

    def enter_visual_mode(self) -> None:
        """Enter visual mode and mark selection start."""
        from vi_editor.core.mode import Mode

        self.visual_start = self.state.cursor.position
        self.state.mode_manager.set_mode(Mode.VISUAL)
        self.state.mode_manager.set_visual_selection(self.visual_start, self.visual_start)

    def update_visual_selection(self) -> None:
        """Update visual selection based on cursor position."""
        if self.visual_start:
            current = self.state.cursor.position
            self.state.mode_manager.set_visual_selection(self.visual_start, current)

    def handle_command(self, key: str) -> bool:
        """Handle a visual mode command.

        Args:
            key: The key pressed.

        Returns:
            True if command was handled, False otherwise.
        """
        from vi_editor.core.mode import Mode

        # Escape - exit visual mode
        if key == "\x1b" or key == "v":  # ESC or v again
            self.state.mode_manager.set_mode(Mode.NORMAL)
            self.visual_start = None
            return True

        # Motion commands - extend selection
        if key in self.motion_handler.motions:
            self.motion_handler.execute_motion(key)
            self.update_visual_selection()
            return True

        # Operations on selection
        if key == "d":  # Delete
            self.delete_selection()
            return True
        elif key == "c":  # Change
            self.change_selection()
            return True
        elif key == "y":  # Yank
            self.yank_selection()
            return True
        elif key == ">":  # Indent
            self.indent_selection()
            return True
        elif key == "<":  # Outdent
            self.outdent_selection()
            return True
        elif key == "~":  # Toggle case
            self.toggle_case_selection()
            return True

        return False

    def get_selection_range(self) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Get the current visual selection range.

        Returns:
            Tuple of (start, end) positions or None.
        """
        selection = self.state.mode_manager.get_visual_selection()
        if not selection:
            return None

        start, end = selection

        # Ensure start comes before end
        if start[0] > end[0] or (start[0] == end[0] and start[1] > end[1]):
            start, end = end, start

        return (start, end)

    def delete_selection(self) -> None:
        """Delete the visual selection."""
        from vi_editor.core.mode import Mode

        selection = self.get_selection_range()
        if not selection:
            return

        start, end = selection
        buffer = self.state.current_buffer

        # Handle different visual modes
        if self.state.mode_manager.current_mode == Mode.VISUAL_LINE:
            # Delete whole lines
            deleted_lines = []
            for _ in range(end[0] - start[0] + 1):
                if start[0] < buffer.line_count:
                    line = buffer.delete_line(start[0])
                    if line:
                        deleted_lines.append(line)

            if deleted_lines:
                buffer.set_register('"', "\n".join(deleted_lines) + "\n")

            # Position cursor
            if start[0] >= buffer.line_count:
                self.state.cursor.set_position(buffer.line_count - 1, 0)
            else:
                self.state.cursor.set_position(start[0], 0)

        else:
            # Character-wise deletion
            text = buffer.delete_range(start[0], start[1], end[0], end[1] + 1)
            buffer.set_register('"', text)
            self.state.cursor.set_position(start[0], start[1])

        # Exit visual mode
        self.state.mode_manager.set_mode(Mode.NORMAL)
        self.visual_start = None

    def change_selection(self) -> None:
        """Change the visual selection."""
        from vi_editor.core.mode import Mode

        # Delete selection and enter insert mode
        self.delete_selection()
        self.state.mode_manager.set_mode(Mode.INSERT)

    def yank_selection(self) -> None:
        """Yank the visual selection."""
        from vi_editor.core.mode import Mode

        selection = self.get_selection_range()
        if not selection:
            return

        start, end = selection
        buffer = self.state.current_buffer

        # Handle different visual modes
        if self.state.mode_manager.current_mode == Mode.VISUAL_LINE:
            # Yank whole lines
            lines = []
            for row in range(start[0], end[0] + 1):
                if row < buffer.line_count:
                    lines.append(buffer.get_line(row))

            if lines:
                buffer.set_register('"', "\n".join(lines) + "\n")
                buffer.set_register("0", "\n".join(lines) + "\n")

        else:
            # Character-wise yank
            if start[0] == end[0]:
                # Single line
                line = buffer.get_line(start[0])
                text = line[start[1] : end[1] + 1]
            else:
                # Multiple lines
                lines = []
                lines.append(buffer.get_line(start[0])[start[1] :])
                for row in range(start[0] + 1, end[0]):
                    lines.append(buffer.get_line(row))
                lines.append(buffer.get_line(end[0])[: end[1] + 1])
                text = "\n".join(lines)

            buffer.set_register('"', text)
            buffer.set_register("0", text)

        # Exit visual mode
        self.state.mode_manager.set_mode(Mode.NORMAL)
        self.visual_start = None
        self.state.set_status(f"Yanked {end[0] - start[0] + 1} lines", "info")

    def indent_selection(self) -> None:
        """Indent the visual selection."""
        from vi_editor.core.mode import Mode

        selection = self.get_selection_range()
        if not selection:
            return

        start, end = selection
        buffer = self.state.current_buffer

        # Indent lines in range
        for row in range(start[0], end[0] + 1):
            if row < buffer.line_count:
                line = buffer.get_line(row)
                buffer.replace_line(row, "    " + line)

        # Exit visual mode
        self.state.mode_manager.set_mode(Mode.NORMAL)
        self.visual_start = None

    def outdent_selection(self) -> None:
        """Outdent the visual selection."""
        from vi_editor.core.mode import Mode

        selection = self.get_selection_range()
        if not selection:
            return

        start, end = selection
        buffer = self.state.current_buffer

        # Outdent lines in range
        for row in range(start[0], end[0] + 1):
            if row < buffer.line_count:
                line = buffer.get_line(row)
                if line.startswith("    "):
                    buffer.replace_line(row, line[4:])
                elif line.startswith("\t"):
                    buffer.replace_line(row, line[1:])

        # Exit visual mode
        self.state.mode_manager.set_mode(Mode.NORMAL)
        self.visual_start = None

    def toggle_case_selection(self) -> None:
        """Toggle case of visual selection."""
        from vi_editor.core.mode import Mode

        selection = self.get_selection_range()
        if not selection:
            return

        start, end = selection
        buffer = self.state.current_buffer

        if self.state.mode_manager.current_mode == Mode.VISUAL_LINE:
            # Toggle case of whole lines
            for row in range(start[0], end[0] + 1):
                if row < buffer.line_count:
                    line = buffer.get_line(row)
                    new_line = "".join(c.upper() if c.islower() else c.lower() if c.isupper() else c for c in line)
                    buffer.replace_line(row, new_line)
        else:
            # Character-wise case toggle
            if start[0] == end[0]:
                # Single line
                line = buffer.get_line(start[0])
                before = line[: start[1]]
                selected = line[start[1] : end[1] + 1]
                after = line[end[1] + 1 :]

                toggled = "".join(c.upper() if c.islower() else c.lower() if c.isupper() else c for c in selected)

                buffer.replace_line(start[0], before + toggled + after)
            else:
                # Multiple lines
                for row in range(start[0], end[0] + 1):
                    if row < buffer.line_count:
                        line = buffer.get_line(row)

                        if row == start[0]:
                            # First line - from start column
                            before = line[: start[1]]
                            selected = line[start[1] :]
                            toggled = "".join(
                                c.upper() if c.islower() else c.lower() if c.isupper() else c for c in selected
                            )
                            buffer.replace_line(row, before + toggled)
                        elif row == end[0]:
                            # Last line - to end column
                            selected = line[: end[1] + 1]
                            after = line[end[1] + 1 :]
                            toggled = "".join(
                                c.upper() if c.islower() else c.lower() if c.isupper() else c for c in selected
                            )
                            buffer.replace_line(row, toggled + after)
                        else:
                            # Middle lines - whole line
                            toggled = "".join(
                                c.upper() if c.islower() else c.lower() if c.isupper() else c for c in line
                            )
                            buffer.replace_line(row, toggled)

        # Exit visual mode
        self.state.mode_manager.set_mode(Mode.NORMAL)
        self.visual_start = None
