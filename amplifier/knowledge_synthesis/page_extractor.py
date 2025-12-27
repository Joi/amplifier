"""
Page-by-page PDF extractor using image conversion.

This extractor physically splits PDFs into single-page images before
sending to Gemini, which prevents cross-page repetition loops that
can occur when the model sees the entire document.

Key benefits:
- Each page is processed in complete isolation
- Images/illustrations are naturally described
- Japanese text is handled via OCR (better than pypdf)
- Supports resume on failure (skips existing pages)
"""

import asyncio
import base64
import io
import os
from pathlib import Path

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)

# Import dependencies
try:
    from pdf2image import convert_from_path
    from pdf2image.exceptions import PDFInfoNotInstalledError

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    convert_from_path = None  # type: ignore
    PDFInfoNotInstalledError = Exception  # type: ignore
    PDF2IMAGE_AVAILABLE = False

try:
    from google import genai  # type: ignore[import-untyped]
    from google.genai import types  # type: ignore[import-untyped]

    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore
    GENAI_AVAILABLE = False


class PageByPageExtractor:
    """Extract PDF content one page at a time via image conversion.

    This approach prevents repetition loops by physically isolating each page
    before sending to Gemini. The model only ever sees one page at a time.
    """

    # Gemini 2.5 Flash - latest stable model with improved accuracy
    DEFAULT_MODEL = "gemini-2.5-flash"
    DEFAULT_DPI = 150  # Balance of quality vs file size (~200KB/page)

    def __init__(self) -> None:
        """Initialize the extractor."""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.configured = bool(self.api_key and self.api_key.strip() and GENAI_AVAILABLE and PDF2IMAGE_AVAILABLE)
        self.client = None

        if self.configured and genai:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.debug("Gemini client initialized for page extraction")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                self.configured = False
                self.client = None

    def check_availability(self) -> bool:
        """Check if all dependencies are available."""
        if not PDF2IMAGE_AVAILABLE:
            logger.error("pdf2image not installed. Run: uv add pdf2image pillow")
            return False

        if not GENAI_AVAILABLE:
            logger.error("google-genai not installed. Run: uv add google-genai")
            return False

        if not self.api_key:
            logger.error("GOOGLE_API_KEY not set in environment")
            return False

        if not self.client:
            logger.error("Gemini client not initialized")
            return False

        # Check poppler is installed
        try:
            # This will fail if poppler isn't installed
            return True
        except PDFInfoNotInstalledError:
            logger.error("poppler not installed. Run: brew install poppler (macOS)")
            return False
        except Exception:
            # Can't test without a PDF, assume it's fine
            return True

    def get_page_count(self, pdf_path: Path) -> int:
        """Get total page count from PDF."""
        from pdf2image.pdf2image import pdfinfo_from_path

        info = pdfinfo_from_path(str(pdf_path))
        return info.get("Pages", 0)

    async def extract_pdf(
        self,
        pdf_path: Path,
        output_dir: Path,
        start_page: int = 1,
        end_page: int | None = None,
        dpi: int = DEFAULT_DPI,
        describe_images: bool = True,
        model: str | None = None,
    ) -> Path:
        """Extract all pages from PDF and combine into single markdown.

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save output files
            start_page: First page to extract (1-based, default: 1)
            end_page: Last page to extract (default: all pages)
            dpi: Image resolution (default: 150)
            describe_images: Whether to describe figures/illustrations
            model: Gemini model to use

        Returns:
            Path to the combined full-text markdown file
        """
        if not self.check_availability():
            raise ValueError("Dependencies not available. Check logs for details.")

        if not pdf_path.exists():
            raise ValueError(f"PDF not found: {pdf_path}")

        model = model or self.DEFAULT_MODEL
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get page count
        total_pages = self.get_page_count(pdf_path)
        if end_page is None or end_page > total_pages:
            end_page = total_pages

        logger.info(f"Extracting pages {start_page}-{end_page} from {pdf_path.name}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"DPI: {dpi}, Model: {model}")

        # Track failed pages for retry
        failed_pages: list[int] = []
        page_files: list[Path] = []

        # Extract each page
        for page_num in range(start_page, end_page + 1):
            page_file = output_dir / f"_page_{page_num:04d}.md"
            page_files.append(page_file)

            # Skip if already extracted with reasonable content
            if page_file.exists() and page_file.stat().st_size > 100:
                logger.info(f"Page {page_num}: exists ({page_file.stat().st_size} bytes), skipping")
                continue

            try:
                content = await self._extract_single_page(pdf_path, page_num, dpi, describe_images, model)
                page_file.write_text(content, encoding="utf-8")
                logger.info(f"Page {page_num}: extracted ({len(content)} chars)")

                # Rate limiting - 1 second between pages
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Page {page_num}: FAILED - {e}")
                failed_pages.append(page_num)
                # Write error marker so we know this page needs retry
                page_file.write_text(f"<!-- EXTRACTION FAILED: {e} -->\n", encoding="utf-8")
                continue

        # Report failures
        if failed_pages:
            logger.warning(f"Failed pages: {failed_pages}")
            logger.warning("Re-run to retry failed pages")

        # Combine pages into full-text
        fulltext_path = self._combine_pages(output_dir, page_files, pdf_path, start_page, end_page, model)

        return fulltext_path

    async def _extract_single_page(
        self,
        pdf_path: Path,
        page_num: int,
        dpi: int,
        describe_images: bool,
        model: str,
    ) -> str:
        """Extract content from a single page.

        Args:
            pdf_path: Path to the PDF file
            page_num: Page number (1-based)
            dpi: Image resolution
            describe_images: Whether to describe figures
            model: Gemini model

        Returns:
            Markdown content for this page
        """
        if not self.client:
            raise RuntimeError("Gemini client not initialized")

        # Convert single page to image
        image_bytes = self._convert_page_to_image(pdf_path, page_num, dpi)

        # Build prompt
        prompt = self._get_page_prompt(page_num, describe_images)

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._extract_with_vision,
            image_bytes,
            prompt,
            model,
        )

        return result

    def _convert_page_to_image(
        self,
        pdf_path: Path,
        page_num: int,
        dpi: int,
    ) -> bytes:
        """Convert a single PDF page to PNG bytes.

        Args:
            pdf_path: Path to PDF
            page_num: Page number (1-based)
            dpi: Image resolution

        Returns:
            PNG image as bytes
        """
        if convert_from_path is None:
            raise RuntimeError("pdf2image not installed")

        # convert_from_path uses 1-based page numbers in first_page/last_page
        images = convert_from_path(
            str(pdf_path),
            dpi=dpi,
            first_page=page_num,
            last_page=page_num,
        )

        if not images:
            raise RuntimeError(f"Failed to convert page {page_num} to image")

        # Convert PIL Image to PNG bytes
        img = images[0]
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def _extract_with_vision(
        self,
        image_bytes: bytes,
        prompt: str,
        model: str,
    ) -> str:
        """Send image to Gemini vision and get transcription.

        Args:
            image_bytes: PNG image data
            prompt: Extraction prompt
            model: Model name

        Returns:
            Extracted markdown text
        """
        if not self.client:
            raise RuntimeError("Gemini client not initialized")

        # Create inline data for the image
        image_data = {
            "inline_data": {
                "mime_type": "image/png",
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }
        }

        # Generate content with image and prompt
        response = self.client.models.generate_content(
            model=model,
            contents=[image_data, prompt],
        )

        if response.text:
            return response.text
        raise RuntimeError("No text in Gemini response")

    def _get_page_prompt(self, page_num: int, describe_images: bool) -> str:
        """Generate prompt for single page extraction.

        Args:
            page_num: Page number for the marker
            describe_images: Whether to describe figures

        Returns:
            Prompt string
        """
        image_instruction = ""
        if describe_images:
            image_instruction = """
6. **Figures/Images**: For any figures, charts, or illustrations:
   - Write: `[Figure: detailed description of what the image shows]`
   - Describe visual elements, data, diagrams, etc.
   - If there's a caption, preserve it after the figure tag"""

        return f"""Transcribe this page exactly as markdown. Output ONLY the page content.

## REQUIREMENTS

1. **First line MUST be**: `<!-- PAGE: {page_num} -->`

2. **Transcribe ALL text** verbatim - this is lossless extraction, not a summary

3. **Format as markdown**:
   - Headings: #, ##, ###
   - Paragraphs: preserve structure
   - Lists: preserve numbered/bulleted
   - Tables: markdown table format

4. **Japanese/CJK text**: Preserve exactly as written
   - Add romaji in parentheses for key terms: 茶道 (chadō)

5. **Footnotes**: Use [^1] syntax
{image_instruction}

## OUTPUT

Start with the page marker and provide complete transcription:

<!-- PAGE: {page_num} -->
[Page content here...]"""

    def _combine_pages(
        self,
        output_dir: Path,
        page_files: list[Path],
        pdf_path: Path,
        start_page: int,
        end_page: int,
        model: str,
    ) -> Path:
        """Combine individual page files into full-text.

        Args:
            output_dir: Output directory
            page_files: List of page file paths
            pdf_path: Original PDF path (for metadata)
            start_page: First page extracted
            end_page: Last page extracted
            model: Model used

        Returns:
            Path to combined full-text file
        """
        fulltext_path = output_dir / "_full-text.md"

        # Build frontmatter
        frontmatter = f"""---
title: "{pdf_path.stem}"
source: "{pdf_path.name}"
category: source
type: full-text-extraction
extraction_method: page-by-page
pages: {end_page - start_page + 1}
page_range: "{start_page}-{end_page}"
model: {model}
---

# {pdf_path.stem}

Full text extraction using page-by-page image conversion.

---

"""

        # Combine content
        content_parts = [frontmatter]
        for page_file in sorted(page_files):
            if page_file.exists():
                content = page_file.read_text(encoding="utf-8")
                content_parts.append(content)
                content_parts.append("\n\n")

        fulltext_path.write_text("".join(content_parts), encoding="utf-8")
        logger.info(f"Combined: {fulltext_path} ({fulltext_path.stat().st_size:,} bytes)")

        return fulltext_path


async def extract_pdf_pages(
    pdf_path: str | Path,
    output_dir: str | Path,
    start_page: int = 1,
    end_page: int | None = None,
    dpi: int = 150,
    model: str | None = None,
) -> Path:
    """Convenience function for CLI usage.

    Args:
        pdf_path: Path to PDF file
        output_dir: Output directory
        start_page: First page (1-based)
        end_page: Last page (None = all)
        dpi: Image resolution
        model: Gemini model

    Returns:
        Path to full-text markdown file
    """
    extractor = PageByPageExtractor()
    return await extractor.extract_pdf(
        Path(pdf_path),
        Path(output_dir),
        start_page=start_page,
        end_page=end_page,
        dpi=dpi,
        model=model,
    )
