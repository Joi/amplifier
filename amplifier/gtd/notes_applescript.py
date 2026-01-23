#!/usr/bin/env python3
"""
AppleScript bridge for Mac Notes.app

Provides CRUD operations for notes via AppleScript/osascript.
Automatically converts Markdown to HTML for proper rendering.

NOTE: This module MUST use AppleScript - there is no EventKit equivalent.
Apple Notes does not expose a public framework (unlike Reminders/Calendar).
AppleScript via osascript is the only supported automation method.
Do not attempt to replace this with EventKit - it won't work.
"""

import html
import re
import subprocess
from datetime import datetime
from typing import Optional

SYNC_FOLDER_NAME = "Obsidian Sync"


def markdown_to_html(md_text: str) -> str:
    """
    Convert Markdown to HTML suitable for Apple Notes.

    Apple Notes supports basic HTML: h1-h3, p, ul/ol/li, b, i, pre, a, br
    """
    lines = md_text.split("\n")
    html_lines: list[str] = []
    in_code_block = False
    in_list = False
    list_type: Optional[str] = None
    code_block_content: list[str] = []

    def close_list() -> None:
        nonlocal in_list, list_type
        if in_list:
            html_lines.append(f"</{list_type}>")
            in_list = False
            list_type = None

    def process_inline(text: str) -> str:
        """Process inline markdown: bold, italic, code, links."""
        # Escape HTML entities first (but not our generated tags)
        text = html.escape(text)

        # Code (backticks) - do first to avoid processing inside code
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

        # Bold **text** or __text__
        text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)

        # Italic *text* or _text_
        text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
        text = re.sub(r"(?<![_\w])_([^_]+)_(?![_\w])", r"<i>\1</i>", text)

        # Links [text](url)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

        return text

    i = 0
    while i < len(lines):
        line = lines[i]

        # Code blocks
        if line.startswith("```"):
            if in_code_block:
                # End code block
                html_lines.append(
                    "<pre>" + html.escape("\n".join(code_block_content)) + "</pre>"
                )
                code_block_content = []
                in_code_block = False
            else:
                close_list()
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_block_content.append(line)
            i += 1
            continue

        # Empty lines
        if not line.strip():
            close_list()
            i += 1
            continue

        # Headers
        if line.startswith("### "):
            close_list()
            html_lines.append(f"<h3>{process_inline(line[4:])}</h3>")
            i += 1
            continue
        if line.startswith("## "):
            close_list()
            html_lines.append(f"<h2>{process_inline(line[3:])}</h2>")
            i += 1
            continue
        if line.startswith("# "):
            close_list()
            html_lines.append(f"<h1>{process_inline(line[2:])}</h1>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", line):
            close_list()
            html_lines.append("<hr>")
            i += 1
            continue

        # Unordered list
        if re.match(r"^[-*+]\s+", line):
            if not in_list or list_type != "ul":
                close_list()
                html_lines.append("<ul>")
                in_list = True
                list_type = "ul"
            content = re.sub(r"^[-*+]\s+", "", line)
            html_lines.append(f"<li>{process_inline(content)}</li>")
            i += 1
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", line):
            if not in_list or list_type != "ol":
                close_list()
                html_lines.append("<ol>")
                in_list = True
                list_type = "ol"
            content = re.sub(r"^\d+\.\s+", "", line)
            html_lines.append(f"<li>{process_inline(content)}</li>")
            i += 1
            continue

        # Blockquote
        if line.startswith("> "):
            close_list()
            content = line[2:]
            html_lines.append(f"<blockquote>{process_inline(content)}</blockquote>")
            i += 1
            continue

        # Table handling (convert to simple format)
        if "|" in line and re.match(r"^\|.*\|$", line.strip()):
            close_list()
            # Check if it's a separator row
            if re.match(r"^\|[\s\-:|]+\|$", line.strip()):
                i += 1
                continue
            # Parse table row
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            row_html = " | ".join(process_inline(c) for c in cells)
            html_lines.append(f"<p><b>{row_html}</b></p>")
            i += 1
            continue

        # Regular paragraph
        close_list()
        html_lines.append(f"<p>{process_inline(line)}</p>")
        i += 1

    # Close any remaining open elements
    close_list()
    if in_code_block:
        html_lines.append(
            "<pre>" + html.escape("\n".join(code_block_content)) + "</pre>"
        )

    return "\n".join(html_lines)


def run_applescript(script: str) -> str:
    """Execute an AppleScript and return the result."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(f"AppleScript error: {result.stderr}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError("AppleScript timed out")


def parse_apple_date(date_str: str) -> datetime:
    """Parse Apple's date format string to a datetime object."""
    if not date_str:
        return datetime.now()

    # Remove "at" and parse - format like "Friday, January 9, 2026 at 10:30:00 AM"
    cleaned = date_str.replace(" at ", " ")

    # Try multiple formats
    formats = [
        "%A, %B %d, %Y %I:%M:%S %p",  # Friday, January 9, 2026 10:30:00 AM
        "%A, %B %d, %Y %H:%M:%S",  # Friday, January 9, 2026 10:30:00
        "%Y-%m-%d %H:%M:%S",  # 2026-01-09 10:30:00
    ]

    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    # Fallback
    print(f"Warning: Could not parse date: {date_str}")
    return datetime.now()


def sync_folder_exists() -> bool:
    """Check if the sync folder exists in Notes.app."""
    script = f'''
    tell application "Notes"
      try
        set f to folder "{SYNC_FOLDER_NAME}"
        return true
      on error
        return false
      end try
    end tell
    '''
    return run_applescript(script) == "true"


def create_sync_folder() -> None:
    """Create the sync folder in Notes.app."""
    script = f'''
    tell application "Notes"
      make new folder with properties {{name:"{SYNC_FOLDER_NAME}"}}
    end tell
    '''
    run_applescript(script)


def ensure_sync_folder() -> None:
    """Ensure the sync folder exists, create if not."""
    if not sync_folder_exists():
        create_sync_folder()


def list_notes_in_sync_folder() -> list[dict]:
    """List all notes in the sync folder."""
    ensure_sync_folder()

    script = f'''
    tell application "Notes"
      set outputText to ""
      try
        set syncFolder to folder "{SYNC_FOLDER_NAME}"
        repeat with n in notes of syncFolder
          set noteId to id of n
          set noteName to name of n
          set createDate to creation date of n
          set modDate to modification date of n
          set outputText to outputText & noteId & "|||" & noteName & "|||" & (createDate as string) & "|||" & (modDate as string) & linefeed
        end repeat
      end try
      return outputText
    end tell
    '''

    output = run_applescript(script)
    if not output:
        return []

    notes = []
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue

        parts = line.split("|||")
        if len(parts) >= 4:
            notes.append(
                {
                    "id": parts[0].strip(),
                    "name": parts[1].strip(),
                    "created_at": parse_apple_date(parts[2].strip()),
                    "modified_at": parse_apple_date(parts[3].strip()),
                }
            )

    return notes


def get_note(note_id: str) -> dict:
    """Get a note's full details including body."""
    escaped_id = note_id.replace('"', '\\"')

    script = f'''
    tell application "Notes"
      set n to note id "{escaped_id}"
      set noteId to id of n
      set noteName to name of n
      set noteBody to body of n
      set createDate to creation date of n
      set modDate to modification date of n
      return noteId & "|||" & noteName & "|||" & noteBody & "|||" & (createDate as string) & "|||" & (modDate as string)
    end tell
    '''

    output = run_applescript(script)
    parts = output.split("|||")

    if len(parts) >= 5:
        return {
            "id": parts[0].strip(),
            "name": parts[1].strip(),
            "body": parts[2].strip(),
            "created_at": parse_apple_date(parts[3].strip()),
            "modified_at": parse_apple_date(parts[4].strip()),
        }

    raise RuntimeError(f"Failed to parse note: {note_id}")


def create_note(name: str, body: str, convert_markdown: bool = True) -> str:
    """Create a new note in the sync folder. Returns the new note's ID.

    Args:
        name: The note title
        body: The note content (Markdown by default)
        convert_markdown: If True (default), convert Markdown to HTML
    """
    ensure_sync_folder()

    # Convert Markdown to HTML for proper rendering in Apple Notes
    if convert_markdown:
        body = markdown_to_html(body)

    # Escape for AppleScript
    escaped_name = name.replace("\\", "\\\\").replace('"', '\\"')
    escaped_body = body.replace("\\", "\\\\").replace('"', '\\"')

    script = f'''
    tell application "Notes"
      set syncFolder to folder "{SYNC_FOLDER_NAME}"
      set newNote to make new note at syncFolder with properties {{name:"{escaped_name}", body:"{escaped_body}"}}
      return id of newNote
    end tell
    '''

    return run_applescript(script)


def update_note(
    note_id: str,
    name: Optional[str] = None,
    body: Optional[str] = None,
    convert_markdown: bool = True,
) -> None:
    """Update an existing note.

    Args:
        note_id: The note's ID
        name: New title (optional)
        body: New content in Markdown (optional)
        convert_markdown: If True (default), convert Markdown to HTML
    """
    escaped_id = note_id.replace('"', '\\"')

    set_statements = []
    if name is not None:
        escaped_name = name.replace("\\", "\\\\").replace('"', '\\"')
        set_statements.append(f'set name of n to "{escaped_name}"')
    if body is not None:
        # Convert Markdown to HTML for proper rendering
        if convert_markdown:
            body = markdown_to_html(body)
        escaped_body = body.replace("\\", "\\\\").replace('"', '\\"')
        set_statements.append(f'set body of n to "{escaped_body}"')

    if not set_statements:
        return

    script = f'''
    tell application "Notes"
      set n to note id "{escaped_id}"
      {chr(10).join(set_statements)}
    end tell
    '''

    run_applescript(script)


def delete_note(note_id: str) -> None:
    """Delete a note."""
    escaped_id = note_id.replace('"', '\\"')

    script = f'''
    tell application "Notes"
      set n to note id "{escaped_id}"
      delete n
    end tell
    '''

    run_applescript(script)
