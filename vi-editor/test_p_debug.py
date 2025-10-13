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

print(f"Before paste: line='{state.current_buffer.get_line(0)}', cursor col={state.cursor.col}")

# Execute paste
normal_handler.handle_command("p")

print(f"After paste: line='{state.current_buffer.get_line(0)}', cursor col={state.cursor.col}")
print("Expected cursor col: 9")
print(f"Character at cursor: '{state.current_buffer.get_line(0)[state.cursor.col]}'")
