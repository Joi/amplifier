"""
Directory Source Parser

Parse directory source strings into structured information.
Handles both git repository and local path formats.
"""

from pathlib import Path
from typing import NamedTuple


class SourceInfo(NamedTuple):
    """Directory source information."""

    type: str  # 'git' or 'local'
    repo: str | None  # GitHub username/repo for git sources
    path: str  # Path within repo or absolute local path


def parse_source(source: str) -> SourceInfo:
    """Parse a directory source string into structured information.

    Args:
        source: Directory source string in format:
            - 'git+username/repo/path' for GitHub repositories
            - '/absolute/path' or 'relative/path' for local directories

    Returns:
        SourceInfo with parsed components

    Raises:
        ValueError: If source format is invalid

    Examples:
        >>> info = parse_source('git+microsoft/amplifier/directory')
        >>> assert info.type == 'git'
        >>> assert info.repo == 'microsoft/amplifier'
        >>> assert info.path == 'directory'

        >>> info = parse_source('/home/user/project')
        >>> assert info.type == 'local'
        >>> assert info.path == '/home/user/project'
    """
    if not source:
        raise ValueError("Source cannot be empty")

    # Check for git source format
    if source.startswith("git+"):
        parts = source[4:].split("/", 2)
        if len(parts) < 3:
            raise ValueError(f"Invalid git source format: '{source}'. Expected: 'git+username/repo/path'")

        username, repo, path = parts[0], parts[1], "/".join(parts[2:])

        if not username or not repo or not path:
            raise ValueError(
                f"Invalid git source format: '{source}'. All components (username, repo, path) must be non-empty"
            )

        return SourceInfo(type="git", repo=f"{username}/{repo}", path=path)

    # Otherwise treat as local path
    path = Path(source)

    # Convert to absolute path if relative
    if not path.is_absolute():
        path = path.resolve()

    return SourceInfo(type="local", repo=None, path=str(path))
