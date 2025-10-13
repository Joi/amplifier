"""Motion commands for vi editor."""

import re
from dataclasses import dataclass
from typing import Callable, Optional, Tuple


@dataclass
class Motion:
    """Represents a vi motion command."""

    type: str  # 'char', 'line', 'word', 'paragraph', etc.
    count: int = 1
    inclusive: bool = True  # Whether motion includes endpoint
    linewise: bool = False  # Whether motion operates on whole lines


class MotionHandler:
    """Handles cursor motion commands."""

    def __init__(self, state):
        """Initialize motion handler.

        Args:
            state: EditorState instance.
        """
        self.state = state
        self.motions = self._init_motions()

    def _init_motions(self) -> dict[str, Callable]:
        """Initialize motion command mappings."""
        return {
            "h": self.move_left,
            "l": self.move_right,
            "j": self.move_down,
            "k": self.move_up,
            "w": self.move_word_forward,
            "W": self.move_WORD_forward,
            "b": self.move_word_backward,
            "B": self.move_WORD_backward,
            "e": self.move_word_end,
            "E": self.move_WORD_end,
            "0": self.move_line_start,
            "^": self.move_first_non_blank,
            "$": self.move_line_end,
            "g": self.handle_g_motion,
            "G": self.move_to_line,
            "{": self.move_paragraph_backward,
            "}": self.move_paragraph_forward,
            "(": self.move_sentence_backward,
            ")": self.move_sentence_forward,
            "%": self.move_matching_bracket,
            "f": self.find_char_forward,
            "F": self.find_char_backward,
            "t": self.till_char_forward,
            "T": self.till_char_backward,
            ";": self.repeat_char_search,
            ",": self.reverse_char_search,
            "n": self.next_search_match,
            "N": self.prev_search_match,
            "*": self.search_word_forward,
            "#": self.search_word_backward,
        }

    def execute_motion(self, motion_char: str, count: int = 1, arg: Optional[str] = None) -> Optional[Tuple[int, int]]:
        """Execute a motion command.

        Args:
            motion_char: The motion character.
            count: Repeat count.
            arg: Additional argument (for f/F/t/T commands).

        Returns:
            New cursor position or None if invalid motion.
        """
        if motion_char in self.motions:
            handler = self.motions[motion_char]
            if motion_char in ["f", "F", "t", "T"] and arg:
                return handler(count, arg)
            elif motion_char == "g" and arg:
                return self.handle_g_motion(arg, count)
            else:
                return handler(count)
        return None

    def move_left(self, count: int = 1) -> Tuple[int, int]:
        """Move cursor left."""
        cursor = self.state.cursor

        new_col = max(0, cursor.col - count)
        cursor.set_position(cursor.row, new_col)
        return cursor.position

    def move_right(self, count: int = 1) -> Tuple[int, int]:
        """Move cursor right."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        line_len = buffer.get_line_length(cursor.row)
        max_col = max(0, line_len - 1) if self.state.mode_manager.is_normal_mode() else line_len
        new_col = min(max_col, cursor.col + count)
        cursor.set_position(cursor.row, new_col)
        return cursor.position

    def move_down(self, count: int = 1) -> Tuple[int, int]:
        """Move cursor down."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        new_row = min(buffer.line_count - 1, cursor.row + count)
        cursor.set_position(new_row, cursor.col)

        # Adjust column for line length
        line_len = buffer.get_line_length(new_row)
        cursor.adjust_column_for_line(line_len)
        return cursor.position

    def move_up(self, count: int = 1) -> Tuple[int, int]:
        """Move cursor up."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        new_row = max(0, cursor.row - count)
        cursor.set_position(new_row, cursor.col)

        # Adjust column for line length
        line_len = buffer.get_line_length(new_row)
        cursor.adjust_column_for_line(line_len)
        return cursor.position

    def move_word_forward(self, count: int = 1) -> Tuple[int, int]:
        """Move forward by word (lowercase w)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        for _ in range(count):
            row, col = cursor.row, cursor.col
            line = buffer.get_line(row)

            # Skip current word
            while col < len(line) and not line[col].isspace() and line[col].isalnum():
                col += 1

            # Skip punctuation
            while col < len(line) and not line[col].isspace() and not line[col].isalnum():
                col += 1

            # Skip whitespace
            while col < len(line) and line[col].isspace():
                col += 1

            # Move to next line if at end
            if col >= len(line):
                if row < buffer.line_count - 1:
                    row += 1
                    col = 0
                    line = buffer.get_line(row)
                    # Skip leading whitespace on new line
                    while col < len(line) and line[col].isspace():
                        col += 1

            cursor.set_position(row, col)

        return cursor.position

    def move_WORD_forward(self, count: int = 1) -> Tuple[int, int]:
        """Move forward by WORD (uppercase W)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        for _ in range(count):
            row, col = cursor.row, cursor.col
            line = buffer.get_line(row)

            # Skip current WORD (non-whitespace)
            while col < len(line) and not line[col].isspace():
                col += 1

            # Skip whitespace
            while col < len(line) and line[col].isspace():
                col += 1

            # Move to next line if at end
            if col >= len(line):
                if row < buffer.line_count - 1:
                    row += 1
                    col = 0
                    line = buffer.get_line(row)
                    # Skip leading whitespace on new line
                    while col < len(line) and line[col].isspace():
                        col += 1

            cursor.set_position(row, col)

        return cursor.position

    def move_word_backward(self, count: int = 1) -> Tuple[int, int]:
        """Move backward by word (lowercase b)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        for _ in range(count):
            row, col = cursor.row, cursor.col
            line = buffer.get_line(row)

            # Move left one char if not at start
            if col > 0:
                col -= 1
            elif row > 0:
                # Move to end of previous line
                row -= 1
                line = buffer.get_line(row)
                col = len(line) - 1 if line else 0
                cursor.set_position(row, col)
                continue

            # Skip whitespace
            while col > 0 and line[col].isspace():
                col -= 1

            # Move to beginning of word
            if col > 0:
                if line[col].isalnum():
                    while col > 0 and line[col - 1].isalnum():
                        col -= 1
                else:
                    while col > 0 and not line[col - 1].isspace() and not line[col - 1].isalnum():
                        col -= 1

            cursor.set_position(row, col)

        return cursor.position

    def move_WORD_backward(self, count: int = 1) -> Tuple[int, int]:
        """Move backward by WORD (uppercase B)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        for _ in range(count):
            row, col = cursor.row, cursor.col
            line = buffer.get_line(row)

            # Move left one char if not at start
            if col > 0:
                col -= 1
            elif row > 0:
                # Move to end of previous line
                row -= 1
                line = buffer.get_line(row)
                col = len(line) - 1 if line else 0
                cursor.set_position(row, col)
                continue

            # Skip whitespace
            while col > 0 and line[col].isspace():
                col -= 1

            # Move to beginning of WORD
            while col > 0 and not line[col - 1].isspace():
                col -= 1

            cursor.set_position(row, col)

        return cursor.position

    def move_word_end(self, count: int = 1) -> Tuple[int, int]:
        """Move to end of word (lowercase e)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        for _ in range(count):
            row, col = cursor.row, cursor.col
            line = buffer.get_line(row)

            # Move right one char if not at end
            if col < len(line) - 1:
                col += 1
            elif row < buffer.line_count - 1:
                # Move to start of next line
                row += 1
                col = 0
                line = buffer.get_line(row)
                # Skip leading whitespace
                while col < len(line) and line[col].isspace():
                    col += 1
                if col < len(line):
                    cursor.set_position(row, col)
                continue

            # Skip whitespace
            while col < len(line) and line[col].isspace():
                col += 1

            # Move to end of word
            if col < len(line):
                if line[col].isalnum():
                    while col < len(line) - 1 and line[col + 1].isalnum():
                        col += 1
                else:
                    while col < len(line) - 1 and not line[col + 1].isspace() and not line[col + 1].isalnum():
                        col += 1

            cursor.set_position(row, col)

        return cursor.position

    def move_WORD_end(self, count: int = 1) -> Tuple[int, int]:
        """Move to end of WORD (uppercase E)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        for _ in range(count):
            row, col = cursor.row, cursor.col
            line = buffer.get_line(row)

            # Move right one char if not at end
            if col < len(line) - 1:
                col += 1
            elif row < buffer.line_count - 1:
                # Move to start of next line
                row += 1
                col = 0
                line = buffer.get_line(row)
                # Skip leading whitespace
                while col < len(line) and line[col].isspace():
                    col += 1
                if col < len(line):
                    cursor.set_position(row, col)
                continue

            # Skip whitespace
            while col < len(line) and line[col].isspace():
                col += 1

            # Move to end of WORD
            while col < len(line) - 1 and not line[col + 1].isspace():
                col += 1

            cursor.set_position(row, col)

        return cursor.position

    def move_line_start(self, count: int = 1) -> Tuple[int, int]:
        """Move to start of line (0)."""
        cursor = self.state.cursor
        cursor.move_to_line_start()
        return cursor.position

    def move_first_non_blank(self, count: int = 1) -> Tuple[int, int]:
        """Move to first non-blank character (^)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer
        line = buffer.get_line(cursor.row)
        cursor.move_to_first_non_blank(line)
        return cursor.position

    def move_line_end(self, count: int = 1) -> Tuple[int, int]:
        """Move to end of line ($)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        # Apply count to move to end of nth line below
        target_row = min(cursor.row + count - 1, buffer.line_count - 1)
        cursor.set_position(target_row, 0)

        line_len = buffer.get_line_length(target_row)
        cursor.move_to_line_end(line_len)
        return cursor.position

    def move_to_line(self, count: Optional[int] = None) -> Tuple[int, int]:
        """Move to specific line (G command)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        if count is None or count == 0:
            # Go to last line
            target_row = buffer.line_count - 1
        else:
            # Go to specific line (1-indexed)
            target_row = min(count - 1, buffer.line_count - 1)

        cursor.set_position(target_row, 0)
        line = buffer.get_line(target_row)
        cursor.move_to_first_non_blank(line)
        return cursor.position

    def handle_g_motion(self, arg: str, count: int = 1) -> Optional[Tuple[int, int]]:
        """Handle g-prefixed motions."""
        if arg == "g":
            # gg - go to first line
            return self.move_to_line(1)
        elif arg == "0":
            # g0 - go to first column of screen line
            return self.move_line_start()
        elif arg == "^":
            # g^ - go to first non-blank of screen line
            return self.move_first_non_blank()
        elif arg == "$":
            # g$ - go to end of screen line
            return self.move_line_end()
        return None

    def move_paragraph_backward(self, count: int = 1) -> Tuple[int, int]:
        """Move backward by paragraph ({)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        for _ in range(count):
            row = cursor.row

            # Skip current paragraph
            while row > 0 and buffer.get_line(row).strip():
                row -= 1

            # Skip blank lines
            while row > 0 and not buffer.get_line(row).strip():
                row -= 1

            # Move to start of paragraph
            while row > 0 and buffer.get_line(row - 1).strip():
                row -= 1

            cursor.set_position(row, 0)

        return cursor.position

    def move_paragraph_forward(self, count: int = 1) -> Tuple[int, int]:
        """Move forward by paragraph (})."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        for _ in range(count):
            row = cursor.row

            # Skip current paragraph
            while row < buffer.line_count - 1 and buffer.get_line(row).strip():
                row += 1

            # Skip blank lines
            while row < buffer.line_count - 1 and not buffer.get_line(row).strip():
                row += 1

            cursor.set_position(row, 0)

        return cursor.position

    def move_sentence_backward(self, count: int = 1) -> Tuple[int, int]:
        """Move backward by sentence (()."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        # Simplified sentence detection
        for _ in range(count):
            row, col = cursor.row, cursor.col
            found = False

            while row >= 0 and not found:
                line = buffer.get_line(row)

                # Search backward in current line
                search_col = col if row == cursor.row else len(line) - 1

                while search_col > 0:
                    if line[search_col] in ".!?" and search_col < len(line) - 1:
                        # Found end of previous sentence
                        cursor.set_position(row, search_col + 1)
                        found = True
                        break
                    search_col -= 1

                if not found:
                    row -= 1
                    col = len(buffer.get_line(row)) if row >= 0 else 0

        return cursor.position

    def move_sentence_forward(self, count: int = 1) -> Tuple[int, int]:
        """Move forward by sentence ())."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        # Simplified sentence detection
        for _ in range(count):
            row, col = cursor.row, cursor.col
            found = False

            while row < buffer.line_count and not found:
                line = buffer.get_line(row)

                # Search forward in current line
                search_col = col if row == cursor.row else 0

                while search_col < len(line):
                    if line[search_col] in ".!?":
                        # Found end of sentence, move past whitespace
                        search_col += 1
                        while search_col < len(line) and line[search_col].isspace():
                            search_col += 1

                        if search_col < len(line):
                            cursor.set_position(row, search_col)
                        else:
                            # Move to next line
                            if row < buffer.line_count - 1:
                                cursor.set_position(row + 1, 0)
                        found = True
                        break
                    search_col += 1

                if not found:
                    row += 1
                    col = 0

        return cursor.position

    def move_matching_bracket(self, count: int = 1) -> Tuple[int, int]:
        """Move to matching bracket (%)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        line = buffer.get_line(cursor.row)
        if cursor.col >= len(line):
            return cursor.position

        char = line[cursor.col]
        brackets = {"(": ")", "[": "]", "{": "}", ")": "(", "]": "[", "}": "{"}

        if char not in brackets:
            # Search forward on current line for a bracket
            for i in range(cursor.col, len(line)):
                if line[i] in brackets:
                    char = line[i]
                    cursor.set_position(cursor.row, i)
                    break
            else:
                return cursor.position

        match = brackets[char]
        forward = char in "([{"

        count = 1
        row, col = cursor.row, cursor.col

        while 0 <= row < buffer.line_count:
            line = buffer.get_line(row)

            if forward:
                col += 1
                while col < len(line):
                    if line[col] == char:
                        count += 1
                    elif line[col] == match:
                        count -= 1
                        if count == 0:
                            cursor.set_position(row, col)
                            return cursor.position
                    col += 1
                row += 1
                col = -1
            else:
                col -= 1
                while col >= 0:
                    if line[col] == char:
                        count += 1
                    elif line[col] == match:
                        count -= 1
                        if count == 0:
                            cursor.set_position(row, col)
                            return cursor.position
                    col -= 1
                row -= 1
                if row >= 0:
                    col = len(buffer.get_line(row))

        return cursor.position

    def find_char_forward(self, count: int, char: str) -> Tuple[int, int]:
        """Find character forward (f)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        line = buffer.get_line(cursor.row)
        col = cursor.col

        for _ in range(count):
            found_col = line.find(char, col + 1)
            if found_col != -1:
                col = found_col
            else:
                break

        if col != cursor.col:
            cursor.set_position(cursor.row, col)

        # Save for repeat
        self.state.last_char_search = ("f", char)

        return cursor.position

    def find_char_backward(self, count: int, char: str) -> Tuple[int, int]:
        """Find character backward (F)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        line = buffer.get_line(cursor.row)
        col = cursor.col

        for _ in range(count):
            found_col = line.rfind(char, 0, col)
            if found_col != -1:
                col = found_col
            else:
                break

        if col != cursor.col:
            cursor.set_position(cursor.row, col)

        # Save for repeat
        self.state.last_char_search = ("F", char)

        return cursor.position

    def till_char_forward(self, count: int, char: str) -> Tuple[int, int]:
        """Move till character forward (t)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        line = buffer.get_line(cursor.row)
        col = cursor.col

        for _ in range(count):
            found_col = line.find(char, col + 1)
            if found_col != -1 and found_col > 0:
                col = found_col - 1
            else:
                break

        if col != cursor.col:
            cursor.set_position(cursor.row, col)

        # Save for repeat
        self.state.last_char_search = ("t", char)

        return cursor.position

    def till_char_backward(self, count: int, char: str) -> Tuple[int, int]:
        """Move till character backward (T)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        line = buffer.get_line(cursor.row)
        col = cursor.col

        for _ in range(count):
            found_col = line.rfind(char, 0, col)
            if found_col != -1 and found_col < len(line) - 1:
                col = found_col + 1
            else:
                break

        if col != cursor.col:
            cursor.set_position(cursor.row, col)

        # Save for repeat
        self.state.last_char_search = ("T", char)

        return cursor.position

    def repeat_char_search(self, count: int = 1) -> Optional[Tuple[int, int]]:
        """Repeat last character search (;)."""
        if hasattr(self.state, "last_char_search"):
            cmd, char = self.state.last_char_search
            if cmd == "f":
                return self.find_char_forward(count, char)
            elif cmd == "F":
                return self.find_char_backward(count, char)
            elif cmd == "t":
                return self.till_char_forward(count, char)
            elif cmd == "T":
                return self.till_char_backward(count, char)
        return None

    def reverse_char_search(self, count: int = 1) -> Optional[Tuple[int, int]]:
        """Reverse last character search (,)."""
        if hasattr(self.state, "last_char_search"):
            cmd, char = self.state.last_char_search
            if cmd == "f":
                return self.find_char_backward(count, char)
            elif cmd == "F":
                return self.find_char_forward(count, char)
            elif cmd == "t":
                return self.till_char_backward(count, char)
            elif cmd == "T":
                return self.till_char_forward(count, char)
        return None

    def next_search_match(self, count: int = 1) -> Optional[Tuple[int, int]]:
        """Move to next search match (n)."""
        if not self.state.search_state.pattern:
            return None

        cursor = self.state.cursor
        buffer = self.state.current_buffer
        pattern = self.state.search_state.pattern

        for _ in range(count):
            # Search from current position
            text = buffer.get_text()
            lines = text.split("\n")

            # Convert cursor position to text offset
            offset = sum(len(lines[i]) + 1 for i in range(cursor.row)) + cursor.col

            # Search forward
            match = re.search(pattern, text[offset + 1 :])
            if match:
                # Convert match position back to row/col
                match_offset = offset + 1 + match.start()
                row = 0
                while match_offset > len(lines[row]):
                    match_offset -= len(lines[row]) + 1
                    row += 1
                col = match_offset
                cursor.set_position(row, col)
            else:
                # Wrap around
                match = re.search(pattern, text)
                if match:
                    match_offset = match.start()
                    row = 0
                    while match_offset > len(lines[row]):
                        match_offset -= len(lines[row]) + 1
                        row += 1
                    col = match_offset
                    cursor.set_position(row, col)

        return cursor.position

    def prev_search_match(self, count: int = 1) -> Optional[Tuple[int, int]]:
        """Move to previous search match (N)."""
        if not self.state.search_state.pattern:
            return None

        cursor = self.state.cursor
        buffer = self.state.current_buffer
        pattern = self.state.search_state.pattern

        for _ in range(count):
            # Search from current position
            text = buffer.get_text()
            lines = text.split("\n")

            # Convert cursor position to text offset
            offset = sum(len(lines[i]) + 1 for i in range(cursor.row)) + cursor.col

            # Search backward
            matches = list(re.finditer(pattern, text[:offset]))
            if matches:
                match = matches[-1]
                # Convert match position back to row/col
                match_offset = match.start()
                row = 0
                while match_offset > len(lines[row]):
                    match_offset -= len(lines[row]) + 1
                    row += 1
                col = match_offset
                cursor.set_position(row, col)
            else:
                # Wrap around
                matches = list(re.finditer(pattern, text))
                if matches:
                    match = matches[-1]
                    match_offset = match.start()
                    row = 0
                    while match_offset > len(lines[row]):
                        match_offset -= len(lines[row]) + 1
                        row += 1
                    col = match_offset
                    cursor.set_position(row, col)

        return cursor.position

    def search_word_forward(self, count: int = 1) -> Tuple[int, int]:
        """Search for word under cursor forward (*)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        line = buffer.get_line(cursor.row)
        if cursor.col >= len(line):
            return cursor.position

        # Get word under cursor
        col = cursor.col
        while col > 0 and line[col - 1].isalnum():
            col -= 1
        start = col

        while col < len(line) and line[col].isalnum():
            col += 1
        end = col

        if start < end:
            word = line[start:end]
            # Set search pattern
            self.state.search_state.pattern = r"\b" + re.escape(word) + r"\b"
            self.state.search_state.direction = "forward"
            # Execute search
            result = self.next_search_match(count)
            return result if result is not None else cursor.position

        return cursor.position

    def search_word_backward(self, count: int = 1) -> Tuple[int, int]:
        """Search for word under cursor backward (#)."""
        cursor = self.state.cursor
        buffer = self.state.current_buffer

        line = buffer.get_line(cursor.row)
        if cursor.col >= len(line):
            return cursor.position

        # Get word under cursor
        col = cursor.col
        while col > 0 and line[col - 1].isalnum():
            col -= 1
        start = col

        while col < len(line) and line[col].isalnum():
            col += 1
        end = col

        if start < end:
            word = line[start:end]
            # Set search pattern
            self.state.search_state.pattern = r"\b" + re.escape(word) + r"\b"
            self.state.search_state.direction = "backward"
            # Execute search
            result = self.prev_search_match(count)
            return result if result is not None else cursor.position

        return cursor.position
