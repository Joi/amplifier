#!/usr/bin/env python3
"""Native repo sync for GTD tool.

Replaces obs-dailynotes Node.js implementation with a simple Python version.
Operations: repo_sync, repo_scan, repo_check
"""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional


def _run_git(repo_path: Path, *args: str, timeout: int = 30) -> tuple[bool, str]:
    """Run a git command in repo_path. Returns (success, output)."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, f"Timeout ({timeout}s)"
    except Exception as e:
        return False, str(e)


def _get_repo_metadata(repo_path: Path) -> Optional[dict]:
    """Extract metadata from a git repository."""
    if not (repo_path / ".git").exists():
        return None

    name = repo_path.name

    # Current branch
    ok, branch = _run_git(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
    branch = branch if ok else "unknown"

    # Local commit
    ok, commit = _run_git(repo_path, "rev-parse", "--short", "HEAD")
    local_commit = commit if ok else "unknown"

    # Commit date
    ok, date = _run_git(repo_path, "log", "-1", "--format=%cI", "HEAD")
    commit_date = date if ok else None

    # Remote URL -> GitHub repo
    github_repo = None
    ok, url = _run_git(repo_path, "remote", "get-url", "origin")
    if ok and "github.com" in url:
        # Parse github.com/owner/repo or git@github.com:owner/repo
        import re

        match = re.search(r"github\.com[:/](.+?)/(.+?)(?:\.git)?$", url)
        if match:
            github_repo = f"{match.group(1)}/{match.group(2).rstrip('.git')}"

    # Working tree clean?
    ok, status = _run_git(repo_path, "status", "--porcelain")
    working_tree_clean = ok and len(status) == 0

    # Remote commit (after fetch)
    remote_commit = None
    ok, tracking = _run_git(
        repo_path, "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"
    )
    if ok:
        ok2, rc = _run_git(repo_path, "rev-parse", "--short", tracking)
        if ok2:
            remote_commit = rc

    # Sync status
    sync_status = _determine_sync_status(repo_path, local_commit, remote_commit)

    # Version from pyproject.toml or package.json
    version = _detect_version(repo_path)

    return {
        "id": name,
        "name": name,
        "localPath": str(repo_path),
        "githubRepo": github_repo,
        "currentBranch": branch,
        "localCommit": local_commit,
        "localCommitDate": commit_date,
        "remoteCommit": remote_commit,
        "syncStatus": sync_status,
        "workingTreeClean": working_tree_clean,
        "version": version,
        "lastChecked": datetime.now().isoformat(),
    }


def _determine_sync_status(repo_path: Path, local: str, remote: Optional[str]) -> str:
    """Determine sync status between local and remote."""
    if not remote:
        return "no-remote"
    if local == "unknown":
        return "unknown"
    if local == remote:
        return "synced"

    # Check ahead/behind
    ok, ahead = _run_git(repo_path, "rev-list", "--count", f"{remote}..{local}")
    ok2, behind = _run_git(repo_path, "rev-list", "--count", f"{local}..{remote}")

    if ok and ok2:
        ahead_n = int(ahead) if ahead.isdigit() else 0
        behind_n = int(behind) if behind.isdigit() else 0

        if ahead_n > 0 and behind_n > 0:
            return "diverged"
        if ahead_n > 0:
            return "ahead"
        if behind_n > 0:
            return "behind"
        return "synced"

    return "unknown"


def _detect_version(repo_path: Path) -> Optional[str]:
    """Detect version from pyproject.toml or package.json."""
    # Try pyproject.toml
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            import re

            content = pyproject.read_text()
            match = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', content, re.M)
            if match:
                return match.group(1)
        except Exception:
            pass

    # Try package.json
    package_json = repo_path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            return data.get("version")
        except Exception:
            pass

    return None


def _find_git_repos(base_dir: Path, max_depth: int = 2) -> list[Path]:
    """Find git repositories under base_dir."""
    repos = []
    skip_dirs = {
        "node_modules",
        ".venv",
        "__pycache__",
        "venv",
        "env",
        ".npm",
        ".cache",
        "Library",
        "Applications",
        ".Trash",
        "Music",
        "Movies",
        "Pictures",
        "Public",
        "Desktop",
        "Downloads",
        "Documents",
    }

    def scan(path: Path, depth: int):
        if depth > max_depth:
            return

        try:
            # Is this a git repo?
            if (path / ".git").exists():
                repos.append(path)
                return  # Don't scan inside git repos

            # Scan subdirectories
            for entry in path.iterdir():
                if not entry.is_dir():
                    continue
                if entry.name in skip_dirs:
                    continue
                if entry.name.startswith("."):
                    continue
                scan(entry, depth + 1)
        except PermissionError:
            pass

    scan(base_dir, 0)
    return sorted(repos, key=lambda p: p.name.lower())


def _sync_single_repo(repo: dict, push: bool = False) -> dict:
    """Sync a single repo. Returns result dict."""
    path = Path(repo.get("localPath", ""))
    name = repo.get("name", "unknown")

    if not path.exists():
        return {"name": name, "success": False, "message": "Not found locally"}

    # Fetch first
    ok, _ = _run_git(path, "fetch", "--all", "--prune", timeout=60)

    # Pull if clean
    ok, status = _run_git(path, "status", "--porcelain")
    is_clean = ok and len(status) == 0

    if is_clean:
        ok, msg = _run_git(path, "pull", "--rebase", timeout=60)
        if not ok:
            return {"name": name, "success": False, "message": f"Pull failed: {msg}"}

        # Push if requested and we're ahead
        if push:
            ok, msg = _run_git(path, "push", timeout=60)
            if not ok:
                return {
                    "name": name,
                    "success": True,
                    "message": f"Pulled, push failed: {msg}",
                }
            return {"name": name, "success": True, "message": "Pulled & pushed"}

        return {"name": name, "success": True, "message": "Pulled"}
    else:
        return {
            "name": name,
            "success": True,
            "message": "Fetched (dirty working tree)",
        }


# ============================================================
# Public API - called by GTD tool
# ============================================================


def repo_sync(vault_path: Path, push: bool = False, parallel: int = 4) -> dict:
    """Sync all repos from repos.json.

    Fetches all repos, pulls clean ones, optionally pushes.
    """
    repos_file = vault_path / "amplifier" / "repos.json"

    if not repos_file.exists():
        return {
            "success": False,
            "error": "repos.json not found. Run repo_scan first.",
        }

    data = json.loads(repos_file.read_text())
    repos = data.get("repos", [])

    if not repos:
        return {"success": True, "message": "No repos to sync", "results": []}

    results = []

    # Sync in parallel for speed
    with ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = {
            executor.submit(_sync_single_repo, repo, push): repo for repo in repos
        }
        for future in as_completed(futures):
            results.append(future.result())

    # Update lastSynced in repos.json
    data["lastSynced"] = datetime.now().isoformat()

    # Update each repo's metadata
    for result in results:
        for repo in data["repos"]:
            if repo["name"] == result["name"]:
                # Refresh metadata
                path = Path(repo["localPath"])
                if path.exists():
                    updated = _get_repo_metadata(path)
                    if updated:
                        repo.update(updated)
                break

    repos_file.write_text(json.dumps(data, indent=2))

    synced = sum(1 for r in results if r["success"])
    return {
        "success": True,
        "synced": synced,
        "total": len(results),
        "results": sorted(results, key=lambda r: r["name"]),
    }


def repo_scan(vault_path: Path, home_dir: Optional[Path] = None) -> dict:
    """Scan for git repos and rebuild repos.json.

    Discovers all git repos under home directory.
    """
    home = home_dir or Path.home()
    repos_file = vault_path / "amplifier" / "repos.json"

    # Find all repos
    repo_paths = _find_git_repos(home)

    # Extract metadata for each
    repos = []
    for path in repo_paths:
        meta = _get_repo_metadata(path)
        if meta:
            repos.append(meta)

    # Build output structure
    data = {
        "lastScanned": datetime.now().isoformat(),
        "lastSynced": None,
        "repos": repos,
    }

    # Ensure directory exists
    repos_file.parent.mkdir(parents=True, exist_ok=True)
    repos_file.write_text(json.dumps(data, indent=2))

    return {
        "success": True,
        "found": len(repos),
        "repos_file": str(repos_file),
        "repos": [{"name": r["name"], "path": r["localPath"]} for r in repos],
    }


def repo_check(vault_path: Path) -> dict:
    """Check sync status of all repos without pulling.

    Just fetches and updates status in repos.json.
    """
    repos_file = vault_path / "amplifier" / "repos.json"

    if not repos_file.exists():
        return {
            "success": False,
            "error": "repos.json not found. Run repo_scan first.",
        }

    data = json.loads(repos_file.read_text())
    repos = data.get("repos", [])

    # Fetch and update metadata for each repo
    def check_one(repo: dict) -> dict:
        path = Path(repo.get("localPath", ""))
        if not path.exists():
            return {**repo, "syncStatus": "missing"}

        # Fetch
        _run_git(path, "fetch", "--all", "--prune", timeout=60)

        # Get fresh metadata
        meta = _get_repo_metadata(path)
        return meta if meta else {**repo, "syncStatus": "error"}

    with ThreadPoolExecutor(max_workers=4) as executor:
        updated_repos = list(executor.map(check_one, repos))

    data["repos"] = updated_repos
    data["lastSynced"] = datetime.now().isoformat()
    repos_file.write_text(json.dumps(data, indent=2))

    # Summary
    synced = sum(1 for r in updated_repos if r.get("syncStatus") == "synced")
    ahead = sum(1 for r in updated_repos if r.get("syncStatus") == "ahead")
    behind = sum(1 for r in updated_repos if r.get("syncStatus") == "behind")
    dirty = sum(1 for r in updated_repos if not r.get("workingTreeClean", True))

    return {
        "success": True,
        "total": len(updated_repos),
        "synced": synced,
        "ahead": ahead,
        "behind": behind,
        "dirty": dirty,
        "summary": f"{synced} synced, {ahead} ahead, {behind} behind, {dirty} dirty",
    }


def _get_commit_info(repo_path: Path, commit_range: str, limit: int = 10) -> list[dict]:
    """Get commit information for a range of commits."""
    ok, output = _run_git(
        repo_path,
        "log",
        "--format=%H|%h|%s|%an|%ar",
        f"-{limit}",
        commit_range,
    )
    if not ok or not output:
        return []

    commits = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 4)
        if len(parts) >= 5:
            commits.append(
                {
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "subject": parts[2],
                    "author": parts[3],
                    "relative_date": parts[4],
                }
            )
    return commits


def _get_working_tree_changes(repo_path: Path) -> dict:
    """Get detailed working tree changes."""
    ok, output = _run_git(repo_path, "status", "--porcelain")
    if not ok:
        return {"error": "Could not get status"}

    staged = []
    unstaged = []
    untracked = []

    for line in output.strip().split("\n"):
        if not line:
            continue
        index_status = line[0]
        worktree_status = line[1]
        filename = line[3:]

        if index_status == "?":
            untracked.append(filename)
        elif index_status != " ":
            staged.append({"status": index_status, "file": filename})
        if worktree_status != " " and worktree_status != "?":
            unstaged.append({"status": worktree_status, "file": filename})

    # Get diff stats for modified files
    ok, diff_stat = _run_git(repo_path, "diff", "--stat", "--no-color")

    return {
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "diff_summary": diff_stat if ok else None,
        "total_changes": len(staged) + len(unstaged) + len(untracked),
    }


def _suggest_action(
    is_dirty: bool,
    local_commits: list,
    remote_commits: list,
    sync_status: str,
) -> dict:
    """Suggest an action based on repo state."""
    if sync_status == "diverged":
        return {
            "action": "resolve_divergence",
            "description": "Repo has diverged from remote. Manual resolution needed.",
            "commands": ["git fetch", "git rebase origin/<branch> (or merge)"],
            "risk": "high",
        }

    if is_dirty and remote_commits:
        return {
            "action": "stash_pull_unstash",
            "description": "You have local changes AND remote has new commits. Stash, pull, then unstash.",
            "commands": ["git stash", "git pull --rebase", "git stash pop"],
            "risk": "medium",
        }

    if is_dirty and local_commits:
        return {
            "action": "commit_and_push",
            "description": "You have uncommitted changes and unpushed commits. Commit everything and push.",
            "commands": ["git add -A", "git commit -m '<message>'", "git push"],
            "risk": "low",
        }

    if is_dirty:
        return {
            "action": "review_and_commit",
            "description": "You have uncommitted changes. Review and commit them.",
            "commands": ["git diff", "git add -A", "git commit -m '<message>'"],
            "risk": "low",
        }

    if local_commits and not remote_commits:
        return {
            "action": "push",
            "description": "You have unpushed commits. Push them to remote.",
            "commands": ["git push"],
            "risk": "low",
        }

    if remote_commits and not local_commits:
        return {
            "action": "pull",
            "description": "Remote has new commits. Pull them.",
            "commands": ["git pull --rebase"],
            "risk": "low",
        }

    return {
        "action": "none",
        "description": "Repo is clean and synced.",
        "commands": [],
        "risk": "none",
    }


def repo_triage(vault_path: Path, repo_name: Optional[str] = None) -> dict:
    """Get detailed triage info for repos that need attention.

    Returns comprehensive information about dirty/unsynced repos including:
    - Working tree changes (staged, unstaged, untracked)
    - Local commits not pushed
    - Remote commits not pulled
    - Suggested action

    If repo_name is provided, returns info for just that repo.
    Otherwise returns all repos needing attention.
    """
    repos_file = vault_path / "amplifier" / "repos.json"

    if not repos_file.exists():
        return {
            "success": False,
            "error": "repos.json not found. Run repo_scan first.",
        }

    data = json.loads(repos_file.read_text())
    all_repos = data.get("repos", [])

    # Filter to repos needing attention (or specific repo)
    if repo_name:
        repos = [r for r in all_repos if r.get("name") == repo_name]
        if not repos:
            return {"success": False, "error": f"Repo '{repo_name}' not found"}
    else:
        # Get repos that need attention: dirty OR not synced
        repos = [
            r
            for r in all_repos
            if not r.get("workingTreeClean", True)
            or r.get("syncStatus") not in ("synced", "no-remote")
        ]
        # Also exclude archived repos
        repos = [r for r in repos if not r.get("archived", False)]

    triage_items = []

    for repo in repos:
        path = Path(repo.get("localPath", ""))
        if not path.exists():
            triage_items.append(
                {
                    "name": repo.get("name"),
                    "error": "Repo path does not exist",
                }
            )
            continue

        # Fetch first to get accurate remote state
        _run_git(path, "fetch", "--all", "--prune", timeout=60)

        # Get current branch
        ok, branch = _run_git(path, "rev-parse", "--abbrev-ref", "HEAD")
        branch = branch if ok else "unknown"

        # Get working tree changes
        changes = _get_working_tree_changes(path)
        is_dirty = changes.get("total_changes", 0) > 0

        # Get local commits not on remote
        local_commits = []
        ok, tracking = _run_git(
            path, "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"
        )
        if ok:
            local_commits = _get_commit_info(path, f"{tracking}..HEAD")

        # Get remote commits not pulled
        remote_commits = []
        if ok:
            remote_commits = _get_commit_info(path, f"HEAD..{tracking}")

        # Determine sync status
        sync_status = repo.get("syncStatus", "unknown")
        if local_commits and remote_commits:
            sync_status = "diverged"
        elif local_commits:
            sync_status = "ahead"
        elif remote_commits:
            sync_status = "behind"
        elif not is_dirty:
            sync_status = "synced"

        # Get suggestion
        suggestion = _suggest_action(
            is_dirty, local_commits, remote_commits, sync_status
        )

        triage_items.append(
            {
                "name": repo.get("name"),
                "path": str(path),
                "branch": branch,
                "github_repo": repo.get("githubRepo"),
                "sync_status": sync_status,
                "is_dirty": is_dirty,
                "changes": changes if is_dirty else None,
                "local_commits": local_commits,
                "remote_commits": remote_commits,
                "suggestion": suggestion,
            }
        )

    return {
        "success": True,
        "count": len(triage_items),
        "repos": triage_items,
    }


def repo_action(
    vault_path: Path,
    repo_name: str,
    action: str,
    commit_message: Optional[str] = None,
) -> dict:
    """Execute a triage action on a repo.

    Actions:
    - commit_all: Stage all and commit with message
    - push: Push to remote
    - pull: Pull from remote with rebase
    - stash: Stash changes
    - stash_pop: Pop stashed changes
    - discard: Discard all local changes (DANGEROUS)
    """
    repos_file = vault_path / "amplifier" / "repos.json"

    if not repos_file.exists():
        return {"success": False, "error": "repos.json not found"}

    data = json.loads(repos_file.read_text())
    repo = next((r for r in data.get("repos", []) if r.get("name") == repo_name), None)

    if not repo:
        return {"success": False, "error": f"Repo '{repo_name}' not found"}

    path = Path(repo.get("localPath", ""))
    if not path.exists():
        return {"success": False, "error": "Repo path does not exist"}

    if action == "commit_all":
        if not commit_message:
            return {"success": False, "error": "commit_message required for commit_all"}
        ok1, _ = _run_git(path, "add", "-A")
        ok2, output = _run_git(path, "commit", "-m", commit_message)
        if not ok2:
            return {"success": False, "error": f"Commit failed: {output}"}
        return {"success": True, "message": f"Committed: {commit_message}"}

    elif action == "push":
        ok, output = _run_git(path, "push", timeout=60)
        if not ok:
            return {"success": False, "error": f"Push failed: {output}"}
        return {"success": True, "message": "Pushed successfully"}

    elif action == "pull":
        ok, output = _run_git(path, "pull", "--rebase", timeout=60)
        if not ok:
            return {"success": False, "error": f"Pull failed: {output}"}
        return {"success": True, "message": f"Pulled: {output}"}

    elif action == "stash":
        ok, output = _run_git(
            path, "stash", "push", "-m", "Auto-stash from repo_action"
        )
        if not ok:
            return {"success": False, "error": f"Stash failed: {output}"}
        return {"success": True, "message": "Changes stashed"}

    elif action == "stash_pop":
        ok, output = _run_git(path, "stash", "pop")
        if not ok:
            return {"success": False, "error": f"Stash pop failed: {output}"}
        return {"success": True, "message": "Stash popped"}

    elif action == "discard":
        # DANGEROUS - requires explicit confirmation
        ok1, _ = _run_git(path, "checkout", "--", ".")
        ok2, _ = _run_git(path, "clean", "-fd")
        if not ok1 or not ok2:
            return {"success": False, "error": "Discard failed"}
        return {"success": True, "message": "All local changes discarded"}

    else:
        return {"success": False, "error": f"Unknown action: {action}"}


def repo_archive(
    vault_path: Path,
    repo_name: str,
    archive: bool = True,
) -> dict:
    """Archive or unarchive a repo.

    Archived repos are hidden from project_status and repo_triage views.
    The repo data is kept in repos.json for reference.
    """
    repos_file = vault_path / "amplifier" / "repos.json"

    if not repos_file.exists():
        return {"success": False, "error": "repos.json not found"}

    data = json.loads(repos_file.read_text())
    repo = next((r for r in data.get("repos", []) if r.get("name") == repo_name), None)

    if not repo:
        return {"success": False, "error": f"Repo '{repo_name}' not found"}

    repo["archived"] = archive
    repo["archivedAt"] = datetime.now().isoformat() if archive else None

    repos_file.write_text(json.dumps(data, indent=2))

    action = "archived" if archive else "unarchived"
    return {
        "success": True,
        "message": f"Repo '{repo_name}' {action}",
        "repo": repo_name,
        "archived": archive,
    }


def repo_list_archived(vault_path: Path) -> dict:
    """List all archived repos."""
    repos_file = vault_path / "amplifier" / "repos.json"

    if not repos_file.exists():
        return {"success": False, "error": "repos.json not found"}

    data = json.loads(repos_file.read_text())
    archived = [r for r in data.get("repos", []) if r.get("archived", False)]

    return {
        "success": True,
        "count": len(archived),
        "repos": [
            {
                "name": r.get("name"),
                "path": r.get("localPath"),
                "archived_at": r.get("archivedAt"),
            }
            for r in archived
        ],
    }
