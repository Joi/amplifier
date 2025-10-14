#!/usr/bin/env python3
"""Debug the vi editor to find issues."""

import logging
import sys

from vi_editor.editor import Editor

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="vi_debug.log",
    filemode="w",
)

# Also log to console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)


def main():
    """Debug the vi editor."""
    logging.info("Starting vi editor debug...")

    # Create editor instance
    editor = Editor()

    # Add some debug logging
    logging.info(f"Terminal size: {editor.terminal.get_size()}")
    logging.info(f"Is raw mode: {editor.terminal.is_raw_mode}")

    # Open a test file
    editor.open_file("test.txt")
    logging.info(f"Buffer content: {editor.state.current_buffer.get_text()[:100]}")

    # Run a simplified main loop for debugging
    editor.display.initialize()
    logging.info("Display initialized")

    # Do one render
    editor.display.render(force=True)
    logging.info("Initial render complete")

    # Simulate pressing 'i' for insert mode
    editor._process_input("i")
    logging.info(f"Mode after 'i': {editor.state.mode_manager.current_mode}")

    # Render again
    editor.display.render(force=True)
    logging.info("Render after mode change")

    # Simulate typing
    editor._process_input("X")
    logging.info(f"Buffer after typing 'X': {editor.state.current_buffer.get_line(0)}")

    # Clean up
    editor.display.cleanup()
    logging.info("Cleanup complete")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception(f"Error: {e}")
        sys.exit(1)
