---
description: Run the complete morning routine - sync reminders, notes, emails, meetings, and generate GTD dashboard and daily note
category: productivity
allowed-tools: Bash, Read
---

# Claude Command: Morning Routine

This command runs your complete morning startup routine in one step using the modern Python GTD system.

## Usage

```
/morning
```

## What This Command Does

1. **Syncs Reminders** - Pulls latest tasks from Apple Reminders via EventKit
2. **Syncs Notes.app** - Bidirectional sync between Notes.app and Obsidian
3. **Syncs Starred Emails** - Creates reminders from starred Gmail emails with optional AI drafts
4. **Syncs Meeting Transcripts** - Fetches Granola meetings via muesli and injects into daily notes with:
   - Auto-detection of Japanese transcripts
   - English translation and summaries
   - Dual links (English + Japanese) for Japanese meetings
5. **Generates GTD Dashboard** - Creates the action-focused GTD Dashboard with:
   - Flagged/priority items for today
   - Context-grouped actions (@computer, @phone, etc.)
   - Waiting-for items
   - Someday/maybe list
6. **Generates Daily Note** - Creates today's daily note with:
   - Calendar events
   - Prioritized tasks
   - Email replies needed
   - Upcoming kimono events
7. **Opens Obsidian** - Opens the GTD Dashboard in Obsidian so you're ready to start

## Execution

Run the Python GTD morning routine:

```bash
cd ~/amplifier
.venv/bin/python scripts/morning_routine.py
```

Or with options:

```bash
# Skip sync steps (only regenerate outputs)
.venv/bin/python scripts/morning_routine.py --skip-sync

# Skip opening Obsidian
.venv/bin/python scripts/morning_routine.py --skip-open
```

## Output Locations

- **GTD Dashboard**: `~/switchboard/GTD Dashboard.md`
- **Daily Note**: `~/switchboard/dailynote/[today's date].md`
- **Notes Sync**: `~/switchboard/notes-sync/` (synced from Notes.app)
- **Meeting Transcripts**: `~/.local/share/muesli/transcripts/` (Japanese originals)
- **English Translations**: `~/.local/share/muesli/transcripts_en/` (auto-generated)
- **Meeting Summaries**: `~/.local/share/muesli/summaries/` (auto-generated)

## Features

### Email Sync with AI Drafts
- Starred Gmail emails → "Email Replies" reminders
- Optional AI-generated draft replies (Claude Sonnet)
- Thread-aware (only latest email per conversation)
- Direct links to Gmail and draft

### Meeting Transcript Integration
- Auto-detects Japanese vs English transcripts
- Translates Japanese → English (saved separately)
- Generates English summaries for all meetings
- Injects into yesterday's daily note (meetings typically completed by then)
- Matches meeting slots by time (±30 minutes tolerance)

## Tips

- Run this first thing when you start your day
- The GTD Dashboard shows what needs your attention NOW
- Daily note tracks your day's activities and meetings
- Meeting transcripts appear in yesterday's note automatically
- Use starred emails for inbox zero workflow

$ARGUMENTS
