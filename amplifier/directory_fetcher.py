"""
Directory Fetcher

Fetch directories from git repositories or local paths.
Provides atomic operations with proper cleanup.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from amplifier.directory_source import SourceInfo


def fetch_directory(source: SourceInfo, target: Path) -> None:
    """Fetch a directory from source to target location.

    Args:
        source: Parsed source information
        target: Target directory path

    Raises:
        RuntimeError: If fetch operation fails
        ValueError: If source type is unknown
    """
    if source.type == "git":
        if source.repo is None:
            raise ValueError("Git source requires repository information")
        fetch_git(source.repo, source.path, target)
    elif source.type == "local":
        fetch_local(Path(source.path), target)
    else:
        raise ValueError(f"Unknown source type: {source.type}")


def fetch_git(repo: str, path: str, target: Path) -> None:
    """Fetch a directory from a GitHub repository using sparse checkout.

    Args:
        repo: GitHub repository in format 'username/repo'
        path: Path within the repository
        target: Target directory path

    Raises:
        RuntimeError: If git operations fail
    """
    # Create temporary directory for git operations
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        repo_path = temp_path / "repo"

        try:
            # Initialize git repository with sparse-checkout
            print("Initializing repository...")
            subprocess.run(["git", "init", str(repo_path)], check=True, capture_output=True, text=True)

            # Enable sparse-checkout
            subprocess.run(
                ["git", "sparse-checkout", "init", "--cone"], cwd=repo_path, check=True, capture_output=True, text=True
            )

            # Set the sparse-checkout path
            subprocess.run(
                ["git", "sparse-checkout", "set", path], cwd=repo_path, check=True, capture_output=True, text=True
            )

            # Add remote
            remote_url = f"https://github.com/{repo}.git"
            subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )

            # Fetch only the required directory
            print(f"Fetching {path} from {repo}...")
            result = subprocess.run(
                ["git", "fetch", "--depth=1", "origin", "main"], cwd=repo_path, capture_output=True, text=True
            )

            # If main branch doesn't exist, try master
            if result.returncode != 0:
                print("Trying 'master' branch...")
                subprocess.run(
                    ["git", "fetch", "--depth=1", "origin", "master"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                branch = "master"
            else:
                branch = "main"

            # Checkout the fetched content
            subprocess.run(
                ["git", "checkout", f"origin/{branch}"], cwd=repo_path, check=True, capture_output=True, text=True
            )

            # Copy the specific directory to target
            source_dir = repo_path / path
            if not source_dir.exists():
                raise RuntimeError(f"Directory '{path}' not found in repository {repo}")

            # Ensure parent directory exists
            target.parent.mkdir(parents=True, exist_ok=True)

            # Remove target if it exists
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()

            # Move directory to final location
            shutil.copytree(source_dir, target)
            print(f"Successfully fetched to {target}")

        except subprocess.CalledProcessError as e:
            error_msg = f"Git operation failed: {e.stderr if e.stderr else str(e)}"
            raise RuntimeError(error_msg) from e
        except Exception as e:
            raise RuntimeError(f"Failed to fetch from git: {str(e)}") from e


def fetch_local(source: Path, target: Path) -> None:
    """Fetch a directory from a local path.

    Args:
        source: Source directory path
        target: Target directory path

    Raises:
        RuntimeError: If copy operation fails
        FileNotFoundError: If source doesn't exist
    """
    if not source.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source}")

    if not source.is_dir():
        raise ValueError(f"Source is not a directory: {source}")

    try:
        # Create temporary directory for atomic operation
        with tempfile.TemporaryDirectory(dir=target.parent if target.parent.exists() else None) as temp_dir:
            temp_path = Path(temp_dir) / "directory"

            # Copy to temporary location
            print(f"Copying from {source} to temporary location...")
            shutil.copytree(source, temp_path, symlinks=True)

            # Ensure parent directory exists
            target.parent.mkdir(parents=True, exist_ok=True)

            # Remove target if it exists
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()

            # Move to final location (atomic on same filesystem)
            shutil.move(str(temp_path), str(target))
            print(f"Successfully copied to {target}")

    except Exception as e:
        raise RuntimeError(f"Failed to copy local directory: {str(e)}") from e
