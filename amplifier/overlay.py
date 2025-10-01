"""Custom directory overlay resolution for Amplifier.

This module provides overlay resolution for custom directories, allowing users to
override official amplifier directory files with their own versions.
"""

from collections.abc import Callable
from pathlib import Path


def create_overlay_resolver(
    custom_dir: Path | None,
    amplifier_base: Path,
) -> Callable[[Path], Path]:
    """Create a resolver function for custom directory overlays.

    Args:
        custom_dir: Path to custom overlay directory (e.g., .amplifier.local/directory)
        amplifier_base: Path to official directory (e.g., .amplifier/directory)

    Returns:
        Resolver function that takes a source path and returns the resolved path
        (custom if exists, original otherwise)

    Examples:
        >>> resolver = create_overlay_resolver(
        ...     Path(".amplifier.local/directory"),
        ...     Path(".amplifier/directory")
        ... )
        >>> resolved = resolver(Path(".amplifier/directory/modes/amplifier-dev/AGENTS.md"))
        >>> # Returns .amplifier.local/directory/modes/amplifier-dev/AGENTS.md if exists
        >>> # Otherwise returns .amplifier/directory/modes/amplifier-dev/AGENTS.md
    """
    if custom_dir is None:
        # No overlay configured, return identity function
        return lambda p: p

    custom_dir = custom_dir.resolve()
    amplifier_base = amplifier_base.resolve()

    def resolver(source_path: Path) -> Path:
        """Resolve source path to custom overlay or original.

        Args:
            source_path: Path to resolve (typically within .amplifier/directory)

        Returns:
            Resolved path (custom if exists, original fallback)
        """
        try:
            # Get relative path from .amplifier/directory
            relative = source_path.relative_to(amplifier_base)
        except ValueError:
            # Path not in amplifier directory, return as-is
            return source_path

        # Check for custom overlay
        custom_path = custom_dir / relative
        if custom_path.exists():
            return custom_path

        # Fallback to original
        return source_path

    return resolver
