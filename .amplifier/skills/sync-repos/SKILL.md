---
name: sync-repos
description: Sync all git repositories from the repos.json inventory. Use when user wants to pull/push all repos, catch up a machine, or sync their git repositories.
version: 1.0.0
---

# Repository Sync Tool

Sync all git repositories tracked in the repo sync system. Pulls repos that are behind, optionally pushes repos that are ahead.

## When to Use

- User asks to "sync repos" or "sync all repositories"
- User wants to "catch up" or "pull all repos"
- User wants to "push all repos"
- User mentions syncing git repositories across machines
- Starting work on a different machine
- Morning/evening routine to stay in sync

## Tool Location

```bash
# Quick sync (pull all repos that are behind)
uv run python ~/amplifier/scripts/sync_repos.py

# Pull and push all repos
uv run python ~/amplifier/scripts/sync_repos.py --push

# Or using make (from amplifier directory)
cd ~/amplifier && make sync-repos
cd ~/amplifier && make sync-repos-push
```

## Commands

### Sync All Repos (Pull)

```bash
uv run python ~/amplifier/scripts/sync_repos.py
```

Pulls all repositories from their remotes. Safe to run anytime.

### Sync All Repos (Pull + Push)

```bash
uv run python ~/amplifier/scripts/sync_repos.py --push
```

Pulls then pushes all repositories.

### Using Make

```bash
cd ~/amplifier && make sync-repos       # Pull only
cd ~/amplifier && make sync-repos-push  # Pull + Push
```

## Data Files

- **`~/switchboard/amplifier/repos.json`** - Repository inventory (source of truth)
- **`~/switchboard/amplifier/REPOS-DASHBOARD.md`** - Visual dashboard
- **`~/switchboard/amplifier/project-status.json`** - Project tracking with repo links

## Output Example

```
🔄 Syncing 24 repositories...

✓ amplifier: Synced
✓ chanoyu-db: Synced
✗ old-project: Not found locally
✓ health-tracker: Synced
...

✅ 23/24 repos synced successfully
```

## Sync Status

- ✓ Synced - successfully pulled (and pushed if --push)
- ✗ Failed - with error message (timeout, not found, git error)

## Examples

```bash
# Morning routine: catch up all repos
uv run python ~/amplifier/scripts/sync_repos.py

# Evening routine: push all work
uv run python ~/amplifier/scripts/sync_repos.py --push

# Using make from amplifier directory
cd ~/amplifier && make sync-repos
```

## Notes

- Missing repos are skipped (not an error)
- Network timeouts are handled (30s per repo)
- Individual failures don't stop the entire process
- Exit code 0 = all synced, 1 = some failed

## Related Documentation

- `~/switchboard/amplifier/REPO-SYNC-GUIDE.md` - Complete user guide
- `~/switchboard/amplifier/REPOS-DASHBOARD.md` - Visual dashboard
- `~/switchboard/amplifier/repos.json` - Repository inventory
