"""Main editor class for vi editor."""

import signal
import sys
from typing import Optional

from vi_editor.commands.ex import ExCommandHandler
from vi_editor.commands.motion import MotionHandler
from vi_editor.commands.normal import NormalCommandHandler
from vi_editor.commands.visual import VisualCommandHandler
from vi_editor.core.mode import Mode
from vi_editor.core.state import EditorState
from vi_editor.file_ops.backup import BackupManager
from vi_editor.file_ops.file_handler import FileHandler
from vi_editor.file_ops.recovery import RecoveryManager
from vi_editor.ui.display import Display
from vi_editor.ui.input import InputHandler
from vi_editor.ui.renderer import Renderer
from vi_editor.ui.terminal import Terminal


class Editor:
    """Main vi editor class that integrates all components."""

    def __init__(self):
        """Initialize the editor."""
        # Core components
        self.state = EditorState()
        self.running = False

        # File operations
        self.backup_manager = BackupManager()
        self.recovery_manager = RecoveryManager()
        self.file_handler = FileHandler(self.backup_manager)

        # UI components
        self.terminal = Terminal()
        self.input_handler = InputHandler()
        self.renderer = Renderer(self.terminal, self.state)
        self.display = Display(self.terminal, self.renderer, self.state)

        # Command handlers
        self.motion_handler = MotionHandler(self.state)
        self.normal_handler = NormalCommandHandler(self.state, self.motion_handler)
        self.ex_handler = ExCommandHandler(self.state, self.file_handler)
        self.visual_handler = VisualCommandHandler(self.state, self.motion_handler)

        # Signal handling
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for clean shutdown."""

        def signal_handler(signum, frame):
            self.quit()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def open_file(self, filename: Optional[str] = None) -> None:
        """Open a file for editing.

        Args:
            filename: Path to file to open.
        """
        if filename:
            try:
                # Expand path
                filename = self.file_handler.expand_path(filename)

                # Check for recovery
                if self.recovery_manager.check_recovery_needed(filename):
                    self.state.set_status(f"Swap file exists for {filename}. Use :recover to restore.", "warning")

                # Read file
                buffer = self.file_handler.read_file(filename)

                # Set as current buffer
                self.state.buffers[0] = buffer
                self.state.cursor.set_position(0, 0)

                # Create swap file
                swap_file = self.recovery_manager.create_swap_file(filename)
                if swap_file:
                    buffer.swap_file = swap_file

            except FileNotFoundError:
                # New file
                self.state.current_buffer.set_filename(filename)
                self.state.set_status(f'"{filename}" [New File]', "info")
            except Exception as e:
                self.state.set_status(f"Error opening file: {str(e)}", "error")

    def run(self) -> None:
        """Run the editor main loop."""
        self.running = True

        # Initialize display
        self.display.initialize()

        try:
            while self.running:
                # Render display
                self.display.render()

                # Get input
                key = self.input_handler.read_key()
                if not key:
                    continue

                # Process input based on mode
                self._process_input(key)

                # Auto-save to swap file periodically
                self._update_swap_file()

        except KeyboardInterrupt:
            pass
        finally:
            self.quit()

    def _process_input(self, key: str) -> None:
        """Process keyboard input based on current mode.

        Args:
            key: The key pressed.
        """
        mode = self.state.mode_manager.current_mode

        if mode == Mode.NORMAL:
            self._process_normal_mode(key)
        elif mode == Mode.INSERT:
            self._process_insert_mode(key)
        elif mode == Mode.VISUAL or mode == Mode.VISUAL_LINE:
            self._process_visual_mode(key)
        elif mode == Mode.COMMAND or mode == Mode.EX:
            self._process_command_mode(key)
        elif mode == Mode.REPLACE:
            self._process_replace_mode(key)

    def _process_normal_mode(self, key: str) -> None:
        """Process input in normal mode.

        Args:
            key: The key pressed.
        """
        # Handle escape
        if key == "ESC" or key == "\x1b":
            self.state.reset_command_state()
            return

        # Handle arrow keys
        if key == "UP":
            self.motion_handler.move_up()
        elif key == "DOWN":
            self.motion_handler.move_down()
        elif key == "LEFT":
            self.motion_handler.move_left()
        elif key == "RIGHT":
            self.motion_handler.move_right()
        else:
            # Process normal command
            self.normal_handler.handle_command(key)

    def _process_insert_mode(self, key: str) -> None:
        """Process input in insert mode.

        Args:
            key: The key pressed.
        """
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        # Handle escape
        if key == "ESC" or key == "\x1b":
            self.state.mode_manager.set_mode(Mode.NORMAL)
            # Move cursor left if not at start
            if cursor.col > 0:
                cursor.move_left()
            return

        # Handle special keys
        if key == "ENTER":
            # Split line at cursor
            line = buffer.get_line(cursor.row)
            before = line[: cursor.col]
            after = line[cursor.col :]

            buffer.replace_line(cursor.row, before)
            buffer.insert_line(cursor.row + 1, after)

            cursor.move_down()
            cursor.move_to_line_start()

        elif key == "BACKSPACE":
            if cursor.col > 0:
                cursor.move_left()
                buffer.delete_char(cursor.row, cursor.col)
            elif cursor.row > 0:
                # Join with previous line
                prev_line = buffer.get_line(cursor.row - 1)
                curr_line = buffer.get_line(cursor.row)

                buffer.replace_line(cursor.row - 1, prev_line + curr_line)
                buffer.delete_line(cursor.row)

                cursor.move_up()
                cursor.set_position(cursor.row, len(prev_line))

        elif key == "TAB":
            # Insert tab or spaces
            if self.state.get_config("expandtab"):
                spaces = " " * self.state.get_config("tabstop", 8)
                buffer.insert_text(cursor.row, cursor.col, spaces)
                cursor.move_right(len(spaces))
            else:
                buffer.insert_char(cursor.row, cursor.col, "\t")
                cursor.move_right()

        elif len(key) == 1 and ord(key) >= 32:
            # Normal character
            buffer.insert_char(cursor.row, cursor.col, key)
            cursor.move_right()

        # Handle arrow keys
        elif key == "UP":
            cursor.move_up()
            line_len = buffer.get_line_length(cursor.row)
            cursor.adjust_column_for_line(line_len)
        elif key == "DOWN":
            cursor.move_down(1, buffer.line_count - 1)
            line_len = buffer.get_line_length(cursor.row)
            cursor.adjust_column_for_line(line_len)
        elif key == "LEFT":
            cursor.move_left()
        elif key == "RIGHT":
            line_len = buffer.get_line_length(cursor.row)
            cursor.move_right(1, line_len)

    def _process_visual_mode(self, key: str) -> None:
        """Process input in visual mode.

        Args:
            key: The key pressed.
        """
        # Let visual handler process the command
        if not self.visual_handler.handle_command(key):
            # If not handled, treat as motion
            if key in self.motion_handler.motions:
                self.motion_handler.execute_motion(key)
                self.visual_handler.update_visual_selection()

    def _process_command_mode(self, key: str) -> None:
        """Process input in command/ex mode.

        Args:
            key: The key pressed.
        """
        # Handle escape
        if key == "ESC" or key == "\x1b":
            self.state.mode_manager.set_mode(Mode.NORMAL)
            self.state.command_buffer = ""
            return

        # Handle enter
        if key == "ENTER":
            command = self.state.command_buffer[1:]  # Remove : or /

            if self.state.command_buffer.startswith(":"):
                # Execute ex command
                result = self.ex_handler.execute(command)

                # Handle special results
                if result == "quit":
                    self.quit()

            elif self.state.command_buffer.startswith("/"):
                # Forward search
                self.state.search_state.pattern = command
                self.state.search_state.direction = "forward"
                self.state.history.add_search(command)
                self.motion_handler.next_search_match()

            elif self.state.command_buffer.startswith("?"):
                # Backward search
                self.state.search_state.pattern = command
                self.state.search_state.direction = "backward"
                self.state.history.add_search(command)
                self.motion_handler.prev_search_match()

            # Return to normal mode
            self.state.mode_manager.set_mode(Mode.NORMAL)
            self.state.command_buffer = ""

        # Handle backspace
        elif key == "BACKSPACE":
            if len(self.state.command_buffer) > 1:
                self.state.command_buffer = self.state.command_buffer[:-1]
            else:
                # Cancel command
                self.state.mode_manager.set_mode(Mode.NORMAL)
                self.state.command_buffer = ""

        # Handle regular character
        elif len(key) == 1 and ord(key) >= 32:
            self.state.command_buffer += key

    def _process_replace_mode(self, key: str) -> None:
        """Process input in replace mode.

        Args:
            key: The key pressed.
        """
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        # Handle escape
        if key == "ESC" or key == "\x1b":
            self.state.mode_manager.set_mode(Mode.NORMAL)
            return

        # Handle regular character
        if len(key) == 1 and ord(key) >= 32:
            # Replace character at cursor
            line = buffer.get_line(cursor.row)
            if cursor.col < len(line):
                new_line = line[: cursor.col] + key + line[cursor.col + 1 :]
                buffer.replace_line(cursor.row, new_line)
                cursor.move_right()

    def _update_swap_file(self) -> None:
        """Update swap file with current buffer content."""
        buffer = self.state.current_buffer

        if hasattr(buffer, "swap_file") and buffer.swap_file and buffer.modified:
            content = buffer.get_text()
            self.recovery_manager.update_swap_file(buffer.swap_file, content)

    def quit(self) -> None:
        """Quit the editor."""
        self.running = False

        # Clean up swap files
        for buffer in self.state.buffers:
            if buffer.filename and hasattr(buffer, "swap_file") and buffer.swap_file:
                self.recovery_manager.remove_swap_file(buffer.swap_file)

        # Clean up display
        self.display.cleanup()

        # Exit
        sys.exit(0)
