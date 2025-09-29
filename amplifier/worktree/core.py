"""
Core git worktree operations.

This module provides the fundamental worktree operations including creation,
removal, and setup of development environments within worktrees.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .utils import ensure_not_in_worktree
from .utils import extract_feature_name
from .utils import get_worktree_info
from .utils import is_in_worktree
from .utils import resolve_worktree_path
from .utils import run_command


def create_worktree(branch_name: str, adopt_remote: bool = False, eval_mode: bool = False) -> Path:
    """Create a git worktree for a branch.

    Creates a new worktree in a sibling directory to the main repository.
    If the branch doesn't exist locally, it will be created.
    If adopt_remote is True, creates a local branch tracking a remote branch.

    Args:
        branch_name: Name of the branch to create worktree for.
        adopt_remote: If True, create from remote branch (assumes origin/).
        eval_mode: If True, suppress output for shell evaluation.

    Returns:
        Path: The path to the created worktree.

    Raises:
        SystemExit: If not in a git repository or if creation fails.
    """
    # Ensure we're not in a worktree
    ensure_not_in_worktree()

    # Extract feature name for directory
    feature_name = extract_feature_name(branch_name)
    worktree_path = resolve_worktree_path(feature_name)

    # Handle remote branch adoption
    if adopt_remote:
        if "/" in branch_name and not branch_name.startswith("origin/"):
            remote_branch = f"origin/{branch_name}"
            local_branch = branch_name
        elif branch_name.startswith("origin/"):
            remote_branch = branch_name
            local_branch = branch_name[7:]  # Strip "origin/"
        else:
            remote_branch = f"origin/{branch_name}"
            local_branch = branch_name

        # Fetch from remote
        if not eval_mode:
            print("Fetching latest from origin...")
        try:
            run_command(["git", "fetch", "origin"], eval_mode=eval_mode)
        except subprocess.CalledProcessError as e:
            if not eval_mode:
                print(f"Warning: Could not fetch from origin: {e}")

        # Create worktree with remote tracking
        if not eval_mode:
            print(f"Creating worktree at {worktree_path}...")
        try:
            run_command(
                ["git", "worktree", "add", str(worktree_path), "-b", local_branch, remote_branch], eval_mode=eval_mode
            )
        except subprocess.CalledProcessError:
            # Try without creating new branch if it already exists
            try:
                run_command(["git", "worktree", "add", str(worktree_path), local_branch], eval_mode=eval_mode)
            except subprocess.CalledProcessError as e:
                print(f"Failed to create worktree: {e}", file=sys.stderr)
                sys.exit(1)

        # Set upstream tracking
        original_dir = Path.cwd()
        try:
            os.chdir(worktree_path)
            run_command(["git", "branch", "--set-upstream-to", remote_branch], eval_mode=eval_mode)
        except subprocess.CalledProcessError as e:
            if not eval_mode:
                print(f"Warning: Could not set upstream: {e}")
        finally:
            os.chdir(original_dir)

    else:
        # Create worktree for local branch
        if not eval_mode:
            print(f"Creating worktree at {worktree_path}...")
        try:
            # Check if branch exists locally
            result = subprocess.run(["git", "rev-parse", "--verify", branch_name], capture_output=True, text=True)

            if result.returncode == 0:
                # Branch exists, use it
                run_command(["git", "worktree", "add", str(worktree_path), branch_name], eval_mode=eval_mode)
            else:
                # Branch doesn't exist, create it
                run_command(["git", "worktree", "add", "-b", branch_name, str(worktree_path)], eval_mode=eval_mode)
                if not eval_mode:
                    print(f"Created new branch: {branch_name}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to create worktree: {e}", file=sys.stderr)
            sys.exit(1)

    return worktree_path


def remove_worktree(branch_name: str, force: bool = False) -> None:
    """Remove a git worktree and optionally its branch.

    Removes the worktree directory and git metadata. If the branch
    is fully merged, it will also be deleted.

    Args:
        branch_name: Name of the branch/worktree to remove.
                    Use "." to remove current worktree.
        force: Force removal even with uncommitted changes.

    Raises:
        SystemExit: If worktree doesn't exist or removal fails.
    """
    in_worktree = is_in_worktree()
    current_branch, main_repo = get_worktree_info()

    # Handle special case: removing current worktree
    if branch_name == ".":
        if not in_worktree:
            print("❌ Error: Cannot use '.' from the main repository.", file=sys.stderr)
            print("Please specify a branch name to remove.", file=sys.stderr)
            sys.exit(1)

        if not current_branch or not main_repo:
            print("❌ Error: Could not determine worktree information.", file=sys.stderr)
            sys.exit(1)

        print(f"⚠️  WARNING: You are about to remove the current worktree '{current_branch}'")
        print("Your current directory will be deleted after this operation.")
        print("You will need to navigate to a valid directory afterwards.\n")
        branch_name = current_branch
        os.chdir(main_repo)

    elif branch_name == current_branch and in_worktree:
        # User specified current branch name explicitly
        if not main_repo:
            print("❌ Error: Could not determine main repository path.", file=sys.stderr)
            sys.exit(1)

        print(f"⚠️  WARNING: You are removing the worktree you're currently in '{current_branch}'")
        print("Your current directory will be deleted after this operation.\n")
        os.chdir(main_repo)

    elif in_worktree:
        # In a worktree but removing a different one
        if not main_repo:
            print("❌ Error: Could not determine main repository path.", file=sys.stderr)
            sys.exit(1)
        print(f"Switching to main repository at {main_repo} to perform removal...")
        os.chdir(main_repo)

    # Continue with normal removal
    feature_name = extract_feature_name(branch_name)
    worktree_path = resolve_worktree_path(feature_name)

    print(f"Looking for worktree at: {worktree_path}")

    # Check if worktree exists
    result = subprocess.run(["git", "worktree", "list"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error: Failed to list worktrees", file=sys.stderr)
        sys.exit(1)

    if str(worktree_path) not in result.stdout:
        print(f"Error: Worktree for branch '{branch_name}' not found at {worktree_path}", file=sys.stderr)
        sys.exit(1)

    # Remove the worktree
    remove_cmd = ["git", "worktree", "remove", str(worktree_path)]
    if force:
        remove_cmd.append("--force")

    print(f"Removing worktree at {worktree_path}...")
    try:
        run_command(remove_cmd)
        print(f"Successfully removed worktree at {worktree_path}")
    except subprocess.CalledProcessError as e:
        if "contains modified or untracked files" in str(e):
            print("Error: Worktree contains uncommitted changes. Use --force to override.", file=sys.stderr)
        else:
            print(f"Error removing worktree: {e}", file=sys.stderr)
        sys.exit(1)

    # Try to delete the branch
    print(f"Attempting to delete branch '{branch_name}'...")

    # Check current branch
    result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip() == branch_name:
        print(f"Cannot delete branch '{branch_name}' - it is currently checked out")
        return

    # Try to delete the branch
    result = subprocess.run(["git", "branch", "-d", branch_name], capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Successfully deleted branch '{branch_name}'")
    elif "not fully merged" in result.stderr:
        # Try force delete if regular delete fails
        print("Branch has unmerged changes, force deleting...")
        result = subprocess.run(["git", "branch", "-D", branch_name], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Successfully force-deleted branch '{branch_name}'")
        else:
            print(f"Warning: Could not delete branch: {result.stderr}")
    else:
        print(f"Warning: Could not delete branch: {result.stderr}")


def setup_worktree_venv(worktree_path: Path, eval_mode: bool = False) -> bool:
    """Set up a virtual environment for a worktree.

    Creates a new virtual environment in the worktree directory and
    installs dependencies using uv if available.

    Args:
        worktree_path: Path to the worktree directory.
        eval_mode: If True, suppress output for shell evaluation.

    Returns:
        bool: True if venv was set up successfully, False otherwise.
    """
    if not eval_mode:
        print("\n🐍 Setting up virtual environment for worktree...")

    # Check if uv is available
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        if not eval_mode:
            print("⚠️  Warning: 'uv' not found. Please install dependencies manually:")
            print(f"   cd {worktree_path}")
            print("   make install")
        return False

    # Create .venv in the worktree
    if not eval_mode:
        print("Creating .venv in worktree...")
    try:
        # Use uv to create venv and sync dependencies
        run_command(["uv", "venv"], cwd=worktree_path, eval_mode=eval_mode)
        if not eval_mode:
            print("Installing dependencies...")

        # Clean environment to avoid VIRTUAL_ENV warning from parent shell
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)

        # Run with clean environment and reduced verbosity
        run_command(["uv", "sync", "--group", "dev", "--quiet"], cwd=worktree_path, env=env, eval_mode=eval_mode)
        if not eval_mode:
            print("✅ Virtual environment created and dependencies installed!")
        return True
    except subprocess.CalledProcessError as e:
        if not eval_mode:
            print(f"⚠️  Warning: Failed to set up venv automatically: {e}")
            print("   You can set it up manually with: make install")
        return False


def copy_data_directory(source: Path, target: Path, eval_mode: bool = False) -> bool:
    """Copy .data directory from source to target.

    Uses rsync for efficient copying if available, otherwise falls back to cp.

    Args:
        source: Source .data directory path.
        target: Target .data directory path.
        eval_mode: If True, suppress output for shell evaluation.

    Returns:
        bool: True if copy succeeded, False otherwise.
    """
    if not source.exists() or not source.is_dir():
        return False

    if not eval_mode:
        print("\nCopying .data directory (this may take a moment)...")

    try:
        # Try rsync first for efficiency
        if eval_mode:
            run_command(
                [
                    "rsync",
                    "-a",  # archive mode
                    f"{source}/",  # trailing slash to copy contents
                    f"{target}/",
                ],
                eval_mode=True,
            )
        else:
            subprocess.run(
                [
                    "rsync",
                    "-av",  # archive mode with verbose
                    "--progress",  # show progress
                    f"{source}/",
                    f"{target}/",
                ],
                check=True,
            )
            print("Data copy complete!")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to cp
        try:
            shutil.copytree(source, target, dirs_exist_ok=True)
            if not eval_mode:
                print("Data copy complete!")
            return True
        except Exception as e:
            if not eval_mode:
                print(f"Warning: Failed to copy .data directory: {e}")
            return False


def list_worktrees() -> list[dict]:
    """List all git worktrees.

    Returns:
        list[dict]: List of worktree information dictionaries containing:
            - path: Worktree path
            - branch: Branch name
            - commit: Current commit hash
    """
    try:
        result = subprocess.run(["git", "worktree", "list", "--porcelain"], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        return []

    worktrees = []
    current_worktree = {}

    for line in result.stdout.strip().split("\n"):
        if not line:
            if current_worktree:
                worktrees.append(current_worktree)
                current_worktree = {}
        elif line.startswith("worktree "):
            current_worktree["path"] = line[9:]
        elif line.startswith("HEAD "):
            current_worktree["commit"] = line[5:]
        elif line.startswith("branch "):
            current_worktree["branch"] = line[7:]

    # Add last worktree if exists
    if current_worktree:
        worktrees.append(current_worktree)

    return worktrees
