#!/usr/bin/env python3
"""Re-extract failed chunk 76-100 with smaller page ranges."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from amplifier.knowledge_synthesis.gemini_extractor import GeminiPdfExtractor
from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


def get_page_range_prompt(start_page: int, end_page: int) -> str:
    """Generate extraction prompt for specific page range - more explicit instructions."""
    return f"""You are a precise text transcription specialist. Your task is to transcribe ONLY PAGES {start_page} to {end_page} from this PDF book.

## CRITICAL INSTRUCTIONS

1. **TRANSCRIBE THE ACTUAL PAGE CONTENT** - Not just headers or page numbers
2. Start with `<!-- PAGE: {start_page} -->`
3. Include ALL text, paragraphs, and content from each page
4. Use proper markdown formatting for headings and paragraphs
5. Preserve Japanese text exactly as written

## PAGE MARKER FORMAT
Insert `<!-- PAGE: n -->` at the START of each page's content.

## WHAT TO INCLUDE
- Main text body paragraphs
- Chapter titles and section headings
- Lists and bullet points
- Quotes and citations
- Footnotes

## WHAT NOT TO DO
- Do NOT just list page numbers
- Do NOT skip content
- Do NOT summarize - transcribe FULLY
- Do NOT repeat the same content

## OUTPUT
Begin with:
<!-- PAGE: {start_page} -->
[Full content of page {start_page}...]

<!-- PAGE: {start_page + 1} -->
[Full content of next page...]

Continue through page {end_page}.
"""


async def extract_small_chunk(
    extractor: GeminiPdfExtractor,
    pdf_path: Path,
    start_page: int,
    end_page: int,
    output_dir: Path,
    model: str,
) -> Path:
    """Extract a small chunk of pages."""
    chunk_file = output_dir / f"_chunk_{start_page:03d}-{end_page:03d}.md"

    prompt = get_page_range_prompt(start_page, end_page)
    logger.info(f"Re-extracting pages {start_page}-{end_page}...")

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

    # Re-extract pages 76-100 in 10-page chunks
    chunks = [(76, 85), (86, 95), (96, 100)]

    for start, end in chunks:
        await extract_small_chunk(extractor, pdf_path, start, end, output_dir, "gemini-2.5-flash")
        await asyncio.sleep(2)

    # Combine the small chunks into the main chunk file
    logger.info("Combining small chunks into _chunk_076-100.md...")
    combined = []
    for start, end in chunks:
        chunk_file = output_dir / f"_chunk_{start:03d}-{end:03d}.md"
        if chunk_file.exists():
            combined.append(chunk_file.read_text(encoding="utf-8"))

    main_chunk = output_dir / "_chunk_076-100.md"
    main_chunk.write_text("\n\n".join(combined), encoding="utf-8")
    logger.info(f"Combined into: {main_chunk} ({main_chunk.stat().st_size} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
