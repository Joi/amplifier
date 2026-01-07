---
name: continuous-improvement
description: Philosophy for handling errors, issues, and improvements during work. When encountering problems, either fix them immediately or create reminders for future work. Always leave the codebase better than you found it.
version: 1.0.0
---

# Continuous Improvement Philosophy

This skill defines how to handle errors, issues, and potential improvements encountered during work.

## Core Principle

**Never let issues slip through the cracks.** When you encounter a problem:
1. Fix it now if quick and relevant, OR
2. Create a reminder/todo if it requires separate attention

## When to Fix Immediately

Fix the issue in the current session when:
- It's directly blocking the current task
- It takes less than 5-10 minutes to fix
- You have all the context needed right now
- The fix is low-risk and well-understood

## When to Create a Reminder

Create a reminder for later when:
- The issue is tangential to the current task
- It requires significant time or research
- You're in the middle of complex work that shouldn't be interrupted
- The fix has dependencies not currently available
- It's a larger architectural concern

## How to Create Reminders

Use the Apple Reminders tool:

```bash
# For code/tool issues
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Fix [specific issue]" \
  --list "Amplifier" \
  --notes "Context: [what you were doing, where the issue is, potential solution]" \
  --priority 2

# For general improvements
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Improve [specific thing]" \
  --list "Amplifier" \
  --notes "[Why it needs improvement, ideas for how]"
```

## Information to Include in Reminders

Always include enough context so future-you (or future-Claude) can pick it up:

1. **What**: Clear description of the issue
2. **Where**: File path, function name, or tool involved
3. **Why**: What problem it causes or what benefit fixing would provide
4. **How** (optional): Ideas for the solution if you have them

## Example Scenarios

### Scenario 1: Error During Routine Task
While running morning routine, Notes sync fails on 3 files with special characters.

**Response**: 
- Note the error in the output
- Create a fix document with the solution
- Add reminder if can't fix in current session

```bash
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Apply Notes sync escaping fix" \
  --list "Amplifier" \
  --notes "Solution in ai_working/migration/NOTES_SYNC_FIX.md. Edit ~/obs-dailynotes/lib/notes-sync/applescript.js"
```

### Scenario 2: Discovered Improvement Opportunity
While reviewing code, notice a pattern that could be refactored.

**Response**: Don't derail current work, but capture the insight:

```bash
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Refactor [pattern] in [module]" \
  --list "Amplifier" \
  --notes "Noticed while working on [X]. Could simplify by [approach]. See [file] line [N]."
```

### Scenario 3: Missing Feature
Realize a tool is missing a useful capability.

**Response**: Add it to the backlog:

```bash
python3 /Users/joi/amplifier/tools/apple_reminders.py add "Add [feature] to [tool]" \
  --list "Amplifier" \
  --notes "Would be useful for [use case]. Similar to how [other tool] does it."
```

## Priority Levels

- **Priority 1 (High)**: Blocking issues, security concerns, data loss risks
- **Priority 2 (Medium)**: Important improvements, recurring annoyances
- **Priority 3 (Low)**: Nice-to-haves, minor polish

## Integration with Workflow

This philosophy should be applied:
- During development sessions
- When running tools/commands
- When reviewing code
- When encountering unexpected behavior
- During any interaction where issues surface

## The Goal

Build a culture of continuous improvement where:
- Issues are never forgotten
- Context is preserved for future work
- The codebase/tools steadily improve over time
- Work doesn't get derailed by tangential issues
- Important fixes don't slip through the cracks
