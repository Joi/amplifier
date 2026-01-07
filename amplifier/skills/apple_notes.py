"""Apple Notes skill - Create, read, search, and manage notes.

Native Amplifier skill for Apple Notes. Works everywhere:
main session, subagents, SDK, scripts, cron jobs.

Usage:
    from amplifier.skills.apple_notes import (
        create_note, read_note, search_notes, list_notes, delete_note
    )

    # Create a note (supports Markdown)
    create_note("Meeting Notes", "## Attendees\\n- Alice\\n- Bob")

    # Read a note
    content = read_note("Meeting Notes")

    # Search notes
    results = search_notes("project")

    # List recent notes
    notes = list_notes(limit=10)
"""

from __future__ import annotations

import html
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Note:
    """Represents an Apple Note."""

    title: str
    id: str | None = None
    content: str | None = None
    folder: str = "Notes"


def _escape_applescript(text: str) -> str:
    """Escape text for use in AppleScript strings."""
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    return text


def _run_applescript(script: str) -> str:
    """Execute AppleScript and return result."""
    result = subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr}")

    return result.stdout.strip()


def markdown_to_html(md_text: str) -> str:
    """Convert Markdown to HTML suitable for Apple Notes.

    Apple Notes supports basic HTML: h1-h3, p, ul/ol/li, b, i, pre, a, br
    """
    lines = md_text.split("\n")
    html_lines = []
    in_code_block = False
    in_list = False
    list_type = None
    code_block_content = []

    def close_list():
        nonlocal in_list, list_type
        if in_list:
            html_lines.append(f"</{list_type}>")
            in_list = False
            list_type = None

    def process_inline(text: str) -> str:
        """Process inline markdown: bold, italic, code, links"""
        text = html.escape(text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)
        text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
        text = re.sub(r"(?<![_\w])_([^_]+)_(?![_\w])", r"<i>\1</i>", text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        return text

    i = 0
    while i < len(lines):
        line = lines[i]

        # Code blocks
        if line.startswith("```"):
            if in_code_block:
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


def create_note(
    title: str,
    content: str,
    folder: str = "Notes",
    convert_markdown: bool = True,
) -> Note:
    """Create a new Apple Note.

    Args:
        title: Note title
        content: Note content (Markdown supported by default)
        folder: Target folder (default: "Notes")
        convert_markdown: Convert Markdown to HTML (default: True)

    Returns:
        The created Note
    """
    if convert_markdown:
        html_content = markdown_to_html(content)
    else:
        html_content = content

    escaped_title = _escape_applescript(title)
    escaped_content = _escape_applescript(html_content)
    escaped_folder = _escape_applescript(folder)

    script = f'''
tell application "Notes"
    tell account "iCloud"
        make new note at folder "{escaped_folder}" with properties {{name:"{escaped_title}", body:"{escaped_content}"}}
    end tell
end tell
'''

    note_id = _run_applescript(script)

    return Note(title=title, id=note_id, content=content, folder=folder)


def read_note(title: str) -> str | None:
    """Read the content of a note by title.

    Args:
        title: Note title (partial match)

    Returns:
        Plain text content of the note, or None if not found
    """
    escaped_title = _escape_applescript(title)

    script = f'''
tell application "Notes"
    tell account "iCloud"
        set matchingNotes to notes whose name contains "{escaped_title}"
        if (count of matchingNotes) > 0 then
            set n to item 1 of matchingNotes
            return plaintext of n
        else
            return ""
        end if
    end tell
end tell
'''

    result = _run_applescript(script)
    return result if result else None


def search_notes(query: str, search_body: bool = False) -> list[str]:
    """Search Apple Notes by title (and optionally body).

    Args:
        query: Search query
        search_body: Also search note body (slower)

    Returns:
        List of matching note titles
    """
    escaped_query = _escape_applescript(query)

    if search_body:
        script = f'''
tell application "Notes"
    tell account "iCloud"
        set matchingNotes to notes whose plaintext contains "{escaped_query}"
        set results to {{}}
        repeat with n in matchingNotes
            set end of results to name of n
        end repeat
        return results
    end tell
end tell
'''
    else:
        script = f'''
tell application "Notes"
    tell account "iCloud"
        set matchingNotes to notes whose name contains "{escaped_query}"
        set results to {{}}
        repeat with n in matchingNotes
            set end of results to name of n
        end repeat
        return results
    end tell
end tell
'''

    output = _run_applescript(script)

    if not output:
        return []

    # AppleScript returns comma-separated list
    return [t.strip() for t in output.split(", ") if t.strip()]


def list_notes(limit: int = 10, folder: str | None = None) -> list[str]:
    """List recent notes.

    Args:
        limit: Maximum notes to return
        folder: Filter by folder name (None for all)

    Returns:
        List of note titles
    """
    if folder:
        escaped_folder = _escape_applescript(folder)
        script = f'''
tell application "Notes"
    tell account "iCloud"
        set noteList to {{}}
        set noteCount to 0
        repeat with n in notes of folder "{escaped_folder}"
            if noteCount < {limit} then
                set end of noteList to name of n
                set noteCount to noteCount + 1
            end if
        end repeat
        return noteList
    end tell
end tell
'''
    else:
        script = f'''
tell application "Notes"
    tell account "iCloud"
        set noteList to {{}}
        set noteCount to 0
        repeat with n in notes
            if noteCount < {limit} then
                set end of noteList to name of n
                set noteCount to noteCount + 1
            end if
        end repeat
        return noteList
    end tell
end tell
'''

    output = _run_applescript(script)

    if not output:
        return []

    return [t.strip() for t in output.split(", ") if t.strip()]


def delete_note(title: str) -> bool:
    """Delete a note by exact title.

    Args:
        title: Exact note title

    Returns:
        True if deleted, False if not found
    """
    escaped_title = _escape_applescript(title)

    script = f'''
tell application "Notes"
    tell account "iCloud"
        set matchingNotes to notes whose name is "{escaped_title}"
        if (count of matchingNotes) > 0 then
            delete item 1 of matchingNotes
            return true
        else
            return false
        end if
    end tell
end tell
'''

    result = _run_applescript(script)
    return "true" in result.lower()


def create_note_from_file(title: str, file_path: str | Path, folder: str = "Notes") -> Note:
    """Create a note from a file.

    Args:
        title: Note title
        file_path: Path to the file (Markdown or text)
        folder: Target folder

    Returns:
        The created Note
    """
    content = Path(file_path).read_text()
    return create_note(title, content, folder=folder)


# =============================================================================
# CLI Interface
# =============================================================================


def _cli_main() -> None:
    """CLI entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Apple Notes CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create command
    create_p = subparsers.add_parser("create", help="Create a note")
    create_p.add_argument("title", help="Note title")
    create_p.add_argument("content", nargs="?", help="Note content (Markdown)")
    create_p.add_argument("--file", "-f", help="Read content from file")
    create_p.add_argument("--stdin", action="store_true", help="Read from stdin")
    create_p.add_argument("--folder", default="Notes", help="Target folder")
    create_p.add_argument("--html", action="store_true", help="Content is HTML")

    # Search command
    search_p = subparsers.add_parser("search", help="Search notes")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--body", action="store_true", help="Search body too")

    # Read command
    read_p = subparsers.add_parser("read", help="Read a note")
    read_p.add_argument("title", help="Note title (partial match)")

    # List command
    list_p = subparsers.add_parser("list", help="List recent notes")
    list_p.add_argument("--limit", "-n", type=int, default=10, help="Limit")
    list_p.add_argument("--folder", help="Filter by folder")

    # Delete command
    delete_p = subparsers.add_parser("delete", help="Delete a note")
    delete_p.add_argument("title", help="Exact note title")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "create":
            if args.stdin:
                content = sys.stdin.read()
            elif args.file:
                content = Path(args.file).read_text()
            elif args.content:
                content = args.content
            else:
                print("Error: Must provide content, --file, or --stdin", file=sys.stderr)
                sys.exit(1)

            note = create_note(
                args.title,
                content,
                folder=args.folder,
                convert_markdown=not args.html,
            )
            print(f"✓ Created note: {note.title}")
            if note.id:
                print(f"  ID: {note.id}")

        elif args.command == "search":
            results = search_notes(args.query, search_body=args.body)
            if results:
                print(f"Found {len(results)} note(s):")
                for title in results:
                    print(f"  • {title}")
            else:
                print("No notes found.")

        elif args.command == "read":
            content = read_note(args.title)
            if content:
                print(content)
            else:
                print(f"Note not found: {args.title}", file=sys.stderr)
                sys.exit(1)

        elif args.command == "list":
            notes = list_notes(args.limit, folder=args.folder)
            if notes:
                print(f"Recent notes ({len(notes)}):")
                for title in notes:
                    print(f"  • {title}")
            else:
                print("No notes found.")

        elif args.command == "delete":
            if delete_note(args.title):
                print(f"✓ Deleted note: {args.title}")
            else:
                print(f"Note not found: {args.title}", file=sys.stderr)
                sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
