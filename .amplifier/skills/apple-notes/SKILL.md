---
name: apple-notes
description: Create, read, search, and manage Apple Notes. Use when user wants to save information to Apple Notes, read existing notes, or search their notes.
version: 1.0.0
---

# Apple Notes Tool

Create, read, search, and manage Apple Notes from the command line.

## When to Use

- User asks to "save this to Apple Notes" or "create a note"
- User wants to read or find an existing Apple Note
- User wants to search their notes for something
- User mentions saving information for later reference

## Tool Location

```bash
python /Users/joi/amplifier/tools/apple_notes.py <command> [options]
```

## Commands

### Create a Note

```bash
# From text (supports Markdown - converted to HTML for proper rendering)
python /Users/joi/amplifier/tools/apple_notes.py create "Note Title" "Content in **markdown**"

# From a file
python /Users/joi/amplifier/tools/apple_notes.py create "Note Title" --file content.md

# From stdin
echo "# My Note" | python /Users/joi/amplifier/tools/apple_notes.py create "Note Title" --stdin

# In a specific folder
python /Users/joi/amplifier/tools/apple_notes.py create "Note Title" "Content" --folder "Work Notes"
```

### Read a Note

```bash
# Read by title (exact match)
python /Users/joi/amplifier/tools/apple_notes.py read "Note Title"

# Read by ID
python /Users/joi/amplifier/tools/apple_notes.py read --id "x-coredata://..."
```

### Search Notes

```bash
# Search by keyword
python /Users/joi/amplifier/tools/apple_notes.py search "keyword"

# Limit results
python /Users/joi/amplifier/tools/apple_notes.py search "keyword" --limit 5
```

### List Notes

```bash
# List recent notes
python /Users/joi/amplifier/tools/apple_notes.py list

# List notes in a folder
python /Users/joi/amplifier/tools/apple_notes.py list --folder "Work Notes"

# Limit results
python /Users/joi/amplifier/tools/apple_notes.py list --limit 10
```

## Markdown Support

The tool automatically converts Markdown to HTML for proper rendering in Apple Notes:

- **Bold** and *italic* text
- Headers (# ## ###)
- Lists (- and 1.)
- Code blocks
- Links
- Tables

## Examples

```bash
# Save a meeting summary
python /Users/joi/amplifier/tools/apple_notes.py create "Meeting Notes - Jan 7" "## Attendees\n- Alice\n- Bob\n\n## Action Items\n1. Review proposal\n2. Schedule follow-up"

# Save this conversation's summary
python /Users/joi/amplifier/tools/apple_notes.py create "Migration Plan Summary" --stdin <<< "$CONTENT"

# Find notes about a project
python /Users/joi/amplifier/tools/apple_notes.py search "amplifier migration"
```
