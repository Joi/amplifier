---
description: Quick alias for renaming the current session and updating tmux
category: session-management
allowed-tools: Bash
---

# /name

Quick alias for renaming the current session and updating tmux.

## Usage

```
/name <session-name>
```

## Arguments

- `session-name`: The name to give this session (e.g., "auth-refactor", "bug-fix")

## Instructions

1. First, use the built-in `/rename` command to rename the session:
   - Tell the user: "Renaming session to: <session-name>"
   - The actual rename happens via Claude Code's built-in `/rename` command

2. If in tmux, also update the tmux window name:
   ```bash
   if [ -n "$TMUX" ]; then
     PROJECT=$(basename "$PWD")
     tmux rename-window "${PROJECT}:$ARGUMENTS"
   fi
   ```

3. Update the local session tracker file:
   ```bash
   if [ -f ~/.claude/current_session.json ]; then
     python3 -c "
   import json
   from pathlib import Path
   f = Path.home() / '.claude' / 'current_session.json'
   if f.exists():
       data = json.loads(f.read_text())
       data['session_name'] = '$ARGUMENTS'
       f.write_text(json.dumps(data, indent=2))
   "
   fi
   ```

4. Confirm: "Session renamed to: $ARGUMENTS"

Note: This is a convenience wrapper. The user can also use `/rename <name>` directly.

## Additional Guidance

$ARGUMENTS
