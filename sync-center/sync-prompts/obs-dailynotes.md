# Amplifier Prompt: Sync Machine to New obs-dailynotes Architecture

## Context

The obs-dailynotes architecture has been updated to separate code from data:
- **Code**: Lives in `~/obs-dailynotes/` (syncs via git)
- **Data**: Lives in `~/switchboard/data/` (syncs via Obsidian)
- **Secrets**: Lives in `~/dotfiles-private/` (syncs via private git)

This machine needs to be updated to match this architecture.

## Current State on This Machine

- Has an old `~/obs-dailynotes/data/reading-queue.json` file that needs to be merged
- May have `~/obs-dailynotes/data/presentations.json` as well
- Using old architecture where data lived in the git repo

## Required Actions

### 1. Update Code Repository

```bash
cd ~/obs-dailynotes
git pull
```

This gets the updated code that reads from `SWITCHBOARD_DATA_PATH` env variable.

### 2. Update Environment Configuration

```bash
cd ~/dotfiles-private
git pull
```

This gets the new `SWITCHBOARD_DATA_PATH=/Users/joi/switchboard/data/` variable.

### 3. Ensure Switchboard Data Directory Exists

```bash
mkdir -p ~/switchboard/data/papers/{to-read,reading,read,archived}
```

Obsidian should have already synced this, but create it if missing.

### 4. Merge reading-queue.json Files

**IMPORTANT**: There are potentially two versions of this file:
- `~/obs-dailynotes/data/reading-queue.json` (local, may have unique entries)
- `~/switchboard/data/reading-queue.json` (synced from other machine)

**Task**: Merge these intelligently:

1. Read both files
2. Compare the `items` arrays
3. Merge items by ID (items in local but not in switchboard should be added)
4. Preserve the higher `nextId` value
5. Write merged result to `~/switchboard/data/reading-queue.json`
6. Keep backup of both originals

**Schema for reading-queue.json**:
```json
{
  "version": "1.0",
  "items": [
    {
      "id": "read-YYYYMMDD-NNN",
      "type": "url" | "pdf",
      "title": "...",
      "url": "..." | null,
      "path": "..." | null,
      "status": "to-read" | "reading" | "read" | "archived",
      "priority": "low" | "medium" | "high" | "urgent",
      "deadline": "YYYY-MM-DD" | null,
      "addedDate": "ISO timestamp",
      "startedDate": "ISO timestamp" | null,
      "finishedDate": "ISO timestamp" | null,
      "archivedDate": "ISO timestamp" | null,
      "source": "manual" | "...",
      "tags": [],
      "notes": "",
      "estimatedMinutes": number | null,
      "reminderTaskId": string | null
    }
  ],
  "nextId": number
}
```

### 5. Handle presentations.json (if exists)

If `~/obs-dailynotes/data/presentations.json` exists:
- Check if `~/switchboard/data/presentations.json` exists
- If both exist, merge by presentation ID
- If only local exists, move it to switchboard
- Keep backup of originals

**Schema for presentations.json**:
```json
{
  "version": "1.0",
  "presentations": [
    {
      "id": "pres-YYYYMMDD-NNN",
      "title": "...",
      "url": "...",
      "status": "planned" | "in-progress" | "completed" | "archived",
      "priority": "low" | "medium" | "high" | "urgent",
      "deadline": "YYYY-MM-DD" | null,
      "addedDate": "ISO timestamp",
      "startedDate": "ISO timestamp" | null,
      "completedDate": "ISO timestamp" | null,
      "archivedDate": "ISO timestamp" | null,
      "notionUrl": "..." | null,
      "tags": [],
      "notes": "",
      "estimatedHours": number | null,
      "actualHours": number | null
    }
  ],
  "nextId": number
}
```

### 6. Clean Up Old Data Directory

```bash
# After merging, remove the old data directory from obs-dailynotes
rm -rf ~/obs-dailynotes/data/
```

### 7. Verify Everything Works

```bash
cd ~/obs-dailynotes
work read list    # Should show merged reading queue
work pres list    # Should show presentations (if any)
```

## Expected Output

Report showing:
1. ✅ Git repos updated (obs-dailynotes, dotfiles-private)
2. ✅ Reading queue merged: X items from local, Y items from switchboard, Z total
3. ✅ Presentations merged: X items from local, Y items from switchboard, Z total
4. ✅ Old data directory removed
5. ✅ Commands verified working

## Implementation Notes

- Use Python or Node.js for the merge logic (JSON manipulation)
- Keep timestamped backups of original files before merging
- If IDs conflict (same ID, different data), prefer the entry with the most recent timestamp
- Validate merged JSON against schema before writing
- Handle missing files gracefully (e.g., if one machine never had presentations)

## Safety

- Always backup before modifying
- Don't delete originals until merge is verified
- Show diff/summary of what was merged before finalizing
