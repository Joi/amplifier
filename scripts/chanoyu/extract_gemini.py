#!/usr/bin/env python3
"""
Gemini 3 Flash PDF Extractor for Complex Multi-Column Japanese Documents.

Gemini 3 Flash excels at:
- Multi-column vertical Japanese text (縦書き)
- Book spreads with 6 columns per page
- Automatic furigana (reading) annotations
- Perfect column separation and reading order

This is the highest-quality extractor but also the slowest and costs money.
Use for complex layouts where YomiToku struggles.

Usage:
    uv run python scripts/chanoyu/extract_gemini.py \
        /path/to/input.pdf \
        /path/to/output/dir

Author: Claude (Amplifier)
Date: 2026-01-04
"""

import argparse
import asyncio
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


# Prompt for multi-column Japanese book spreads
MULTI_COLUMN_PROMPT = """This is a scanned Japanese book spread with MULTI-COLUMN VERTICAL TEXT (縦書き).

## CRITICAL: READING ORDER FOR VERTICAL JAPANESE

In vertical Japanese text, read in this EXACT order:
1. Start at the TOP-RIGHT corner of the RIGHT page
2. Read DOWN the rightmost column (top to bottom)
3. Move LEFT to the next column
4. Continue until all columns on the RIGHT page are done
5. Then start at the TOP-RIGHT of the LEFT page
6. Repeat the same pattern

## LAYOUT
```
RIGHT PAGE          |  LEFT PAGE
Col1  Col2  Col3    |  Col4  Col5  Col6
(1st) (2nd) (3rd)   |  (4th) (5th) (6th)
 ↓     ↓     ↓      |   ↓     ↓     ↓
 ↓     ↓     ↓      |   ↓     ↓     ↓
```

The RIGHTMOST column on the RIGHT page is read FIRST (Column 1).
The LEFTMOST column on the LEFT page is read LAST (Column 6).

## TASK
Extract ALL text in the correct reading order, column by column.

## OUTPUT FORMAT

=== RIGHT PAGE ===

### Column 1 (右ページ・右端 - rightmost on right page, READ FIRST)
[Full text from top to bottom of this column]

### Column 2 (右ページ・中央 - middle of right page)
[Full text from top to bottom of this column]

### Column 3 (右ページ・左端 - leftmost on right page)
[Full text from top to bottom of this column]

=== LEFT PAGE ===

### Column 4 (左ページ・右端 - rightmost on left page)
[Full text from top to bottom of this column]

### Column 5 (左ページ・中央 - middle of left page)
[Full text from top to bottom of this column]

### Column 6 (左ページ・左端 - leftmost on left page, READ LAST)
[Full text from top to bottom of this column]

## RULES
- Extract ALL Japanese text exactly as written
- Keep columns strictly separate - never mix content between columns
- Note images: [図: description]
- Include page numbers at bottom
- Add furigana readings in parentheses for difficult kanji

Extract now:"""


@dataclass
class PageResult:
    """Result from extracting a single page."""

    page_num: int
    text: str
    extraction_time: float
    success: bool = True
    error: str | None = None


class GeminiExtractor:
    """Extract text from PDFs using Gemini 3 Flash."""

    MODEL = "gemini-3-flash-preview"

    def __init__(self) -> None:
        """Initialize the extractor."""
        self._extractor = None

    @property
    def extractor(self):
        """Lazy-load Gemini extractor."""
        if self._extractor is None:
            from amplifier.knowledge_synthesis.gemini_extractor import GeminiPdfExtractor

            self._extractor = GeminiPdfExtractor()
        return self._extractor

    def check_availability(self) -> bool:
        """Check if Gemini API is available."""
        try:
            return self.extractor.check_availability()
        except Exception as e:
            logger.error(f"Gemini API not available: {e}")
            return False

    def _convert_pdf_to_images(
        self,
        pdf_path: Path,
        output_dir: Path,
        dpi: int = 200,
        start_page: int = 1,
        end_page: int | None = None,
    ) -> list[Path]:
        """Convert PDF pages to PNG images using pdftoppm."""
        cmd = [
            "pdftoppm",
            "-png",
            "-r",
            str(dpi),
            "-f",
            str(start_page),
        ]

        if end_page:
            cmd.extend(["-l", str(end_page)])

        cmd.extend([str(pdf_path), str(output_dir / "page")])

        logger.info(f"Converting PDF to images (dpi={dpi})...")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"pdftoppm failed: {result.stderr}")

        # Find generated images
        images = sorted(output_dir.glob("page-*.png"))
        logger.info(f"Generated {len(images)} page images")

        return images

    async def _extract_page_async(
        self,
        image_path: Path,
        page_num: int,
        prompt: str,
    ) -> PageResult:
        """Extract text from a single page image using Gemini 3."""
        start_time = time.time()

        try:
            result = await self.extractor.extract_from_file(
                image_path,
                prompt,
                model=self.MODEL,
            )

            elapsed = time.time() - start_time

            return PageResult(
                page_num=page_num,
                text=result,
                extraction_time=elapsed,
                success=True,
            )

        except Exception as e:
            elapsed = time.time() - start_time
            return PageResult(
                page_num=page_num,
                text="",
                extraction_time=elapsed,
                success=False,
                error=str(e),
            )

    async def extract_pdf_async(
        self,
        pdf_path: Path,
        output_dir: Path,
        start_page: int = 1,
        end_page: int | None = None,
        dpi: int = 200,
        skip_cover: bool = True,
        prompt: str | None = None,
    ) -> Path:
        """Extract text from PDF using Gemini 3 Flash.

        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory
            start_page: First page (1-based)
            end_page: Last page (None = all)
            dpi: Image resolution
            skip_cover: Skip first page (usually cover/calibration)
            prompt: Custom extraction prompt (default: multi-column Japanese)

        Returns:
            Path to combined full-text markdown
        """
        if not self.check_availability():
            raise ValueError("Gemini API not available")

        if not pdf_path.exists():
            raise ValueError(f"PDF not found: {pdf_path}")

        output_dir.mkdir(parents=True, exist_ok=True)
        pages_dir = output_dir / "pages"
        pages_dir.mkdir(exist_ok=True)

        logger.info(f"PDF: {pdf_path.name}")
        logger.info(f"Model: {self.MODEL}")
        logger.info(f"Output: {output_dir}")

        # Convert PDF to images
        images = self._convert_pdf_to_images(
            pdf_path,
            pages_dir,
            dpi=dpi,
            start_page=start_page,
            end_page=end_page,
        )

        if not images:
            raise RuntimeError("No images generated from PDF")

        # Use default prompt if not specified
        extraction_prompt = prompt or MULTI_COLUMN_PROMPT

        # Extract text from each page
        pages: list[PageResult] = []
        total_time = 0

        for i, image_path in enumerate(images, start=1):
            # Calculate actual page number
            actual_page = start_page + i - 1

            # Skip cover page if requested (only when starting from page 1)
            if skip_cover and start_page == 1 and i == 1:
                logger.info("Skipping page 1 (cover)")
                continue

            logger.info(f"Extracting page {actual_page}/{len(images) + start_page - 1}: {image_path.name}")

            result = await self._extract_page_async(
                image_path,
                actual_page,  # Use actual page number
                extraction_prompt,
            )

            total_time += result.extraction_time

            if result.success:
                logger.info(f"  Time: {result.extraction_time:.1f}s, Length: {len(result.text)} chars")

                # Save individual page
                page_file = output_dir / f"_page_{actual_page:04d}.md"
                page_content = f"<!-- PAGE: {actual_page} (Gemini 3 Flash) -->\n\n{result.text}"
                page_file.write_text(page_content, encoding="utf-8")
            else:
                logger.warning(f"  Page {actual_page} failed: {result.error}")

            pages.append(result)

        logger.info(f"Total extraction time: {total_time:.1f}s")

        # Combine into full text
        fulltext_path = self._combine_pages(output_dir, pages, pdf_path, total_time)

        return fulltext_path

    def extract_pdf(
        self,
        pdf_path: Path,
        output_dir: Path,
        start_page: int = 1,
        end_page: int | None = None,
        dpi: int = 200,
        skip_cover: bool = True,
        prompt: str | None = None,
    ) -> Path:
        """Synchronous wrapper for extract_pdf_async."""
        return asyncio.run(
            self.extract_pdf_async(
                pdf_path,
                output_dir,
                start_page=start_page,
                end_page=end_page,
                dpi=dpi,
                skip_cover=skip_cover,
                prompt=prompt,
            )
        )

    def _combine_pages(
        self,
        output_dir: Path,
        pages: list[PageResult],
        pdf_path: Path,
        total_time: float,
    ) -> Path:
        """Combine extracted pages into full-text markdown."""
        fulltext_path = output_dir / "_full-text.md"

        successful_pages = sum(1 for p in pages if p.success)
        avg_time = total_time / len(pages) if pages else 0

        frontmatter = f"""---
title: "{pdf_path.stem}"
source: "{pdf_path.name}"
category: source
type: full-text-extraction
extraction_method: gemini-3-flash
model: {self.MODEL}
pages: {len(pages)}
successful_pages: {successful_pages}
total_extraction_time: {total_time:.1f}s
avg_time_per_page: {avg_time:.1f}s
---

# {pdf_path.stem}

Full text extraction using Gemini 3 Flash for multi-column Japanese text.

**Extraction method**: Gemini 3 Flash (gemini-3-flash-preview)
**Pages extracted**: {successful_pages}/{len(pages)}
**Total time**: {total_time:.1f}s

---

"""

        content_parts = [frontmatter]
        for result in sorted(pages, key=lambda p: p.page_num):
            if result.success:
                content_parts.append(f"\n\n{'=' * 60}\n")
                content_parts.append(f"## PAGE {result.page_num}\n")
                content_parts.append(f"{'=' * 60}\n\n")
                content_parts.append(result.text)
                content_parts.append("\n\n")

        fulltext_path.write_text("".join(content_parts), encoding="utf-8")
        logger.info(f"Combined: {fulltext_path} ({fulltext_path.stat().st_size:,} bytes)")

        return fulltext_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract text from PDFs using Gemini 3 Flash",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Gemini 3 Flash advantages:
  - Perfect column separation for multi-column layouts
  - Automatic furigana (reading) annotations
  - Handles book spreads with 6 columns correctly
  - Highest quality for complex Japanese documents

Trade-offs:
  - Slower than YomiToku (~38 sec/page vs ~6 sec/page)
  - Costs money (~$0.02/page)
  - Requires GEMINI_API_KEY

Use this for complex multi-column layouts where YomiToku struggles.

Examples:
  # Extract multi-column Japanese book
  uv run python scripts/chanoyu/extract_gemini.py \\
      ~/Media/journal.pdf \\
      ~/output/

  # Extract specific page range
  uv run python scripts/chanoyu/extract_gemini.py \\
      ~/Media/journal.pdf \\
      ~/output/ \\
      --start-page 2 --end-page 10

  # Include cover page
  uv run python scripts/chanoyu/extract_gemini.py \\
      ~/Media/journal.pdf \\
      ~/output/ \\
      --no-skip-cover
""",
    )

    parser.add_argument("pdf_path", type=Path, help="Path to PDF file")
    parser.add_argument("output_dir", type=Path, help="Output directory")
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="First page to extract (1-based)",
    )
    parser.add_argument(
        "--end-page",
        type=int,
        default=None,
        help="Last page to extract (default: all)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Image resolution (default: 200)",
    )
    parser.add_argument(
        "--no-skip-cover",
        action="store_true",
        help="Don't skip the first page (cover)",
    )

    args = parser.parse_args()

    extractor = GeminiExtractor()

    try:
        fulltext_path = extractor.extract_pdf(
            args.pdf_path,
            args.output_dir,
            start_page=args.start_page,
            end_page=args.end_page,
            dpi=args.dpi,
            skip_cover=not args.no_skip_cover,
        )

        print(f"\n✅ Extraction complete: {fulltext_path}")
        print(f"   Size: {fulltext_path.stat().st_size:,} bytes")

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
