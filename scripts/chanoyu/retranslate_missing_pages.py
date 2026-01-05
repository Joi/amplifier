#!/usr/bin/env python3
"""
Targeted re-translation script for missing pages in chanoyu extractions.

This script extracts specific page ranges from Japanese source files and
re-translates them using Gemini, then merges them into the English translation.

Usage:
    python retranslate_missing_pages.py <source_dir> --pages 12-21
"""

import argparse
import re
import sys
from pathlib import Path

import google.generativeai as genai


def extract_page_range(japanese_text: str, start_page: int, end_page: int) -> str:
    """Extract a range of pages from Japanese source text."""
    lines = japanese_text.split("\n")
    result_lines = []
    in_range = False

    page_pattern = re.compile(r"<!--\s*PAGE:\s*(\d+)\s*-->")

    for line in lines:
        match = page_pattern.search(line)
        if match:
            page_num = int(match.group(1))
            if page_num >= start_page and page_num <= end_page:
                in_range = True
            elif page_num > end_page:
                in_range = False
                break

        if in_range:
            result_lines.append(line)

    return "\n".join(result_lines)


def translate_with_gemini(japanese_text: str, model_name: str = "gemini-2.5-flash") -> str:
    """Translate Japanese text to English using Gemini."""
    model = genai.GenerativeModel(model_name)

    prompt = f"""You are translating a Japanese book about tea ceremony ceramics (茶陶).

CRITICAL INSTRUCTIONS:
1. Translate ALL content - do not skip or summarize any pages
2. Preserve ALL page markers exactly as they appear: <!-- PAGE: X -->
3. Preserve figure references as: [Figure X.Y: description]
4. For Japanese terms, use format: **English term** (日本語 / romanization)
5. Preserve furigana readings in parentheses after the term
6. Maintain paragraph structure and formatting

IMPORTANT: This is a re-translation of pages that were previously missing.
Translate completely and accurately.

Japanese text to translate:

{japanese_text}

Provide the complete English translation:"""

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=32000,
        ),
    )

    return response.text


def find_insertion_point(english_text: str, start_page: int) -> int:
    """Find where to insert the re-translated pages."""
    lines = english_text.split("\n")
    page_pattern = re.compile(r"<!--\s*PAGE:\s*(\d+)\s*-->")

    for i, line in enumerate(lines):
        match = page_pattern.search(line)
        if match:
            page_num = int(match.group(1))
            if page_num == start_page:
                return i

    return -1


def merge_translations(english_text: str, new_translation: str, start_page: int, end_page: int) -> str:
    """Merge new translation into existing English text, replacing incomplete pages."""
    lines = english_text.split("\n")
    page_pattern = re.compile(r"<!--\s*PAGE:\s*(\d+)\s*-->")

    # Find start and end indices to replace
    start_idx = -1
    end_idx = -1

    for i, line in enumerate(lines):
        match = page_pattern.search(line)
        if match:
            page_num = int(match.group(1))
            if page_num == start_page and start_idx == -1:
                start_idx = i
            elif page_num == end_page + 1:
                end_idx = i
                break

    if start_idx == -1:
        print(f"Warning: Could not find PAGE: {start_page} marker")
        return english_text

    if end_idx == -1:
        # Find next page after end_page
        for i, line in enumerate(lines[start_idx:], start=start_idx):
            match = page_pattern.search(line)
            if match:
                page_num = int(match.group(1))
                if page_num > end_page:
                    end_idx = i
                    break

    if end_idx == -1:
        end_idx = len(lines)

    # Merge
    result_lines = lines[:start_idx] + [new_translation] + lines[end_idx:]
    return "\n".join(result_lines)


def main():
    parser = argparse.ArgumentParser(description="Re-translate missing pages from Japanese source")
    parser.add_argument("source_dir", type=Path, help="Source directory with _full-text.md files")
    parser.add_argument("--pages", required=True, help="Page range to translate (e.g., 12-21)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without translating")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model to use")

    args = parser.parse_args()

    # Parse page range
    start_page, end_page = map(int, args.pages.split("-"))

    # Find source files
    japanese_file = args.source_dir / "_full-text.md"
    english_file = args.source_dir / "_full-text-english.md"

    if not japanese_file.exists():
        print(f"Error: Japanese source not found: {japanese_file}")
        sys.exit(1)

    if not english_file.exists():
        print(f"Error: English translation not found: {english_file}")
        sys.exit(1)

    print(f"Source directory: {args.source_dir}")
    print(f"Extracting pages {start_page}-{end_page} from Japanese source...")

    japanese_text = japanese_file.read_text(encoding="utf-8")
    extracted = extract_page_range(japanese_text, start_page, end_page)

    if not extracted.strip():
        print(f"Error: No content found for pages {start_page}-{end_page}")
        sys.exit(1)

    # Count pages found
    page_markers = re.findall(r"<!--\s*PAGE:\s*\d+\s*-->", extracted)
    print(f"Found {len(page_markers)} page markers in extracted content")

    if args.dry_run:
        print("\n--- DRY RUN: Would translate this content ---")
        print(extracted[:500] + "..." if len(extracted) > 500 else extracted)
        return

    print(f"\nTranslating with {args.model}...")
    translated = translate_with_gemini(extracted, args.model)

    print("Merging into English translation...")
    english_text = english_file.read_text(encoding="utf-8")
    merged = merge_translations(english_text, translated, start_page, end_page)

    # Backup original
    backup_file = english_file.with_suffix(".md.bak")
    english_file.rename(backup_file)
    print(f"Backed up original to: {backup_file}")

    # Write merged
    english_file.write_text(merged, encoding="utf-8")
    print(f"Updated: {english_file}")

    # Verify
    new_content = english_file.read_text(encoding="utf-8")
    new_markers = re.findall(r"<!--\s*PAGE:\s*(\d+)\s*-->", new_content)
    print(f"\nVerification: Found {len(new_markers)} page markers in updated file")


if __name__ == "__main__":
    main()
