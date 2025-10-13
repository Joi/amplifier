"""Terminal handling for vi editor."""

import fcntl
import os
import struct
import sys
import termios
import tty
from typing import Optional, Tuple


class Terminal:
    """Handles terminal operations and configuration."""

    def __init__(self):
        """Initialize terminal handler."""
        self.original_settings: Optional[list] = None
        self.is_raw_mode = False
        self._width = 80
        self._height = 24

    def setup(self) -> None:
        """Set up terminal for vi editor."""
        # Save original terminal settings
        if sys.stdin.isatty():
            self.original_settings = termios.tcgetattr(sys.stdin)

        # Get terminal size
        self._update_size()

        # Enter raw mode
        self.enter_raw_mode()

        # Hide cursor initially
        self.hide_cursor()

        # Clear screen
        self.clear_screen()

    def cleanup(self) -> None:
        """Restore terminal to original state."""
        # Show cursor
        self.show_cursor()

        # Exit raw mode
        self.exit_raw_mode()

        # Clear screen
        self.clear_screen()

        # Move cursor to top
        self.move_cursor(0, 0)

    def enter_raw_mode(self) -> None:
        """Enter raw terminal mode."""
        if sys.stdin.isatty() and not self.is_raw_mode:
            tty.setraw(sys.stdin.fileno())
            self.is_raw_mode = True

    def exit_raw_mode(self) -> None:
        """Exit raw terminal mode and restore settings."""
        if sys.stdin.isatty() and self.is_raw_mode and self.original_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_settings)
            self.is_raw_mode = False

    def _update_size(self) -> None:
        """Update terminal size."""
        try:
            # Try ioctl first
            if sys.stdout.isatty():
                size = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, b"\x00" * 8)
                rows, cols = struct.unpack("hh", size[:4])
                if rows > 0 and cols > 0:
                    self._height = rows
                    self._width = cols
                    return
        except (OSError, IOError):
            pass

        # Fallback to environment variables
        try:
            self._height = int(os.environ.get("LINES", 24))
            self._width = int(os.environ.get("COLUMNS", 80))
        except (TypeError, ValueError):
            self._height = 24
            self._width = 80

    @property
    def width(self) -> int:
        """Get terminal width."""
        return self._width

    @property
    def height(self) -> int:
        """Get terminal height."""
        return self._height

    def get_size(self) -> Tuple[int, int]:
        """Get terminal size as (height, width)."""
        self._update_size()
        return (self._height, self._width)

    def clear_screen(self) -> None:
        """Clear the entire screen."""
        sys.stdout.write("\x1b[2J")
        sys.stdout.flush()

    def clear_line(self) -> None:
        """Clear the current line."""
        sys.stdout.write("\x1b[2K")
        sys.stdout.flush()

    def move_cursor(self, row: int, col: int) -> None:
        """Move cursor to specified position.

        Args:
            row: Row position (0-based).
            col: Column position (0-based).
        """
        # Terminal uses 1-based indexing
        sys.stdout.write(f"\x1b[{row + 1};{col + 1}H")
        sys.stdout.flush()

    def hide_cursor(self) -> None:
        """Hide the cursor."""
        sys.stdout.write("\x1b[?25l")
        sys.stdout.flush()

    def show_cursor(self) -> None:
        """Show the cursor."""
        sys.stdout.write("\x1b[?25h")
        sys.stdout.flush()

    def set_cursor_style(self, style: str) -> None:
        """Set cursor style.

        Args:
            style: 'block', 'underline', or 'bar'.
        """
        if style == "block":
            sys.stdout.write("\x1b[1 q")
        elif style == "underline":
            sys.stdout.write("\x1b[3 q")
        elif style == "bar":
            sys.stdout.write("\x1b[5 q")
        sys.stdout.flush()

    def write(self, text: str, row: Optional[int] = None, col: Optional[int] = None) -> None:
        """Write text at specified position.

        Args:
            text: Text to write.
            row: Row position (optional).
            col: Column position (optional).
        """
        if row is not None and col is not None:
            self.move_cursor(row, col)
        sys.stdout.write(text)
        sys.stdout.flush()

    def write_styled(self, text: str, style: str = "") -> None:
        """Write styled text.

        Args:
            text: Text to write.
            style: Style codes (e.g., '31' for red, '1' for bold).
        """
        if style:
            sys.stdout.write(f"\x1b[{style}m{text}\x1b[0m")
        else:
            sys.stdout.write(text)
        sys.stdout.flush()

    def set_color(self, fg: Optional[int] = None, bg: Optional[int] = None) -> None:
        """Set text colors.

        Args:
            fg: Foreground color (30-37, 90-97).
            bg: Background color (40-47, 100-107).
        """
        codes = []
        if fg is not None:
            codes.append(str(fg))
        if bg is not None:
            codes.append(str(bg))
        if codes:
            sys.stdout.write(f"\x1b[{';'.join(codes)}m")
            sys.stdout.flush()

    def reset_style(self) -> None:
        """Reset all text styling."""
        sys.stdout.write("\x1b[0m")
        sys.stdout.flush()

    def scroll_up(self, lines: int = 1) -> None:
        """Scroll screen up by specified lines.

        Args:
            lines: Number of lines to scroll.
        """
        sys.stdout.write(f"\x1b[{lines}S")
        sys.stdout.flush()

    def scroll_down(self, lines: int = 1) -> None:
        """Scroll screen down by specified lines.

        Args:
            lines: Number of lines to scroll.
        """
        sys.stdout.write(f"\x1b[{lines}T")
        sys.stdout.flush()

    def save_cursor_position(self) -> None:
        """Save current cursor position."""
        sys.stdout.write("\x1b[s")
        sys.stdout.flush()

    def restore_cursor_position(self) -> None:
        """Restore saved cursor position."""
        sys.stdout.write("\x1b[u")
        sys.stdout.flush()

    def enable_alternate_screen(self) -> None:
        """Switch to alternate screen buffer."""
        sys.stdout.write("\x1b[?1049h")
        sys.stdout.flush()

    def disable_alternate_screen(self) -> None:
        """Return to normal screen buffer."""
        sys.stdout.write("\x1b[?1049l")
        sys.stdout.flush()

    def ring_bell(self) -> None:
        """Ring the terminal bell."""
        sys.stdout.write("\a")
        sys.stdout.flush()
