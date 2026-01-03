#!/usr/bin/env python3
"""
Extract the Handmade Culture (Raku Potters) book.

This English-language book about Raku pottery and tea culture.
"""

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from amplifier.knowledge_synthesis.gemini_extractor import GeminiPdfExtractor
from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


def get_extraction_prompt(start_page: int, end_page: int) -> str:
    """Generate extraction prompt for English academic book."""
    return f"""You are transcribing pages {start_page} to {end_page} from "Handmade Culture: Raku Potters, Patrons, and Tea Practitioners in Japan" by Morgan Pitelka.

## CRITICAL: OUTPUT REQUIREMENTS

### Page Markers
- Start each page with: <!-- PAGE: n -->
- Every page boundary must be marked

### Complete Transcription
- Transcribe ALL text from pages {start_page}-{end_page}
- This is a LOSSLESS extraction - nothing summarized or omitted
- Preserve paragraph structure
- Maintain heading hierarchy (use #, ##, ###)

### Japanese Terms
- Preserve ALL Japanese text (kanji, hiragana, katakana) exactly
- Keep romaji transliterations as written
- Format: 楽 (raku) when both appear

### Academic Content
- Preserve footnotes using markdown: [^1]
- Keep all citations and references
- Maintain quoted material in blockquotes (>)
- Preserve figure/table captions

### Tables and Lists
- Recreate tables in markdown format
- Preserve numbered and bulleted lists

### Figures
- Insert placeholder: [Figure X: description]
- Preserve captions exactly

## ANTI-REPETITION RULES
1. NEVER repeat the same line more than twice
2. If you notice repetition, STOP and move forward
3. Each page should have DIFFERENT content
4. Quality over quantity

## OUTPUT FORMAT
Start immediately with:
<!-- PAGE: {start_page} -->

Then transcribe pages {start_page} through {end_page}.
Stop cleanly after page {end_page}.

Transcribe now:"""


def detect_repetition(text: str, threshold: int = 5) -> tuple[bool, str]:
    """Detect problematic repetition patterns."""
    lines = text.strip().split("\n")

    if len(lines) < threshold:
        return False, "Too short to analyze"

    # Check last N lines for identical content
    last_lines = lines[-threshold:]
    if len(set(last_lines)) == 1 and len(last_lines[0]) > 20:
        return True, f"Last {threshold} lines identical"

    # Check for consecutive repetition
    consecutive_count = 1
    for i in range(1, len(lines)):
        if lines[i] == lines[i-1] and len(lines[i]) > 10:
            consecutive_count += 1
            if consecutive_count >= threshold:
                return True, f"Line repeated {consecutive_count}+ times"
        else:
            consecutive_count = 1

    return False, "No repetition detected"


def count_page_markers(text: str) -> list[int]:
    """Extract all page numbers from PAGE markers."""
    pattern = r'<!-- PAGE: (\d+) -->'
    matches = re.findall(pattern, text)
    return [int(m) for m in matches]


async def extract_chunk(
    extractor: GeminiPdfExtractor,
    pdf_path: Path,
    start_page: int,
    end_page: int,
    output_dir: Path,
    model: str,
    max_retries: int = 2,
) -> tuple[Path, bool]:
    """Extract a chunk with retry logic."""
    chunk_file = output_dir / f"chunk_{start_page:03d}-{end_page:03d}.md"

    # Check if chunk already exists and is valid
    if chunk_file.exists():
        existing = chunk_file.read_text(encoding="utf-8")
        is_rep, _ = detect_repetition(existing)
        if not is_rep and len(existing) > 500:
            pages = count_page_markers(existing)
            expected = list(range(start_page, end_page + 1))
            if len(pages) >= len(expected) * 0.7:
                logger.info(f"Chunk {start_page}-{end_page} already valid, skipping")
                return chunk_file, True

    prompt = get_extraction_prompt(start_page, end_page)

    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Extracting pages {start_page}-{end_page} (attempt {attempt + 1})...")
            result = await extractor.extract_from_file(pdf_path, prompt, model)

            # Check for repetition
            is_rep, reason = detect_repetition(result)
            if is_rep:
                logger.warning(f"Repetition detected: {reason}")
                if attempt < max_retries:
                    await asyncio.sleep(3)
                    continue
                else:
                    chunk_file.write_text(result, encoding="utf-8")
                    return chunk_file, False

            # Save successful extraction
            chunk_file.write_text(result, encoding="utf-8")
            pages = count_page_markers(result)
            logger.info(f"Saved: {chunk_file.name} ({len(result)} chars, pages: {pages})")
            return chunk_file, True

        except Exception as e:
            logger.error(f"Error extracting chunk {start_page}-{end_page}: {e}")
            if attempt < max_retries:
                await asyncio.sleep(5)
                continue
            return chunk_file, False

    return chunk_file, False


async def extract_book(
    pdf_path: Path,
    output_dir: Path,
    total_pages: int,
    chunk_size: int = 15,
    model: str = "gemini-2.5-flash",
) -> Path:
    """Extract entire book in chunks."""

    output_dir.mkdir(parents=True, exist_ok=True)

    extractor = GeminiPdfExtractor()
    if not extractor.check_availability():
        raise RuntimeError("Gemini API not available. Check GOOGLE_API_KEY.")

    # Calculate chunks
    chunks = []
    start = 1
    while start <= total_pages:
        end = min(start + chunk_size - 1, total_pages)
        chunks.append((start, end))
        start = end + 1

    logger.info(f"Extracting {total_pages} pages in {len(chunks)} chunks of {chunk_size} pages")

    # Extract each chunk
    results = []
    failed_chunks = []

    for i, (start_page, end_page) in enumerate(chunks):
        logger.info(f"\n=== Chunk {i+1}/{len(chunks)}: pages {start_page}-{end_page} ===")
        chunk_file, success = await extract_chunk(
            extractor, pdf_path, start_page, end_page, output_dir, model
        )
        results.append((chunk_file, success))
        if not success:
            failed_chunks.append((start_page, end_page))

        # Rate limiting
        await asyncio.sleep(2)

    # Report results
    success_count = sum(1 for _, s in results if s)
    logger.info(f"\n=== Extraction Complete ===")
    logger.info(f"Successful: {success_count}/{len(chunks)}")
    if failed_chunks:
        logger.warning(f"Failed chunks: {failed_chunks}")

    # Combine chunks
    combined_path = output_dir / "_full-text.md"
    combine_chunks(output_dir, combined_path, total_pages, model, pdf_path)

    return combined_path


def combine_chunks(
    output_dir: Path,
    output_file: Path,
    total_pages: int,
    model: str,
    pdf_path: Path,
) -> None:
    """Combine all chunks into a single file."""

    chunk_files = sorted(output_dir.glob("chunk_*.md"))

    if not chunk_files:
        logger.error("No chunk files found!")
        return

    logger.info(f"Combining {len(chunk_files)} chunks...")

    # Build frontmatter
    content = [f"""---
title: "Handmade Culture: Raku Potters, Patrons, and Tea Practitioners in Japan"
author: "Morgan Pitelka"
category: source
type: full-text-extraction
format: book
language: English
extraction_method: chunked-anti-repetition
total_pages: {total_pages}
model: {model}
source_file: "{pdf_path.name}"
---

# Handmade Culture: Raku Potters, Patrons, and Tea Practitioners in Japan

**Author:** Morgan Pitelka

---

"""]

    # Add each chunk
    all_pages = set()
    for chunk_file in chunk_files:
        chunk_content = chunk_file.read_text(encoding="utf-8")

        # Extract page numbers for tracking
        pages = count_page_markers(chunk_content)
        all_pages.update(pages)

        content.append(chunk_content)
        content.append("\n\n")

    # Write combined file
    output_file.write_text("".join(content), encoding="utf-8")

    # Report coverage
    expected_pages = set(range(1, total_pages + 1))
    missing_pages = expected_pages - all_pages

    logger.info(f"Combined file: {output_file}")
    logger.info(f"Pages extracted: {len(all_pages)}/{total_pages}")
    if missing_pages:
        logger.warning(f"Missing pages: {sorted(missing_pages)}")


async def main():
    """Extract the Raku book."""

    pdf_path = Path("/Users/joi/Media/chanoyu-sources/dokumen.pub_handmade-culture-raku-potters-patrons-and-tea-practitioners-in-japan.pdf")
    output_dir = Path("/Users/joi/switchboard/chanoyu/sources/handmade-culture-raku/chunks")
    total_pages = 269

    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return

    logger.info(f"Source PDF: {pdf_path}")
    logger.info(f"Output dir: {output_dir}")
    logger.info(f"Total pages: {total_pages}")

    result = await extract_book(
        pdf_path=pdf_path,
        output_dir=output_dir,
        total_pages=total_pages,
        chunk_size=15,  # 15 pages per chunk for English text
        model="gemini-2.5-flash",
    )

    logger.info(f"\nDone! Full text saved to: {result}")


if __name__ == "__main__":
    asyncio.run(main())
