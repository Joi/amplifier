#!/usr/bin/env python3
"""
Batch Re-extraction Script using YomiToku.

Re-extracts all Japanese PDFs in the chanoyu collection using YomiToku
for improved vertical text handling.

This script:
1. Scans PDF source directories for all PDFs
2. Maps each PDF to its output directory in the chanoyu vault
3. Runs YomiToku extraction
4. Preserves existing Gemini extractions for comparison

Usage:
    uv run python scripts/chanoyu/batch_reextract_yomitoku.py --dry-run
    uv run python scripts/chanoyu/batch_reextract_yomitoku.py

Author: Claude (Amplifier)
Date: 2026-01-03
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)

# Import the YomiToku extractor
from scripts.chanoyu.extract_yomitoku import ReadingOrder
from scripts.chanoyu.extract_yomitoku import YomiTokuExtractor


@dataclass
class PDFSource:
    """Represents a PDF source file and its extraction destination."""

    pdf_path: Path
    output_dir: Path
    collection: str  # e.g., "jikunyu-raku"
    name: str  # e.g., "geinoushi_kenkyuu_1991-01"
    already_extracted: bool = False


# Configuration
PDF_SOURCE_DIRS = [
    Path.home() / "Media" / "chanoyu-sources" / "jikunyu-raku",
    Path.home() / "Media" / "chanoyu-sources",
]

# Note: ~/raku Sources contains duplicates of jikunyu-raku, skip it
SKIP_DIRS = [
    Path.home() / "raku Sources",  # Duplicates
]

# English PDFs to skip - YomiToku is optimized for Japanese vertical text
SKIP_ENGLISH_PDFS = [
    "dokumen.pub_handmade-culture-raku-potters-patrons-and-tea-practitioners-in-japan.pdf",
]

VAULT_BASE = Path.home() / "switchboard" / "chanoyu" / "sources"


def slugify(name: str) -> str:
    """Convert filename to slug for directory name."""
    # Remove extension
    name = Path(name).stem

    # Replace common patterns
    name = re.sub(r"[（(].*?[）)]", "", name)  # Remove parenthetical
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^\w_-]", "", name)
    name = name.lower()

    return name


def find_output_dir(pdf_path: Path) -> tuple[Path, str]:
    """Find or create the output directory for a PDF.

    Returns (output_dir, collection_name)
    """
    filename = pdf_path.stem

    # Check if this PDF is in jikunyu-raku collection
    if "jikunyu-raku" in str(pdf_path.parent):
        collection = "jikunyu-raku"
        slug = slugify(filename)
        output_dir = VAULT_BASE / collection / slug
    else:
        # Other sources go in root
        collection = "misc"
        slug = slugify(filename)
        output_dir = VAULT_BASE / slug

    return output_dir, collection


def scan_pdf_sources() -> list[PDFSource]:
    """Scan source directories for PDFs."""
    sources: list[PDFSource] = []
    seen_names: set[str] = set()

    for source_dir in PDF_SOURCE_DIRS:
        if not source_dir.exists():
            logger.warning(f"Source directory not found: {source_dir}")
            continue

        # Find all PDFs recursively
        for pdf_path in source_dir.rglob("*.pdf"):
            # Skip if in a skip directory
            if any(skip in pdf_path.parents for skip in SKIP_DIRS):
                continue

            # Skip English PDFs (YomiToku is for Japanese)
            if pdf_path.name in SKIP_ENGLISH_PDFS:
                logger.info(f"Skipping English PDF: {pdf_path.name}")
                continue

            # Find output directory
            output_dir, collection = find_output_dir(pdf_path)
            name = output_dir.name

            # Skip duplicates
            key = f"{collection}/{name}"
            if key in seen_names:
                logger.info(f"Skipping duplicate: {pdf_path.name}")
                continue
            seen_names.add(key)

            # Check if already extracted with YomiToku
            yomitoku_dir = output_dir / "yomitoku"
            already_extracted = yomitoku_dir.exists() and any(yomitoku_dir.glob("*.md"))

            sources.append(
                PDFSource(
                    pdf_path=pdf_path,
                    output_dir=output_dir,
                    collection=collection,
                    name=name,
                    already_extracted=already_extracted,
                )
            )

    return sources


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch re-extract Japanese PDFs using YomiToku",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be extracted without doing it",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-extract even if YomiToku output exists",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of PDFs to process",
    )
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help="Only process PDFs matching this pattern",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    # Scan for PDFs
    logger.info("Scanning for PDF sources...")
    sources = scan_pdf_sources()

    # Filter if requested
    if args.filter:
        sources = [s for s in sources if args.filter.lower() in s.name.lower()]

    # Sort by name
    sources.sort(key=lambda s: s.name)

    # Show summary
    total = len(sources)
    already = sum(1 for s in sources if s.already_extracted)
    to_extract = [s for s in sources if not s.already_extracted or args.force]

    logger.info("\nPDF Sources Summary:")
    logger.info(f"  Total PDFs found: {total}")
    logger.info(f"  Already extracted: {already}")
    logger.info(f"  To extract: {len(to_extract)}")

    if args.limit:
        to_extract = to_extract[: args.limit]
        logger.info(f"  Limited to: {args.limit}")

    # Show what will be extracted
    print("\n" + "=" * 60)
    print("PDFs to extract:")
    print("=" * 60)

    for i, source in enumerate(to_extract, 1):
        status = "⚡ FORCE" if source.already_extracted else "📄 NEW"
        print(f"{i:3d}. [{status}] {source.name}")
        print(f"     Source: {source.pdf_path.name}")
        print(f"     Output: {source.output_dir}")

    if args.dry_run:
        print("\n[DRY RUN] No extractions performed")
        return

    if not to_extract:
        print("\n✅ All PDFs already extracted!")
        return

    # Confirm
    print(f"\nReady to extract {len(to_extract)} PDFs")
    if not args.yes:
        response = input("Proceed? [y/N] ").strip().lower()
        if response != "y":
            print("Aborted")
            return

    # Run extractions
    extractor = YomiTokuExtractor()

    if not extractor.check_availability():
        logger.error("YomiToku not available")
        sys.exit(1)

    success = 0
    failed = 0

    for i, source in enumerate(to_extract, 1):
        print(f"\n[{i}/{len(to_extract)}] Extracting: {source.name}")

        try:
            fulltext_path = extractor.extract_pdf(
                source.pdf_path,
                source.output_dir,
                reading_order=ReadingOrder.JAPANESE_BOOK_SPREAD,
            )
            print(f"  ✅ Complete: {fulltext_path}")
            success += 1

        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            logger.error(f"Failed to extract {source.name}: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("Extraction Complete")
    print("=" * 60)
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")
    print(f"  Total: {success + failed}")


if __name__ == "__main__":
    main()
