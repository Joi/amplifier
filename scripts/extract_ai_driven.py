#!/usr/bin/env python3
"""Extract full text from AI Driven book using chunked approach."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from amplifier.knowledge_synthesis.gemini_extractor import GeminiPdfExtractor
from amplifier.utils.logger import get_logger

logger = get_logger(__name__)

PDF_PATH = Path("/Users/joi/My Drive (joi@ito.com)/Books/ai_driven_nen.pdf")
OUTPUT_DIR = Path("/Users/joi/switchboard/joi-writing/books/ai-driven-nen")


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

## OUTPUT FORMAT
<!-- PAGE: {start_page} -->
[Full content of page {start_page}...]

<!-- PAGE: {start_page + 1} -->
[Full content of next page...]

Continue through page {end_page}. Transcribe ALL text, not summaries.
"""


async def get_page_count(extractor) -> int:
    """Get the total page count from the PDF."""
    prompt = "How many pages does this PDF document have? Reply with just the number."
    result = await extractor.extract_from_file(PDF_PATH, prompt, "gemini-2.5-flash")
    # Extract number from result
    import re

    match = re.search(r"\d+", result)
    if match:
        return int(match.group())
    raise ValueError(f"Could not determine page count from: {result}")


async def extract_chunk(extractor, start_page: int, end_page: int) -> Path:
    """Extract a single chunk of pages."""
    chunk_file = OUTPUT_DIR / f"_chunk_{start_page:03d}-{end_page:03d}.md"

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

    # Get page count
    logger.info("Getting page count...")
    total_pages = await get_page_count(extractor)
    logger.info(f"Total pages: {total_pages}")

    # Calculate chunks (10 pages each for reliability)
    chunk_size = 10
    chunks = []
    for start in range(1, total_pages + 1, chunk_size):
        end = min(start + chunk_size - 1, total_pages)
        chunks.append((start, end))

    logger.info(f"Will extract {len(chunks)} chunks of ~{chunk_size} pages each")

    # Extract each chunk
    for start, end in chunks:
        await extract_chunk(extractor, start, end)
        await asyncio.sleep(2)  # Rate limiting

    logger.info(f"Done! Extracted {len(chunks)} chunks for {total_pages} pages.")


if __name__ == "__main__":
    asyncio.run(main())
