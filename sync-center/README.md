# Amplifier Sync Center

Central coordination point for keeping all machines in sync across multiple repos.

## Quick Start

When you open Amplifier on any machine:

```bash
cd ~/amplifier
amplifier sync check    # Check what needs syncing (future)
```

Or manually:

```bash
# Review what repos need attention
cat sync-center/repos.json

# Run specific sync prompt
amplifier apply sync-center/sync-prompts/obs-dailynotes.md
```

## Architecture

### What This Is
- **Central registry** of all repos you work with
- **Sync prompts** for each repo's specific migration needs
- **Checklist generator** to see what needs updating
- **Machine coordination** without conflicts

### What Syncs via Git
- ✅ `repos.json` - Master list of repos to track
- ✅ `sync-prompts/` - Instructions for syncing each repo
- ✅ `README.md` - This file

### What Stays Local (Git-Ignored)
- ❌ `machine-status/` - Machine-specific state (creates conflicts)
- Use Amplifier's memory/context instead

## Repository Registry

`repos.json` contains:
- List of all repos you use
- Their locations on disk
- Sync requirements (git pull, env files, data migration, etc.)
- Dependencies between repos

## Sync Prompts

Each repo gets a markdown file in `sync-prompts/`:
- `obs-dailynotes.md` - Sync code, merge data, update env
- `amplifier.md` - Pull latest, check for new dependencies
- `dotfiles-private.md` - Pull latest secrets
- etc.

## Usage Patterns

### Daily Check-In
```bash
# Quick health check
amplifier sync status

# Shows:
# ✅ amplifier: up to date
# ⚠️  obs-dailynotes: 3 commits behind origin
# ⚠️  dotfiles-private: needs pull
```

### After Switching Machines
```bash
# Full sync
amplifier sync all

# Or specific repo
amplifier sync obs-dailynotes
```

### One-Time Migrations
When architecture changes (like obs-dailynotes data → switchboard):
1. Create migration prompt in `sync-prompts/`
2. Add to git, push
3. On other machines, Amplifier detects and applies it
4. Archive the migration prompt after all machines updated

## Design Philosophy

**Pull-based, not push-based**
- Machines pull what they need
- No central server coordination
- Git is the sync mechanism

**Declarative, not imperative**
- Describe desired state
- Amplifier figures out how to get there
- Idempotent operations

**Fail-safe**
- Always backup before changes
- Dry-run by default
- Clear rollback instructions

## Future Enhancements

- [ ] Automated sync status check on Amplifier startup
- [ ] Machine fingerprinting to detect which machine you're on
- [ ] Dependency resolution (sync repo A before repo B)
- [ ] Conflict detection and resolution
- [ ] Sync analytics (how often each repo needs updates)
