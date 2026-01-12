#!/usr/bin/env python3
"""
Re-extract specific missing pages from a PDF and insert into existing extraction.

Usage:
    uv run python scripts/chanoyu/reextract_pages.py \
        ~/Media/chanoyu-sources/jikunyu-raku/tousetsu_2006-08.pdf \
        ~/switchboard/chanoyu/sources/jikunyu-raku/tousetsu_2006-08 \
        --pages 11 12 13 14 15 17

Author: Claude (Amplifier)
Date: 2026-01-10
"""

import argparse
import asyncio
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


async def extract_single_page(
    pdf_path: Path,
    page_num: int,
    output_dir: Path,
    dpi: int = 200,
) -> tuple[int, str]:
    """Extract a single page using Gemini 3 Flash."""
    # Import here to avoid circular imports
    from scripts.chanoyu.extract_gemini import GeminiExtractor, MULTI_COLUMN_PROMPT

    # Create temp directory for this page
    temp_dir = output_dir / f"_temp_page_{page_num}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Convert just this page to image
    image_path = temp_dir / f"page-{page_num}.png"

    cmd = [
        "pdftoppm",
        "-png",
        "-r",
        str(dpi),
        "-f",
        str(page_num),
        "-l",
        str(page_num),
        str(pdf_path),
        str(temp_dir / "page"),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pdftoppm failed: {result.stderr}")

    # Find generated image (pdftoppm adds page number suffix)
    images = list(temp_dir.glob("page-*.png"))
    if not images:
        raise RuntimeError(f"No image generated for page {page_num}")

    image_path = images[0]

    # Extract with Gemini
    extractor = GeminiExtractor()

    if not extractor.check_availability():
        raise RuntimeError("Gemini API not available")

    result = await extractor.extractor.extract_from_file(
        image_path,
        MULTI_COLUMN_PROMPT,
        model=extractor.MODEL,
    )

    # Clean up temp directory
    for f in temp_dir.iterdir():
        f.unlink()
    temp_dir.rmdir()

    return page_num, result


def rebuild_fulltext(output_dir: Path, pdf_stem: str) -> None:
    """Rebuild _full-text.md from individual page files."""
    # Find all page files
    page_pattern = re.compile(r"_page_(\d{4})\.md")
    page_files = []

    for f in output_dir.iterdir():
        match = page_pattern.match(f.name)
        if match:
            page_num = int(match.group(1))
            page_files.append((page_num, f))

    # Sort by page number
    page_files.sort(key=lambda x: x[0])

    if not page_files:
        logger.warning("No page files found")
        return

    logger.info(f"Rebuilding _full-text.md from {len(page_files)} page files")

    # Build content
    frontmatter = f"""---
title: "{pdf_stem}"
source: "{pdf_stem}.pdf"
category: source
type: full-text-extraction
extraction_method: gemini-3-flash
pages: {len(page_files)}
---

# {pdf_stem}

Full text extraction from Japanese PDF using Gemini 3 Flash.

---

"""

    content_parts = [frontmatter]

    for page_num, page_file in page_files:
        page_content = page_file.read_text(encoding="utf-8")
        content_parts.append(page_content)
        content_parts.append("\n\n")

    fulltext_path = output_dir / "_full-text.md"
    fulltext_path.write_text("".join(content_parts), encoding="utf-8")
    logger.info(f"Rebuilt: {fulltext_path}")


async def main_async(args: argparse.Namespace) -> None:
    """Async main function."""
    pdf_path = Path(args.pdf_path).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    pages = args.pages

    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        sys.exit(1)

    if not output_dir.exists():
        logger.error(f"Output directory not found: {output_dir}")
        sys.exit(1)

    logger.info(f"PDF: {pdf_path.name}")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Pages to extract: {pages}")

    # Extract each page
    for page_num in pages:
        logger.info(f"Extracting page {page_num}...")

        try:
            _, text = await extract_single_page(pdf_path, page_num, output_dir, args.dpi)

            # Save page file
            page_file = output_dir / f"_page_{page_num:04d}.md"
            page_content = f"<!-- PAGE: {page_num} (Gemini 3 Flash - re-extracted) -->\n\n{text}"
            page_file.write_text(page_content, encoding="utf-8")

            logger.info(f"  Saved: {page_file.name} ({len(text)} chars)")

        except Exception as e:
            logger.error(f"  Failed to extract page {page_num}: {e}")
            continue

    # Rebuild full-text
    rebuild_fulltext(output_dir, pdf_path.stem)
    logger.info("Done!")


def main():
    parser = argparse.ArgumentParser(
        description="Re-extract specific pages from PDF and rebuild full-text",
    )
    parser.add_argument("pdf_path", type=str, help="Path to source PDF")
    parser.add_argument("output_dir", type=str, help="Existing output directory")
    parser.add_argument(
        "--pages",
        type=int,
        nargs="+",
        required=True,
        help="Page numbers to re-extract",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Image resolution (default: 200)",
    )

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
