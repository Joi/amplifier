---
description: Access Granola meeting transcripts via muesli CLI
category: productivity
allowed-tools: Bash, Read
---

# /muesli - Meeting Transcripts

Access and search Granola meeting transcripts using the muesli CLI.

## Usage

```
/muesli                     # List recent meetings
/muesli list                # List all synced meetings
/muesli search <query>      # Search meeting transcripts
/muesli fetch <id>          # Get full transcript by ID
/muesli sync                # Sync latest meetings from Granola
/muesli summarize <id>      # Summarize a transcript with AI
/muesli inject              # Inject today's meetings into daily note
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `muesli list` | List all synced documents |
| `muesli sync` | Sync new meetings from Granola |
| `muesli fetch <id>` | Get transcript by document ID |
| `muesli search <query>` | Search indexed documents |
| `muesli summarize <id>` | AI-powered summary |
| `muesli open` | Open data directory |

### Daily Note Injection

The GTD muesli module lives in `~/amplifier-bundle-joi/` and is invoked directly:

| Command | Description |
|---------|-------------|
| `muesli-inject` | Shell alias: sync and inject into today's daily note |
| `muesli-list` | Shell alias: list today's meetings |
| `python3 $AMPLIFIER_BUNDLE/modules/tool-gtd/amplifier_module_tool_gtd/muesli.py sync-inject --translate` | Full command |
| `python3 $AMPLIFIER_BUNDLE/modules/tool-gtd/amplifier_module_tool_gtd/muesli.py list` | List meetings |
| `python3 $AMPLIFIER_BUNDLE/modules/tool-gtd/amplifier_module_tool_gtd/muesli.py inject --date 2026-01-22` | Inject for specific date |

**Shell aliases** (defined in `~/.zshrc`):
- `muesli-inject` - Sync and inject with translation
- `muesli-list` - List today's meetings
- `muesli <command>` - Run any muesli.py command

## Instructions

### Default: List Recent Meetings

If no arguments, list recent meetings:

```bash
muesli list 2>&1 | head -20
```

Format output as a table showing: Date, Title, ID

### Sync New Meetings

```bash
muesli sync
```

### Fetch Full Transcript

```bash
muesli fetch <document-id>
```

The document ID is the UUID shown in the list output.

### Search Meetings

```bash
muesli search "<query>"
```

Searches indexed meeting content.

### Summarize a Meeting

```bash
muesli summarize <document-id>
```

Uses OpenAI to generate a summary of the transcript.

## Data Location

Transcripts are stored in: `~/Library/Application Support/muesli/`

Each meeting is saved as a markdown file with:
- Meeting title
- Date and time
- Participants
- Full transcript
- Summary (if generated)

## MCP Integration

Muesli also runs as an MCP server providing:
- `list_meetings` - List all synced meetings
- `get_meeting` - Get full transcript
- `search_meetings` - Search content
- `sync_meetings` - Sync from Granola

The MCP server is enabled in Claude Code settings.

## Examples

**List today's meetings:**
```
/muesli list | grep 2026-01-23
```

**Search for a topic:**
```
/muesli search "budget discussion"
```

**Get full transcript:**
```
/muesli fetch 9fb3b05b-547c-4fbd-98fa-a0f1ea35bf31
```

## Notes

- Requires Granola account and API token
- Token stored in system keychain (use `muesli set-api-key`)
- Transcripts sync automatically with `muesli sync`
- Search requires the 'index' feature

## Daily Note Injection

The GTD muesli module syncs meetings from Granola and inserts summaries into daily notes.

**Source:** `~/amplifier-bundle-joi/modules/tool-gtd/amplifier_module_tool_gtd/muesli.py`

**What it does:**
1. Syncs latest transcripts from Granola
2. Matches meetings to calendar events by **fuzzy title AND time** (±30 min tolerance)
3. Generates AI summaries (using Anthropic API)
4. Translates Japanese transcripts to English (with `--translate`)
5. Inserts formatted notes under each meeting heading

**Commands for Claude Code:**
```bash
# List today's meetings
python3 ~/amplifier-bundle-joi/modules/tool-gtd/amplifier_module_tool_gtd/muesli.py list

# Sync and inject into daily note (with translation)
python3 ~/amplifier-bundle-joi/modules/tool-gtd/amplifier_module_tool_gtd/muesli.py sync-inject --translate

# Inject only (no sync, no translation)
python3 ~/amplifier-bundle-joi/modules/tool-gtd/amplifier_module_tool_gtd/muesli.py inject

# Dry run (preview without writing)
python3 ~/amplifier-bundle-joi/modules/tool-gtd/amplifier_module_tool_gtd/muesli.py inject --dry-run
```

**Transcript locations:**
- Original transcripts: `~/switchboard/muesli/`
- English translations: `~/.local/share/muesli/transcripts_en/`
- Summaries: `~/.local/share/muesli/summaries/`

**Example output in daily note:**
```markdown
### 09:00 AI Tools

#### Summary

**Key Points**
- Point 1
- Point 2

**Action Items**
- Action 1
- Action 2

**Transcript**: [[muesli/2026-01-23_ai-tools|View full transcript]]
**Granola ID**: `c48017f7-1fcd-4e7f-87b6-6b254d191662`
```

## Additional Guidance

$ARGUMENTS
