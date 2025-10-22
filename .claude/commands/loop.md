---
description: Keep working on a goal until complete using DotRunner loop workflow
category: workflow-automation
allowed-tools: Bash
argument-hint: <goal description>
---

You will execute the loop-until-done DotRunner workflow to keep working on a goal until completion.

## User's Goal

{{PROMPT}}

## Your Task

Run the DotRunner loop-until-done workflow with this goal:

```bash
GOAL="{{PROMPT}}" uv run python -m ai_working.dotrunner run ai_flows/loop-until-done.yaml
```

## How It Works

The workflow will:
1. **Work** - Execute the goal
2. **Check** - Evaluate if COMPLETE or INCOMPLETE
3. **Continue** - If incomplete, keep working (loops back to check)
4. **Done** - Terminal node when complete

The workflow loops automatically until the goal is achieved (max 20 iterations for safety).

## Important

- DotRunner manages the loop automatically - you just start it
- Monitor execution and report final results
- The workflow saves checkpoints, so it's resumable if interrupted
