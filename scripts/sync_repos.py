#!/usr/bin/env python3
"""Sync all tracked git repositories.

Reads ~/switchboard/amplifier/repos.json and git pulls each repo.
"""

import json
import subprocess
import sys
from pathlib import Path


def sync_repo(path: str, push: bool = False) -> tuple[bool, str]:
    """Sync one repo. Returns (success, message)."""
    repo_path = Path(path).expanduser()
    if not repo_path.exists():
        return (False, "Not found locally")

    try:
        # Pull from remote
        result = subprocess.run(["git", "pull"], cwd=repo_path, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return (False, result.stderr.strip())

        # Push if requested
        if push:
            result = subprocess.run(["git", "push"], cwd=repo_path, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return (False, f"Pull OK, push failed: {result.stderr.strip()}")

        return (True, "Synced" + (" (pulled & pushed)" if push else ""))
    except subprocess.TimeoutExpired:
        return (False, "Timeout (30s)")
    except Exception as e:
        return (False, str(e))


def main() -> None:
    """Sync all repos from repos.json."""
    push = "--push" in sys.argv

    repos_file = Path.home() / "switchboard/amplifier/repos.json"
    if not repos_file.exists():
        print(f"❌ Error: {repos_file} not found")
        print("Run: cd ~/obs-dailynotes && npm run repos:scan")
        sys.exit(1)

    data = json.loads(repos_file.read_text())
    repos = data.get("repos", [])

    if not repos:
        print("⚠️  No repos found in repos.json")
        sys.exit(0)

    print(f"🔄 Syncing {len(repos)} repositories{'  (push enabled)' if push else ''}...\n")

    results = []
    for repo in repos:
        name = repo.get("name", "unknown")
        path = repo.get("localPath", "")

        success, msg = sync_repo(path, push)
        status = "✓" if success else "✗"
        print(f"{status} {name}: {msg}")
        results.append(success)

    synced = sum(results)
    total = len(results)
    print(f"\n{'✅' if synced == total else '⚠️ '} {synced}/{total} repos synced successfully")

    if synced < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
