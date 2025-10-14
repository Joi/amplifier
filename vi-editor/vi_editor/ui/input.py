"""Input handling for vi editor."""

import select
import sys
from typing import List, Optional


class InputHandler:
    """Handles keyboard input."""

    def __init__(self):
        """Initialize input handler."""
        self.buffer: List[str] = []
        self.escape_buffer: List[str] = []
        self.in_escape_sequence = False

    def read_key(self, timeout: Optional[float] = None) -> Optional[str]:
        """Read a single key press.

        Args:
            timeout: Timeout in seconds (None for blocking).

        Returns:
            Key string or None if timeout.
        """
        # Check buffered input first
        if self.buffer:
            return self.buffer.pop(0)

        # Check for input availability
        if timeout is not None:
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if not ready:
                return None
        else:
            # For blocking read, also use select to avoid hanging
            ready, _, _ = select.select([sys.stdin], [], [], None)
            if not ready:
                return None

        # Read character
        char = sys.stdin.read(1)

        if not char:
            return None

        # Handle escape sequences
        if char == "\x1b":  # ESC
            # Try to read more for escape sequence
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            if ready:
                seq = [char]
                # Read escape sequence
                while True:
                    next_char = sys.stdin.read(1)
                    if not next_char:
                        break
                    seq.append(next_char)
                    # Check for end of sequence
                    if next_char.isalpha() or next_char == "~":
                        break
                    # Check if more available
                    ready, _, _ = select.select([sys.stdin], [], [], 0.01)
                    if not ready:
                        break

                # Parse escape sequence
                full_seq = "".join(seq)
                return self._parse_escape_sequence(full_seq)
            else:
                # Just ESC key
                return "\x1b"

        # Handle special characters
        return self._process_char(char)

    def _parse_escape_sequence(self, seq: str) -> str:
        """Parse an escape sequence.

        Args:
            seq: The escape sequence string.

        Returns:
            Parsed key name.
        """
        # Arrow keys
        if seq == "\x1b[A" or seq == "\x1bOA":
            return "UP"
        elif seq == "\x1b[B" or seq == "\x1bOB":
            return "DOWN"
        elif seq == "\x1b[C" or seq == "\x1bOC":
            return "RIGHT"
        elif seq == "\x1b[D" or seq == "\x1bOD":
            return "LEFT"

        # Page Up/Down
        elif seq == "\x1b[5~":
            return "PAGE_UP"
        elif seq == "\x1b[6~":
            return "PAGE_DOWN"

        # Home/End
        elif seq == "\x1b[H" or seq == "\x1b[1~":
            return "HOME"
        elif seq == "\x1b[F" or seq == "\x1b[4~":
            return "END"

        # Insert/Delete
        elif seq == "\x1b[2~":
            return "INSERT"
        elif seq == "\x1b[3~":
            return "DELETE"

        # Function keys
        elif seq == "\x1bOP":
            return "F1"
        elif seq == "\x1bOQ":
            return "F2"
        elif seq == "\x1bOR":
            return "F3"
        elif seq == "\x1bOS":
            return "F4"
        elif seq == "\x1b[15~":
            return "F5"
        elif seq == "\x1b[17~":
            return "F6"
        elif seq == "\x1b[18~":
            return "F7"
        elif seq == "\x1b[19~":
            return "F8"
        elif seq == "\x1b[20~":
            return "F9"
        elif seq == "\x1b[21~":
            return "F10"
        elif seq == "\x1b[23~":
            return "F11"
        elif seq == "\x1b[24~":
            return "F12"

        # Alt+key combinations
        elif len(seq) == 2 and seq[0] == "\x1b":
            return f"ALT+{seq[1]}"

        # Unknown sequence
        return seq

    def _process_char(self, char: str) -> str:
        """Process a single character.

        Args:
            char: The character to process.

        Returns:
            Processed character or key name.
        """
        # Control characters
        if ord(char) < 32:
            if char == "\x00":
                return "CTRL+@"
            elif char == "\x01":
                return "CTRL+A"
            elif char == "\x02":
                return "CTRL+B"
            elif char == "\x03":
                return "CTRL+C"
            elif char == "\x04":
                return "CTRL+D"
            elif char == "\x05":
                return "CTRL+E"
            elif char == "\x06":
                return "CTRL+F"
            elif char == "\x07":
                return "CTRL+G"
            elif char == "\x08":
                return "BACKSPACE"
            elif char == "\x09":
                return "TAB"
            elif char == "\x0a" or char == "\x0d":
                return "ENTER"
            elif char == "\x0b":
                return "CTRL+K"
            elif char == "\x0c":
                return "CTRL+L"
            elif char == "\x0e":
                return "CTRL+N"
            elif char == "\x0f":
                return "CTRL+O"
            elif char == "\x10":
                return "CTRL+P"
            elif char == "\x11":
                return "CTRL+Q"
            elif char == "\x12":
                return "CTRL+R"
            elif char == "\x13":
                return "CTRL+S"
            elif char == "\x14":
                return "CTRL+T"
            elif char == "\x15":
                return "CTRL+U"
            elif char == "\x16":
                return "CTRL+V"
            elif char == "\x17":
                return "CTRL+W"
            elif char == "\x18":
                return "CTRL+X"
            elif char == "\x19":
                return "CTRL+Y"
            elif char == "\x1a":
                return "CTRL+Z"
            elif char == "\x1b":
                return "ESC"
            elif char == "\x1c":
                return "CTRL+\\"
            elif char == "\x1d":
                return "CTRL+]"
            elif char == "\x1e":
                return "CTRL+^"
            elif char == "\x1f":
                return "CTRL+_"

        # Delete character
        elif ord(char) == 127:
            return "BACKSPACE"

        # Normal character
        return char

    def push_back(self, key: str) -> None:
        """Push a key back to the buffer for later reading.

        Args:
            key: Key to push back.
        """
        self.buffer.append(key)

    def clear_buffer(self) -> None:
        """Clear the input buffer."""
        self.buffer.clear()
        self.escape_buffer.clear()
        self.in_escape_sequence = False

    def peek_key(self, timeout: float = 0.01) -> Optional[str]:
        """Peek at the next key without consuming it.

        Args:
            timeout: Timeout in seconds.

        Returns:
            Next key or None if no input available.
        """
        key = self.read_key(timeout)
        if key:
            self.push_back(key)
        return key

    def read_line(self, prompt: str = "") -> str:
        """Read a line of input.

        Args:
            prompt: Prompt to display.

        Returns:
            The input line.
        """
        # Temporarily exit raw mode for line input
        # This would need terminal mode management
        sys.stdout.write(prompt)
        sys.stdout.flush()

        line = []
        while True:
            key = self.read_key()
            if not key:
                continue

            if key == "ENTER":
                break
            elif key == "BACKSPACE":
                if line:
                    line.pop()
                    # Visual feedback
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif key == "ESC":
                # Cancel input
                return ""
            elif len(key) == 1 and ord(key) >= 32:
                line.append(key)
                sys.stdout.write(key)
                sys.stdout.flush()

        return "".join(line)
