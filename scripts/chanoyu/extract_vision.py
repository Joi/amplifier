#!/usr/bin/env python3
"""
Google Cloud Vision PDF Extractor for Mixed-Language Documents.

Google Cloud Vision API excels at:
- Mixed English/Japanese content
- Horizontal text layouts
- Documents with multiple languages
- English-only documents

This script:
1. Converts PDF pages to images
2. Runs Vision API document_text_detection on each page
3. Combines into full-text with proper page ordering

Usage:
    uv run python scripts/chanoyu/extract_vision.py \
        /path/to/input.pdf \
        /path/to/output/dir

Author: Claude (Amplifier)
Date: 2026-01-03
"""

import argparse
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PageResult:
    """Result from extracting a single page."""

    page_num: int
    text: str
    confidence: float | None = None
    success: bool = True
    error: str | None = None


class VisionExtractor:
    """Extract text from PDFs using Google Cloud Vision API."""

    def __init__(self) -> None:
        """Initialize the extractor."""
        self._client = None

    @property
    def client(self):
        """Lazy-load Vision client."""
        if self._client is None:
            from google.cloud import vision
            self._client = vision.ImageAnnotatorClient()
        return self._client

    def check_availability(self) -> bool:
        """Check if Vision API is available."""
        try:
            # Try to import and create client
            from google.cloud import vision
            client = vision.ImageAnnotatorClient()
            return True
        except Exception as e:
            logger.error(f"Vision API not available: {e}")
            logger.error(
                "Setup instructions:\n"
                "  1. Install gcloud CLI: brew install google-cloud-sdk\n"
                "  2. Authenticate: gcloud auth application-default login\n"
                "  3. Enable API: gcloud services enable vision.googleapis.com"
            )
            return False

    def _convert_pdf_to_images(
        self,
        pdf_path: Path,
        temp_dir: Path,
        dpi: int = 200,
        start_page: int = 1,
        end_page: int | None = None,
    ) -> list[Path]:
        """Convert PDF pages to PNG images using pdftoppm."""
        cmd = [
            "pdftoppm",
            "-png",
            "-r", str(dpi),
            "-f", str(start_page),
        ]

        if end_page:
            cmd.extend(["-l", str(end_page)])

        cmd.extend([str(pdf_path), str(temp_dir / "page")])

        logger.info(f"Converting PDF to images (dpi={dpi})...")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"pdftoppm failed: {result.stderr}")

        # Find generated images
        images = sorted(temp_dir.glob("page-*.png"))
        logger.info(f"Generated {len(images)} page images")

        return images

    def _extract_page(self, image_path: Path, page_num: int) -> PageResult:
        """Extract text from a single page image."""
        from google.cloud import vision

        try:
            with open(image_path, "rb") as f:
                content = f.read()

            image = vision.Image(content=content)
            response = self.client.document_text_detection(image=image)

            if response.error.message:
                return PageResult(
                    page_num=page_num,
                    text="",
                    success=False,
                    error=response.error.message,
                )

            text = response.full_text_annotation.text if response.full_text_annotation else ""

            # Calculate average confidence if available
            confidence = None
            if response.full_text_annotation and response.full_text_annotation.pages:
                confidences = []
                for page in response.full_text_annotation.pages:
                    for block in page.blocks:
                        if block.confidence:
                            confidences.append(block.confidence)
                if confidences:
                    confidence = sum(confidences) / len(confidences)

            return PageResult(
                page_num=page_num,
                text=text,
                confidence=confidence,
                success=True,
            )

        except Exception as e:
            return PageResult(
                page_num=page_num,
                text="",
                success=False,
                error=str(e),
            )

    def extract_pdf(
        self,
        pdf_path: Path,
        output_dir: Path,
        start_page: int = 1,
        end_page: int | None = None,
        dpi: int = 200,
    ) -> Path:
        """Extract text from PDF using Google Cloud Vision.

        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory
            start_page: First page (1-based)
            end_page: Last page (None = all)
            dpi: Image resolution

        Returns:
            Path to combined full-text markdown
        """
        if not self.check_availability():
            raise ValueError("Vision API not available")

        if not pdf_path.exists():
            raise ValueError(f"PDF not found: {pdf_path}")

        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"PDF: {pdf_path.name}")
        logger.info(f"Output: {output_dir}")

        # Convert PDF to images in temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            images = self._convert_pdf_to_images(
                pdf_path,
                temp_path,
                dpi=dpi,
                start_page=start_page,
                end_page=end_page,
            )

            if not images:
                raise RuntimeError("No images generated from PDF")

            # Extract text from each page
            pages: list[PageResult] = []

            for i, image_path in enumerate(images, start=1):
                logger.info(f"Extracting page {i}/{len(images)}...")
                result = self._extract_page(image_path, i)

                if result.success:
                    logger.info(f"  Page {i}: {len(result.text)} chars")
                    if result.confidence:
                        logger.info(f"  Confidence: {result.confidence:.2%}")
                else:
                    logger.warning(f"  Page {i} failed: {result.error}")

                pages.append(result)

                # Save individual page
                page_file = output_dir / f"_page_{i:04d}.md"
                page_content = f"<!-- PAGE: {i} -->\n{result.text}"
                page_file.write_text(page_content, encoding="utf-8")

        # Combine into full text
        fulltext_path = self._combine_pages(output_dir, pages, pdf_path)

        return fulltext_path

    def _combine_pages(
        self,
        output_dir: Path,
        pages: list[PageResult],
        pdf_path: Path,
    ) -> Path:
        """Combine extracted pages into full-text markdown."""
        fulltext_path = output_dir / "_full-text.md"

        successful_pages = sum(1 for p in pages if p.success)
        avg_confidence = None
        confidences = [p.confidence for p in pages if p.confidence is not None]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)

        frontmatter = f"""---
title: "{pdf_path.stem}"
source: "{pdf_path.name}"
category: source
type: full-text-extraction
extraction_method: google-cloud-vision
pages: {len(pages)}
successful_pages: {successful_pages}
"""
        if avg_confidence:
            frontmatter += f"average_confidence: {avg_confidence:.2%}\n"

        frontmatter += f"""---

# {pdf_path.stem}

Full text extraction using Google Cloud Vision API.

**Extraction method**: Google Cloud Vision (document_text_detection)
**Pages extracted**: {successful_pages}/{len(pages)}

---

"""

        content_parts = [frontmatter]
        for result in sorted(pages, key=lambda p: p.page_num):
            content_parts.append(f"<!-- PAGE: {result.page_num} -->\n")
            content_parts.append(result.text)
            content_parts.append("\n\n")

        fulltext_path.write_text("".join(content_parts), encoding="utf-8")
        logger.info(f"Combined: {fulltext_path} ({fulltext_path.stat().st_size:,} bytes)")

        return fulltext_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract text from PDFs using Google Cloud Vision API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Google Cloud Vision advantages:
  - Excellent for mixed English/Japanese content
  - Good for horizontal text layouts
  - Works with English-only documents
  - Provides confidence scores

For pure Japanese vertical text (縦書き), use extract_yomitoku.py instead.

Examples:
  # Extract English or mixed-language PDF
  uv run python scripts/chanoyu/extract_vision.py \\
      ~/Media/article.pdf \\
      ~/output/

  # Extract specific page range
  uv run python scripts/chanoyu/extract_vision.py \\
      ~/Media/article.pdf \\
      ~/output/ \\
      --start-page 1 --end-page 10
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

    args = parser.parse_args()

    extractor = VisionExtractor()

    try:
        fulltext_path = extractor.extract_pdf(
            args.pdf_path,
            args.output_dir,
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
