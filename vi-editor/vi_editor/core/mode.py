"""Mode management for vi editor."""

from enum import Enum, auto
from typing import Callable, Dict, Optional


class Mode(Enum):
    """Vi editor modes."""

    NORMAL = auto()
    INSERT = auto()
    VISUAL = auto()
    VISUAL_LINE = auto()
    VISUAL_BLOCK = auto()
    COMMAND = auto()
    REPLACE = auto()
    EX = auto()


class ModeManager:
    """Manages the current mode and mode transitions."""

    def __init__(self):
        """Initialize the mode manager."""
        self._current_mode = Mode.NORMAL
        self._previous_mode = Mode.NORMAL
        self._mode_callbacks: Dict[Mode, Callable] = {}
        self._visual_start: Optional[tuple[int, int]] = None
        self._visual_end: Optional[tuple[int, int]] = None

    @property
    def current_mode(self) -> Mode:
        """Get the current mode."""
        return self._current_mode

    @property
    def previous_mode(self) -> Mode:
        """Get the previous mode."""
        return self._previous_mode

    def set_mode(self, mode: Mode) -> None:
        """Set the current mode.

        Args:
            mode: The mode to switch to.
        """
        if mode != self._current_mode:
            self._previous_mode = self._current_mode
            self._current_mode = mode

            # Call mode change callback if registered
            if mode in self._mode_callbacks:
                self._mode_callbacks[mode]()

            # Clear visual selection when leaving visual modes
            if self._previous_mode in (Mode.VISUAL, Mode.VISUAL_LINE, Mode.VISUAL_BLOCK):
                if mode not in (Mode.VISUAL, Mode.VISUAL_LINE, Mode.VISUAL_BLOCK):
                    self._visual_start = None
                    self._visual_end = None

    def register_mode_callback(self, mode: Mode, callback: Callable) -> None:
        """Register a callback for mode changes.

        Args:
            mode: The mode to register callback for.
            callback: Function to call when entering this mode.
        """
        self._mode_callbacks[mode] = callback

    def is_insert_mode(self) -> bool:
        """Check if currently in insert mode."""
        return self._current_mode in (Mode.INSERT, Mode.REPLACE)

    def is_visual_mode(self) -> bool:
        """Check if currently in visual mode."""
        return self._current_mode in (Mode.VISUAL, Mode.VISUAL_LINE, Mode.VISUAL_BLOCK)

    def is_normal_mode(self) -> bool:
        """Check if currently in normal mode."""
        return self._current_mode == Mode.NORMAL

    def is_command_mode(self) -> bool:
        """Check if currently in command or ex mode."""
        return self._current_mode in (Mode.COMMAND, Mode.EX)

    def set_visual_selection(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        """Set the visual selection range.

        Args:
            start: Starting position (row, col).
            end: Ending position (row, col).
        """
        self._visual_start = start
        self._visual_end = end

    def get_visual_selection(self) -> Optional[tuple[tuple[int, int], tuple[int, int]]]:
        """Get the current visual selection range.

        Returns:
            Tuple of (start, end) positions or None if no selection.
        """
        if self._visual_start and self._visual_end:
            return (self._visual_start, self._visual_end)
        return None

    def toggle_visual_mode(self, mode_type: str = "char") -> None:
        """Toggle visual mode.

        Args:
            mode_type: Type of visual mode ('char', 'line', 'block').
        """
        if mode_type == "char":
            target_mode = Mode.VISUAL
        elif mode_type == "line":
            target_mode = Mode.VISUAL_LINE
        elif mode_type == "block":
            target_mode = Mode.VISUAL_BLOCK
        else:
            target_mode = Mode.VISUAL

        if self._current_mode == target_mode:
            self.set_mode(Mode.NORMAL)
        else:
            self.set_mode(target_mode)
