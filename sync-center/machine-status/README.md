# Machine Status Directory

This directory is for **machine-specific** state that should NOT be synced via git.

## What Goes Here (Git-Ignored)

Machine-specific files like:
- `last-sync.json` - When this machine last synced each repo
- `machine-id.json` - Fingerprint of this machine
- `repo-states/` - Current state of each repo on this machine

## Why Git-Ignored?

Machine-specific state in git causes merge conflicts and confusion:
- Machine A's state ≠ Machine B's state
- Syncing state files = constant conflicts
- Each machine tracks its own state locally

## Alternative: Use Amplifier's Memory

Instead of files here, Amplifier can:
- Store state in its own memory system
- Use git commit hashes to detect drift
- Query repos directly for current state

This directory exists mainly for **documentation** of what NOT to sync.
