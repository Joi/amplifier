---
description: Run the complete morning routine - refresh reminders, generate GTD dashboard, and create daily note
category: productivity
allowed-tools: Bash, Read
---

# Claude Command: Morning Routine

This command runs your complete morning startup routine in one step.

## Usage

```
/morning
```

## What This Command Does

1. **Updates Reminders Cache** - Pulls latest tasks from Apple Reminders
2. **Syncs Notes.app** - Bidirectional sync between Notes.app "Obsidian Sync" folder and Obsidian
3. **Generates GTD Dashboard** - Creates the action-focused GTD Dashboard with:
   - Flagged/priority items for today
   - Upcoming tasks
   - Waiting-for items
   - Amplifier project status (software development initiatives)
   - Active tasks grouped by project
   - Someday/maybe items
4. **Generates Daily Note** - Creates today's daily note with:
   - Calendar events
   - Prioritized tasks
   - Amplifier project tracking
5. **Opens Obsidian** - Opens the GTD Dashboard in Obsidian so you're ready to start

## Execution Steps

Run these commands in sequence in the obs-dailynotes directory:

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

- **GTD Dashboard**: `~/switchboard/GTD Dashboard.md`
- **Daily Note**: `~/switchboard/dailynote/[today's date].md`
- **Notes Sync**: `~/switchboard/notes-sync/` (synced from Notes.app "Obsidian Sync" folder)

## Tips

- Run this first thing when you start your day
- The GTD Dashboard shows what needs your attention NOW
- The daily note tracks your day's activities and meetings
- Both include Amplifier project status for software development work
- Add notes to the "Obsidian Sync" folder in Notes.app - they'll appear in your vault after sync

$ARGUMENTS
