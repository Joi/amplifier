#!/usr/bin/env python3
"""
Chunked PDF extraction for large books.

Uses smaller page ranges to avoid Gemini output token limits.
"""

import asyncio
import sys
from pathlib import Path

# Add amplifier to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from amplifier.knowledge_synthesis.gemini_extractor import GeminiPdfExtractor
from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


def get_page_range_prompt(start_page: int, end_page: int) -> str:
    """Generate extraction prompt for specific page range."""
    return f"""You are a precise text transcription specialist. Your task is to create a
complete, lossless markdown transcription of PAGES {start_page} to {end_page} from this PDF book.

## CRITICAL REQUIREMENTS

### 1. Page Markers (MOST IMPORTANT)
- Insert `<!-- PAGE: n -->` marker at the START of each page's content
- Every page boundary must be marked
- Page numbers enable precise citations later

### 2. Complete Transcription
- Transcribe ALL text from pages {start_page}-{end_page}, not just "key points"
- This is a LOSSLESS extraction - nothing should be summarized or omitted
- Preserve paragraph structure
- Maintain heading hierarchy (use #, ##, ###)
- Keep original punctuation and formatting

### 3. Japanese/Original Language Text
- Preserve ALL kanji, hiragana, katakana EXACTLY as written
- Add romaji in parentheses for specialized terms on first occurrence
- Format: 茶道 (chadō)
- Keep original-language quotations intact

### 4. Tables and Lists
- Recreate tables in markdown format
- Preserve numbered and bulleted lists
- Maintain original ordering

### 5. Quotations
- Use blockquote (>) for quotations
- Preserve quotation attribution

### 6. Figures and Images
- Insert placeholder: `[Figure X.Y: brief description]`
- Preserve captions exactly

### 7. Footnotes/Endnotes
- Preserve using markdown footnote syntax: [^1]
- Place footnote content at end of this section

## OUTPUT FORMAT

Start immediately with the page content. First line should be:
<!-- PAGE: {start_page} -->

Then provide the complete transcription of pages {start_page} to {end_page}.

## IMPORTANT
- Only transcribe pages {start_page} through {end_page}
- Do NOT repeat content or enter loops
- Stop cleanly at page {end_page}
"""


async def extract_chunk(
    extractor: GeminiPdfExtractor,
    pdf_path: Path,
    start_page: int,
    end_page: int,
    output_dir: Path,
    model: str,
) -> Path:
    """Extract a single chunk of pages."""
    chunk_file = output_dir / f"_chunk_{start_page:03d}-{end_page:03d}.md"

    if chunk_file.exists() and chunk_file.stat().st_size > 5000:
        logger.info(f"Chunk {start_page}-{end_page} already exists ({chunk_file.stat().st_size} bytes), skipping")
        return chunk_file

    prompt = get_page_range_prompt(start_page, end_page)

    logger.info(f"Extracting pages {start_page}-{end_page}...")

    try:
        result = await extractor.extract_from_file(pdf_path, prompt, model)

        # Check for degenerate output (repetition)
        if len(result) > 1000:
            # Check last 500 chars for repetition
            last_chunk = result[-500:]
            lines = last_chunk.split("\n")
            if len(lines) > 3:
                # If last 3 lines are identical, likely hit MAX_TOKENS
                if lines[-1] == lines[-2] == lines[-3] and len(lines[-1]) > 10:
                    logger.warning(f"Chunk {start_page}-{end_page} may have hit MAX_TOKENS (repetitive ending)")

        chunk_file.write_text(result, encoding="utf-8")
        logger.info(f"Saved chunk: {chunk_file.name} ({len(result)} chars)")
        return chunk_file

    except Exception as e:
        logger.error(f"Failed to extract chunk {start_page}-{end_page}: {e}")
        raise


async def extract_book_chunked(
    pdf_path: Path,
    output_dir: Path,
    total_pages: int,
    chunk_size: int = 25,
    model: str = "gemini-2.5-flash",
) -> Path:
    """Extract entire book in chunks and combine."""

    output_dir.mkdir(parents=True, exist_ok=True)

    extractor = GeminiPdfExtractor()
    if not extractor.check_availability():
        raise RuntimeError("Gemini API not available")

    # Calculate page ranges
    chunks = []
    start = 1
    while start <= total_pages:
        end = min(start + chunk_size - 1, total_pages)
        chunks.append((start, end))
        start = end + 1

    logger.info(f"Will extract {len(chunks)} chunks: {chunks}")

    # Extract each chunk
    chunk_files = []
    for start_page, end_page in chunks:
        chunk_file = await extract_chunk(extractor, pdf_path, start_page, end_page, output_dir, model)
        chunk_files.append(chunk_file)
        # Small delay between chunks
        await asyncio.sleep(2)

    # Combine chunks
    logger.info("Combining chunks...")
    combined_path = output_dir / "_full-text.md"

    # Add frontmatter
    frontmatter = f"""---
title: "{pdf_path.stem}"
category: source
type: full-text-extraction
extraction_method: chunked
chunks: {len(chunks)}
pages: {total_pages}
model: {model}
---

"""

    combined_content = [frontmatter]
    for chunk_file in sorted(chunk_files):
        content = chunk_file.read_text(encoding="utf-8")
        # Remove any duplicate frontmatter from chunks
        if content.startswith("---"):
            # Find end of frontmatter
            end_idx = content.find("---", 3)
            if end_idx > 0:
                content = content[end_idx + 3 :].strip()
        combined_content.append(content)
        combined_content.append("\n\n")

    combined_path.write_text("\n".join(combined_content), encoding="utf-8")
    logger.info(f"Combined file: {combined_path} ({combined_path.stat().st_size} bytes)")

    return combined_path


async def main():
    # Configuration for technology-mirai book
    pdf_path = Path("/Users/joi/My Drive (joi@ito.com)/Books/technology-mirai.pdf")
    output_dir = Path("/Users/joi/switchboard/joi-writing/books/technology-mirai")
    total_pages = 230
    chunk_size = 25  # Smaller chunks for reliability

    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return

    result = await extract_book_chunked(
        pdf_path=pdf_path,
        output_dir=output_dir,
        total_pages=total_pages,
        chunk_size=chunk_size,
        model="gemini-2.5-flash",
    )

    logger.info(f"\n✓ Extraction complete: {result}")


if __name__ == "__main__":
    asyncio.run(main())
