---
name: apple-notes
description: Create, read, search, and manage Apple Notes with Markdown support. Use when user wants to save information, read notes, or search their notes.
version: 2.0.0
---

# Apple Notes Skill

Native integration with Apple Notes via AppleScript. Supports Markdown-to-HTML conversion.

## When to Use

- User says "save this to notes" or "create a note"
- User wants to read/find an existing note
- User asks to search their notes
- Saving research, meeting notes, or documentation
- Part of morning routine workflows

## Python API (Preferred)

```python
from amplifier.skills import (
    create_note, read_note, search_notes, list_notes, delete_note,
    markdown_to_html, Note
)

# Create a note (Markdown auto-converted to HTML)
note = create_note("Meeting Notes", """
## Attendees
- Alice
- Bob

## Action Items
1. Review proposal
2. Send follow-up email

**Important:** Deadline is Friday
""")

# Create in specific folder
note = create_note("Project Ideas", content, folder="Work")

# Create without Markdown conversion (raw HTML)
note = create_note("Raw Note", "<h1>Title</h1>", convert_markdown=False)

# Read a note
content = read_note("Meeting Notes")  # Partial title match
if content:
    print(content)

# Search notes
results = search_notes("project")  # Search titles
results = search_notes("deadline", search_body=True)  # Search content too

# List recent notes
notes = list_notes(limit=20)
notes = list_notes(folder="Work")

# Delete a note
delete_note("Old Note")  # Exact title match
```

## Data Classes

```python
@dataclass
class Note:
    title: str
    id: str | None = None
    content: str | None = None
    folder: str = "Notes"
```

## Markdown Support

The skill converts Markdown to HTML that Apple Notes understands:

| Markdown | Result |
|----------|--------|
| `# Heading` | `<h1>` |
| `## Heading` | `<h2>` |
| `**bold**` | `<b>` |
| `*italic*` | `<i>` |
| `- item` | `<ul><li>` |
| `1. item` | `<ol><li>` |
| `` `code` `` | `<code>` |
| `[link](url)` | `<a href>` |
| ` ``` ` blocks | `<pre>` |

## CLI Interface

```bash
# Create note
python -m amplifier.skills.apple_notes create "Title" "Content in **markdown**"
python -m amplifier.skills.apple_notes create "Title" --file notes.md
echo "Content" | python -m amplifier.skills.apple_notes create "Title" --stdin

# Search
python -m amplifier.skills.apple_notes search "keyword"
python -m amplifier.skills.apple_notes search "keyword" --body

# Read
python -m amplifier.skills.apple_notes read "Note Title"

# List
python -m amplifier.skills.apple_notes list --limit 20

# Delete
python -m amplifier.skills.apple_notes delete "Exact Title"
```

## Helper Function

```python
from amplifier.skills import markdown_to_html

# Convert Markdown to Apple Notes HTML
html = markdown_to_html("# Title\n\n**Bold** text")
# Returns: <h1>Title</h1>\n<p><b>Bold</b> text</p>
```

## Advantages Over MCP

- ✅ Works in subagents (MCP tools don't inherit)
- ✅ Built-in Markdown conversion
- ✅ Works in scripts, cron jobs, SDK calls
- ✅ Returns proper Python dataclasses
