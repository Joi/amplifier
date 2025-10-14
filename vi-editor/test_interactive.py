#!/usr/bin/env python3
"""Interactive test for vi editor."""

import subprocess
import sys
import time


def test_vi_editor():
    """Test vi editor with automated input."""
    print("Testing vi editor...")

    # Create test file
    with open("test.txt", "w") as f:
        f.write("Hello World\n")

    # Start vi editor
    proc = subprocess.Popen(
        ["python", "-m", "vi_editor.main", "test.txt"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(0.5)  # Let it initialize

    # Send commands
    commands = [
        b"j",  # Move down (should stay on line 1)
        b"l",  # Move right
        b"l",  # Move right again
        b"i",  # Enter insert mode
        b"TEST",  # Type some text
        b"\x1b",  # ESC to exit insert mode
        b":wq\n",  # Save and quit
    ]

    for cmd in commands:
        proc.stdin.write(cmd)
        proc.stdin.flush()
        time.sleep(0.1)

    # Wait for process to finish
    proc.wait(timeout=2)

    # Check if file was saved
    with open("test.txt", "r") as f:
        content = f.read()
        print(f"File content after edit: {repr(content)}")
        if "TEST" in content:
            print("✓ Edit was successful!")
        else:
            print("✗ Edit failed - content not saved")

    return proc.returncode == 0


if __name__ == "__main__":
    try:
        success = test_vi_editor()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
