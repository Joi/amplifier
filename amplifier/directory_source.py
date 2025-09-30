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
    branch: str | None = None  # Optional branch for git sources


def parse_source(source: str) -> SourceInfo:
    """Parse a directory source string into structured information.

    Args:
        source: Directory source string in format:
            - 'git+username/repo/path' for GitHub repositories
            - 'git+username/repo/path@branch' to specify a branch
            - 'git+https://github.com/username/repo/path.git' for full URLs
            - 'git+https://github.com/username/repo/path.git@branch' to specify a branch
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

        >>> info = parse_source('git+microsoft/amplifier/directory@dev')
        >>> assert info.type == 'git'
        >>> assert info.repo == 'microsoft/amplifier'
        >>> assert info.path == 'directory'
        >>> assert info.branch == 'dev'

        >>> info = parse_source('/home/user/project')
        >>> assert info.type == 'local'
        >>> assert info.path == '/home/user/project'
    """
    if not source:
        raise ValueError("Source cannot be empty")

    # Check for git source format
    if source.startswith("git+"):
        source_part = source[4:]

        # Extract branch if specified with @branch
        branch = None
        if "@" in source_part:
            source_part, branch = source_part.rsplit("@", 1)

        # Check if this is a full URL
        if "://" in source_part:
            # Full URL format: git+https://github.com/user/repo/path.git
            # Remove .git suffix if present
            source_part = source_part.removesuffix(".git")

            # Split URL to extract repo and path
            # URLs look like: https://github.com/user/repo/path
            parts = source_part.split("/")
            if len(parts) < 5:  # Need at least: https:, , domain, user, repo
                raise ValueError(f"Invalid git URL format: '{source}'. Expected: 'git+https://domain/username/repo/path'")

            # Reconstruct base URL (protocol + domain + user + repo)
            base_url = "/".join(parts[:5])  # https://github.com/user/repo
            path = "/".join(parts[5:]) if len(parts) > 5 else ""

            if not path:
                raise ValueError(f"Invalid git URL format: '{source}'. Must specify a path within the repository")

            return SourceInfo(type="git", repo=base_url, path=path, branch=branch)
        else:
            # Short format: username/repo/path
            parts = source_part.split("/", 2)
            if len(parts) < 3:
                raise ValueError(f"Invalid git source format: '{source}'. Expected: 'git+username/repo/path' or 'git+username/repo/path@branch'")

            username, repo, path = parts[0], parts[1], "/".join(parts[2:])

            if not username or not repo or not path:
                raise ValueError(
                    f"Invalid git source format: '{source}'. All components (username, repo, path) must be non-empty"
                )

            return SourceInfo(type="git", repo=f"{username}/{repo}", path=path, branch=branch)

    # Otherwise treat as local path
    path = Path(source)

    # Convert to absolute path if relative
    if not path.is_absolute():
        path = path.resolve()

    return SourceInfo(type="local", repo=None, path=str(path), branch=None)
