"""Ex (colon) commands for vi editor."""

import re
from typing import Callable, Optional


class ExCommand:
    """Represents an ex command."""

    def __init__(self, command: str):
        """Initialize ex command.

        Args:
            command: The command string (without the colon).
        """
        self.raw = command
        self.command = ""
        self.args = []
        self.range_start: Optional[int] = None
        self.range_end: Optional[int] = None
        self._parse()

    def _parse(self) -> None:
        """Parse the command string."""
        # Parse range (e.g., 1,5 or % or .)
        match = re.match(r"^([.\d]+)?,?([.\d]+)?(.*)$", self.raw)
        if match:
            start_str, end_str, rest = match.groups()

            # Parse start of range
            if start_str:
                if start_str == ".":
                    self.range_start = "current"
                elif start_str == "$":
                    self.range_start = "last"
                else:
                    try:
                        self.range_start = int(start_str)
                    except ValueError:
                        pass

            # Parse end of range
            if end_str:
                if end_str == ".":
                    self.range_end = "current"
                elif end_str == "$":
                    self.range_end = "last"
                else:
                    try:
                        self.range_end = int(end_str)
                    except ValueError:
                        pass

            # Parse command and args
            if rest:
                parts = rest.strip().split(None, 1)
                if parts:
                    self.command = parts[0]
                    if len(parts) > 1:
                        self.args = parts[1].split()
        else:
            # No range, just command
            parts = self.raw.strip().split(None, 1)
            if parts:
                self.command = parts[0]
                if len(parts) > 1:
                    self.args = parts[1].split()


class ExCommandHandler:
    """Handles ex commands."""

    def __init__(self, state, file_handler=None):
        """Initialize ex command handler.

        Args:
            state: EditorState instance.
            file_handler: FileHandler instance (optional).
        """
        self.state = state
        self.file_handler = file_handler
        self.commands = self._init_commands()

    def _init_commands(self) -> dict[str, Callable]:
        """Initialize ex command mappings."""
        return {
            "q": self.quit,
            "quit": self.quit,
            "q!": self.force_quit,
            "quit!": self.force_quit,
            "w": self.write,
            "write": self.write,
            "wq": self.write_quit,
            "x": self.write_quit,
            "e": self.edit,
            "edit": self.edit,
            "r": self.read,
            "read": self.read,
            "set": self.set_option,
            "s": self.substitute,
            "substitute": self.substitute,
            "%s": self.global_substitute,
            "d": self.delete_lines,
            "delete": self.delete_lines,
            "y": self.yank_lines,
            "yank": self.yank_lines,
            "put": self.put_lines,
            "undo": self.undo,
            "redo": self.redo,
            "n": self.next_file,
            "next": self.next_file,
            "prev": self.prev_file,
            "previous": self.prev_file,
            "bn": self.next_buffer,
            "bnext": self.next_buffer,
            "bp": self.prev_buffer,
            "bprev": self.prev_buffer,
            "bd": self.delete_buffer,
            "bdelete": self.delete_buffer,
            "ls": self.list_buffers,
            "buffers": self.list_buffers,
            "marks": self.list_marks,
            "registers": self.list_registers,
            "help": self.show_help,
            "version": self.show_version,
        }

    def execute(self, command_str: str) -> bool:
        """Execute an ex command.

        Args:
            command_str: The command string (without the colon).

        Returns:
            True if command executed successfully, False otherwise.
        """
        if not command_str:
            return False

        # Parse command
        cmd = ExCommand(command_str)

        # Handle special cases
        if cmd.raw.startswith("%s"):
            return self.global_substitute(cmd)

        # Look for command handler
        handler = self.commands.get(cmd.command)
        if handler:
            try:
                return handler(cmd)
            except Exception as e:
                self.state.set_status(f"Error: {str(e)}", "error")
                return False

        # Check for abbreviations
        for full_cmd, handler in self.commands.items():
            if full_cmd.startswith(cmd.command):
                try:
                    return handler(cmd)
                except Exception as e:
                    self.state.set_status(f"Error: {str(e)}", "error")
                    return False

        self.state.set_status(f"Unknown command: {cmd.command}", "error")
        return False

    # File commands
    def quit(self, cmd: ExCommand) -> bool:
        """Quit the editor."""
        buffer = self.state.current_buffer
        if buffer.modified:
            self.state.set_status("No write since last change (add ! to override)", "warning")
            return False
        return "quit"  # Special return value to signal quit

    def force_quit(self, cmd: ExCommand) -> bool:
        """Force quit without saving."""
        return "quit"  # Special return value to signal quit

    def write(self, cmd: ExCommand) -> bool:
        """Write the current buffer."""
        if not self.file_handler:
            self.state.set_status("No file handler available", "error")
            return False

        buffer = self.state.current_buffer
        filename = cmd.args[0] if cmd.args else buffer.filename

        if not filename:
            self.state.set_status("No file name", "error")
            return False

        try:
            lines_written = self.file_handler.write_file(filename, buffer)
            buffer.set_filename(filename)
            self.state.set_status(f'"{filename}" {lines_written}L written', "info")
            return True
        except Exception as e:
            self.state.set_status(f"Error writing file: {str(e)}", "error")
            return False

    def write_quit(self, cmd: ExCommand) -> bool:
        """Write and quit."""
        if self.write(cmd):
            return "quit"
        return False

    def edit(self, cmd: ExCommand) -> bool:
        """Edit a file."""
        if not self.file_handler or not cmd.args:
            self.state.set_status("Usage: :e filename", "error")
            return False

        filename = cmd.args[0]
        try:
            buffer = self.file_handler.read_file(filename)
            buffer.set_filename(filename)

            # Add buffer to state
            index = self.state.add_buffer(buffer)
            self.state.switch_buffer(index)

            self.state.set_status(f'"{filename}" {buffer.line_count}L', "info")
            return True
        except FileNotFoundError:
            # Create new buffer for new file
            buffer = self.state.current_buffer
            buffer.clear()
            buffer.set_filename(filename)
            self.state.set_status(f'"{filename}" [New File]', "info")
            return True
        except Exception as e:
            self.state.set_status(f"Error reading file: {str(e)}", "error")
            return False

    def read(self, cmd: ExCommand) -> bool:
        """Read a file into current buffer."""
        if not self.file_handler or not cmd.args:
            self.state.set_status("Usage: :r filename", "error")
            return False

        filename = cmd.args[0]
        try:
            temp_buffer = self.file_handler.read_file(filename)
            buffer = self.state.current_buffer
            cursor = self.state.cursor

            # Insert content at cursor position
            for i, line in enumerate(temp_buffer.lines):
                buffer.insert_line(cursor.row + i + 1, line)

            self.state.set_status(f'"{filename}" {temp_buffer.line_count}L read', "info")
            return True
        except Exception as e:
            self.state.set_status(f"Error reading file: {str(e)}", "error")
            return False

    # Options
    def set_option(self, cmd: ExCommand) -> bool:
        """Set editor options."""
        if not cmd.args:
            # Show all options
            options = []
            for key, value in self.state.config.items():
                if isinstance(value, bool):
                    if value:
                        options.append(key)
                    else:
                        options.append(f"no{key}")
                else:
                    options.append(f"{key}={value}")
            self.state.set_status(" ".join(options), "info")
            return True

        for arg in cmd.args:
            if "=" in arg:
                # Set option with value
                key, value = arg.split("=", 1)
                try:
                    # Try to convert to appropriate type
                    if value.lower() in ("true", "false"):
                        value = value.lower() == "true"
                    elif value.isdigit():
                        value = int(value)
                    self.state.set_config(key, value)
                except Exception:
                    self.state.set_status(f"Invalid option: {arg}", "error")
                    return False
            elif arg.startswith("no"):
                # Boolean option - set to false
                key = arg[2:]
                self.state.set_config(key, False)
            else:
                # Boolean option - set to true
                self.state.set_config(arg, True)

        return True

    # Text manipulation
    def substitute(self, cmd: ExCommand) -> bool:
        """Substitute text on current or specified lines."""
        if not cmd.args:
            self.state.set_status("Usage: :s/pattern/replacement/[flags]", "error")
            return False

        # Parse substitution command
        arg = " ".join(cmd.args)

        # Find delimiter (usually /)
        if arg and arg[0] in "/\\|":
            delim = arg[0]
            parts = arg.split(delim)
            if len(parts) >= 3:
                pattern = parts[1]
                replacement = parts[2]
                flags = parts[3] if len(parts) > 3 else ""

                return self._do_substitution(cmd, pattern, replacement, flags)

        self.state.set_status("Invalid substitution syntax", "error")
        return False

    def global_substitute(self, cmd: ExCommand) -> bool:
        """Global substitution."""
        # Set range to whole file if not specified
        if cmd.range_start is None:
            cmd.range_start = 1
            cmd.range_end = "last"

        return self.substitute(cmd)

    def _do_substitution(self, cmd: ExCommand, pattern: str, replacement: str, flags: str) -> bool:
        """Perform the actual substitution."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        # Determine range
        start_row = self._resolve_line(cmd.range_start) if cmd.range_start else cursor.row
        end_row = self._resolve_line(cmd.range_end) if cmd.range_end else start_row

        # Ensure valid range
        start_row = max(0, min(start_row, buffer.line_count - 1))
        end_row = max(0, min(end_row, buffer.line_count - 1))

        if start_row > end_row:
            start_row, end_row = end_row, start_row

        # Compile pattern
        regex_flags = 0
        if "i" in flags:
            regex_flags |= re.IGNORECASE

        try:
            compiled = re.compile(pattern, regex_flags)
        except re.error as e:
            self.state.set_status(f"Invalid pattern: {str(e)}", "error")
            return False

        # Perform substitution
        changes = 0
        for row in range(start_row, end_row + 1):
            line = buffer.get_line(row)

            if "g" in flags:
                # Global replacement
                new_line, count = compiled.subn(replacement, line)
            else:
                # Single replacement
                new_line, count = compiled.subn(replacement, line, count=1)

            if count > 0:
                buffer.replace_line(row, new_line)
                changes += count

        if changes > 0:
            self.state.set_status(f"{changes} substitution(s)", "info")
        else:
            self.state.set_status("Pattern not found", "warning")

        return True

    def delete_lines(self, cmd: ExCommand) -> bool:
        """Delete lines."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        # Determine range
        start_row = self._resolve_line(cmd.range_start) if cmd.range_start else cursor.row
        end_row = self._resolve_line(cmd.range_end) if cmd.range_end else start_row

        # Ensure valid range
        start_row = max(0, min(start_row, buffer.line_count - 1))
        end_row = max(0, min(end_row, buffer.line_count - 1))

        if start_row > end_row:
            start_row, end_row = end_row, start_row

        # Delete lines
        deleted_lines = []
        for _ in range(end_row - start_row + 1):
            if start_row < buffer.line_count:
                line = buffer.delete_line(start_row)
                if line:
                    deleted_lines.append(line)

        if deleted_lines:
            buffer.set_register('"', "\n".join(deleted_lines) + "\n")
            self.state.set_status(f"{len(deleted_lines)} line(s) deleted", "info")

        # Adjust cursor
        if cursor.row >= buffer.line_count:
            cursor.set_position(buffer.line_count - 1, 0)

        return True

    def yank_lines(self, cmd: ExCommand) -> bool:
        """Yank lines."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        # Determine range
        start_row = self._resolve_line(cmd.range_start) if cmd.range_start else cursor.row
        end_row = self._resolve_line(cmd.range_end) if cmd.range_end else start_row

        # Ensure valid range
        start_row = max(0, min(start_row, buffer.line_count - 1))
        end_row = max(0, min(end_row, buffer.line_count - 1))

        if start_row > end_row:
            start_row, end_row = end_row, start_row

        # Yank lines
        lines = []
        for row in range(start_row, end_row + 1):
            lines.append(buffer.get_line(row))

        if lines:
            buffer.set_register('"', "\n".join(lines) + "\n")
            self.state.set_status(f"{len(lines)} line(s) yanked", "info")

        return True

    def put_lines(self, cmd: ExCommand) -> bool:
        """Put yanked lines."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor

        text = buffer.get_register('"')
        if not text:
            self.state.set_status("Nothing to put", "warning")
            return False

        lines = text.rstrip("\n").split("\n")
        for i, line in enumerate(lines):
            buffer.insert_line(cursor.row + i + 1, line)

        self.state.set_status(f"{len(lines)} line(s) put", "info")
        return True

    # Undo/Redo
    def undo(self, cmd: ExCommand) -> bool:
        """Undo changes."""
        buffer = self.state.current_buffer
        pos = buffer.undo()
        if pos:
            self.state.cursor.set_position(pos[0], pos[1])
            self.state.set_status("Undo", "info")
            return True
        else:
            self.state.set_status("Already at oldest change", "warning")
            return False

    def redo(self, cmd: ExCommand) -> bool:
        """Redo changes."""
        buffer = self.state.current_buffer
        pos = buffer.redo()
        if pos:
            self.state.cursor.set_position(pos[0], pos[1])
            self.state.set_status("Redo", "info")
            return True
        else:
            self.state.set_status("Already at newest change", "warning")
            return False

    # Buffer management
    def next_file(self, cmd: ExCommand) -> bool:
        """Go to next file."""
        # This would be implemented with file list management
        self.state.set_status("Not implemented", "warning")
        return False

    def prev_file(self, cmd: ExCommand) -> bool:
        """Go to previous file."""
        # This would be implemented with file list management
        self.state.set_status("Not implemented", "warning")
        return False

    def next_buffer(self, cmd: ExCommand) -> bool:
        """Go to next buffer."""
        current = self.state.current_buffer_index
        next_index = (current + 1) % len(self.state.buffers)
        self.state.switch_buffer(next_index)

        buffer = self.state.buffers[next_index]
        name = buffer.filename or "[No Name]"
        self.state.set_status(f"Buffer {next_index + 1}: {name}", "info")
        return True

    def prev_buffer(self, cmd: ExCommand) -> bool:
        """Go to previous buffer."""
        current = self.state.current_buffer_index
        prev_index = (current - 1) % len(self.state.buffers)
        self.state.switch_buffer(prev_index)

        buffer = self.state.buffers[prev_index]
        name = buffer.filename or "[No Name]"
        self.state.set_status(f"Buffer {prev_index + 1}: {name}", "info")
        return True

    def delete_buffer(self, cmd: ExCommand) -> bool:
        """Delete current buffer."""
        if self.state.close_buffer():
            self.state.set_status("Buffer deleted", "info")
            return True
        else:
            self.state.set_status("Cannot delete last buffer", "warning")
            return False

    def list_buffers(self, cmd: ExCommand) -> bool:
        """List all buffers."""
        lines = []
        for i, buffer in enumerate(self.state.buffers):
            marker = "%" if i == self.state.current_buffer_index else " "
            modified = "+" if buffer.modified else " "
            name = buffer.filename or "[No Name]"
            lines.append(f"{i + 1:3}{marker}{modified} {name}")

        self.state.set_status("\n".join(lines), "info", timeout=10)
        return True

    # Info commands
    def list_marks(self, cmd: ExCommand) -> bool:
        """List all marks."""
        buffer = self.state.current_buffer
        marks = []

        for mark, pos in sorted(buffer._marks.items()):
            line = buffer.get_line(pos[0])[:40]
            marks.append(f" {mark} {pos[0] + 1:4} {pos[1]:3}  {line}")

        if marks:
            self.state.set_status("mark line  col  text\n" + "\n".join(marks), "info", timeout=10)
        else:
            self.state.set_status("No marks set", "info")

        return True

    def list_registers(self, cmd: ExCommand) -> bool:
        """List all registers."""
        buffer = self.state.current_buffer
        registers = []

        for reg, content in sorted(buffer._registers.items()):
            # Truncate long content
            display = content[:50].replace("\n", "^J")
            if len(content) > 50:
                display += "..."
            registers.append(f'"{reg}   {display}')

        if registers:
            self.state.set_status("\n".join(registers), "info", timeout=10)
        else:
            self.state.set_status("No registers set", "info")

        return True

    def show_help(self, cmd: ExCommand) -> bool:
        """Show help."""
        help_text = """Vi Editor Commands:

Movement: h j k l w b e 0 $ ^ G gg
Insert: i I a A o O
Delete: x X dd D
Change: cc C s S
Yank: yy Y
Put: p P
Undo: u
Search: / ? n N * #
Marks: m' `
Visual: v V

Ex Commands:
:w - write  :q - quit  :wq - write & quit
:e file - edit file  :r file - read file
:s/old/new/ - substitute
:%s/old/new/g - global substitute
:set option - set option
"""
        self.state.set_status(help_text, "info", timeout=30)
        return True

    def show_version(self, cmd: ExCommand) -> bool:
        """Show version information."""
        self.state.set_status("Vi Editor Clone v0.1.0", "info")
        return True

    # Helper methods
    def _resolve_line(self, line_spec) -> int:
        """Resolve a line specification to actual line number."""
        if line_spec == "current":
            return self.state.cursor.row
        elif line_spec == "last":
            return self.state.current_buffer.line_count - 1
        elif isinstance(line_spec, int):
            # Convert 1-based to 0-based
            return line_spec - 1
        else:
            return self.state.cursor.row
