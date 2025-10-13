"""Vi Editor Clone - A complete vi implementation in Python."""

__version__ = "0.1.0"
__author__ = "Vi Editor Team"

from vi_editor.buffer import Buffer
from vi_editor.editor import Editor

__all__ = ["Editor", "Buffer", "__version__"]
