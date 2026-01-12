#!/usr/bin/env python3
"""Fix alphabetical page ordering in chanoyu extraction files.

The issue: Pages were sorted alphabetically (1, 10, 11, 12... 2, 20, 21... 3)
instead of numerically (1, 2, 3... 10, 11, 12... 20, 21).

Usage:
    python fix_page_order.py <file_path>
"""

import re
import sys
from pathlib import Path


def fix_page_order(file_path: Path) -> None:
    """Fix page ordering in a _full-text.md file."""
    content = file_path.read_text(encoding="utf-8")

    # Split by page markers, keeping the markers
    # Pattern: <!-- PAGE: N --> where N is the page number
    page_pattern = r"(<!-- PAGE: (\d+) -->)"

    # Find all page markers and their positions
    matches = list(re.finditer(page_pattern, content))

    if not matches:
        print(f"No page markers found in {file_path}")
        return

    # Extract header (content before first page marker)
    header = content[: matches[0].start()]

    # Extract each page section (from one marker to the next)
    pages: list[tuple[int, str]] = []
    for i, match in enumerate(matches):
        page_num = int(match.group(2))
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        page_content = content[start:end]
        pages.append((page_num, page_content))

    # Check if already in correct order
    page_nums = [p[0] for p in pages]
    sorted_nums = sorted(page_nums)

    if page_nums == sorted_nums:
        print(f"✓ {file_path.name}: Pages already in correct order")
        return

    # Show the order issue
    print(f"✗ {file_path.name}: Fixing page order")
    print(f"  Before: {page_nums[:10]}{'...' if len(page_nums) > 10 else ''}")
    print(f"  After:  {sorted_nums[:10]}{'...' if len(sorted_nums) > 10 else ''}")

    # Sort pages numerically
    pages_sorted = sorted(pages, key=lambda p: p[0])

    # Reconstruct the file
    new_content = header + "".join(p[1] for p in pages_sorted)

    # Backup original
    backup_path = file_path.with_suffix(".md.bak")
    file_path.rename(backup_path)
    print(f"  Backup: {backup_path.name}")

    # Write fixed content
    file_path.write_text(new_content, encoding="utf-8")
    print(f"  Fixed:  {file_path.name}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python fix_page_order.py <file_path>")
        print("       python fix_page_order.py --all  # Fix all known problem files")
        sys.exit(1)

    if sys.argv[1] == "--all":
        # Fix all known problem files
        base = Path.home() / "switchboard/chanoyu/sources/jikunyu-raku"
        problem_files = [
            base / "sekai_touji_zenshuu_1955/_full-text.md",
            base / "tou_1993/_full-text.md",
        ]
        for file_path in problem_files:
            if file_path.exists():
                fix_page_order(file_path)
            else:
                print(f"Not found: {file_path}")
    else:
        file_path = Path(sys.argv[1])
        if not file_path.exists():
            print(f"File not found: {file_path}")
            sys.exit(1)
        fix_page_order(file_path)


if __name__ == "__main__":
    main()
