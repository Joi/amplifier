#!/usr/bin/env python3
"""
HTML ↔ Markdown converter for Notes.app sync

Notes.app uses simple HTML:
- <div>content</div> for paragraphs
- <div><br></div> for empty lines
- <b>bold</b> and <i>italic</i> for formatting
- <h1>, <h2>, etc. for headings
- <ul><li>item</li></ul> for lists
- <a href="url">text</a> for links
"""

import re
from typing import Tuple


def html_to_markdown(html: str) -> str:
    """Convert Notes.app HTML to Markdown."""
    if not html:
        return ""

    md = html

    # Handle headings first (before divs)
    md = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1\n", md, flags=re.IGNORECASE)
    md = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1\n", md, flags=re.IGNORECASE)
    md = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1\n", md, flags=re.IGNORECASE)
    md = re.sub(r"<h4[^>]*>(.*?)</h4>", r"#### \1\n", md, flags=re.IGNORECASE)
    md = re.sub(r"<h5[^>]*>(.*?)</h5>", r"##### \1\n", md, flags=re.IGNORECASE)
    md = re.sub(r"<h6[^>]*>(.*?)</h6>", r"###### \1\n", md, flags=re.IGNORECASE)

    # Handle lists
    md = re.sub(r"<ul[^>]*>", "", md, flags=re.IGNORECASE)
    md = re.sub(r"</ul>", "", md, flags=re.IGNORECASE)
    md = re.sub(r"<ol[^>]*>", "", md, flags=re.IGNORECASE)
    md = re.sub(r"</ol>", "", md, flags=re.IGNORECASE)
    md = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", md, flags=re.IGNORECASE)

    # Handle links
    md = re.sub(
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", md, flags=re.IGNORECASE
    )

    # Handle bold and italic
    md = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", md, flags=re.IGNORECASE)
    md = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", md, flags=re.IGNORECASE)
    md = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", md, flags=re.IGNORECASE)
    md = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", md, flags=re.IGNORECASE)

    # Handle strikethrough
    md = re.sub(r"<s[^>]*>(.*?)</s>", r"~~\1~~", md, flags=re.IGNORECASE)
    md = re.sub(r"<strike[^>]*>(.*?)</strike>", r"~~\1~~", md, flags=re.IGNORECASE)

    # Handle code
    md = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", md, flags=re.IGNORECASE)

    # Handle empty divs (empty lines)
    md = re.sub(r"<div><br\s*/?></div>", "\n", md, flags=re.IGNORECASE)

    # Handle divs (paragraphs)
    md = re.sub(r"<div[^>]*>", "", md, flags=re.IGNORECASE)
    md = re.sub(r"</div>", "\n", md, flags=re.IGNORECASE)

    # Handle br tags
    md = re.sub(r"<br\s*/?>", "\n", md, flags=re.IGNORECASE)

    # Handle paragraphs
    md = re.sub(r"<p[^>]*>", "", md, flags=re.IGNORECASE)
    md = re.sub(r"</p>", "\n\n", md, flags=re.IGNORECASE)

    # Handle span tags (often used for styling, just remove)
    md = re.sub(r"<span[^>]*>", "", md, flags=re.IGNORECASE)
    md = re.sub(r"</span>", "", md, flags=re.IGNORECASE)

    # Decode common HTML entities
    md = md.replace("&nbsp;", " ")
    md = md.replace("&amp;", "&")
    md = md.replace("&lt;", "<")
    md = md.replace("&gt;", ">")
    md = md.replace("&quot;", '"')
    md = md.replace("&#39;", "'")

    # Clean up multiple newlines
    md = re.sub(r"\n{3,}", "\n\n", md)

    # Trim whitespace
    md = md.strip()

    return md


def convert_inline_markdown(text: str) -> str:
    """Convert inline Markdown formatting to HTML."""
    html = text

    # Handle links [text](url)
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

    # Handle bold **text** or __text__
    html = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", html)
    html = re.sub(r"__([^_]+)__", r"<b>\1</b>", html)

    # Handle italic *text* or _text_ (but not ** or __)
    html = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", html)
    html = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<i>\1</i>", html)

    # Handle strikethrough ~~text~~
    html = re.sub(r"~~([^~]+)~~", r"<s>\1</s>", html)

    # Handle inline code `text`
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

    return html


def markdown_to_html(markdown: str) -> str:
    """Convert Markdown to Notes.app HTML."""
    if not markdown:
        return ""

    lines = markdown.split("\n")
    html_lines = []

    for line in lines:
        # Handle headings
        if line.startswith("######"):
            text = re.sub(r"^######\s*", "", line)
            html_lines.append(f"<h6>{text}</h6>")
            continue
        if line.startswith("#####"):
            text = re.sub(r"^#####\s*", "", line)
            html_lines.append(f"<h5>{text}</h5>")
            continue
        if line.startswith("####"):
            text = re.sub(r"^####\s*", "", line)
            html_lines.append(f"<h4>{text}</h4>")
            continue
        if line.startswith("###"):
            text = re.sub(r"^###\s*", "", line)
            html_lines.append(f"<h3>{text}</h3>")
            continue
        if line.startswith("##"):
            text = re.sub(r"^##\s*", "", line)
            html_lines.append(f"<h2>{text}</h2>")
            continue
        if line.startswith("#"):
            text = re.sub(r"^#\s*", "", line)
            html_lines.append(f"<h1>{text}</h1>")
            continue

        # Handle list items
        if re.match(r"^[\-\*]\s+", line):
            text = re.sub(r"^[\-\*]\s+", "", line)
            html_lines.append(f"<div>• {convert_inline_markdown(text)}</div>")
            continue

        # Handle numbered lists
        if re.match(r"^\d+\.\s+", line):
            text = re.sub(r"^\d+\.\s+", "", line)
            html_lines.append(f"<div>{convert_inline_markdown(text)}</div>")
            continue

        # Handle empty lines
        if line.strip() == "":
            html_lines.append("<div><br></div>")
            continue

        # Regular paragraph
        html_lines.append(f"<div>{convert_inline_markdown(line)}</div>")

    return "".join(html_lines)


def title_to_filename(title: str) -> str:
    """Generate a safe filename from a note title."""
    # Keep alphanumeric, Japanese chars, spaces, and hyphens
    safe = re.sub(r"[^a-zA-Z0-9\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf\s\-]", "", title)
    # Replace spaces with hyphens
    safe = re.sub(r"\s+", "-", safe.lower())
    # Clean up multiple hyphens
    safe = re.sub(r"-+", "-", safe)
    # Remove leading/trailing hyphens
    safe = safe.strip("-")
    # Limit length
    safe = safe[:100] if safe else "untitled"
    return safe


def filename_to_title(filename: str) -> str:
    """Extract title from filename."""
    # Remove .md extension
    title = re.sub(r"\.md$", "", filename)
    # Replace hyphens with spaces
    title = title.replace("-", " ")
    # Title case
    title = title.title()
    return title


def add_frontmatter(markdown: str, meta: dict) -> str:
    """Add YAML frontmatter to markdown content."""
    title_escaped = meta.get("title", "").replace('"', '\\"')

    frontmatter = f'''---
title: "{title_escaped}"
created: {meta.get("created", "")}
modified: {meta.get("modified", "")}
notes-id: "{meta.get("notes_id", "")}"
---

{markdown}'''

    return frontmatter


def parse_frontmatter(content: str) -> Tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    match = re.match(r"^---\n([\s\S]*?)\n---\n([\s\S]*)$", content)

    if not match:
        return {}, content

    frontmatter_str = match.group(1)
    body = match.group(2)

    # Simple YAML parsing
    frontmatter = {}
    for line in frontmatter_str.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            frontmatter[key] = value

    return frontmatter, body
