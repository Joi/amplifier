#!/usr/bin/env python3
"""
Clean up the English translation of the chanoyu letter book.

Fixes:
- Remove stray code fences
- Convert page markers to proper section headers
- Remove excessive --- dividers
- Standardize term formatting
- Improve overall readability
"""

import re
from pathlib import Path

INPUT_FILE = Path.home() / "switchboard/chanoyu/sources/chanoyunotegamibureishu/_full-text-english.md"
OUTPUT_FILE = INPUT_FILE  # Overwrite

def clean_translation(content: str) -> str:
    """Apply all cleanup transformations."""

    # 1. Remove stray code fences (``` that appear alone)
    content = re.sub(r'^```\s*$', '', content, flags=re.MULTILINE)

    # 2. Convert page markers to proper headers
    # <!-- PAGE: n --> becomes ---\n## Page n\n
    def format_page(match):
        page_num = match.group(1)
        return f"\n---\n\n## Page {page_num}\n"

    content = re.sub(r'<!-- PAGE: (\d+) -->', format_page, content)

    # 3. Remove excessive standalone --- dividers (keep only between sections)
    # Multiple --- in a row -> single ---
    content = re.sub(r'(---\s*\n){2,}', '---\n\n', content)

    # Remove --- that appear alone between paragraphs (not as section breaks)
    # Keep --- only when they separate major sections
    lines = content.split('\n')
    cleaned_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip standalone --- unless it's before a header or after page marker
        if line.strip() == '---':
            # Check if next non-empty line is a header or we just had a page marker
            next_content_idx = i + 1
            while next_content_idx < len(lines) and not lines[next_content_idx].strip():
                next_content_idx += 1

            if next_content_idx < len(lines):
                next_line = lines[next_content_idx].strip()
                # Keep --- if it's before a header (## or #) or after Page header
                if next_line.startswith('#') or (cleaned_lines and cleaned_lines[-1].strip().startswith('## Page')):
                    cleaned_lines.append(line)
            # Otherwise skip the ---
        else:
            cleaned_lines.append(line)
        i += 1

    content = '\n'.join(cleaned_lines)

    # 4. Standardize term formatting: **term** (kanji / romaji) - remove italics from romaji
    content = re.sub(r'\*([a-zA-Zōūāīēô\-]+)\*', r'\1', content)

    # 5. Clean up redundant term annotations
    # Remove duplicate term definitions like "**Tea Gathering** (茶事 / chaji) / **Tea Party** (茶会 / chakai)"
    # appearing multiple times in the same paragraph - keep first occurrence per paragraph

    # 6. Remove redundant parenthetical translations that repeat the English
    # e.g., "(Invitation) / **Pre-greeting** (前礼 / Zenrei - Pre-greeting)" -> simpler
    content = re.sub(r'\s*-\s*[A-Z][a-zA-Z\s]+\)', ')', content)

    # 7. Clean up "(Blank Page)" entries
    content = re.sub(r'\(Blank Page\)', '*[Blank page in original]*', content)

    # 8. Fix table of contents - remove duplicate entries (pages 4-7 have same TOC)
    # We'll keep only the first occurrence of the full TOC

    # 9. Standardize bullet points
    content = re.sub(r'^-\s+', '- ', content, flags=re.MULTILINE)

    # 10. Clean up multiple blank lines
    content = re.sub(r'\n{4,}', '\n\n\n', content)

    # 11. Clean up escaped asterisks
    content = content.replace(r'\*', '*')

    # 12. Simplify overly verbose term definitions
    # "**Term** (漢字 / Romaji Description - Term)" -> "**Term** (漢字 / romaji)"
    def simplify_term(match):
        full = match.group(0)
        # If it has redundant " - Something" at the end, remove it
        simplified = re.sub(r'\s*-\s*[A-Z][^)]*\)', ')', full)
        return simplified

    content = re.sub(r'\*\*[^*]+\*\*\s*\([^)]+\)', simplify_term, content)

    return content


def add_improved_frontmatter(content: str) -> str:
    """Replace frontmatter with improved version."""
    # Remove existing frontmatter (proper YAML block between --- delimiters)
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL, count=1)
    # Remove any stray frontmatter lines that might appear without proper delimiters
    # These can appear when the original frontmatter wasn't properly delimited
    stray_frontmatter_pattern = r'^(title:|title_japanese:|category:|type:|source_language:|target_language:|translation_method:|total_pages:|note:).*\n'
    while re.match(stray_frontmatter_pattern, content):
        content = re.sub(stray_frontmatter_pattern, '', content, count=1)

    new_frontmatter = """---
title: "Definitive Edition: Tea Ceremony Letter Examples Collection"
title_japanese: "決定版 茶の湯の手紙文例集"
category: source
type: full-text-translation
source_language: Japanese
target_language: English
translation_method: gemini-2.0-flash
total_pages: 169
formatting: cleaned
note: >
  Key tea ceremony terms preserved in format: **English** (漢字 / romaji).
  Page numbers correspond to the original Japanese book.
---

# Tea Ceremony Letter Examples Collection
## 決定版 茶の湯の手紙文例集

*Definitive Edition: From Invitations to Tea Gathering Records*

"""
    return new_frontmatter + content.lstrip()


def main():
    print("Cleaning up translation...")

    content = INPUT_FILE.read_text(encoding='utf-8')
    original_lines = len(content.splitlines())

    # Apply cleanups
    content = clean_translation(content)
    content = add_improved_frontmatter(content)

    # Write output
    OUTPUT_FILE.write_text(content, encoding='utf-8')

    new_lines = len(content.splitlines())
    print(f"Original: {original_lines} lines")
    print(f"Cleaned:  {new_lines} lines")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
