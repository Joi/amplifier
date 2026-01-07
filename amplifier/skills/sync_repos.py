"""Repository sync skill - Sync all tracked git repositories.

Native Amplifier skill for repository synchronization. Works everywhere:
main session, subagents, SDK, scripts, cron jobs.

Usage:
    from amplifier.skills.sync_repos import sync_all, sync_repo, get_repos

    # Sync all repos (pull only)
    results = await sync_all()

    # Sync all repos with push
    results = await sync_all(push=True)

    # Sync a single repo
    success, message = await sync_repo("~/projects/my-repo")

    # Get list of tracked repos
    repos = get_repos()
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


# Default repos.json location
REPOS_FILE = Path.home() / "switchboard/amplifier/repos.json"


@dataclass
class Repo:
    """Represents a tracked repository."""

    name: str
    local_path: str
    remote_url: str | None = None
    branch: str | None = None


@dataclass
class SyncResult:
    """Result of syncing a repository."""

    name: str
    path: str
    success: bool
    message: str


def get_repos(repos_file: Path | str | None = None) -> list[Repo]:
    """Get list of tracked repositories from repos.json.

    Args:
        repos_file: Path to repos.json (default: ~/switchboard/amplifier/repos.json)

    Returns:
        List of Repo objects

    Raises:
        FileNotFoundError: If repos.json doesn't exist
    """
    repos_path = Path(repos_file) if repos_file else REPOS_FILE

    if not repos_path.exists():
        raise FileNotFoundError(
            f"repos.json not found at {repos_path}\n"
            "Run: cd ~/obs-dailynotes && npm run repos:scan"
        )

    data = json.loads(repos_path.read_text())
    repos = data.get("repos", [])

    return [
        Repo(
            name=r.get("name", "unknown"),
            local_path=r.get("localPath", ""),
            remote_url=r.get("remoteUrl"),
            branch=r.get("branch"),
        )
        for r in repos
    ]


async def sync_repo(
    path: str | Path,
    push: bool = False,
    timeout: int = 30,
) -> tuple[bool, str]:
    """Sync a single repository.

    Args:
        path: Path to the repository
        push: Also push after pulling
        timeout: Timeout in seconds for git operations

    Returns:
        Tuple of (success, message)
    """
    repo_path = Path(path).expanduser()

    if not repo_path.exists():
        return (False, "Not found locally")

    if not (repo_path / ".git").exists():
        return (False, "Not a git repository")

    def _sync():
        try:
            # Pull from remote
            result = subprocess.run(
                ["git", "pull"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                return (False, result.stderr.strip() or "Pull failed")

            # Push if requested
            if push:
                result = subprocess.run(
                    ["git", "push"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if result.returncode != 0:
                    return (False, f"Pull OK, push failed: {result.stderr.strip()}")

            return (True, "Synced" + (" (pulled & pushed)" if push else ""))

        except subprocess.TimeoutExpired:
            return (False, f"Timeout ({timeout}s)")
        except Exception as e:
            return (False, str(e))

    # Run in thread pool for async compatibility
    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def sync_all(
    push: bool = False,
    repos_file: Path | str | None = None,
    timeout: int = 30,
) -> list[SyncResult]:
    """Sync all tracked repositories.

    Args:
        push: Also push after pulling
        repos_file: Path to repos.json
        timeout: Timeout per repo in seconds

    Returns:
        List of SyncResult objects
    """
    repos = get_repos(repos_file)

    if not repos:
        return []

    results = []

    # Sync repos sequentially to avoid overwhelming git/network
    for repo in repos:
        success, message = await sync_repo(repo.local_path, push=push, timeout=timeout)
        results.append(
            SyncResult(
                name=repo.name,
                path=repo.local_path,
                success=success,
                message=message,
            )
        )

    return results


def sync_all_sync(
    push: bool = False,
    repos_file: Path | str | None = None,
    timeout: int = 30,
) -> list[SyncResult]:
    """Synchronous wrapper for sync_all.

    See sync_all() for full documentation.
    """
    return asyncio.run(sync_all(push=push, repos_file=repos_file, timeout=timeout))


def get_status(path: str | Path) -> dict:
    """Get git status for a repository.

    Args:
        path: Path to the repository

    Returns:
        Dict with status info (branch, ahead, behind, dirty)
    """
    repo_path = Path(path).expanduser()

    if not repo_path.exists() or not (repo_path / ".git").exists():
        return {"error": "Not a git repository"}

    try:
        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        branch = result.stdout.strip() if result.returncode == 0 else "unknown"

        # Get ahead/behind counts
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", f"{branch}...@{{u}}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            ahead = int(parts[0]) if len(parts) > 0 else 0
            behind = int(parts[1]) if len(parts) > 1 else 0
        else:
            ahead, behind = 0, 0

        # Check for uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        dirty = bool(result.stdout.strip())

        return {
            "branch": branch,
            "ahead": ahead,
            "behind": behind,
            "dirty": dirty,
        }

    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# CLI Interface
# =============================================================================


def _cli_main() -> None:
    """CLI entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Sync all tracked git repositories")
    parser.add_argument(
        "--push",
        action="store_true",
        help="Also push after pulling",
    )
    parser.add_argument(
        "--repos-file",
        type=Path,
        default=REPOS_FILE,
        help=f"Path to repos.json (default: {REPOS_FILE})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout per repo in seconds (default: 30)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command")

    # List repos
    list_p = subparsers.add_parser("list", help="List tracked repos")
    list_p.add_argument("--json", action="store_true", help="Output JSON")

    # Status of one repo
    status_p = subparsers.add_parser("status", help="Get status of a repo")
    status_p.add_argument("path", help="Repository path")

    args = parser.parse_args()

    try:
        if args.command == "list":
            repos = get_repos(args.repos_file if hasattr(args, "repos_file") else None)
            if args.json:
                print(json.dumps([r.__dict__ for r in repos], indent=2))
            else:
                print(f"📋 Tracked repositories ({len(repos)}):\n")
                for r in repos:
                    exists = "✓" if Path(r.local_path).expanduser().exists() else "✗"
                    print(f"  {exists} {r.name}")
                    print(f"    {r.local_path}")

        elif args.command == "status":
            status = get_status(args.path)
            if "error" in status:
                print(f"Error: {status['error']}", file=sys.stderr)
                sys.exit(1)
            print(f"Branch: {status['branch']}")
            print(f"Ahead: {status['ahead']}, Behind: {status['behind']}")
            print(f"Dirty: {'Yes' if status['dirty'] else 'No'}")

        else:
            # Default: sync all
            repos = get_repos(args.repos_file)
            print(
                f"🔄 Syncing {len(repos)} repositories"
                f"{'  (push enabled)' if args.push else ''}...\n"
            )

            results = sync_all_sync(
                push=args.push,
                repos_file=args.repos_file,
                timeout=args.timeout,
            )

            if args.json:
                print(json.dumps([r.__dict__ for r in results], indent=2))
            else:
                for r in results:
                    status = "✓" if r.success else "✗"
                    print(f"{status} {r.name}: {r.message}")

                synced = sum(1 for r in results if r.success)
                total = len(results)
                icon = "✅" if synced == total else "⚠️"
                print(f"\n{icon} {synced}/{total} repos synced successfully")

                if synced < total:
                    sys.exit(1)

    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
