"""Core module for the vi editor - fundamental data structures and interfaces."""

from vi_editor.core.buffer import Buffer
from vi_editor.core.cursor import Cursor
from vi_editor.core.mode import Mode, ModeManager
from vi_editor.core.state import EditorState

__all__ = ["Buffer", "Cursor", "Mode", "ModeManager", "EditorState"]
