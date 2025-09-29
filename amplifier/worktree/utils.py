"""
Shared utilities for git worktree operations.

This module provides common utility functions used across the worktree package,
including repository name resolution, path handling, and command execution.
"""

import subprocess
import sys
from pathlib import Path


def get_repo_name() -> str:
    """Get the repository name from git.

    Returns:
        str: The repository name derived from the git root directory.

    Raises:
        SystemExit: If not in a git repository.
    """
    try:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(result.stdout.strip()).name
    except subprocess.CalledProcessError:
        print("❌ Error: Not in a git repository.", file=sys.stderr)
        sys.exit(1)


def resolve_worktree_path(feature_name: str) -> Path:
    """Resolve the worktree path from a feature name.

    Creates a path for a worktree based on the repository name and feature name.
    Uses dot separator for consistency (repo.feature).

    Args:
        feature_name: The feature/branch name (without repo prefix).

    Returns:
        Path: The resolved worktree path (sibling to main repo).
    """
    repo_name = get_repo_name()
    current_path = Path.cwd()

    # Navigate to the repository root if we're in a subdirectory
    try:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        repo_root = Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        repo_root = current_path

    # Build worktree path using dot separator
    worktree_name = f"{repo_name}.{feature_name}"
    return repo_root.parent / worktree_name


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    capture_output: bool = False,
    env: dict | None = None,
    eval_mode: bool = False,
) -> subprocess.CompletedProcess:
    """Run a command with consistent error handling.

    Args:
        cmd: Command and arguments as a list.
        cwd: Working directory for the command.
        capture_output: Whether to capture stdout/stderr.
        env: Environment variables to use.
        eval_mode: If True, suppress output for shell evaluation.

    Returns:
        subprocess.CompletedProcess: The completed process result.

    Raises:
        subprocess.CalledProcessError: If the command fails.
    """
    try:
        # In eval mode, redirect stdout to stderr to avoid interfering with eval
        if eval_mode and not capture_output:
            result = subprocess.run(
                cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True, check=True, env=env
            )
        else:
            result = subprocess.run(cmd, cwd=cwd, capture_output=capture_output, text=True, check=True, env=env)
        return result
    except subprocess.CalledProcessError as e:
        if capture_output and e.stderr:
            print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
            print(f"Error: {e.stderr}", file=sys.stderr)
        raise


def ensure_not_in_worktree() -> None:
    """Ensure we're not running from within a worktree.

    Checks if the current directory is a worktree and exits with an error
    if it is. This prevents creating worktrees from within worktrees.

    Raises:
        SystemExit: If running from within a worktree or not in a git repo.
    """
    try:
        # Get the main git directory
        result = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=True)
        git_common_dir = Path(result.stdout.strip()).resolve()

        # Get the current git directory
        result = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True, text=True, check=True)
        git_dir = Path(result.stdout.strip()).resolve()

        # If they differ, we're in a worktree
        if git_common_dir != git_dir:
            # Get the main repo path
            main_repo = git_common_dir.parent
            print("❌ Error: Cannot create worktrees from within a worktree.", file=sys.stderr)
            print("\nPlease run this command from the main repository:", file=sys.stderr)
            print(f"  cd {main_repo}", file=sys.stderr)
            sys.exit(1)
    except subprocess.CalledProcessError:
        # Not in a git repository at all
        print("❌ Error: Not in a git repository.", file=sys.stderr)
        sys.exit(1)


def is_in_worktree() -> bool:
    """Check if we're running from within a worktree.

    Returns:
        bool: True if in a worktree (not main repo), False otherwise.
    """
    try:
        # Get the main git directory
        result = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=True)
        git_common_dir = Path(result.stdout.strip()).resolve()

        # Get the current git directory
        result = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True, text=True, check=True)
        git_dir = Path(result.stdout.strip()).resolve()

        # If they differ, we're in a worktree
        return git_common_dir != git_dir
    except subprocess.CalledProcessError:
        return False


def get_worktree_info() -> tuple[str | None, Path | None]:
    """Get current worktree branch and main repo path.

    Returns:
        Tuple[Optional[str], Optional[Path]]: Current branch name and main repo path,
            or (None, None) if not in a worktree or on error.
    """
    try:
        # Get current branch
        result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, check=True)
        current_branch = result.stdout.strip()

        # Get main repo path
        result = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=True)
        git_common_dir = Path(result.stdout.strip()).resolve()
        main_repo = git_common_dir.parent

        return current_branch, main_repo
    except subprocess.CalledProcessError:
        return None, None


def extract_feature_name(branch_name: str) -> str:
    """Extract feature name from branch name.

    Handles branch names with slashes (e.g., feature/my-feature) by
    extracting the last component.

    Args:
        branch_name: Full branch name.

    Returns:
        str: Feature name (last component after '/').
    """
    return branch_name.split("/")[-1] if "/" in branch_name else branch_name
