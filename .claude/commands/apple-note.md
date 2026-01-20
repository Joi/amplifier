---
description: Read from or save to Apple Notes
category: productivity
allowed-tools: Bash
---

# Claude Command: Apple Note

Read from or save content to Apple Notes. **Always use the Python tool** which handles Markdown-to-HTML conversion automatically.

## Usage

### Reading Notes (search)
```
/apple-note find <search phrase>
/apple-note search <search phrase>
/apple-note read <search phrase>
```

Examples:
```
/apple-note find NAAN
/apple-note search meeting notes
/apple-note read tea foundation
```

### Writing Notes (save)
```
/apple-note save <description of what to save>
/apple-note create <title>
/apple-note add <description>
```

Examples:
```
/apple-note save the NAAN report
/apple-note create a note with the meeting summary
/apple-note add this recipe to my notes
```

## Technical Implementation

**IMPORTANT:** Always use the Python CLI tool at `~/amplifier/tools/apple_notes.py`. This tool automatically converts Markdown to HTML that renders properly in Apple Notes.

### Creating Notes

```bash
# Create a note - content can be in Markdown, it will be converted automatically
uv run ~/amplifier/tools/apple_notes.py create "Note Title" "Content with **bold** and *italic*"

# Create from a file
uv run ~/amplifier/tools/apple_notes.py create "Note Title" --file /path/to/content.md

# Create from stdin (useful for longer content)
echo "# Heading

Content with **markdown** formatting.

- Bullet point 1
- Bullet point 2
" | uv run ~/amplifier/tools/apple_notes.py create "Note Title" --stdin

# Create in a specific folder
uv run ~/amplifier/tools/apple_notes.py create "Note Title" "Content" --folder "Work"
```

### Reading Notes

```bash
# Read a note by title (partial match)
uv run ~/amplifier/tools/apple_notes.py read "Note Title"
```

### Searching Notes

```bash
# Search by title
uv run ~/amplifier/tools/apple_notes.py search "search phrase"

# Search in note body too
uv run ~/amplifier/tools/apple_notes.py search "search phrase" --body
```

### Listing Notes

```bash
# List recent notes
uv run ~/amplifier/tools/apple_notes.py list

# List more notes
uv run ~/amplifier/tools/apple_notes.py list --limit 20
```

### Deleting Notes

```bash
# Delete by exact title
uv run ~/amplifier/tools/apple_notes.py delete "Exact Note Title"
```

## Markdown Support

The tool converts these Markdown elements to Apple Notes HTML:

| Markdown | Apple Notes |
|----------|-------------|
| `# Heading` | Large heading |
| `## Heading` | Medium heading |
| `### Heading` | Small heading |
| `**bold**` | **Bold text** |
| `*italic*` | *Italic text* |
| `- item` | Bullet list |
| `1. item` | Numbered list |
| `` `code` `` | Inline code |
| ` ``` ` blocks | Code block |
| `[text](url)` | Clickable link |
| `> quote` | Blockquote |

## Best Practice for Saving Content

When saving content from the conversation:

1. Compose the content in Markdown format
2. Use `--stdin` to pass longer content:

```bash
cat << 'EOF' | uv run ~/amplifier/tools/apple_notes.py create "Note Title" --stdin
# Main Heading

Some introductory text.

## Section 1

- Point one
- Point two

## Section 2

1. First item
2. Second item

**Important:** Don't forget this!
EOF
```

## Folder Options

By default, notes are created in the "Notes" folder. Common folders:
- `Notes` (default)
- `Work`
- `Personal`

$ARGUMENTS
