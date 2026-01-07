#!/usr/bin/env python3
"""
Apple Notes Tool - Create, read, and search Apple Notes with proper formatting.

Converts Markdown to HTML for proper rendering in Apple Notes.

Usage:
    # Create a note from text
    python apple_notes.py create "Note Title" "Content in **markdown**"
    
    # Create a note from a file
    python apple_notes.py create "Note Title" --file content.md
    
    # Create a note from stdin
    echo "# My Note" | python apple_notes.py create "Note Title" --stdin
    
    # Search notes by title
    python apple_notes.py search "search phrase"
    
    # Read a note
    python apple_notes.py read "note title"
    
    # List recent notes
    python apple_notes.py list [--limit N]
    
    # Delete a note by title
    python apple_notes.py delete "note title"
"""

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path


def markdown_to_html(md_text: str) -> str:
    """
    Convert Markdown to HTML suitable for Apple Notes.
    
    Apple Notes supports basic HTML: h1-h3, p, ul/ol/li, b, i, pre, a, br
    """
    lines = md_text.split('\n')
    html_lines = []
    in_code_block = False
    in_list = False
    list_type = None
    code_block_content = []
    
    def close_list():
        nonlocal in_list, list_type
        if in_list:
            html_lines.append(f'</{list_type}>')
            in_list = False
            list_type = None
    
    def process_inline(text: str) -> str:
        """Process inline markdown: bold, italic, code, links"""
        # Escape HTML entities first (but not our generated tags)
        text = html.escape(text)
        
        # Code (backticks) - do first to avoid processing inside code
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        
        # Bold **text** or __text__
        text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__([^_]+)__', r'<b>\1</b>', text)
        
        # Italic *text* or _text_
        text = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', text)
        text = re.sub(r'(?<![_\w])_([^_]+)_(?![_\w])', r'<i>\1</i>', text)
        
        # Links [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        
        return text
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Code blocks
        if line.startswith('```'):
            if in_code_block:
                # End code block
                html_lines.append('<pre>' + html.escape('\n'.join(code_block_content)) + '</pre>')
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
        if line.startswith('### '):
            close_list()
            html_lines.append(f'<h3>{process_inline(line[4:])}</h3>')
            i += 1
            continue
        if line.startswith('## '):
            close_list()
            html_lines.append(f'<h2>{process_inline(line[3:])}</h2>')
            i += 1
            continue
        if line.startswith('# '):
            close_list()
            html_lines.append(f'<h1>{process_inline(line[2:])}</h1>')
            i += 1
            continue
        
        # Horizontal rule
        if re.match(r'^[-*_]{3,}\s*$', line):
            close_list()
            html_lines.append('<hr>')
            i += 1
            continue
        
        # Unordered list
        if re.match(r'^[-*+]\s+', line):
            if not in_list or list_type != 'ul':
                close_list()
                html_lines.append('<ul>')
                in_list = True
                list_type = 'ul'
            content = re.sub(r'^[-*+]\s+', '', line)
            html_lines.append(f'<li>{process_inline(content)}</li>')
            i += 1
            continue
        
        # Ordered list
        if re.match(r'^\d+\.\s+', line):
            if not in_list or list_type != 'ol':
                close_list()
                html_lines.append('<ol>')
                in_list = True
                list_type = 'ol'
            content = re.sub(r'^\d+\.\s+', '', line)
            html_lines.append(f'<li>{process_inline(content)}</li>')
            i += 1
            continue
        
        # Blockquote
        if line.startswith('> '):
            close_list()
            content = line[2:]
            html_lines.append(f'<blockquote>{process_inline(content)}</blockquote>')
            i += 1
            continue
        
        # Table handling (convert to simple format)
        if '|' in line and re.match(r'^\|.*\|$', line.strip()):
            close_list()
            # Check if it's a separator row
            if re.match(r'^\|[\s\-:|]+\|$', line.strip()):
                i += 1
                continue
            # Parse table row
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            row_html = ' | '.join(process_inline(c) for c in cells)
            html_lines.append(f'<p><b>{row_html}</b></p>')
            i += 1
            continue
        
        # Regular paragraph
        close_list()
        html_lines.append(f'<p>{process_inline(line)}</p>')
        i += 1
    
    # Close any remaining open elements
    close_list()
    if in_code_block:
        html_lines.append('<pre>' + html.escape('\n'.join(code_block_content)) + '</pre>')
    
    return '\n'.join(html_lines)


def escape_applescript(text: str) -> str:
    """Escape text for use in AppleScript strings."""
    # Replace backslashes first, then quotes
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    return text


def create_note(title: str, content: str, folder: str = "Notes", convert_md: bool = True) -> str:
    """Create a new Apple Note with the given title and content."""
    if convert_md:
        html_content = markdown_to_html(content)
    else:
        html_content = content
    
    # Escape for AppleScript
    escaped_title = escape_applescript(title)
    escaped_content = escape_applescript(html_content)
    escaped_folder = escape_applescript(folder)
    
    script = f'''
tell application "Notes"
    tell account "iCloud"
        make new note at folder "{escaped_folder}" with properties {{name:"{escaped_title}", body:"{escaped_content}"}}
    end tell
end tell
'''
    
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to create note: {result.stderr}")
    
    return result.stdout.strip()


def search_notes(query: str, search_body: bool = False) -> list[dict]:
    """Search Apple Notes by title (and optionally body)."""
    escaped_query = escape_applescript(query)
    
    if search_body:
        script = f'''
tell application "Notes"
    tell account "iCloud"
        set matchingNotes to notes whose plaintext contains "{escaped_query}"
        set results to {{}}
        repeat with n in matchingNotes
            set end of results to {{title:name of n, id:id of n}}
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
    
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to search notes: {result.stderr}")
    
    # Parse the output
    output = result.stdout.strip()
    if not output:
        return []
    
    # AppleScript returns comma-separated list
    titles = [t.strip() for t in output.split(', ') if t.strip()]
    return titles


def read_note(title: str) -> str:
    """Read the content of a note by title."""
    escaped_title = escape_applescript(title)
    
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
    
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to read note: {result.stderr}")
    
    return result.stdout


def list_notes(limit: int = 10) -> list[str]:
    """List recent notes."""
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
    
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to list notes: {result.stderr}")
    
    output = result.stdout.strip()
    if not output:
        return []
    
    return [t.strip() for t in output.split(', ') if t.strip()]


def delete_note(title: str) -> bool:
    """Delete a note by title."""
    escaped_title = escape_applescript(title)
    
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
    
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to delete note: {result.stderr}")
    
    return 'true' in result.stdout.lower()


def main():
    parser = argparse.ArgumentParser(
        description='Apple Notes Tool - Create, read, and search Apple Notes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new note')
    create_parser.add_argument('title', help='Note title')
    create_parser.add_argument('content', nargs='?', help='Note content (Markdown supported)')
    create_parser.add_argument('--file', '-f', help='Read content from file')
    create_parser.add_argument('--stdin', action='store_true', help='Read content from stdin')
    create_parser.add_argument('--folder', default='Notes', help='Target folder (default: Notes)')
    create_parser.add_argument('--html', action='store_true', help='Content is already HTML, skip conversion')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search notes by title')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--body', action='store_true', help='Also search note body')
    
    # Read command
    read_parser = subparsers.add_parser('read', help='Read a note by title')
    read_parser.add_argument('title', help='Note title (partial match)')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List recent notes')
    list_parser.add_argument('--limit', '-n', type=int, default=10, help='Number of notes to list')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a note by title')
    delete_parser.add_argument('title', help='Exact note title')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'create':
            if args.stdin:
                content = sys.stdin.read()
            elif args.file:
                content = Path(args.file).read_text()
            elif args.content:
                content = args.content
            else:
                print("Error: Must provide content, --file, or --stdin", file=sys.stderr)
                sys.exit(1)
            
            result = create_note(
                args.title, 
                content, 
                folder=args.folder,
                convert_md=not args.html
            )
            print(f"✓ Created note: {args.title}")
            print(f"  ID: {result}")
        
        elif args.command == 'search':
            results = search_notes(args.query, search_body=args.body)
            if results:
                print(f"Found {len(results)} note(s):")
                for title in results:
                    print(f"  • {title}")
            else:
                print("No notes found.")
        
        elif args.command == 'read':
            content = read_note(args.title)
            if content:
                print(content)
            else:
                print(f"Note not found: {args.title}", file=sys.stderr)
                sys.exit(1)
        
        elif args.command == 'list':
            notes = list_notes(args.limit)
            if notes:
                print(f"Recent notes ({len(notes)}):")
                for title in notes:
                    print(f"  • {title}")
            else:
                print("No notes found.")
        
        elif args.command == 'delete':
            if delete_note(args.title):
                print(f"✓ Deleted note: {args.title}")
            else:
                print(f"Note not found: {args.title}", file=sys.stderr)
                sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
