#!/usr/bin/env python3
"""Integration test framework that bypasses terminal UI and tests vi logic directly.

This tests the vi editor by simulating keystrokes and verifying file output,
without relying on terminal rendering which doesn't work in Codespaces.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from vi_editor.core.state import EditorState
from vi_editor.core.buffer import Buffer
from vi_editor.core.mode import Mode
from vi_editor.commands.motion import MotionHandler
from vi_editor.commands.normal import NormalCommandHandler
from vi_editor.commands.visual import VisualCommandHandler
from vi_editor.commands.ex import ExCommandHandler
from vi_editor.file_ops.file_handler import FileHandler
from vi_editor.file_ops.backup import BackupManager


class ViSimulator:
    """Simulates vi editor without terminal UI for testing."""
    
    def __init__(self, initial_content: str = ""):
        """Initialize simulator with optional initial content."""
        self.state = EditorState()
        self.file_handler = FileHandler(BackupManager())
        
        # Initialize with content
        if initial_content:
            lines = initial_content.split('\n')
            buffer = Buffer(lines)
            self.state.buffers[0] = buffer
        
        # Command handlers
        self.motion_handler = MotionHandler(self.state)
        self.normal_handler = NormalCommandHandler(self.state, self.motion_handler)
        self.visual_handler = VisualCommandHandler(self.state, self.motion_handler)
        self.ex_handler = ExCommandHandler(self.state, self.file_handler)
    
    def send_keys(self, keys: str) -> None:
        """Send a sequence of keys to the editor.
        
        Special keys:
        - <ESC> - Escape key
        - <CR> or <ENTER> - Enter/return
        - <BS> or <BACKSPACE> - Backspace
        - <TAB> - Tab
        - i, a, o - Enter insert mode
        - : - Enter command mode
        """
        i = 0
        while i < len(keys):
            # Handle special keys
            if keys[i:i+5] == '<ESC>':
                self._process_key('ESC')
                i += 5
            elif keys[i:i+4] == '<CR>' or keys[i:i+7] == '<ENTER>':
                self._process_key('ENTER')
                i += 7 if keys[i:i+7] == '<ENTER>' else 4
            elif keys[i:i+4] == '<BS>' or keys[i:i+11] == '<BACKSPACE>':
                self._process_key('BACKSPACE')
                i += 11 if keys[i:i+11] == '<BACKSPACE>' else 4
            elif keys[i:i+5] == '<TAB>':
                self._process_key('TAB')
                i += 5
            else:
                # Regular character
                self._process_key(keys[i])
                i += 1
    
    def _process_key(self, key: str) -> None:
        """Process a single key based on current mode."""
        mode = self.state.mode_manager.current_mode
        
        if mode == Mode.NORMAL:
            self._process_normal(key)
        elif mode == Mode.INSERT:
            self._process_insert(key)
        elif mode == Mode.VISUAL or mode == Mode.VISUAL_LINE:
            self._process_visual(key)
        elif mode == Mode.COMMAND or mode == Mode.EX:
            self._process_command(key)
    
    def _process_normal(self, key: str) -> None:
        """Process key in normal mode."""
        if key == 'ESC':
            self.state.reset_command_state()
        else:
            self.normal_handler.handle_command(key)
    
    def _process_insert(self, key: str) -> None:
        """Process key in insert mode."""
        buffer = self.state.current_buffer
        cursor = self.state.cursor
        
        if key == 'ESC':
            self.state.mode_manager.set_mode(Mode.NORMAL)
            if cursor.col > 0:
                cursor.move_left()
        elif key == 'ENTER':
            line = buffer.get_line(cursor.row)
            before = line[:cursor.col]
            after = line[cursor.col:]
            buffer.replace_line(cursor.row, before)
            buffer.insert_line(cursor.row + 1, after)
            cursor.move_down()
            cursor.move_to_line_start()
        elif key == 'BACKSPACE':
            if cursor.col > 0:
                cursor.move_left()
                buffer.delete_char(cursor.row, cursor.col)
            elif cursor.row > 0:
                prev_line = buffer.get_line(cursor.row - 1)
                curr_line = buffer.get_line(cursor.row)
                buffer.replace_line(cursor.row - 1, prev_line + curr_line)
                buffer.delete_line(cursor.row)
                cursor.move_up()
                cursor.set_position(cursor.row, len(prev_line))
        elif key == 'TAB':
            buffer.insert_text(cursor.row, cursor.col, '    ')
            cursor.move_right(4)
        elif len(key) == 1 and ord(key) >= 32:
            buffer.insert_char(cursor.row, cursor.col, key)
            cursor.move_right()
    
    def _process_visual(self, key: str) -> None:
        """Process key in visual mode."""
        self.visual_handler.handle_command(key)
    
    def _process_command(self, key: str) -> None:
        """Process key in command mode."""
        if key == 'ESC':
            self.state.mode_manager.set_mode(Mode.NORMAL)
            self.state.command_buffer = ""
        elif key == 'ENTER':
            command = self.state.command_buffer[1:]
            if self.state.command_buffer.startswith(':'):
                self.ex_handler.execute(command)
            self.state.mode_manager.set_mode(Mode.NORMAL)
            self.state.command_buffer = ""
        elif key == 'BACKSPACE':
            if len(self.state.command_buffer) > 1:
                self.state.command_buffer = self.state.command_buffer[:-1]
            else:
                self.state.mode_manager.set_mode(Mode.NORMAL)
                self.state.command_buffer = ""
        elif len(key) == 1 and ord(key) >= 32:
            self.state.command_buffer += key
    
    def get_buffer_content(self) -> str:
        """Get current buffer content as string."""
        return self.state.current_buffer.get_text()
    
    def save_to_file(self, filename: str) -> None:
        """Save current buffer to file."""
        self.state.current_buffer.set_filename(filename)
        self.file_handler.write_file(filename, self.state.current_buffer)
    
    def load_from_file(self, filename: str) -> None:
        """Load file into buffer."""
        buffer = self.file_handler.read_file(filename)
        self.state.buffers[0] = buffer
        self.state.cursor.set_position(0, 0)


def run_test(name: str, initial: str, keys: str, expected: str) -> bool:
    """Run a single integration test.
    
    Args:
        name: Test name
        initial: Initial file content
        keys: Key sequence to send
        expected: Expected final content
        
    Returns:
        True if test passed
    """
    print(f"Running: {name}...", end=" ")
    
    sim = ViSimulator(initial)
    sim.send_keys(keys)
    result = sim.get_buffer_content()
    
    if result == expected:
        print("✅ PASS")
        return True
    else:
        print("❌ FAIL")
        print(f"  Expected:\n{repr(expected)}")
        print(f"  Got:\n{repr(result)}")
        return False


if __name__ == '__main__':
    print("Vi Editor Integration Test Framework")
    print("=" * 50)
    print()
    
    # Example test
    passed = run_test(
        "Insert mode basic",
        "",
        "iHello World<ESC>",
        "Hello World"
    )
    
    sys.exit(0 if passed else 1)
