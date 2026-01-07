---
name: morning-routine
description: Run the complete GTD morning routine - refresh reminders, sync notes, generate dashboard and daily note. Use when user says "morning routine", "start my day", or asks about their tasks/reminders.
version: 1.0.0
---

# Morning Routine

Complete GTD morning startup routine that syncs Apple Reminders/Notes and generates your daily dashboard.

## When to Use

- User says "morning routine" or "start my day"
- User asks to refresh their reminders or tasks
- User wants their GTD dashboard updated
- First thing in the morning to prepare for the day

## What It Does

1. **Updates Reminders Cache** - Pulls latest tasks from Apple Reminders
2. **Syncs Notes.app** - Bidirectional sync between Notes.app "Obsidian Sync" folder and Obsidian
3. **Generates GTD Dashboard** - Action-focused view with:
   - Flagged/priority items for today
   - Upcoming tasks
   - Waiting-for items
   - Amplifier project status
   - Active tasks grouped by project
   - Someday/maybe items
4. **Generates Daily Note** - Today's note with calendar events and prioritized tasks
5. **Opens Obsidian** - Opens GTD Dashboard so you're ready to start

## Execution

Run these commands in sequence:

```bash
cd ~/obs-dailynotes

# Step 1: Update reminders cache from Apple Reminders
echo "📥 Updating reminders cache from Apple Reminders..."
npm run reminders:update-cache

# Step 2: Sync Notes.app ↔ Obsidian
echo ""
echo "📝 Syncing Notes.app with Obsidian..."
npm run notes:sync

# Step 3: Generate GTD Dashboard
echo ""
echo "📊 Generating GTD Dashboard..."
node lib/gtd-simple/dashboard.js

# Step 4: Generate Daily Note
echo ""
echo "📅 Generating today's daily note..."
npm run daily

# Step 5: Open Obsidian to GTD Dashboard
echo ""
echo "🚀 Opening GTD Dashboard in Obsidian..."
open "obsidian://open?vault=switchboard&file=GTD%20Dashboard"

echo ""
echo "✅ Morning routine complete!"
```

## Output Locations

| Output | Location |
|--------|----------|
| GTD Dashboard | `~/switchboard/GTD Dashboard.md` |
| Daily Note | `~/switchboard/dailynote/[today's date].md` |
| Synced Notes | `~/switchboard/notes-sync/` |

## Prerequisites

The `obs-dailynotes` project must be set up at `~/obs-dailynotes` with:
- Node.js and npm installed
- Project dependencies installed (`npm install`)
- Apple Reminders access configured

## Tips

- Run first thing when starting your day
- The GTD Dashboard shows what needs attention NOW
- The daily note tracks activities and meetings
- Add notes to "Obsidian Sync" folder in Notes.app - they'll sync to your vault
