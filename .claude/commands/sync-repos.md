---
description: Sync all tracked git repositories across machines
category: version-control-git
allowed-tools: Bash
---

# /sync-repos

Sync all tracked git repositories with a single command. Perfect for catching up a machine after working from a different location.

## Usage

```
/sync-repos
```

Or to sync both ways (pull + push):

```
/sync-repos --push
```

## What This Command Does

1. Reads your repository inventory from `~/switchboard/amplifier/repos.json`
2. For each tracked repository:
   - Pulls latest changes from remote (git pull)
   - Optionally pushes local changes (if --push flag is used)
   - Reports status: ✓ Synced or ✗ Failed (with reason)
3. Provides summary: "X/Y repos synced successfully"
4. Continues processing even if individual repos fail

## Instructions

### Standard Sync (Pull Only)

If no arguments or `--push` is not present, run:

```bash
make sync-repos
```

### Bidirectional Sync (Pull + Push)

If `--push` argument is present, run:

```bash
make sync-repos-push
```

### Output

The command will show:
- Progress for each repository (✓ or ✗)
- Clear error messages for any failures
- Summary count at the end

Example:
```
🔄 Syncing 24 repositories...

✓ amplifier: Synced
✓ chanoyu-db: Synced
✗ old-project: Not found locally
✓ health-tracker: Synced
...

✅ 23/24 repos synced successfully
```

## When to Use This

- **New machine**: Quick catch-up after cloning amplifier
- **Morning routine**: Sync all repos before starting work
- **After travel**: Update all repos when switching between machines
- **Before committing**: Make sure you have latest from all repos

## Prerequisites

This command requires:
- Repository inventory already created (run `npm run repos:scan` from `~/obs-dailynotes` if needed)
- Git repositories cloned locally (missing repos are skipped with clear message)

## Notes

- Missing repos are skipped (not an error)
- Network timeouts are handled (30s per repo)
- Individual failures don't stop the entire process
- Exit code indicates success (0) or partial failure (1)

## Additional Guidance

$ARGUMENTS
