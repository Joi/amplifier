from vi_editor.commands.motion import MotionHandler
from vi_editor.commands.normal import NormalCommandHandler
from vi_editor.core.buffer import Buffer
from vi_editor.core.state import EditorState

# Setup
state = EditorState()
motion_handler = MotionHandler(state)
normal_handler = NormalCommandHandler(state, motion_handler)

# Test setup
state.buffers[0] = Buffer(["hello world"])
state.current_buffer.set_register('"', "TEXT")
state.cursor.set_position(0, 4)

line = state.current_buffer.get_line(0)
print(f"Original line: '{line}'")
print(f"Cursor at col {state.cursor.col}, char: '{line[state.cursor.col]}'")
print()

# Where will text be inserted?
insert_pos = state.cursor.col + 1
print(f"Text will be inserted at position {insert_pos}")
print(f"Text is 'TEXT' (length {len('TEXT')})")
print(f"So text will occupy positions {insert_pos} to {insert_pos + len('TEXT') - 1}")
print()

# Execute paste
normal_handler.handle_command("p")

result_line = state.current_buffer.get_line(0)
print(f"Result line: '{result_line}'")
print(f"Cursor at col {state.cursor.col}")
if state.cursor.col < len(result_line):
    print(f"Cursor char: '{result_line[state.cursor.col]}'")
print()

# What does the test expect?
print("Test expects cursor at col 9")
if 9 < len(result_line):
    print(f"Character at col 9: '{result_line[9]}'")

# Analysis
print("\nAnalysis:")
print(f"Text was inserted starting at position {insert_pos}")
print(f"Last character of 'TEXT' is at position {insert_pos + len('TEXT') - 1}")
print(
    f"Test expects cursor at position 9, which is {9 - (insert_pos + len('TEXT') - 1)} positions after the last character"
)
