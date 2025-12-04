"""CLI for Blog Poster tool."""

import json
import sys
from pathlib import Path

import click

from blog_poster.config import get_blog, load_blogs
from blog_poster.drafts import DraftWorkspace, create_workspace_template
from blog_poster.formatter import parse_content_file


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Blog Poster - Create blog posts in Notion via MCP.

    This tool helps prepare blog posts for publishing to Notion.
    The actual posting is done via Claude Code's MCP integration.
    """
    pass


@main.command("list")
def list_blogs():
    """List configured blogs."""
    blogs = load_blogs()

    if not blogs:
        click.echo("No blogs configured. Add entries to blogs.json")
        return

    click.echo(f"Configured blogs ({len(blogs)}):\n")
    for slug, config in blogs.items():
        click.echo(f"  {slug}")
        click.echo(f"    Name: {config.name}")
        if config.description:
            click.echo(f"    Description: {config.description}")
        click.echo(f"    Languages: {', '.join(config.languages) or 'Not specified'}")
        click.echo()


@main.command("show")
@click.argument("blog_slug")
def show_blog(blog_slug: str):
    """Show details for a specific blog."""
    blog = get_blog(blog_slug)

    if not blog:
        click.echo(f"Blog '{blog_slug}' not found. Use 'list' to see available blogs.", err=True)
        sys.exit(1)

    click.echo(f"Blog: {blog.name}")
    click.echo(f"Database ID: {blog.database_id}")
    click.echo(f"Data Source: {blog.data_source}")
    click.echo()
    click.echo("Schema mapping:")
    for field, prop in blog.schema_mapping.model_dump().items():
        if prop:
            click.echo(f"  {field}: {prop}")
    click.echo()
    click.echo("Defaults:")
    for field, value in blog.defaults.model_dump().items():
        if value:
            click.echo(f"  {field}: {value}")


@main.command("prepare")
@click.argument("content_file", type=click.Path(exists=True))
@click.option("--blog", "blog_slug", required=True, help="Target blog slug")
@click.option("--title", help="Override title from content file")
@click.option("--date", help="Publish date (YYYY-MM-DD)")
@click.option("--photographer", help="Photographer credit")
@click.option("--writer", help="Writer credit")
@click.option("--language", help="Language (English/Japanese)")
@click.option("--output", "-o", type=click.Path(), help="Output file for MCP command")
def prepare_post(
    content_file: str,
    blog_slug: str,
    title: str | None,
    date: str | None,
    photographer: str | None,
    writer: str | None,
    language: str | None,
    output: str | None,
):
    """Prepare a blog post from a content file.

    This parses the content file and generates the MCP command
    to create the post in Notion.
    """
    blog = get_blog(blog_slug)
    if not blog:
        click.echo(f"Blog '{blog_slug}' not found.", err=True)
        sys.exit(1)

    # Parse content file
    with open(content_file) as f:
        content = f.read()

    blog_content = parse_content_file(content)

    # Apply overrides
    if title:
        blog_content.title = title
    if date:
        blog_content.publish_date = date
    if photographer:
        blog_content.photographer = photographer
    elif blog.defaults.photographer:
        blog_content.photographer = blog.defaults.photographer
    if writer:
        blog_content.writer = writer
    elif blog.defaults.writer:
        blog_content.writer = blog.defaults.writer
    if language:
        blog_content.language = language
    elif blog.defaults.language:
        blog_content.language = blog.defaults.language

    # Generate Notion markdown
    notion_content = blog_content.to_notion_markdown()

    # Generate properties
    schema = blog.schema_mapping.model_dump()
    properties = blog_content.to_properties(schema)

    # Build the MCP command structure
    mcp_command = {
        "tool": "notion-create-pages",
        "params": {
            "parent": {"data_source_id": blog.data_source.replace("collection://", "")},
            "pages": [{"properties": properties, "content": notion_content}],
        },
    }

    # Output
    result = json.dumps(mcp_command, indent=2, ensure_ascii=False)

    if output:
        with open(output, "w") as f:
            f.write(result)
        click.echo(f"MCP command written to {output}")
    else:
        click.echo("Generated MCP command:")
        click.echo("-" * 40)
        click.echo(result)

    click.echo()
    click.echo("To create this post, run in Claude Code:")
    click.echo("  Use notion-create-pages with the above parameters")


@main.command("template")
@click.argument("output_file", type=click.Path())
@click.option("--title", default="Post Title", help="Initial title")
def create_template(output_file: str, title: str):
    """Create a template content file."""
    template = f"""# {title}

Opening paragraph that sets the scene and introduces the topic.

[IMAGE: image-01.jpg]
Description of what this image shows and its significance.

[IMAGE: image-02.jpg]
More context about the second image.

## Section Heading

Continue the narrative with more details...

[IMAGE: image-03.jpg]
Another image with description.

Closing thoughts and any concluding remarks.
"""

    with open(output_file, "w") as f:
        f.write(template)

    click.echo(f"Template created: {output_file}")
    click.echo()
    click.echo("Edit the file with your content, then use 'prepare' to generate the MCP command.")


@main.group("draft")
def draft_group():
    """Manage draft workspaces for collecting post materials."""
    pass


@draft_group.command("new")
@click.argument("output_file", type=click.Path())
@click.option("--blog", "blog_slug", required=True, help="Target blog slug")
@click.option("--title", default="Untitled Post", help="Working title")
@click.option("--date", "event_date", help="Event date (YYYY-MM-DD)")
@click.option("--format", "fmt", type=click.Choice(["json", "md"]), default="md", help="Output format")
def draft_new(output_file: str, blog_slug: str, title: str, event_date: str | None, fmt: str):
    """Create a new draft workspace for collecting materials.

    The workspace helps you organize photos, notes, and context
    before generating the blog post.
    """
    blog = get_blog(blog_slug)
    if not blog:
        click.echo(f"Blog '{blog_slug}' not found.", err=True)
        sys.exit(1)

    workspace = create_workspace_template(blog_slug, title, event_date)
    workspace.language = blog.defaults.language or "English"

    output_path = Path(output_file)

    if fmt == "md":
        # Create human-friendly markdown template
        template = f"""# {title}

> Draft workspace for: **{blog.name}**
> Edit this file, then run: `blog-poster draft context {output_file}`

## Basic Info

- **Event Date:** {workspace.event_date}
- **Language:** {workspace.language}

## Event Context

**Type:** (e.g., tea gathering, practice session, seasonal event)


**Occasion:** (e.g., New Year's first tea, memorial, casual practice)


**Location:**


**Participants:** (who was there, their roles)


## Tea Ceremony Details

**Tea:** (type, preparation style)


**Sweets:** (wagashi served)


**Utensils:** (notable tea ware)


**Seasonal Elements:** (flowers, scroll, seasonal references)


## Key Moments

What stood out? Memorable moments?


## Reflections

Personal thoughts, what you learned or felt...


## Mood / Atmosphere

The feeling of the event...


## Photos

List your photos with context. Format:
- `filename.jpg` | Caption | What's happening, why it matters

Example:
- `IMG_001.jpg` | Preparing the tea | The careful attention to each movement
- `IMG_002.jpg` | Seasonal flowers | Camellias arranged in the tokonoma

Your photos:



## Additional Notes

Any other thoughts, raw notes, stream of consciousness...


"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(template)
        click.echo(f"Draft workspace created: {output_path}")
        click.echo()
        click.echo("Next steps:")
        click.echo("  1. Edit the file with your notes and photo list")
        click.echo(f"  2. Run: blog-poster draft context {output_file}")
        click.echo("  3. Use the context to generate a draft with Claude")

    else:
        # JSON format
        workspace.save(output_path)
        click.echo(f"Draft workspace created: {output_path}")
        click.echo("Edit the JSON file with your notes and photos.")


@draft_group.command("context")
@click.argument("workspace_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file (default: stdout)")
def draft_context(workspace_file: str, output: str | None):
    """Generate AI context from a draft workspace.

    This creates a structured prompt you can give to Claude
    to generate the blog post draft.
    """
    workspace_path = Path(workspace_file)

    if workspace_path.suffix == ".json":
        workspace = DraftWorkspace.load(workspace_path)
        context = workspace.to_prompt_context()
    else:
        # Parse markdown format
        context = _parse_markdown_workspace(workspace_path)

    prompt = f"""{context}

---

## Instructions for Draft Generation

Based on the above context, please write a blog post draft that:

1. **Captures the essence** of the event/experience
2. **Weaves in the photos** naturally at appropriate moments
3. **Reflects the mood** and atmosphere described
4. **Uses the specified language** ({_extract_language(context)})
5. **Follows this structure:**
   - Opening that sets the scene
   - Key moments interspersed with photos
   - Personal reflections
   - Closing thoughts

Output format should be ready for the `blog-poster prepare` command:
```
# Title

Opening paragraph...

[IMAGE: filename.jpg]
Caption for the image.

More text...
```
"""

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(prompt)
        click.echo(f"Context written to: {output}")
    else:
        click.echo(prompt)


def _extract_language(context: str) -> str:
    """Extract language from context string."""
    if "Japanese" in context and "Language:** Japanese" in context:
        return "Japanese"
    return "English"


def _parse_markdown_workspace(path: Path) -> str:
    """Parse markdown workspace and return context."""
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # For markdown format, return as-is since it's already human-readable
    # Just clean up the instruction comments
    lines = []
    for line in content.split("\n"):
        if line.startswith("> "):
            continue  # Skip instruction lines
        lines.append(line)

    return "\n".join(lines)


@draft_group.command("photos")
@click.argument("directory", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file for photo list")
def draft_photos(directory: str, output: str | None):
    """Scan a directory for photos and create a list template.

    Helps you inventory photos before adding context.
    """
    photo_dir = Path(directory)
    extensions = {".jpg", ".jpeg", ".png", ".heic", ".webp"}

    photos = []
    for ext in extensions:
        photos.extend(photo_dir.glob(f"*{ext}"))
        photos.extend(photo_dir.glob(f"*{ext.upper()}"))

    photos = sorted(set(photos))

    if not photos:
        click.echo(f"No photos found in {directory}")
        return

    lines = [
        "# Photo Inventory",
        "",
        f"Found {len(photos)} photos in {directory}",
        "",
        "Edit this list to add captions and context:",
        "",
        "| # | Filename | Caption | Context |",
        "|---|----------|---------|---------|",
    ]

    for i, photo in enumerate(photos, 1):
        lines.append(f"| {i} | {photo.name} |  |  |")

    result = "\n".join(lines)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(result)
        click.echo(f"Photo list written to: {output}")
    else:
        click.echo(result)


if __name__ == "__main__":
    main()
