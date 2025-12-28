#!/usr/bin/env python3
"""Re-extract failed chunks from AI Driven book using smaller page ranges."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from amplifier.knowledge_synthesis.gemini_extractor import GeminiPdfExtractor
from amplifier.utils.logger import get_logger

logger = get_logger(__name__)

PDF_PATH = Path("/Users/joi/My Drive (joi@ito.com)/Books/ai_driven_nen.pdf")
OUTPUT_DIR = Path("/Users/joi/switchboard/joi-writing/books/ai-driven-nen")

# Load API key from session file
API_KEY_FILE = Path("/tmp/.gemini_api_key_session")
if API_KEY_FILE.exists():
    os.environ["GOOGLE_API_KEY"] = API_KEY_FILE.read_text().strip()


def get_page_range_prompt(start_page: int, end_page: int) -> str:
    """Generate extraction prompt for specific page range."""
    return f"""You are a precise text transcription specialist. Transcribe ONLY PAGES {start_page} to {end_page} from this PDF.

## CRITICAL INSTRUCTIONS
- Start with `<!-- PAGE: {start_page} -->`
- Include ALL text content from each page
- Do NOT just list page numbers - transcribe the actual text
- Use markdown formatting for headings and paragraphs
- Preserve Japanese text exactly as written
- Add romanization in parentheses for key terms
- STOP after page {end_page} - do not continue or repeat

## OUTPUT FORMAT
<!-- PAGE: {start_page} -->
[Full content of page {start_page}...]

<!-- PAGE: {start_page + 1} -->
[Full content of next page...]

Continue through page {end_page}. Transcribe ALL text, not summaries.
"""


async def extract_chunk(extractor, start_page: int, end_page: int) -> Path:
    """Extract a single chunk of pages."""
    chunk_file = OUTPUT_DIR / f"_chunk_{start_page:03d}-{end_page:03d}.md"

    # Skip if already exists and is reasonable size
    if chunk_file.exists():
        size = chunk_file.stat().st_size
        if 1000 < size < 100000:  # Between 1KB and 100KB is reasonable
            logger.info(f"Skipping {chunk_file.name} - already exists ({size:,} bytes)")
            return chunk_file

    prompt = get_page_range_prompt(start_page, end_page)
    logger.info(f"Extracting pages {start_page}-{end_page}...")

    result = await extractor.extract_from_file(PDF_PATH, prompt, "gemini-2.5-flash")
    chunk_file.write_text(result, encoding="utf-8")

    # Count page markers
    page_count = result.count("<!-- PAGE:")
    logger.info(f"Saved: {chunk_file.name} ({len(result):,} chars, {page_count} pages)")

    return chunk_file


async def main():
    extractor = GeminiPdfExtractor()
    if not extractor.check_availability():
        raise RuntimeError("Gemini API not available - check GOOGLE_API_KEY")

    # Delete corrupted chunks first
    corrupted = [
        OUTPUT_DIR / "_chunk_001-010.md",
        OUTPUT_DIR / "_chunk_041-050.md",
        OUTPUT_DIR / "_chunk_131-140.md",
    ]
    for f in corrupted:
        if f.exists():
            logger.info(f"Deleting corrupted: {f.name}")
            f.unlink()

    # Re-extract with smaller 5-page chunks
    failed_ranges = [
        (1, 5),
        (6, 10),  # Was 1-10
        (41, 45),
        (46, 50),  # Was 41-50
        (131, 135),
        (136, 140),  # Was 131-140
    ]

    logger.info(f"Re-extracting {len(failed_ranges)} chunks with smaller page ranges")

    for start, end in failed_ranges:
        await extract_chunk(extractor, start, end)
        await asyncio.sleep(2)  # Rate limiting

    logger.info("Done re-extracting failed chunks!")


if __name__ == "__main__":
    asyncio.run(main())
