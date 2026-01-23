---
description: Manage beads issues - lightweight issue tracking with dependency support
category: project-management
allowed-tools: Bash, Read, Glob
---

# /beads - Issue Tracking

Manage issues with beads (bd CLI) - a lightweight issue tracker with first-class dependency support.

## Usage

```
/beads                    # Show ready issues (no blockers)
/beads list               # List all open issues
/beads show <id>          # Show issue details
/beads create <title>     # Create new issue
/beads close <id>         # Close an issue
/beads ready              # Show issues ready to work on
/beads status             # Database overview and statistics
/beads <repo>             # Work with a specific repo's beads
```

## Quick Reference

### Viewing Issues

| Command | Description |
|---------|-------------|
| `bd ready --json` | Issues with no blockers |
| `bd list --json` | All open issues |
| `bd list --status in_progress --json` | In-progress issues |
| `bd show <id> --json` | Issue details |
| `bd blocked --json` | Blocked issues |
| `bd status` | Database overview |

### Managing Issues

| Command | Description |
|---------|-------------|
| `bd create "<title>" -t task` | Create task |
| `bd create "<title>" -t epic` | Create epic |
| `bd create "<title>" -t bug -p 1` | Create P1 bug |
| `bd update <id> --status in_progress` | Start working |
| `bd close <id>` | Close issue |
| `bd dep add <id> --blocks <other-id>` | Add dependency |

### Issue Types
- `epic` - Large feature/initiative
- `task` - Standard work item
- `bug` - Bug fix
- `feature` - New feature
- `chore` - Maintenance

### Priority Levels
- `0` - Critical
- `1` - High
- `2` - Medium (default)
- `3` - Low
- `4` - Backlog

## Instructions

### Default: Show Ready Issues

If no arguments provided, show ready issues in current repo:

```bash
cd $(pwd) && bd ready --json 2>/dev/null || echo "No beads database found in this repo"
```

Format output as a table showing: ID, Title, Priority, Type

### Working with Other Repos

If a repo name is specified (e.g., `/beads chanoyu-adventure`), change to that repo first:

```bash
cd ~/<repo-name> && bd ready --json
```

Common repos with beads:
- `~/amplifier`
- `~/chanoyu-adventure`
- `~/switchboard`

### Creating Issues

When creating issues:
1. Ask for title and description
2. Determine appropriate type (task, epic, bug, feature, chore)
3. Set priority based on urgency
4. Add dependencies if related to existing issues

```bash
bd create "<title>" -t <type> -p <priority> -d "<description>" --deps <dep-ids>
```

### Updating Issue Status

Workflow: `open` → `in_progress` → `closed`

```bash
# Start working on an issue
bd update <id> --status in_progress

# Close when done
bd close <id>
```

### Viewing Dependencies

```bash
# Show dependency graph
bd graph <id>

# Show what blocks an issue
bd show <id> --json | jq '.blocked_by'
```

### Cross-Repo Operations

To work with beads in a different repo:

```bash
cd ~/chanoyu-adventure && bd ready --json
cd ~/amplifier && bd list --json
```

## Examples

**Show ready issues in current repo:**
```
/beads
```

**Show ready issues in chanoyu-adventure:**
```
/beads chanoyu-adventure ready
```

**Create a new task:**
```
/beads create "Implement user authentication"
```

**Close issue with ID bd-5:**
```
/beads close bd-5
```

## Notes

- Each repo has its own `.beads/` directory with its database
- Issues use hierarchical IDs: `prefix-N` (e.g., `bd-5`, `chanoyu-adventure-s9l`)
- Sub-issues use dot notation: `bd-5.1`, `bd-5.2`
- The daemon auto-syncs changes to git (if configured)

## Additional Guidance

$ARGUMENTS
