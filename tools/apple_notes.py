#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyobjc-framework-ScriptingBridge",
# ]
# ///
"""
Apple Notes Tool - Create, read, and search Apple Notes using ScriptingBridge.

Converts Markdown to HTML for proper rendering in Apple Notes.
Uses native Python bindings via PyObjC - no subprocess/AppleScript needed.

Usage:
    # Run with uv (handles dependencies automatically)
    uv run ~/amplifier/tools/apple_notes.py create "Note Title" "Content in **markdown**"

    # Create a note from a file
    uv run ~/amplifier/tools/apple_notes.py create "Note Title" --file content.md

    # Create a note from stdin
    echo "# My Note" | uv run ~/amplifier/tools/apple_notes.py create "Note Title" --stdin

    # Search notes by title
    uv run ~/amplifier/tools/apple_notes.py search "search phrase"

    # Read a note
    uv run ~/amplifier/tools/apple_notes.py read "note title"

    # List recent notes
    uv run ~/amplifier/tools/apple_notes.py list [--limit N]

    # Delete a note by title
    uv run ~/amplifier/tools/apple_notes.py delete "note title"
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ScriptingBridge import SBApplication

if TYPE_CHECKING:
    pass


@dataclass
class Note:
    """Represents an Apple Note."""

    title: str
    id: str | None = None
    content: str | None = None
    folder: str = "Notes"


def get_notes_app():
    """Get the Notes application via ScriptingBridge."""
    app = SBApplication.applicationWithBundleIdentifier_("com.apple.Notes")
    if app is None:
        raise RuntimeError("Could not connect to Notes.app")
    return app


def get_icloud_account(app):
    """Get the iCloud account from Notes app."""
    for account in app.accounts():
        if account.name() == "iCloud":
            return account
    # Fallback to first account
    accounts = list(app.accounts())
    if accounts:
        return accounts[0]
    raise RuntimeError("No Notes accounts found")


def get_folder(account, folder_name: str):
    """Get a folder by name, creating it if needed."""
    for folder in account.folders():
        if folder.name() == folder_name:
            return folder
    # Folder not found - use default Notes folder
    for folder in account.folders():
        if folder.name() == "Notes":
            return folder
    raise RuntimeError(f"Folder '{folder_name}' not found")


def markdown_to_html(md_text: str) -> str:
    """
    Convert Markdown to HTML suitable for Apple Notes.

    Apple Notes supports basic HTML: h1-h3, p, ul/ol/li, b, i, pre, a, br
    """
    lines = md_text.split("\n")
    html_lines: list[str] = []
    in_code_block = False
    in_list = False
    list_type: str | None = None
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
                html_lines.append("<pre>" + html.escape("\n".join(code_block_content)) + "</pre>")
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
        html_lines.append("<pre>" + html.escape("\n".join(code_block_content)) + "</pre>")

    return "\n".join(html_lines)


def create_note(title: str, content: str, folder: str = "Notes", convert_md: bool = True) -> Note:
    """Create a new Apple Note with the given title and content."""
    if convert_md:
        html_content = markdown_to_html(content)
    else:
        html_content = content

    app = get_notes_app()
    account = get_icloud_account(app)
    target_folder = get_folder(account, folder)

    # Create the note using ScriptingBridge
    note_class = app.classForScriptingClass_("note")
    new_note = note_class.alloc().initWithProperties_({"name": title, "body": html_content})

    target_folder.notes().addObject_(new_note)

    return Note(
        title=title,
        id=str(new_note.id()) if new_note.id() else None,
        folder=folder,
    )


def search_notes(query: str, search_body: bool = False) -> list[str]:
    """Search Apple Notes by title (and optionally body)."""
    app = get_notes_app()
    account = get_icloud_account(app)

    query_lower = query.lower()
    results: list[str] = []

    for note in account.notes():
        name = note.name()
        if name and query_lower in name.lower():
            results.append(name)
        elif search_body:
            plaintext = note.plaintext()
            if plaintext and query_lower in plaintext.lower():
                results.append(name)

    return results


def read_note(title: str) -> str | None:
    """Read the content of a note by title (partial match)."""
    app = get_notes_app()
    account = get_icloud_account(app)

    title_lower = title.lower()

    for note in account.notes():
        name = note.name()
        if name and title_lower in name.lower():
            return note.plaintext()

    return None


def list_notes(limit: int = 10, folder: str | None = None) -> list[str]:
    """List recent notes."""
    app = get_notes_app()
    account = get_icloud_account(app)

    results: list[str] = []
    count = 0

    if folder:
        target_folder = get_folder(account, folder)
        notes_iter = target_folder.notes()
    else:
        notes_iter = account.notes()

    for note in notes_iter:
        if count >= limit:
            break
        name = note.name()
        if name:
            results.append(name)
            count += 1

    return results


def delete_note(title: str) -> bool:
    """Delete a note by exact title match."""
    app = get_notes_app()
    account = get_icloud_account(app)

    for note in account.notes():
        if note.name() == title:
            note.delete()
            return True

    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apple Notes Tool - Create, read, and search Apple Notes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new note")
    create_parser.add_argument("title", help="Note title")
    create_parser.add_argument("content", nargs="?", help="Note content (Markdown supported)")
    create_parser.add_argument("--file", "-f", help="Read content from file")
    create_parser.add_argument("--stdin", action="store_true", help="Read content from stdin")
    create_parser.add_argument("--folder", default="Notes", help="Target folder (default: Notes)")
    create_parser.add_argument("--html", action="store_true", help="Content is already HTML, skip conversion")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search notes by title")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--body", action="store_true", help="Also search note body")

    # Read command
    read_parser = subparsers.add_parser("read", help="Read a note by title")
    read_parser.add_argument("title", help="Note title (partial match)")

    # List command
    list_parser = subparsers.add_parser("list", help="List recent notes")
    list_parser.add_argument("--limit", "-n", type=int, default=10, help="Number of notes to list")
    list_parser.add_argument("--folder", help="List notes from specific folder")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a note by title")
    delete_parser.add_argument("title", help="Exact note title")

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
                convert_md=not args.html,
            )
            print(f"Created note: {args.title}")
            if note.id:
                print(f"  ID: {note.id}")

        elif args.command == "search":
            results = search_notes(args.query, search_body=args.body)
            if results:
                print(f"Found {len(results)} note(s):")
                for title in results:
                    print(f"  - {title}")
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
                    print(f"  - {title}")
            else:
                print("No notes found.")

        elif args.command == "delete":
            if delete_note(args.title):
                print(f"Deleted note: {args.title}")
            else:
                print(f"Note not found: {args.title}", file=sys.stderr)
                sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
