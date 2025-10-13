"""Editor state management for vi editor."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from vi_editor.core.buffer import Buffer
from vi_editor.core.cursor import Cursor
from vi_editor.core.mode import Mode, ModeManager


@dataclass
class SearchState:
    """Manages search state."""

    pattern: str = ""
    direction: str = "forward"  # 'forward' or 'backward'
    last_match: Optional[tuple[int, int]] = None
    case_sensitive: bool = False
    whole_word: bool = False
    regex: bool = False


@dataclass
class CommandHistory:
    """Manages command and search history."""

    commands: List[str] = field(default_factory=list)
    searches: List[str] = field(default_factory=list)
    max_history: int = 100
    command_index: int = -1
    search_index: int = -1

    def add_command(self, command: str) -> None:
        """Add a command to history."""
        if command and (not self.commands or command != self.commands[-1]):
            self.commands.append(command)
            if len(self.commands) > self.max_history:
                self.commands.pop(0)
        self.command_index = -1

    def add_search(self, pattern: str) -> None:
        """Add a search pattern to history."""
        if pattern and (not self.searches or pattern != self.searches[-1]):
            self.searches.append(pattern)
            if len(self.searches) > self.max_history:
                self.searches.pop(0)
        self.search_index = -1

    def get_prev_command(self) -> Optional[str]:
        """Get previous command from history."""
        if self.commands:
            if self.command_index == -1:
                self.command_index = len(self.commands) - 1
            elif self.command_index > 0:
                self.command_index -= 1
            return self.commands[self.command_index]
        return None

    def get_next_command(self) -> Optional[str]:
        """Get next command from history."""
        if self.commands and self.command_index >= 0:
            if self.command_index < len(self.commands) - 1:
                self.command_index += 1
                return self.commands[self.command_index]
            else:
                self.command_index = -1
                return ""
        return None

    def get_prev_search(self) -> Optional[str]:
        """Get previous search from history."""
        if self.searches:
            if self.search_index == -1:
                self.search_index = len(self.searches) - 1
            elif self.search_index > 0:
                self.search_index -= 1
            return self.searches[self.search_index]
        return None

    def get_next_search(self) -> Optional[str]:
        """Get next search from history."""
        if self.searches and self.search_index >= 0:
            if self.search_index < len(self.searches) - 1:
                self.search_index += 1
                return self.searches[self.search_index]
            else:
                self.search_index = -1
                return ""
        return None


@dataclass
class StatusMessage:
    """Represents a status message."""

    text: str
    type: str = "info"  # 'info', 'warning', 'error'
    timeout: float = 3.0


class EditorState:
    """Manages the complete editor state."""

    def __init__(self):
        """Initialize editor state."""
        self.buffers: List[Buffer] = [Buffer()]
        self.current_buffer_index = 0
        self.cursor = Cursor()
        self.mode_manager = ModeManager()
        self.search_state = SearchState()
        self.history = CommandHistory()
        self.command_buffer = ""
        self.count_prefix = ""  # For command repetition (e.g., 3dd)
        self.last_command = ""
        self.status_message: Optional[StatusMessage] = None
        self.config: Dict[str, Any] = self._default_config()
        self.macros: Dict[str, str] = {}
        self.recording_macro: Optional[str] = None
        self.macro_buffer: List[str] = []
        self.viewport_row = 0  # First visible row
        self.viewport_height = 24  # Terminal height
        self.viewport_width = 80  # Terminal width

    @property
    def current_buffer(self) -> Buffer:
        """Get the current buffer."""
        return self.buffers[self.current_buffer_index]

    @property
    def mode(self) -> Mode:
        """Get the current mode."""
        return self.mode_manager.current_mode

    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "tabstop": 8,
            "expandtab": False,
            "shiftwidth": 8,
            "autoindent": True,
            "number": False,
            "relativenumber": False,
            "wrap": True,
            "hlsearch": True,
            "incsearch": True,
            "ignorecase": False,
            "smartcase": True,
            "scrolloff": 0,
            "showmode": True,
            "showcmd": True,
            "ruler": True,
            "laststatus": 2,
            "syntax": True,
        }

    def add_buffer(self, buffer: Buffer) -> int:
        """Add a new buffer.

        Args:
            buffer: Buffer to add.

        Returns:
            Index of the added buffer.
        """
        self.buffers.append(buffer)
        return len(self.buffers) - 1

    def switch_buffer(self, index: int) -> bool:
        """Switch to a different buffer.

        Args:
            index: Buffer index to switch to.

        Returns:
            True if switch successful, False otherwise.
        """
        if 0 <= index < len(self.buffers):
            self.current_buffer_index = index
            # Reset cursor position for new buffer
            self.cursor.set_position(0, 0)
            return True
        return False

    def close_buffer(self, index: Optional[int] = None) -> bool:
        """Close a buffer.

        Args:
            index: Buffer index to close, or None for current.

        Returns:
            True if closed successfully, False otherwise.
        """
        if index is None:
            index = self.current_buffer_index

        if len(self.buffers) <= 1:
            # Can't close last buffer
            return False

        if 0 <= index < len(self.buffers):
            del self.buffers[index]
            # Adjust current buffer index if needed
            if self.current_buffer_index >= len(self.buffers):
                self.current_buffer_index = len(self.buffers) - 1
            return True
        return False

    def set_status(self, message: str, type: str = "info", timeout: float = 3.0) -> None:
        """Set a status message.

        Args:
            message: Message text.
            type: Message type ('info', 'warning', 'error').
            timeout: How long to display the message.
        """
        self.status_message = StatusMessage(message, type, timeout)

    def clear_status(self) -> None:
        """Clear the status message."""
        self.status_message = None

    def start_recording_macro(self, register: str) -> bool:
        """Start recording a macro.

        Args:
            register: Register to record into.

        Returns:
            True if recording started, False if already recording.
        """
        if self.recording_macro is not None:
            return False

        self.recording_macro = register
        self.macro_buffer = []
        self.set_status(f"Recording macro @{register}", "info")
        return True

    def stop_recording_macro(self) -> bool:
        """Stop recording a macro.

        Returns:
            True if recording stopped, False if not recording.
        """
        if self.recording_macro is None:
            return False

        register = self.recording_macro
        self.macros[register] = "".join(self.macro_buffer)
        self.recording_macro = None
        self.macro_buffer = []
        self.set_status(f"Macro recorded to @{register}", "info")
        return True

    def record_macro_key(self, key: str) -> None:
        """Record a key press for macro recording.

        Args:
            key: Key to record.
        """
        if self.recording_macro is not None:
            self.macro_buffer.append(key)

    def play_macro(self, register: str) -> Optional[str]:
        """Play a recorded macro.

        Args:
            register: Register containing the macro.

        Returns:
            Macro content or None if not found.
        """
        return self.macros.get(register)

    def adjust_viewport(self) -> None:
        """Adjust viewport to keep cursor visible."""
        cursor_row = self.cursor.row

        # Scroll up if cursor is above viewport
        if cursor_row < self.viewport_row + self.config.get("scrolloff", 0):
            self.viewport_row = max(0, cursor_row - self.config.get("scrolloff", 0))

        # Scroll down if cursor is below viewport
        elif cursor_row >= self.viewport_row + self.viewport_height - self.config.get("scrolloff", 0):
            self.viewport_row = max(0, cursor_row - self.viewport_height + 1 + self.config.get("scrolloff", 0))

    def get_visible_range(self) -> tuple[int, int]:
        """Get the range of visible lines.

        Returns:
            Tuple of (first_visible_row, last_visible_row).
        """
        return (self.viewport_row, min(self.viewport_row + self.viewport_height, self.current_buffer.line_count))

    def reset_command_state(self) -> None:
        """Reset command-related state."""
        self.command_buffer = ""
        self.count_prefix = ""

    def get_count(self, default: int = 1) -> int:
        """Get the current count prefix.

        Args:
            default: Default value if no count specified.

        Returns:
            The count value.
        """
        if self.count_prefix:
            try:
                return int(self.count_prefix)
            except ValueError:
                return default
        return default

    def append_count(self, digit: str) -> None:
        """Append a digit to the count prefix.

        Args:
            digit: Digit character to append.
        """
        if digit.isdigit():
            self.count_prefix += digit

    def set_config(self, option: str, value: Any) -> bool:
        """Set a configuration option.

        Args:
            option: Option name.
            value: Option value.

        Returns:
            True if option was set, False if invalid option.
        """
        if option in self.config:
            self.config[option] = value
            return True
        return False

    def get_config(self, option: str, default: Any = None) -> Any:
        """Get a configuration option.

        Args:
            option: Option name.
            default: Default value if option not found.

        Returns:
            Option value or default.
        """
        return self.config.get(option, default)
