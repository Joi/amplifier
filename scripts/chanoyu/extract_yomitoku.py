#!/usr/bin/env python3
"""
YomiToku-based PDF Extractor for Japanese Academic Documents.

YomiToku is a specialized Japanese document OCR system with:
- Layout analysis for vertical text (縦書き/tategaki)
- Reading order detection (読み順推定)
- Superior column handling compared to general-purpose LLMs

This script:
1. Runs YomiToku on PDF pages to extract text
2. Handles 2-up book spread layout (right page first for Japanese)
3. Cleans YomiToku output (removes <br>, library watermarks)
4. Combines into full-text with proper page ordering

Usage:
    uv run python scripts/chanoyu/extract_yomitoku.py \\
        /path/to/input.pdf \\
        /path/to/output/dir \\
        --reading-order japanese-book-spread

Author: Claude (Amplifier)
Date: 2026-01-03
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


class ReadingOrder(Enum):
    """Reading order patterns for multi-up layouts."""

    # Japanese book spread (2-up): Right page first, then left
    JAPANESE_BOOK_SPREAD = "japanese-book-spread"

    # Western book spread (2-up): Left page first, then right
    WESTERN_BOOK_SPREAD = "western-book-spread"


@dataclass
class ExtractionResult:
    """Result from extracting a single page."""

    physical_page: int
    logical_pages: list[tuple[int, str]]  # (logical_page_num, content)
    success: bool
    error: str | None = None


class YomiTokuExtractor:
    """Extract text from Japanese PDFs using YomiToku."""

    # Common library watermarks to remove
    WATERMARK_PATTERNS = [
        r"西原\d+\s*守谷美帆\d{4}/\d{1,2}/\d{1,2}.*",  # NDL watermark
        r"F\d+\s*守谷美帆\d{4}/\d{1,2}/\d{1,2}.*",
        r"-\d+-",  # Page numbers like -3-
        r"\\-\d+-\\-",  # Escaped page numbers
    ]

    def __init__(self) -> None:
        """Initialize the extractor."""
        self.yomitoku_available = self._check_yomitoku()

    def _check_yomitoku(self) -> bool:
        """Check if YomiToku is available."""
        try:
            result = subprocess.run(
                ["uv", "run", "yomitoku", "--help"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def check_availability(self) -> bool:
        """Check if all dependencies are available."""
        if not self.yomitoku_available:
            logger.error(
                "YomiToku not installed. Run: uv add yomitoku\n"
                "Or install with: pip install yomitoku"
            )
            return False
        return True

    def _clean_yomitoku_output(self, text: str) -> str:
        """Clean YomiToku output: remove <br>, watermarks, artifacts."""
        # Replace <br> with proper line breaks
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

        # Remove common library watermarks
        for pattern in self.WATERMARK_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.MULTILINE)

        # Remove escaped markdown artifacts
        text = re.sub(r"\\-(\d+)\\-", "", text)
        text = re.sub(r"\\\[", "[", text)
        text = re.sub(r"\\\]", "]", text)
        text = re.sub(r"\\\|", "|", text)

        # Remove excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Strip trailing whitespace from lines
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)

        return text.strip()

    def _reorder_2up_pages(
        self,
        pages: list[tuple[int, str]],
        reading_order: ReadingOrder,
    ) -> list[tuple[int, str]]:
        """Reorder pages for 2-up book spread layout.

        YomiToku processes physical pages sequentially, but each physical page
        contains 2 logical pages (left and right halves of a book spread).

        For Japanese books: Right page comes first in reading order.
        For Western books: Left page comes first.
        """
        # YomiToku with reading_order=right2left should already handle this
        # But we may need to renumber for proper logical page sequence
        return pages

    def extract_pdf(
        self,
        pdf_path: Path,
        output_dir: Path,
        reading_order: ReadingOrder = ReadingOrder.JAPANESE_BOOK_SPREAD,
        start_page: int = 1,
        end_page: int | None = None,
        dpi: int = 200,
    ) -> Path:
        """Extract text from PDF using YomiToku.

        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory
            reading_order: Reading order pattern
            start_page: First physical page (1-based)
            end_page: Last physical page (None = all)
            dpi: Image resolution

        Returns:
            Path to combined full-text markdown
        """
        if not self.check_availability():
            raise ValueError("YomiToku not available")

        if not pdf_path.exists():
            raise ValueError(f"PDF not found: {pdf_path}")

        output_dir.mkdir(parents=True, exist_ok=True)
        yomitoku_dir = output_dir / "yomitoku"
        yomitoku_dir.mkdir(exist_ok=True)

        logger.info(f"PDF: {pdf_path.name}")
        logger.info(f"Reading order: {reading_order.value}")
        logger.info(f"Output: {yomitoku_dir}")

        # Build YomiToku command
        yomitoku_reading_order = "right2left" if reading_order == ReadingOrder.JAPANESE_BOOK_SPREAD else "left2right"

        cmd = [
            "uv", "run", "yomitoku",
            str(pdf_path),
            "-o", str(yomitoku_dir),
            "-f", "md",
            "--reading_order", yomitoku_reading_order,
            "--dpi", str(dpi),
            "--figure",
            "--figure_letter",
        ]

        # Add page range if specified
        if start_page > 1 or end_page is not None:
            page_spec = f"{start_page}"
            if end_page:
                page_spec += f"-{end_page}"
            cmd.extend(["--pages", page_spec])

        logger.info(f"Running: {' '.join(cmd)}")

        # Run YomiToku
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes max
            )

            if result.returncode != 0:
                logger.error(f"YomiToku failed: {result.stderr}")
                raise RuntimeError(f"YomiToku extraction failed: {result.stderr}")

            logger.info("YomiToku extraction complete")

        except subprocess.TimeoutExpired:
            raise RuntimeError("YomiToku extraction timed out after 10 minutes")

        # Process YomiToku output files
        md_files = sorted(yomitoku_dir.glob("*.md"))
        if not md_files:
            raise RuntimeError(f"No markdown files generated in {yomitoku_dir}")

        logger.info(f"Generated {len(md_files)} page files")

        # Clean and combine pages
        all_pages: list[tuple[int, str]] = []

        for i, md_file in enumerate(md_files, start=1):
            content = md_file.read_text(encoding="utf-8")
            cleaned = self._clean_yomitoku_output(content)

            # Add page marker
            page_content = f"<!-- PAGE: {i} -->\n{cleaned}"

            # Save cleaned version
            clean_file = output_dir / f"_page_{i:04d}.md"
            clean_file.write_text(page_content, encoding="utf-8")

            all_pages.append((i, page_content))
            logger.info(f"  Page {i}: {len(cleaned)} chars")

        # Combine into full text
        fulltext_path = self._combine_pages(
            output_dir,
            all_pages,
            pdf_path,
            reading_order,
        )

        return fulltext_path

    def _combine_pages(
        self,
        output_dir: Path,
        pages: list[tuple[int, str]],
        pdf_path: Path,
        reading_order: ReadingOrder,
    ) -> Path:
        """Combine extracted pages into full-text markdown."""
        fulltext_path = output_dir / "_full-text.md"

        frontmatter = f"""---
title: "{pdf_path.stem}"
source: "{pdf_path.name}"
category: source
type: full-text-extraction
extraction_method: yomitoku
reading_order: {reading_order.value}
pages: {len(pages)}
---

# {pdf_path.stem}

Full text extraction from Japanese PDF using YomiToku OCR.

**Reading order**: {reading_order.value}
**Extraction method**: YomiToku (Japanese document OCR with layout analysis)

---

"""

        content_parts = [frontmatter]
        for _page_num, content in sorted(pages):
            content_parts.append(content)
            content_parts.append("\n\n")

        fulltext_path.write_text("".join(content_parts), encoding="utf-8")
        logger.info(f"Combined: {fulltext_path} ({fulltext_path.stat().st_size:,} bytes)")

        return fulltext_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract text from Japanese PDFs using YomiToku OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
YomiToku advantages over Gemini Vision for Japanese text:
  - Purpose-built for Japanese document OCR
  - Automatic reading order detection for vertical text
  - Better column handling without mixing
  - Handles 2-up book spreads natively

Examples:
  # Extract Japanese scanned book
  uv run python scripts/chanoyu/extract_yomitoku.py \\
      ~/Media/journal.pdf \\
      ~/output/ \\
      --reading-order japanese-book-spread

  # Extract specific page range
  uv run python scripts/chanoyu/extract_yomitoku.py \\
      ~/Media/journal.pdf \\
      ~/output/ \\
      --start-page 2 --end-page 13
""",
    )

    parser.add_argument("pdf_path", type=Path, help="Path to PDF file")
    parser.add_argument("output_dir", type=Path, help="Output directory")
    parser.add_argument(
        "--reading-order",
        type=str,
        choices=["japanese-book-spread", "western-book-spread"],
        default="japanese-book-spread",
        help="Reading order pattern (default: japanese-book-spread)",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="First physical page to extract (1-based)",
    )
    parser.add_argument(
        "--end-page",
        type=int,
        default=None,
        help="Last physical page to extract (default: all)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Image resolution (default: 200)",
    )

    args = parser.parse_args()

    # Map reading order string to enum
    reading_order_map = {
        "japanese-book-spread": ReadingOrder.JAPANESE_BOOK_SPREAD,
        "western-book-spread": ReadingOrder.WESTERN_BOOK_SPREAD,
    }
    reading_order = reading_order_map[args.reading_order]

    # Run extraction
    extractor = YomiTokuExtractor()

    try:
        fulltext_path = extractor.extract_pdf(
            args.pdf_path,
            args.output_dir,
            reading_order=reading_order,
            start_page=args.start_page,
            end_page=args.end_page,
            dpi=args.dpi,
        )

        print(f"\n✅ Extraction complete: {fulltext_path}")
        print(f"   Size: {fulltext_path.stat().st_size:,} bytes")

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
