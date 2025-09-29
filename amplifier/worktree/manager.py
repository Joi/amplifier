"""
Advanced worktree management operations.

This module provides the WorktreeManager class for advanced operations like
stashing/unstashing worktrees and managing worktree metadata.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .utils import get_repo_name


class WorktreeManager:
    """Manages advanced git worktree operations including stashing and restoration."""

    def __init__(self):
        """Initialize the worktree manager.

        Raises:
            SystemExit: If not in a git repository.
        """
        self.git_dir = Path(".git")
        self.stash_file = self.git_dir / "worktree-stash.json"

        if not self.git_dir.exists():
            print("Error: Not in a git repository", file=sys.stderr)
            sys.exit(1)

    def _run_git(self, *args: str) -> tuple[int, str, str]:
        """Run a git command and return results.

        Args:
            *args: Git command arguments.

        Returns:
            tuple: (returncode, stdout, stderr) from the git command.
        """
        result = subprocess.run(["git"] + list(args), capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    def _load_stash_manifest(self) -> dict[str, Any]:
        """Load the stash manifest from disk.

        Returns:
            dict: The stash manifest containing stashed worktree information.
        """
        if not self.stash_file.exists():
            return {"stashed": []}

        try:
            with open(self.stash_file) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {"stashed": []}

    def _save_stash_manifest(self, manifest: dict[str, Any]) -> None:
        """Save the stash manifest to disk atomically.

        Args:
            manifest: The manifest data to save.

        Raises:
            SystemExit: If saving fails.
        """
        temp_file = self.stash_file.with_suffix(".tmp")

        try:
            with open(temp_file, "w") as f:
                json.dump(manifest, f, indent=2)
            temp_file.replace(self.stash_file)
        except OSError as e:
            print(f"Error saving manifest: {e}", file=sys.stderr)
            sys.exit(1)

    def resolve_worktree_path(self, feature_name: str) -> Path | None:
        """Resolve worktree path from feature name.

        Checks for existing worktrees with dot separator first, then hyphen
        for backwards compatibility.

        Args:
            feature_name: The feature/branch name.

        Returns:
            Path or None: The resolved path or None if not found.
        """
        repo_name = get_repo_name()
        main_repo = Path.cwd()

        # Try dot separator first (new format)
        dot_path = main_repo.parent / f"{repo_name}.{feature_name}"
        if dot_path.exists():
            return dot_path

        # Fall back to hyphen separator (old format)
        hyphen_path = main_repo.parent / f"{repo_name}-{feature_name}"
        if hyphen_path.exists():
            return hyphen_path

        return None

    def _get_worktree_info(self, path: str) -> dict[str, str] | None:
        """Get worktree information for a given path.

        Args:
            path: Path to the worktree.

        Returns:
            dict or None: Worktree information or None if not found.
        """
        code, stdout, _ = self._run_git("worktree", "list", "--porcelain")

        if code != 0:
            return None

        # Parse worktree list output
        current_worktree = {}
        for line in stdout.strip().split("\n"):
            if not line:
                if current_worktree.get("worktree") == path:
                    return current_worktree
                current_worktree = {}
            elif line.startswith("worktree "):
                current_worktree["worktree"] = line[9:]
            elif line.startswith("branch "):
                current_worktree["branch"] = line[7:]
            elif line.startswith("HEAD "):
                current_worktree["head"] = line[5:]

        # Check last worktree
        if current_worktree.get("worktree") == path:
            return current_worktree

        return None

    def stash_by_name(self, feature_name: str) -> None:
        """Stash a worktree by feature name.

        Args:
            feature_name: The feature/branch name to stash.

        Raises:
            SystemExit: If worktree not found.
        """
        path = self.resolve_worktree_path(feature_name)
        if not path:
            print(f"Error: Worktree not found for feature: {feature_name}", file=sys.stderr)
            print(f"  Looked for: {get_repo_name()}.{feature_name}", file=sys.stderr)
            print(f"  And: {get_repo_name()}-{feature_name}", file=sys.stderr)
            sys.exit(1)
        self.stash(str(path))

    def unstash_by_name(self, feature_name: str) -> None:
        """Unstash a worktree by feature name.

        Args:
            feature_name: The feature/branch name to unstash.

        Raises:
            SystemExit: If worktree not found.
        """
        path = self.resolve_worktree_path(feature_name)
        if not path:
            print(f"Error: Worktree not found for feature: {feature_name}", file=sys.stderr)
            print(f"  Looked for: {get_repo_name()}.{feature_name}", file=sys.stderr)
            print(f"  And: {get_repo_name()}-{feature_name}", file=sys.stderr)
            sys.exit(1)
        self.unstash(str(path))

    def stash(self, worktree_path: str) -> None:
        """Stash a worktree - hide from git but keep directory.

        Removes git metadata for the worktree while preserving the directory
        and its contents. The worktree information is saved for later restoration.

        Args:
            worktree_path: Path to the worktree to stash.

        Raises:
            SystemExit: If stashing fails.
        """
        # Resolve path
        path = Path(worktree_path).resolve()

        if not path.exists():
            print(f"Error: Worktree path does not exist: {path}", file=sys.stderr)
            sys.exit(1)

        # Get worktree info before removing
        info = self._get_worktree_info(str(path))

        if not info:
            print(f"Error: {path} is not a git worktree", file=sys.stderr)
            sys.exit(1)

        # Find the worktree metadata directory in .git/worktrees
        worktrees_dir = self.git_dir / "worktrees"
        if not worktrees_dir.exists():
            print(f"Error: No worktrees directory found in {self.git_dir}", file=sys.stderr)
            sys.exit(1)

        # Find the matching worktree metadata directory
        worktree_meta_dir = None
        for meta_dir in worktrees_dir.iterdir():
            if meta_dir.is_dir():
                gitdir_file = meta_dir / "gitdir"
                if gitdir_file.exists():
                    try:
                        with open(gitdir_file) as f:
                            stored_path = Path(f.read().strip())
                            # gitdir contains path/.git, so compare parent
                            if stored_path.parent.resolve() == path:
                                worktree_meta_dir = meta_dir
                                break
                    except (OSError, ValueError):
                        continue

        if not worktree_meta_dir:
            print(f"Error: Could not find git metadata for worktree: {path}", file=sys.stderr)
            sys.exit(1)

        # Remove the git metadata directory
        try:
            shutil.rmtree(worktree_meta_dir)
        except OSError as e:
            print(f"Error removing worktree metadata: {e}", file=sys.stderr)
            sys.exit(1)

        # Add to stash manifest
        manifest = self._load_stash_manifest()

        stash_entry = {"path": str(path), "branch": info.get("branch", ""), "head": info.get("head", "")}

        # Avoid duplicates
        if not any(s["path"] == str(path) for s in manifest["stashed"]):
            manifest["stashed"].append(stash_entry)
            self._save_stash_manifest(manifest)

        print(f"✓ Stashed worktree: {path}")
        print(f"  Branch: {info.get('branch', 'unknown')}")

    def unstash(self, worktree_path: str) -> None:
        """Restore a stashed worktree back to git tracking.

        Restores git metadata for a previously stashed worktree, making it
        active again in git's worktree list.

        Args:
            worktree_path: Path to the worktree to unstash.

        Raises:
            SystemExit: If unstashing fails.
        """
        # Resolve path
        path = Path(worktree_path).resolve()

        if not path.exists():
            print(f"Error: Worktree path does not exist: {path}", file=sys.stderr)
            sys.exit(1)

        # Load manifest and find entry
        manifest = self._load_stash_manifest()

        stash_entry = None
        for entry in manifest["stashed"]:
            if Path(entry["path"]).resolve() == path:
                stash_entry = entry
                break

        if not stash_entry:
            print(f"Error: {path} is not in stash", file=sys.stderr)
            sys.exit(1)

        # Re-add worktree
        branch = stash_entry.get("branch", "")

        # Strip refs/heads/ prefix if present
        if branch.startswith("refs/heads/"):
            branch = branch[11:]

        if not branch:
            print("Error: No branch information in stash", file=sys.stderr)
            sys.exit(1)

        # Git worktree add won't work if directory exists
        # So we need to temporarily move it aside
        temp_path = Path(tempfile.mkdtemp(dir=path.parent, prefix=f".{path.name}_temp_"))

        try:
            # Move existing directory to temp location
            shutil.move(str(path), str(temp_path))

            # Add worktree (will create new directory)
            code, _, stderr = self._run_git("worktree", "add", str(path), branch)

            if code != 0:
                # Restore original if failed
                shutil.move(str(temp_path), str(path))
                print(f"Error restoring worktree: {stderr}", file=sys.stderr)
                sys.exit(1)

            # Remove the newly created directory
            shutil.rmtree(str(path))

            # Restore the original directory
            shutil.move(str(temp_path), str(path))

        except Exception as e:
            # Try to restore on any error
            if temp_path.exists() and not path.exists():
                shutil.move(str(temp_path), str(path))
            print(f"Error during unstash: {e}", file=sys.stderr)
            sys.exit(1)

        # Remove from stash manifest
        manifest["stashed"] = [s for s in manifest["stashed"] if Path(s["path"]).resolve() != path]
        self._save_stash_manifest(manifest)

        print(f"✓ Unstashed worktree: {path}")
        print(f"  Branch: {branch}")

    def adopt(self, branch_name: str, worktree_name: str | None = None) -> None:
        """Create local worktree from remote branch.

        Creates a new worktree tracking a remote branch, useful for adopting
        branches created by other developers.

        Args:
            branch_name: Remote branch name (with or without origin/ prefix).
            worktree_name: Optional custom name for the worktree directory.

        Raises:
            SystemExit: If adoption fails.
        """
        # Parse branch name
        if "/" in branch_name and not branch_name.startswith("origin/"):
            remote_branch = f"origin/{branch_name}"
            local_branch = branch_name
        elif branch_name.startswith("origin/"):
            remote_branch = branch_name
            local_branch = branch_name[7:]  # Strip "origin/"
        else:
            remote_branch = f"origin/{branch_name}"
            local_branch = branch_name

        # Determine worktree directory name
        if worktree_name:
            dir_name = worktree_name
        else:
            repo_name = get_repo_name()
            # Replace slashes in branch name with dots
            safe_branch = local_branch.replace("/", ".")
            dir_name = f"{repo_name}.{safe_branch}"

        # Create worktree path
        main_repo = Path.cwd()
        worktree_path = main_repo.parent / dir_name

        # Fetch latest from remote
        print("Fetching latest from origin...")
        code, _, stderr = self._run_git("fetch", "origin")

        if code != 0:
            print(f"Warning: Could not fetch from origin: {stderr}")

        # Create worktree
        print(f"Creating worktree at {worktree_path}...")
        code, _, stderr = self._run_git("worktree", "add", str(worktree_path), "-b", local_branch, remote_branch)

        if code != 0:
            # Try without creating new branch if it already exists
            code, _, stderr = self._run_git("worktree", "add", str(worktree_path), local_branch)

            if code != 0:
                print(f"Error creating worktree: {stderr}", file=sys.stderr)
                sys.exit(1)

        # Set upstream tracking
        original_dir = Path.cwd()
        try:
            os.chdir(worktree_path)
            code, _, stderr = self._run_git("branch", "--set-upstream-to", remote_branch)

            if code != 0:
                print(f"Warning: Could not set upstream: {stderr}")
        finally:
            os.chdir(original_dir)

        print(f"✓ Created worktree: {worktree_path}")
        print(f"  Local branch: {local_branch}")
        print(f"  Tracking: {remote_branch}")

    def list_stashed(self) -> list[dict[str, str]]:
        """List all stashed worktrees.

        Returns:
            list[dict]: List of stashed worktree information.
        """
        manifest = self._load_stash_manifest()
        return manifest.get("stashed", [])
