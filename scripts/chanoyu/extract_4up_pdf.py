#!/usr/bin/env python3
"""
4-Up Layout PDF Extractor using Gemini Vision.

Japanese academic journals often print 4 pages per sheet (2x2 layout).
The correct reading order for vertical Japanese text is:
    Upper-right → Lower-right → Upper-left → Lower-left

This script:
1. Converts each physical PDF page to an image
2. Splits into 4 quadrants
3. Extracts text from each quadrant using Gemini Vision
4. Combines in the correct reading order

Usage:
    op run --env-file=~/.env -- python scripts/chanoyu/extract_4up_pdf.py \\
        /path/to/input.pdf \\
        /path/to/output/dir \\
        --reading-order japanese-vertical

Author: Claude (Amplifier)
Date: 2025-01-02
"""

import argparse
import asyncio
import base64
import io
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Add amplifier to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)

# Import dependencies
try:
    from pdf2image import convert_from_path
    from PIL import Image

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    convert_from_path = None
    Image = None
    PDF2IMAGE_AVAILABLE = False

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False


class ReadingOrder(Enum):
    """Reading order patterns for multi-up layouts."""

    # Japanese book spread (2-up): Right page first, then left
    # This is for scanned open books with Japanese vertical text
    # Physical page shows: [LEFT PAGE] [RIGHT PAGE]
    # Reading order: RIGHT → LEFT (because Japanese reads right-to-left)
    JAPANESE_BOOK_SPREAD = "japanese-book-spread"

    # Japanese 4-up: right-to-left, then top-to-bottom
    # Physical page shows: [UL] [UR]
    #                      [LL] [LR]
    # Reading order: UR → LR → UL → LL
    JAPANESE_4UP = "japanese-4up"

    # Western book spread (2-up): Left page first, then right
    # Reading order: LEFT → RIGHT
    WESTERN_BOOK_SPREAD = "western-book-spread"

    # Western 4-up: left-to-right, then top-to-bottom
    # Reading order: UL → UR → LL → LR
    WESTERN_4UP = "western-4up"


@dataclass
class Quadrant:
    """Represents a quadrant of a 4-up page."""

    position: str  # UL, UR, LL, LR
    logical_page: int  # The logical page number this represents
    image: Image.Image | None = None
    text: str = ""


class FourUpExtractor:
    """Extract text from 4-up layout PDFs with correct reading order."""

    DEFAULT_MODEL = "gemini-2.5-flash"
    DEFAULT_DPI = 200  # Higher DPI for splitting into quadrants

    def __init__(self) -> None:
        """Initialize the extractor."""
        # Check for cached API key first (avoids repeated biometric auth)
        cache_file = Path.home() / ".cache" / "amplifier" / "gemini_api_key"
        if cache_file.exists():
            self.api_key = cache_file.read_text().strip()
        else:
            self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

        # Log which key source we're using
        if self.api_key:
            if cache_file.exists():
                pass  # Silent - using cached key
            else:
                print("Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY.")

        self.configured = bool(
            self.api_key and
            self.api_key.strip() and
            GENAI_AVAILABLE and
            PDF2IMAGE_AVAILABLE
        )
        self.client = None

        if self.configured and genai:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Gemini client initialized for 4-up extraction")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.configured = False

    def check_availability(self) -> bool:
        """Check if all dependencies are available."""
        if not PDF2IMAGE_AVAILABLE:
            logger.error("pdf2image/PIL not installed. Run: uv add pdf2image pillow")
            return False

        if not GENAI_AVAILABLE:
            logger.error("google-genai not installed. Run: uv add google-genai")
            return False

        if not self.api_key:
            logger.error(
                "GOOGLE_API_KEY not set. Either:\n"
                "  1. Cache key: op read 'op://Employee/Amplifier Gemini Key/credential' > ~/.cache/amplifier/gemini_api_key\n"
                "  2. Use wrapper: ./scripts/chanoyu/run_with_gemini.sh uv run python ...\n"
                "  3. Use op run: op run --env-file=.env.local -- uv run python ..."
            )
            return False

        if not self.client:
            logger.error("Gemini client not initialized")
            return False

        return True

    def get_reading_order(self, order: ReadingOrder) -> list[str]:
        """Get quadrant order based on reading pattern.

        Returns list of quadrant positions in reading order.
        """
        if order == ReadingOrder.JAPANESE_BOOK_SPREAD:
            # Japanese book: right page first, then left
            return ["R", "L"]
        elif order == ReadingOrder.JAPANESE_4UP:
            # Japanese 4-up: upper-right → lower-right → upper-left → lower-left
            return ["UR", "LR", "UL", "LL"]
        elif order == ReadingOrder.WESTERN_BOOK_SPREAD:
            # Western book: left page first, then right
            return ["L", "R"]
        elif order == ReadingOrder.WESTERN_4UP:
            # Western 4-up: upper-left → upper-right → lower-left → lower-right
            return ["UL", "UR", "LL", "LR"]
        else:
            raise ValueError(f"Unknown reading order: {order}")

    def split_image_4up(self, image: Image.Image) -> dict[str, Image.Image]:
        """Split an image into 4 quadrants.

        Args:
            image: PIL Image of a full page

        Returns:
            Dict mapping position (UL, UR, LL, LR) to cropped image
        """
        width, height = image.size
        mid_x = width // 2
        mid_y = height // 2

        # Add small overlap to avoid cutting text at boundaries
        overlap = 10

        quadrants = {
            "UL": image.crop((0, 0, mid_x + overlap, mid_y + overlap)),
            "UR": image.crop((mid_x - overlap, 0, width, mid_y + overlap)),
            "LL": image.crop((0, mid_y - overlap, mid_x + overlap, height)),
            "LR": image.crop((mid_x - overlap, mid_y - overlap, width, height)),
        }

        return quadrants

    def split_image_2up(self, image: Image.Image) -> dict[str, Image.Image]:
        """Split an image into 2 halves (left and right).

        Args:
            image: PIL Image of a full page

        Returns:
            Dict mapping position (L, R) to cropped image
        """
        width, height = image.size
        mid_x = width // 2
        overlap = 10

        return {
            "L": image.crop((0, 0, mid_x + overlap, height)),
            "R": image.crop((mid_x - overlap, 0, width, height)),
        }

    def image_to_bytes(self, image: Image.Image) -> bytes:
        """Convert PIL Image to PNG bytes."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    async def extract_quadrant(
        self,
        image: Image.Image,
        logical_page: int,
        position: str,
        model: str,
    ) -> str:
        """Extract text from a single quadrant image.

        Args:
            image: PIL Image of the quadrant
            logical_page: Logical page number
            position: Quadrant position (UL, UR, etc.)
            model: Gemini model name

        Returns:
            Extracted markdown text
        """
        if not self.client:
            raise RuntimeError("Gemini client not initialized")

        # Convert to bytes
        image_bytes = self.image_to_bytes(image)

        # Build prompt
        prompt = self._get_quadrant_prompt(logical_page, position)

        # Run extraction
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._extract_with_vision,
            image_bytes,
            prompt,
            model,
        )

        return result

    def _extract_with_vision(
        self,
        image_bytes: bytes,
        prompt: str,
        model: str,
    ) -> str:
        """Send image to Gemini and get transcription."""
        if not self.client:
            raise RuntimeError("Gemini client not initialized")

        image_data = {
            "inline_data": {
                "mime_type": "image/png",
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }
        }

        # Use generation config to prevent repetition loops
        from google.genai import types
        config = types.GenerateContentConfig(
            temperature=0.0,  # Zero for deterministic column-order reading
            max_output_tokens=8192,  # Enough for full pages but prevents infinite loops
        )

        response = self.client.models.generate_content(
            model=model,
            contents=[image_data, prompt],
            config=config,
        )

        if response.text:
            return response.text
        raise RuntimeError("No text in Gemini response")

    def _get_quadrant_prompt(self, logical_page: int, position: str) -> str:
        """Generate prompt for quadrant extraction."""
        return f"""Transcribe this Japanese page image COLUMN BY COLUMN.

## STEP 1: IDENTIFY COLUMNS (REQUIRED)

This is VERTICAL Japanese text (縦書き/tategaki). First, mentally identify each vertical column from RIGHT to LEFT.
Columns are separated by whitespace or visual breaks. A typical academic page has 10-15 columns.

## STEP 2: READ EACH COLUMN IN ORDER

For each column (starting from the RIGHTMOST):
- Read from TOP to BOTTOM
- Complete the ENTIRE column before moving left
- When text continues across a column boundary, JOIN it into complete sentences

## CRITICAL RULES

1. **NEVER mix text from different columns** - this is the most common error
2. **Complete each column fully** before moving to the next column
3. **Join sentences across columns** - if a sentence ends mid-word at the bottom of column N, it continues at the top of column N+1

## OUTPUT FORMAT

**First line MUST be**: `<!-- PAGE: {logical_page} -->`

Then transcribe the text as flowing paragraphs with complete sentences.

## SENTENCE COMPLETENESS

Each sentence MUST be complete with proper ending punctuation (。, ?, !, etc.)

**WRONG** (fragmented):
```
千利休が亡くなりましたの
が一五九一年ですので、一
九九〇年が、四百年忌に相
```

**CORRECT** (complete sentences):
```
千利休が亡くなりましたのが一五九一年ですので、一九九〇年が、四百年忌に相当するという訳で、この三月二八日に大徳寺の法堂におきまして法要が行われました。
```

## FORMATTING

- Use markdown headings (#, ##, ###) for titles
- Preserve paragraph breaks
- For proper names, add reading: 利休 (Rikyū), 大徳寺 (Daitokuji)
- For key terms, add reading: 茶道 (chadō), 遠忌 (enki)
- Figures: `[Figure: description]`

## IMPORTANT

- Transcribe ALL text exactly ONCE - no repetition, no summarization
- If there are ~500 characters of text, output ~500 characters
- Do NOT add content that isn't in the image
- Read columns RIGHT→LEFT, text within columns TOP→BOTTOM

This is quadrant {position} of the physical page.

<!-- PAGE: {logical_page} -->
[Begin transcription here...]"""

    async def extract_pdf(
        self,
        pdf_path: Path,
        output_dir: Path,
        reading_order: ReadingOrder = ReadingOrder.JAPANESE_BOOK_SPREAD,
        start_physical_page: int = 1,
        end_physical_page: int | None = None,
        dpi: int = DEFAULT_DPI,
        model: str | None = None,
    ) -> Path:
        """Extract text from a 4-up layout PDF.

        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory
            reading_order: Reading order pattern
            start_physical_page: First physical page (1-based)
            end_physical_page: Last physical page (None = all)
            dpi: Image resolution
            model: Gemini model

        Returns:
            Path to combined full-text markdown
        """
        if not self.check_availability():
            raise ValueError("Dependencies not available")

        if not pdf_path.exists():
            raise ValueError(f"PDF not found: {pdf_path}")

        model = model or self.DEFAULT_MODEL
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get physical page count
        from pdf2image.pdf2image import pdfinfo_from_path
        info = pdfinfo_from_path(str(pdf_path))
        total_physical_pages = info.get("Pages", 0)

        if end_physical_page is None or end_physical_page > total_physical_pages:
            end_physical_page = total_physical_pages

        # Determine number of logical pages per physical page
        is_4up = reading_order in (ReadingOrder.JAPANESE_4UP, ReadingOrder.WESTERN_4UP)
        pages_per_sheet = 4 if is_4up else 2

        logger.info(f"PDF: {pdf_path.name}")
        logger.info(f"Physical pages: {total_physical_pages}")
        logger.info(f"Layout: {'4-up' if is_4up else '2-up'}")
        logger.info(f"Reading order: {reading_order.value}")
        logger.info(f"Estimated logical pages: {total_physical_pages * pages_per_sheet}")

        # Get quadrant order
        quadrant_order = self.get_reading_order(reading_order)

        # Track all extracted pages
        all_pages: list[tuple[int, str]] = []  # (logical_page, content)

        # Process each physical page
        # Calculate starting logical page based on physical page offset
        logical_page = (start_physical_page - 1) * pages_per_sheet + 1
        for physical_page in range(start_physical_page, end_physical_page + 1):
            logger.info(f"Processing physical page {physical_page}/{end_physical_page}...")

            # Convert physical page to image
            images = convert_from_path(
                str(pdf_path),
                dpi=dpi,
                first_page=physical_page,
                last_page=physical_page,
            )

            if not images:
                logger.error(f"Failed to convert physical page {physical_page}")
                continue

            full_image = images[0]

            # Split into quadrants
            if is_4up:
                quadrants = self.split_image_4up(full_image)
            else:
                quadrants = self.split_image_2up(full_image)

            # Extract each quadrant in reading order
            for position in quadrant_order:
                if position not in quadrants:
                    continue

                quadrant_image = quadrants[position]
                page_file = output_dir / f"_page_{logical_page:04d}.md"

                # Skip if already extracted
                if page_file.exists() and page_file.stat().st_size > 100:
                    logger.info(f"  Logical page {logical_page} ({position}): exists, skipping")
                    content = page_file.read_text(encoding="utf-8")
                else:
                    try:
                        logger.info(f"  Extracting logical page {logical_page} ({position})...")
                        content = await self.extract_quadrant(
                            quadrant_image,
                            logical_page,
                            position,
                            model,
                        )
                        page_file.write_text(content, encoding="utf-8")
                        logger.info(f"  Logical page {logical_page}: {len(content)} chars")

                        # Rate limiting
                        await asyncio.sleep(1.5)

                    except Exception as e:
                        logger.error(f"  Logical page {logical_page} FAILED: {e}")
                        content = f"<!-- EXTRACTION FAILED: {e} -->\n"
                        page_file.write_text(content, encoding="utf-8")

                all_pages.append((logical_page, content))
                logical_page += 1

        # Combine into full text
        fulltext_path = self._combine_pages(
            output_dir,
            all_pages,
            pdf_path,
            reading_order,
            model,
        )

        return fulltext_path

    def _combine_pages(
        self,
        output_dir: Path,
        pages: list[tuple[int, str]],
        pdf_path: Path,
        reading_order: ReadingOrder,
        model: str,
    ) -> Path:
        """Combine extracted pages into full-text markdown."""
        fulltext_path = output_dir / "_full-text.md"

        # Build frontmatter
        frontmatter = f"""---
title: "{pdf_path.stem}"
source: "{pdf_path.name}"
category: source
type: full-text-extraction
extraction_method: 4-up-layout
reading_order: {reading_order.value}
logical_pages: {len(pages)}
model: {model}
---

# {pdf_path.stem}

Full text extraction from 4-up layout PDF using Gemini Vision.

**Reading order**: {reading_order.value}
- For Japanese vertical text: upper-right → lower-right → upper-left → lower-left

---

"""

        # Combine in order
        content_parts = [frontmatter]
        for _page_num, content in sorted(pages):
            content_parts.append(content)
            content_parts.append("\n\n")

        fulltext_path.write_text("".join(content_parts), encoding="utf-8")
        logger.info(f"Combined: {fulltext_path} ({fulltext_path.stat().st_size:,} bytes)")

        return fulltext_path


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract text from 4-up layout PDFs with correct reading order",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Reading Order Patterns:
  japanese-book-spread  Right page → Left page (scanned book spreads, Japanese)
  japanese-4up          UR → LR → UL → LL (4 pages per sheet, Japanese)
  western-book-spread   Left page → Right page (scanned book spreads, Western)
  western-4up           UL → UR → LL → LR (4 pages per sheet, Western)

Examples:
  # Extract Japanese scanned book (2-up book spread)
  op run --env-file=~/.env -- python scripts/chanoyu/extract_4up_pdf.py \\
      ~/Media/journal.pdf \\
      ~/output/ \\
      --reading-order japanese-book-spread

  # Extract with specific page range (skip cover page)
  op run --env-file=~/.env -- python scripts/chanoyu/extract_4up_pdf.py \\
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
        choices=["japanese-book-spread", "japanese-4up", "western-book-spread", "western-4up"],
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
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-flash",
        help="Gemini model (default: gemini-2.5-flash)",
    )

    args = parser.parse_args()

    # Map reading order string to enum
    reading_order_map = {
        "japanese-book-spread": ReadingOrder.JAPANESE_BOOK_SPREAD,
        "japanese-4up": ReadingOrder.JAPANESE_4UP,
        "western-book-spread": ReadingOrder.WESTERN_BOOK_SPREAD,
        "western-4up": ReadingOrder.WESTERN_4UP,
    }
    reading_order = reading_order_map[args.reading_order]

    # Run extraction
    extractor = FourUpExtractor()

    try:
        fulltext_path = await extractor.extract_pdf(
            args.pdf_path,
            args.output_dir,
            reading_order=reading_order,
            start_physical_page=args.start_page,
            end_physical_page=args.end_page,
            dpi=args.dpi,
            model=args.model,
        )

        print(f"\n✅ Extraction complete: {fulltext_path}")
        print(f"   Size: {fulltext_path.stat().st_size:,} bytes")

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
