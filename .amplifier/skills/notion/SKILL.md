---
name: notion
description: Notion workspace integration - search, read, create, and update pages and databases. Use when user wants to interact with their Notion workspace.
version: 1.0.0
---

# Notion Skill

Full Notion API integration with authenticated access via Amplifier secrets.

## When to Use

- User asks to "search Notion for X" or "find my notes about Y"
- User wants to read a Notion page or database
- User asks to "create a page in Notion" or "add to my database"
- User wants to query a database with filters
- User mentions updating or archiving Notion content

## Python API (Preferred)

```python
from amplifier.skills.notion import (
    search, get_page, get_database, query_database,
    create_page, update_page, append_blocks, extract_plain_text
)

# Search pages and databases
results = await search("meeting notes")
results = await search("projects", filter_type="database")

# Get page with content
page = await get_page("page-id-here")
print(page.title)
print(extract_plain_text(page.content_blocks))

# Get database schema
db = await get_database("database-id")
for prop_name, schema in db.properties_schema.items():
    print(f"{prop_name}: {schema['type']}")

# Query database with filters
rows = await query_database(
    "database-id",
    filter={"property": "Status", "status": {"equals": "Done"}},
    sorts=[{"property": "Date", "direction": "descending"}]
)

# Create a page in a database
page = await create_page(
    parent_id="database-id",
    title="New Task",
    content="## Description\n\nTask details here."
)

# Create a subpage under another page
page = await create_page(
    parent_id="page-id",
    title="Subpage",
    content="Content here",
    parent_type="page_id"
)

# Update page properties
await update_page("page-id", properties={
    "Status": {"status": {"name": "Done"}}
})

# Archive a page
await update_page("page-id", archived=True)

# Append content to existing page
await append_blocks("page-id", "## New Section\n\nMore content.")
```

## CLI Interface

```bash
# Search
python -m amplifier.skills.notion search "project notes"
python -m amplifier.skills.notion search "tasks" -t database

# Get page content
python -m amplifier.skills.notion page "page-id-here"

# Get database info
python -m amplifier.skills.notion database "database-id"

# Query database
python -m amplifier.skills.notion query "database-id" -n 20

# Create page
python -m amplifier.skills.notion create "database-id" "New Page Title" -c "Page content"
```

## Data Models

### NotionPage
- `id`: Page ID
- `title`: Page title
- `url`: Notion URL
- `parent_type`: "database_id" or "page_id"
- `parent_id`: Parent ID
- `properties`: Raw properties dict
- `content_blocks`: List of block objects (when fetched)
- `created_time`, `last_edited_time`: Timestamps

### NotionDatabase
- `id`: Database ID
- `title`: Database title
- `url`: Notion URL
- `description`: Database description
- `properties_schema`: Dict of property definitions

## Markdown Support

When creating pages, the skill converts markdown to Notion blocks:
- Headers (`#`, `##`, `###`)
- Bullet lists (`-` or `*`)
- Numbered lists (`1.`, `2.`, etc.)
- Code blocks (``` with language)
- Paragraphs

## Authentication

Uses Notion token from `amplifier.utils.secrets`:
- Keychain: "Amplifier Notion Token"
- age-encrypted: `NOTION_TOKEN`
- Environment: `NOTION_TOKEN`

## Filter Examples

```python
# Status equals
{"property": "Status", "status": {"equals": "In Progress"}}

# Checkbox is checked
{"property": "Done", "checkbox": {"equals": True}}

# Date after
{"property": "Due", "date": {"after": "2024-01-01"}}

# Text contains
{"property": "Name", "rich_text": {"contains": "meeting"}}

# Compound filter (AND)
{
    "and": [
        {"property": "Status", "status": {"equals": "Done"}},
        {"property": "Priority", "select": {"equals": "High"}}
    ]
}
```

## Advantages Over MCP

- ✅ Works in subagents (MCP tools don't inherit)
- ✅ Uses Amplifier secrets system (age + Keychain)
- ✅ Pure Python, no Node.js dependency
- ✅ Works in scripts, cron jobs, SDK calls
- ✅ Full control over API calls and error handling
