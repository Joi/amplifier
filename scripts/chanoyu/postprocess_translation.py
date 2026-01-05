#!/usr/bin/env python3
"""
Post-processing cleanup script for chanoyu translation files.

Fixes common issues in Gemini-generated translations:
1. Incorrect romanization of Japanese terms
2. Orphaned furigana annotations
3. Page boundary cleanup
4. Consistent formatting

Usage:
    python postprocess_translation.py <english_file> [--dry-run]
"""

import argparse
import re
from pathlib import Path

# Known romanization corrections based on partner feedback
# Format: (incorrect, correct, context_hint)
ROMANIZATION_FIXES = [
    # From partner feedback on chatou_to_sono_kyoshou_1977
    ("munagawara", "munegawara", "棟瓦"),
    ("kuzushiguro", "tokegusuri", "解ぐすり"),  # Note: partner said tokegururi but likely tokegusuri
    ("(shō)", "(me)", "賞"),  # Context: when 賞 is read as め
    ("(waku)", "(segare)", "枠"),  # Context: when 枠 refers to child/heir
    ("yakunuki", "yakinuki", "焼貫"),
    ("tenma-jō", "Denba-jō", "伝馬状"),
    ("Motozumi", "Genpaku", "元住→元伯"),
    # Common tea ceremony romanization patterns
    ("uwagusuri", "yūyaku", None),  # 釉薬 - keep both as variants
    ("Rakujawan", "Raku chawan", None),  # Normalize to spaced version
    # Add more corrections as discovered
]


def fix_romanization(text: str, dry_run: bool = False) -> tuple[str, list[str]]:
    """Apply romanization corrections to text."""
    changes = []

    for incorrect, correct, context in ROMANIZATION_FIXES:
        if context:
            # Context-aware replacement
            pattern = re.compile(rf"({re.escape(context)}[^)]*?\()" + re.escape(incorrect) + r"(\))", re.IGNORECASE)
            if pattern.search(text):
                if not dry_run:
                    text = pattern.sub(rf"\1{correct}\2", text)
                changes.append(f"Fixed: {incorrect} → {correct} (near {context})")
        else:
            # Simple replacement
            if incorrect in text:
                if not dry_run:
                    text = text.replace(incorrect, correct)
                changes.append(f"Fixed: {incorrect} → {correct}")

    return text, changes


def clean_orphaned_furigana(text: str, dry_run: bool = False) -> tuple[str, list[str]]:
    """
    Clean up orphaned furigana annotations.

    Orphaned furigana appear as standalone lines like:
    おおかめだに (Ōkametani)
    さんさい (sansai)

    These should either be merged with the preceding term or removed if duplicate.
    """
    changes = []
    lines = text.split("\n")
    result_lines = []
    skip_next = False

    # Pattern for standalone furigana line: hiragana followed by (romanization)
    furigana_pattern = re.compile(r"^([ぁ-んー]+)\s*\(([A-Za-z\-]+)\)\s*$")

    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        match = furigana_pattern.match(line.strip())
        if match:
            hiragana = match.group(1)
            romanization = match.group(2)

            # Check if this romanization already appears nearby
            context_start = max(0, i - 5)
            context = "\n".join(lines[context_start:i])

            if romanization in context or romanization.lower() in context.lower():
                # Already present, skip this orphaned line
                changes.append(f"Removed duplicate furigana: {hiragana} ({romanization})")
                continue
            # Keep but mark for review
            changes.append(f"Kept orphaned furigana (review): {hiragana} ({romanization})")

        result_lines.append(line)

    if not dry_run:
        text = "\n".join(result_lines)

    return text, changes


def fix_page_boundaries(text: str, dry_run: bool = False) -> tuple[str, list[str]]:
    """
    Fix issues at page boundaries.

    Common issues:
    - Sentences cut off mid-word
    - Incomplete section headers
    """
    changes = []

    # Pattern for incomplete lines before page markers
    # This is a heuristic - lines ending with particles/incomplete words
    incomplete_patterns = [
        (r"([ぁ-んァ-ン一-龯]+)\n(<!--\s*PAGE:\s*\d+\s*-->)", r"\1\n\n\2"),
    ]

    for pattern, replacement in incomplete_patterns:
        matches = re.findall(pattern, text)
        if matches and not dry_run:
            text = re.sub(pattern, replacement, text)
            changes.append(f"Fixed {len(matches)} page boundary issues")

    return text, changes


def validate_page_sequence(text: str) -> list[str]:
    """Check for missing or out-of-order pages."""
    issues = []
    page_pattern = re.compile(r"<!--\s*PAGE:\s*(\d+)\s*-->")
    pages = [int(m.group(1)) for m in page_pattern.finditer(text)]

    if not pages:
        issues.append("No page markers found")
        return issues

    # Check for gaps
    for i in range(1, len(pages)):
        expected = pages[i - 1] + 1
        if pages[i] != expected and pages[i] != pages[i - 1]:
            gap_start = pages[i - 1] + 1
            gap_end = pages[i] - 1
            if gap_start == gap_end:
                issues.append(f"Missing page: {gap_start}")
            else:
                issues.append(f"Missing pages: {gap_start}-{gap_end}")

    # Check for duplicates
    seen = set()
    for p in pages:
        if p in seen:
            issues.append(f"Duplicate page marker: {p}")
        seen.add(p)

    return issues


def format_term_annotations(text: str, dry_run: bool = False) -> tuple[str, list[str]]:
    """
    Standardize term annotation format.

    Target format: **English term** (日本語 / romanization)
    """
    changes = []

    # Pattern to fix: term (日本語/romanization) without space
    pattern = r"\*\*([^*]+)\*\*\s*\(([一-龯ぁ-んァ-ン]+)/([A-Za-z\-]+)\)"
    replacement = r"**\1** (\2 / \3)"

    matches = re.findall(pattern, text)
    if matches and not dry_run:
        text = re.sub(pattern, replacement, text)
        changes.append(f"Standardized {len(matches)} term annotations")

    return text, changes


def main():
    parser = argparse.ArgumentParser(description="Post-process chanoyu translation files")
    parser.add_argument("file", type=Path, help="English translation file to process")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--validate-only", action="store_true", help="Only validate, don't fix")

    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        return 1

    text = args.file.read_text(encoding="utf-8")
    all_changes = []

    print(f"Processing: {args.file}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'APPLYING CHANGES'}")
    print("-" * 60)

    # Validation
    print("\n1. Validating page sequence...")
    issues = validate_page_sequence(text)
    if issues:
        print("   Issues found:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("   ✓ Page sequence OK")

    if args.validate_only:
        return 0 if not issues else 1

    # Apply fixes
    print("\n2. Fixing romanization...")
    text, changes = fix_romanization(text, args.dry_run)
    all_changes.extend(changes)
    for c in changes:
        print(f"   {c}")
    if not changes:
        print("   No romanization fixes needed")

    print("\n3. Cleaning orphaned furigana...")
    text, changes = clean_orphaned_furigana(text, args.dry_run)
    all_changes.extend(changes)
    for c in changes:
        print(f"   {c}")
    if not changes:
        print("   No orphaned furigana found")

    print("\n4. Fixing page boundaries...")
    text, changes = fix_page_boundaries(text, args.dry_run)
    all_changes.extend(changes)
    for c in changes:
        print(f"   {c}")
    if not changes:
        print("   No page boundary fixes needed")

    print("\n5. Standardizing term annotations...")
    text, changes = format_term_annotations(text, args.dry_run)
    all_changes.extend(changes)
    for c in changes:
        print(f"   {c}")
    if not changes:
        print("   No annotation fixes needed")

    # Summary
    print("\n" + "=" * 60)
    print(f"Total changes: {len(all_changes)}")

    if not args.dry_run and all_changes:
        # Backup and write
        backup = args.file.with_suffix(".md.bak")
        if not backup.exists():  # Don't overwrite existing backup
            args.file.rename(backup)
            print(f"Backed up to: {backup}")

        args.file.write_text(text, encoding="utf-8")
        print(f"Updated: {args.file}")

    return 0


if __name__ == "__main__":
    exit(main())
