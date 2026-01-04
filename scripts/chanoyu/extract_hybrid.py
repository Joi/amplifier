#!/usr/bin/env python3
"""
Hybrid PDF Extractor with 3-Tier Intelligent Routing.

Routes documents to the appropriate extraction backend using two-stage detection:

TIER 1 - Language Detection:
- **English/Mixed** → Google Cloud Vision (fast, cheap)
- **Japanese** → TIER 2

TIER 2 - Layout Complexity Detection:
- **Simple layout** → YomiToku (free, fast, good for single-column)
- **Multi-column/Complex** → Gemini 3 Flash (best quality, slower, costs money)

Layout complexity is detected via:
1. Manual hint (--layout multi-column)
2. Known difficult sources (jikunyu-raku, tousetsu journals)
3. PDF aspect ratio (book spreads are wider than single pages)

Optional: Translate Japanese content to English using DeepL API.

Usage:
    # Auto-detect language and layout, route appropriately
    uv run python scripts/chanoyu/extract_hybrid.py \
        /path/to/input.pdf \
        /path/to/output/dir

    # Force specific backend
    uv run python scripts/chanoyu/extract_hybrid.py \
        /path/to/input.pdf \
        /path/to/output/dir \
        --backend gemini

    # Hint that this is a multi-column document
    uv run python scripts/chanoyu/extract_hybrid.py \
        /path/to/input.pdf \
        /path/to/output/dir \
        --layout multi-column

    # Extract and translate Japanese to English
    uv run python scripts/chanoyu/extract_hybrid.py \
        /path/to/input.pdf \
        /path/to/output/dir \
        --translate

Author: Claude (Amplifier)
Date: 2026-01-03 (updated 2026-01-04 for 3-tier routing)
"""

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


class ExtractionBackend(Enum):
    """Available extraction backends."""
    YOMITOKU = "yomitoku"  # Japanese vertical text, simple layouts
    VISION = "vision"      # English/mixed content
    GEMINI = "gemini"      # Multi-column Japanese, complex layouts
    AUTO = "auto"          # Auto-detect


class LayoutComplexity(Enum):
    """Layout complexity for Japanese documents."""
    SIMPLE = "simple"           # Single column, standard layout → YomiToku
    MULTI_COLUMN = "multi"      # Multiple columns, book spreads → Gemini 3
    UNKNOWN = "unknown"         # Can't determine → default to simple


# Known filenames/patterns that are ALWAYS multi-column and need Gemini 3
# Be specific - use filenames, not broad directory names
KNOWN_MULTI_COLUMN_SOURCES = [
    "tousetsu_2000-07",  # Specific journal issue we tested - 3-column
    "tousetsu_",         # Tousetsu journal articles are typically multi-column
    # Add more specific filenames as discovered
]


@dataclass
class LanguageAnalysis:
    """Result of language analysis on a document sample."""

    total_chars: int
    japanese_chars: int
    english_chars: int
    other_chars: int
    japanese_ratio: float
    english_ratio: float
    has_vertical_text_indicators: bool
    recommended_backend: ExtractionBackend
    confidence: str  # "high", "medium", "low"
    reason: str


class HybridExtractor:
    """Hybrid PDF extractor with language-based routing."""

    # Japanese character ranges (hiragana, katakana, kanji)
    JAPANESE_PATTERN = re.compile(
        r'[\u3040-\u309F'  # Hiragana
        r'\u30A0-\u30FF'   # Katakana
        r'\u4E00-\u9FFF'   # CJK Unified Ideographs (Kanji)
        r'\u3400-\u4DBF'   # CJK Extension A
        r'\uF900-\uFAFF]'  # CJK Compatibility Ideographs
    )

    # ASCII letters (English)
    ENGLISH_PATTERN = re.compile(r'[a-zA-Z]')

    # Vertical text indicators in Japanese
    VERTICAL_INDICATORS = [
        "縦書き", "たてがき", "右から左",
        # Common patterns in vertical text metadata
    ]

    def __init__(self) -> None:
        """Initialize the extractor."""
        self._yomitoku_extractor = None
        self._vision_extractor = None
        self._gemini_extractor = None

    @property
    def yomitoku_extractor(self):
        """Lazy-load YomiToku extractor."""
        if self._yomitoku_extractor is None:
            from scripts.chanoyu.extract_yomitoku import YomiTokuExtractor
            self._yomitoku_extractor = YomiTokuExtractor()
        return self._yomitoku_extractor

    @property
    def vision_extractor(self):
        """Lazy-load Vision extractor."""
        if self._vision_extractor is None:
            from scripts.chanoyu.extract_vision import VisionExtractor
            self._vision_extractor = VisionExtractor()
        return self._vision_extractor

    @property
    def gemini_extractor(self):
        """Lazy-load Gemini 3 Flash extractor."""
        if self._gemini_extractor is None:
            from scripts.chanoyu.extract_gemini import GeminiExtractor
            self._gemini_extractor = GeminiExtractor()
        return self._gemini_extractor

    def _get_pdf_dimensions(self, pdf_path: Path) -> tuple[float, float]:
        """Get PDF page dimensions using pdfinfo."""
        try:
            result = subprocess.run(
                ["pdfinfo", str(pdf_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Page size:"):
                        # Parse "Page size:      841.89 x 595.28 pts"
                        parts = line.split(":")[1].strip()
                        dims = parts.split("x")
                        if len(dims) >= 2:
                            width = float(dims[0].strip().split()[0])
                            height = float(dims[1].strip().split()[0])
                            return width, height
        except Exception as e:
            logger.debug(f"Could not get PDF dimensions: {e}")
        return 0, 0

    def detect_layout_complexity(
        self,
        pdf_path: Path,
        layout_hint: str = "auto",
    ) -> LayoutComplexity:
        """Detect layout complexity for Japanese documents.

        Args:
            pdf_path: Path to PDF
            layout_hint: Manual hint ("auto", "simple", "multi-column")

        Returns:
            LayoutComplexity indicating whether Gemini 3 is needed
        """
        # 1. Manual override takes priority
        if layout_hint == "multi-column":
            logger.info("Layout: multi-column (manual hint)")
            return LayoutComplexity.MULTI_COLUMN
        if layout_hint == "simple":
            logger.info("Layout: simple (manual hint)")
            return LayoutComplexity.SIMPLE

        # 2. Known difficult sources
        pdf_str = str(pdf_path).lower()
        for source in KNOWN_MULTI_COLUMN_SOURCES:
            if source.lower() in pdf_str:
                logger.info(f"Layout: multi-column (known source: {source})")
                return LayoutComplexity.MULTI_COLUMN

        # 3. Dimension-based detection (book spreads are wider)
        width, height = self._get_pdf_dimensions(pdf_path)
        if width > 0 and height > 0:
            aspect_ratio = width / height
            if aspect_ratio > 1.3:
                # Wide pages = likely book spread with multiple columns
                logger.info(f"Layout: multi-column (aspect ratio: {aspect_ratio:.2f})")
                return LayoutComplexity.MULTI_COLUMN
            else:
                logger.info(f"Layout: simple (aspect ratio: {aspect_ratio:.2f})")
                return LayoutComplexity.SIMPLE

        # 4. Default to simple (saves cost)
        logger.info("Layout: simple (default)")
        return LayoutComplexity.SIMPLE

    def _get_sample_text(self, pdf_path: Path, sample_page: int = 1) -> str:
        """Extract sample text from a PDF page for language analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Convert sample page to image
            image_path = temp_path / "sample.png"
            cmd = [
                "pdftoppm", "-png",
                "-f", str(sample_page),
                "-l", str(sample_page),
                "-singlefile",
                str(pdf_path),
                str(temp_path / "sample"),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Failed to convert sample page: {result.stderr}")
                return ""

            # Use Vision API for initial analysis (quick and universal)
            try:
                from google.cloud import vision
                client = vision.ImageAnnotatorClient()

                with open(image_path, "rb") as f:
                    content = f.read()

                image = vision.Image(content=content)
                response = client.document_text_detection(image=image)

                if response.full_text_annotation:
                    return response.full_text_annotation.text
                return ""

            except Exception as e:
                logger.warning(f"Vision API sample failed: {e}")
                return ""

    def analyze_language(self, pdf_path: Path, sample_page: int = 2) -> LanguageAnalysis:
        """Analyze the language composition of a document.

        Args:
            pdf_path: Path to PDF
            sample_page: Page to sample (default 2 to skip title pages)

        Returns:
            LanguageAnalysis with recommendation
        """
        logger.info(f"Analyzing language in {pdf_path.name} (page {sample_page})...")

        sample_text = self._get_sample_text(pdf_path, sample_page)

        if not sample_text:
            # Can't analyze - default to Vision (more universal)
            return LanguageAnalysis(
                total_chars=0,
                japanese_chars=0,
                english_chars=0,
                other_chars=0,
                japanese_ratio=0,
                english_ratio=0,
                has_vertical_text_indicators=False,
                recommended_backend=ExtractionBackend.VISION,
                confidence="low",
                reason="Could not extract sample text for analysis",
            )

        # Count characters by type
        total = len(sample_text)
        japanese = len(self.JAPANESE_PATTERN.findall(sample_text))
        english = len(self.ENGLISH_PATTERN.findall(sample_text))
        other = total - japanese - english

        japanese_ratio = japanese / total if total > 0 else 0
        english_ratio = english / total if total > 0 else 0

        # Check for vertical text indicators
        has_vertical = any(ind in sample_text for ind in self.VERTICAL_INDICATORS)

        # Decision logic
        if japanese_ratio >= 0.7:
            # Predominantly Japanese
            backend = ExtractionBackend.YOMITOKU
            confidence = "high"
            reason = f"Pure Japanese ({japanese_ratio:.0%} Japanese characters)"
        elif japanese_ratio >= 0.4 and english_ratio >= 0.2:
            # Mixed content
            backend = ExtractionBackend.VISION
            confidence = "high"
            reason = f"Mixed language ({japanese_ratio:.0%} Japanese, {english_ratio:.0%} English)"
        elif english_ratio >= 0.5:
            # Predominantly English
            backend = ExtractionBackend.VISION
            confidence = "high"
            reason = f"Predominantly English ({english_ratio:.0%} English)"
        elif japanese_ratio >= 0.3:
            # Some Japanese - use YomiToku for better vertical text handling
            backend = ExtractionBackend.YOMITOKU
            confidence = "medium"
            reason = f"Moderate Japanese ({japanese_ratio:.0%}), may have vertical text"
        else:
            # Default to Vision
            backend = ExtractionBackend.VISION
            confidence = "medium"
            reason = "General content, using Vision API"

        # Override for vertical text
        if has_vertical and backend == ExtractionBackend.VISION:
            backend = ExtractionBackend.YOMITOKU
            reason += " (vertical text detected)"

        return LanguageAnalysis(
            total_chars=total,
            japanese_chars=japanese,
            english_chars=english,
            other_chars=other,
            japanese_ratio=japanese_ratio,
            english_ratio=english_ratio,
            has_vertical_text_indicators=has_vertical,
            recommended_backend=backend,
            confidence=confidence,
            reason=reason,
        )

    def extract_pdf(
        self,
        pdf_path: Path,
        output_dir: Path,
        backend: ExtractionBackend = ExtractionBackend.AUTO,
        layout_hint: str = "auto",
        start_page: int = 1,
        end_page: int | None = None,
        dpi: int = 200,
        sample_page: int = 2,
        translate: bool = False,
        target_lang: str = "EN-US",
    ) -> tuple[Path, Path | None]:
        """Extract text from PDF using appropriate backend.

        Uses 3-tier routing:
        1. Language detection → English/Mixed → Vision
        2. Layout complexity → Simple Japanese → YomiToku
        3. Layout complexity → Multi-column Japanese → Gemini 3 Flash

        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory
            backend: Extraction backend (auto, yomitoku, vision, gemini)
            layout_hint: Layout hint for Japanese docs ("auto", "simple", "multi-column")
            start_page: First page (1-based)
            end_page: Last page (None = all)
            dpi: Image resolution
            sample_page: Page to sample for auto-detection
            translate: Whether to translate Japanese content to English
            target_lang: Target language for translation (default: EN-US)

        Returns:
            Tuple of (fulltext_path, translated_path or None)
        """
        if not pdf_path.exists():
            raise ValueError(f"PDF not found: {pdf_path}")

        # Determine backend
        if backend == ExtractionBackend.AUTO:
            # TIER 1: Language detection
            analysis = self.analyze_language(pdf_path, sample_page)
            logger.info(f"Language analysis: {analysis.reason}")
            logger.info(f"  Japanese: {analysis.japanese_ratio:.0%}")
            logger.info(f"  English: {analysis.english_ratio:.0%}")

            if analysis.recommended_backend == ExtractionBackend.VISION:
                # English or mixed → Vision
                actual_backend = ExtractionBackend.VISION
                logger.info(f"  TIER 1 routing: Vision (English/Mixed)")
            else:
                # Japanese → TIER 2: Layout complexity
                layout = self.detect_layout_complexity(pdf_path, layout_hint)

                if layout == LayoutComplexity.MULTI_COLUMN:
                    actual_backend = ExtractionBackend.GEMINI
                    logger.info(f"  TIER 2 routing: Gemini 3 (multi-column)")
                else:
                    actual_backend = ExtractionBackend.YOMITOKU
                    logger.info(f"  TIER 2 routing: YomiToku (simple layout)")
        else:
            actual_backend = backend
            logger.info(f"Using forced backend: {actual_backend.value}")

        # Route to appropriate extractor with fallbacks
        if actual_backend == ExtractionBackend.GEMINI:
            if not self.gemini_extractor.check_availability():
                logger.warning("Gemini API not available, falling back to YomiToku")
                actual_backend = ExtractionBackend.YOMITOKU

        if actual_backend == ExtractionBackend.YOMITOKU:
            if not self.yomitoku_extractor.check_availability():
                logger.warning("YomiToku not available, falling back to Vision")
                actual_backend = ExtractionBackend.VISION

        # Execute extraction
        if actual_backend == ExtractionBackend.GEMINI:
            fulltext_path = self.gemini_extractor.extract_pdf(
                pdf_path,
                output_dir,
                start_page=start_page,
                end_page=end_page,
                dpi=dpi,
            )
        elif actual_backend == ExtractionBackend.YOMITOKU:
            from scripts.chanoyu.extract_yomitoku import ReadingOrder
            fulltext_path = self.yomitoku_extractor.extract_pdf(
                pdf_path,
                output_dir,
                reading_order=ReadingOrder.JAPANESE_BOOK_SPREAD,
                start_page=start_page,
                end_page=end_page,
                dpi=dpi,
            )
        else:
            fulltext_path = self.vision_extractor.extract_pdf(
                pdf_path,
                output_dir,
                start_page=start_page,
                end_page=end_page,
                dpi=dpi,
            )

        # Translate if requested
        translated_path = None
        if translate:
            logger.info(f"Translating extracted text to {target_lang}...")
            from scripts.chanoyu.translate import DeepLTranslator

            translator = DeepLTranslator()
            translated_path = fulltext_path.parent / "_full-text-en.md"

            result = translator.translate_file(
                fulltext_path,
                translated_path,
                source_lang="JA",
                target_lang=target_lang,
            )

            if result.success:
                logger.info(f"Translation saved: {translated_path}")
                logger.info(f"Characters translated: {result.chars_used:,}")
            else:
                logger.error(f"Translation failed: {result.error}")
                translated_path = None

        return fulltext_path, translated_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Hybrid PDF extractor with 3-tier intelligent routing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Extraction backends:
  auto      - 3-tier intelligent routing (default)
  yomitoku  - Japanese vertical text specialist (free, fast)
  vision    - Google Cloud Vision (mixed/English content)
  gemini    - Gemini 3 Flash (multi-column Japanese, best quality)

3-Tier Routing Logic:
  TIER 1 - Language:
    - English/Mixed (>30% English) → Vision
    - Japanese (>70%) → TIER 2

  TIER 2 - Layout Complexity:
    - Simple layout → YomiToku (free)
    - Multi-column/book spread → Gemini 3 Flash ($)

Layout Detection:
  - Manual hint (--layout multi-column)
  - Known sources (tousetsu_ journals)
  - Aspect ratio (wide pages = book spreads)

Examples:
  # Auto-detect language and layout
  uv run python scripts/chanoyu/extract_hybrid.py \\
      ~/Media/document.pdf \\
      ~/output/

  # Force Gemini 3 for complex multi-column
  uv run python scripts/chanoyu/extract_hybrid.py \\
      ~/Media/journal.pdf \\
      ~/output/ \\
      --backend gemini

  # Hint that this is multi-column (triggers Gemini 3)
  uv run python scripts/chanoyu/extract_hybrid.py \\
      ~/Media/japanese-book.pdf \\
      ~/output/ \\
      --layout multi-column

  # Force YomiToku for simple Japanese
  uv run python scripts/chanoyu/extract_hybrid.py \\
      ~/Media/simple-text.pdf \\
      ~/output/ \\
      --backend yomitoku

  # Extract and translate to English
  uv run python scripts/chanoyu/extract_hybrid.py \\
      ~/Media/japanese-book.pdf \\
      ~/output/ \\
      --translate
""",
    )

    parser.add_argument("pdf_path", type=Path, help="Path to PDF file")
    parser.add_argument("output_dir", type=Path, help="Output directory")
    parser.add_argument(
        "--backend",
        type=str,
        choices=["auto", "yomitoku", "vision", "gemini"],
        default="auto",
        help="Extraction backend (default: auto = 3-tier routing)",
    )
    parser.add_argument(
        "--layout",
        type=str,
        choices=["auto", "simple", "multi-column"],
        default="auto",
        help="Layout hint for Japanese docs (default: auto-detect)",
    )
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
        "--sample-page",
        type=int,
        default=2,
        help="Page to sample for language detection (default: 2)",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Translate Japanese content to English using DeepL",
    )
    parser.add_argument(
        "--target-lang",
        type=str,
        default="EN-US",
        help="Target language for translation (default: EN-US)",
    )

    args = parser.parse_args()

    # Map backend string to enum
    backend_map = {
        "auto": ExtractionBackend.AUTO,
        "yomitoku": ExtractionBackend.YOMITOKU,
        "vision": ExtractionBackend.VISION,
        "gemini": ExtractionBackend.GEMINI,
    }
    backend = backend_map[args.backend]

    extractor = HybridExtractor()

    try:
        fulltext_path, translated_path = extractor.extract_pdf(
            args.pdf_path,
            args.output_dir,
            backend=backend,
            layout_hint=args.layout,
            start_page=args.start_page,
            end_page=args.end_page,
            dpi=args.dpi,
            sample_page=args.sample_page,
            translate=args.translate,
            target_lang=args.target_lang,
        )

        print(f"\n✅ Extraction complete: {fulltext_path}")
        print(f"   Size: {fulltext_path.stat().st_size:,} bytes")

        if translated_path:
            print(f"\n✅ Translation complete: {translated_path}")
            print(f"   Size: {translated_path.stat().st_size:,} bytes")

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
