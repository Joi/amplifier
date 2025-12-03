# Blog Poster

Create and post blog entries to Notion via MCP. Supports multiple blogs with a structured workflow for collecting materials and generating drafts.

## Installation

```bash
make install
```

## Workflow Overview

```
1. Create draft workspace     →  Collect photos & notes
2. Fill in the workspace      →  Add context, captions, reflections
3. Generate AI context        →  Create prompt for Claude
4. Generate draft with Claude →  Get blog post draft
5. Prepare MCP command        →  Ready to post
6. Post via MCP               →  Creates entry in Notion
```

## Commands

### List configured blogs

```bash
blog-poster list
```

### Show blog details

```bash
blog-poster show tea-journey
blog-poster show tea-journey-jp
```

### Create a draft workspace

Start by creating a workspace to collect your materials:

```bash
blog-poster draft new my-post.md --blog tea-journey --title "Spring Tea Gathering" --date 2025-01-15
```

This creates a markdown file with sections for:
- Event context (type, occasion, location, participants)
- Tea ceremony details (tea, sweets, utensils, seasonal elements)
- Key moments and reflections
- Photo list with captions and context
- Additional notes

### Scan photos from a directory

If you have photos in a folder, generate an inventory:

```bash
blog-poster draft photos ~/Photos/tea-gathering/
blog-poster draft photos ~/Photos/tea-gathering/ -o photos.md
```

This creates a table you can copy into your workspace.

### Generate AI context

After filling in your workspace, generate the prompt for Claude:

```bash
blog-poster draft context my-post.md
blog-poster draft context my-post.md -o context.txt
```

This outputs structured context plus instructions for generating a draft.

### Prepare for posting

Once you have a draft in the standard format, prepare the MCP command:

```bash
blog-poster prepare draft.md --blog tea-journey --date 2025-01-15
```

Options:
- `--title` - Override title from content
- `--date` - Publish date (YYYY-MM-DD)
- `--photographer` - Photographer credit
- `--writer` - Writer credit
- `--language` - Language (English/Japanese)
- `-o FILE` - Output to file instead of stdout

### Create a content template

If you prefer to write directly without the workspace:

```bash
blog-poster template my-post.md --title "Post Title"
```

## Complete Example Workflow

### 1. Create workspace

```bash
blog-poster draft new hatsukamai.md --blog tea-journey --title "Hatsukamai 2025" --date 2025-01-03
```

### 2. Edit the workspace

Fill in the generated `hatsukamai.md` with your notes:
- Describe the event, participants, mood
- List your photos with captions and context
- Add reflections and key moments

### 3. Generate context for Claude

```bash
blog-poster draft context hatsukamai.md
```

### 4. Generate draft with Claude

Copy the context output and ask Claude to generate a draft. Claude will produce content in the standard format:

```markdown
# Hatsukamai 2025

Opening paragraph setting the scene...

[IMAGE: tokonoma.jpg]
The New Year tokonoma arrangement.

More narrative text...

[IMAGE: koicha.jpg]
The first bowl of thick tea.
```

### 5. Save and prepare

Save Claude's draft to a file, then prepare for posting:

```bash
blog-poster prepare hatsukamai-draft.md --blog tea-journey --date 2025-01-03
```

### 6. Post via MCP

The `prepare` command outputs the MCP `notion-create-pages` parameters. In Claude Code:

```
Use notion-create-pages with parent data_source_id "..." and the page properties/content shown above.
```

## Content Format

Blog posts use a simple markdown format with image markers:

```markdown
# Post Title

Opening paragraph with context and scene-setting.

[IMAGE: photo1.jpg]
Caption describing this image.

More narrative text continuing the story...

## Section Heading

Additional content organized by sections.

[IMAGE: photo2.jpg]
Another image with its caption.

Closing thoughts and reflections.
```

## Photo Handling

Photos should be:
1. Uploaded to a hosting service (or your Notion workspace)
2. Referenced by URL in the final content

During the draft phase, use filenames as placeholders. Replace with URLs before posting.

## Adding New Blogs

To add a new blog, edit `blogs.json`:

```json
{
  "my-blog": {
    "name": "My Blog Name",
    "description": "Description",
    "data_source": "collection://UUID",
    "database_id": "UUID",
    "main_page": "UUID",
    "schema": {
      "title": "Title",
      "date": "Publish Date",
      "photographer": "Photographer",
      "writer": "Writer",
      "language": "Select"
    },
    "languages": ["English", "Japanese"],
    "defaults": {
      "photographer": "Your Name",
      "writer": "Your Name",
      "language": "English"
    }
  }
}
```

Get the UUIDs by fetching the Notion page/database via MCP.

## MCP Tools Used

- `notion-create-pages` - Create the blog post
- `notion-update-page` - Add/modify content
- `notion-fetch` - Preview and verify
- `notion-search` - Find existing posts
