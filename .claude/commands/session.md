---
description: Display the current Claude Code session information
category: session-management
allowed-tools: Bash, Read
---

# /session

Display the current Claude Code session information.

## Usage

```
/session
```

## Instructions

Read the session info from `~/.claude/current_session.json` and display it in a clean format:

```bash
cat ~/.claude/current_session.json 2>/dev/null || echo '{"error": "No session info found"}'
```

Then format and display:
- **Session ID**: The full session UUID
- **Session Name**: Custom name (if set via /name or /rename)
- **Project**: The project directory
- **Model**: Current model being used

If the file doesn't exist, tell the user the session tracker hook may not be configured.

Keep output concise - just show the key info.
