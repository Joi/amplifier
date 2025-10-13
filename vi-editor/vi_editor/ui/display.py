"""Display management for vi editor."""

import time


class Display:
    """Manages the overall display and coordinates rendering."""

    def __init__(self, terminal, renderer, state):
        """Initialize display manager.

        Args:
            terminal: Terminal instance.
            renderer: Renderer instance.
            state: EditorState instance.
        """
        self.terminal = terminal
        self.renderer = renderer
        self.state = state
        self.needs_full_redraw = True
        self.last_render_time = 0
        self.min_render_interval = 0.016  # ~60 FPS

    def initialize(self) -> None:
        """Initialize the display."""
        # Set up terminal
        self.terminal.setup()

        # Enable alternate screen
        self.terminal.enable_alternate_screen()

        # Initial render
        self.render()

    def cleanup(self) -> None:
        """Clean up the display."""
        # Disable alternate screen
        self.terminal.disable_alternate_screen()

        # Clean up terminal
        self.terminal.cleanup()

    def render(self, force: bool = False) -> None:
        """Render the display.

        Args:
            force: Force render even if not needed.
        """
        # Rate limiting
        current_time = time.time()
        if not force and not self.needs_full_redraw:
            if current_time - self.last_render_time < self.min_render_interval:
                return

        # Perform render
        if self.needs_full_redraw:
            self.renderer.render()
            self.needs_full_redraw = False
        else:
            # Partial update
            self._render_partial()

        self.last_render_time = current_time

    def _render_partial(self) -> None:
        """Perform a partial render update."""
        # Update cursor position
        self.renderer._position_cursor()

        # Update status if needed
        if self._status_changed():
            self.renderer.refresh_status()

        # Update command line if needed
        if self._command_changed():
            self.renderer.refresh_command()

    def _status_changed(self) -> bool:
        """Check if status line needs update.

        Returns:
            True if status changed.
        """
        # Check for changes that affect status line
        # This is simplified - real implementation would track changes
        return False

    def _command_changed(self) -> bool:
        """Check if command line needs update.

        Returns:
            True if command line changed.
        """
        # Check for changes that affect command line
        return bool(self.state.command_buffer or self.state.status_message)

    def request_redraw(self) -> None:
        """Request a full redraw on next render."""
        self.needs_full_redraw = True

    def render_line(self, row: int) -> None:
        """Render a specific line.

        Args:
            row: Line number to render.
        """
        self.renderer.refresh_line(row)

    def show_message(self, message: str, msg_type: str = "info", timeout: float = 3.0) -> None:
        """Show a message on the command line.

        Args:
            message: Message to show.
            msg_type: Message type ('info', 'warning', 'error').
            timeout: How long to show the message.
        """
        self.state.set_status(message, msg_type, timeout)
        self.renderer.refresh_command()

    def clear_message(self) -> None:
        """Clear any displayed message."""
        self.state.clear_status()
        self.renderer.refresh_command()

    def handle_resize(self) -> None:
        """Handle terminal resize event."""
        # Update terminal size
        height, width = self.terminal.get_size()

        # Update state viewport
        self.state.viewport_height = height - 2
        self.state.viewport_width = width

        # Request full redraw
        self.request_redraw()
        self.render(force=True)

    def get_input_position(self) -> tuple[int, int]:
        """Get the position for input display.

        Returns:
            Tuple of (row, col) for input position.
        """
        height = self.terminal.height
        return (height - 1, len(self.state.command_buffer))

    def show_line_numbers(self, enabled: bool) -> None:
        """Toggle line number display.

        Args:
            enabled: Whether to show line numbers.
        """
        self.state.set_config("number", enabled)
        self.request_redraw()

    def set_syntax_highlighting(self, enabled: bool) -> None:
        """Toggle syntax highlighting.

        Args:
            enabled: Whether to enable syntax highlighting.
        """
        self.state.set_config("syntax", enabled)
        self.request_redraw()

    def update_cursor_style(self) -> None:
        """Update cursor style based on current mode."""
        from vi_editor.core.mode import Mode

        mode = self.state.mode_manager.current_mode

        if mode == Mode.INSERT:
            self.terminal.set_cursor_style("bar")
        elif mode == Mode.REPLACE:
            self.terminal.set_cursor_style("underline")
        else:
            self.terminal.set_cursor_style("block")
