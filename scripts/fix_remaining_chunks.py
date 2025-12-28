#!/usr/bin/env python3
"""Fix remaining problematic chunks with smaller page ranges."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from amplifier.knowledge_synthesis.gemini_extractor import GeminiPdfExtractor
from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


def get_page_range_prompt(start_page: int, end_page: int) -> str:
    """Generate extraction prompt for specific page range."""
    return f"""You are a precise text transcription specialist. Transcribe ONLY PAGES {start_page} to {end_page} from this PDF.

## CRITICAL INSTRUCTIONS
- Start with `<!-- PAGE: {start_page} -->`
- Include ALL text content from each page
- Do NOT just list page numbers - transcribe the actual text
- Use markdown formatting for headings and paragraphs
- Preserve Japanese text exactly as written

## OUTPUT
<!-- PAGE: {start_page} -->
[Full content of page {start_page}...]

<!-- PAGE: {start_page + 1} -->
[Full content of next page...]

Continue through page {end_page}. Transcribe ALL text, not summaries.
"""


async def extract_chunk(extractor, pdf_path, start_page, end_page, output_dir, model):
    """Extract a single chunk of pages."""
    chunk_file = output_dir / f"_chunk_{start_page:03d}-{end_page:03d}.md"

    prompt = get_page_range_prompt(start_page, end_page)
    logger.info(f"Extracting pages {start_page}-{end_page}...")

    result = await extractor.extract_from_file(pdf_path, prompt, model)
    chunk_file.write_text(result, encoding="utf-8")
    logger.info(f"Saved: {chunk_file.name} ({len(result)} chars)")
    return chunk_file


async def main():
    pdf_path = Path("/Users/joi/My Drive (joi@ito.com)/Books/technology-mirai.pdf")
    output_dir = Path("/Users/joi/switchboard/joi-writing/books/technology-mirai")

    extractor = GeminiPdfExtractor()
    if not extractor.check_availability():
        raise RuntimeError("Gemini API not available")

    # Problematic chunks that need re-extraction with smaller ranges
    # Chunk 26-50: only 2/25 pages
    # Chunk 51-75: only 12/25 pages
    # Chunk 151-175: only 15/25 pages
    # Chunk 201-225: only 6/25 pages

    chunks_to_fix = [
        (26, 35),
        (36, 45),
        (46, 50),  # Fix 26-50
        (51, 60),
        (61, 70),
        (71, 75),  # Fix 51-75
        (151, 160),
        (161, 170),
        (171, 175),  # Fix 151-175
        (201, 210),
        (211, 220),
        (221, 225),  # Fix 201-225
    ]

    for start, end in chunks_to_fix:
        await extract_chunk(extractor, pdf_path, start, end, output_dir, "gemini-2.5-flash")
        await asyncio.sleep(3)

    logger.info("Done! Now recombine the chunks.")


if __name__ == "__main__":
    asyncio.run(main())
