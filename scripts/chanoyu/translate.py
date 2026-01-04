#!/usr/bin/env python3
"""
DeepL Translation Utility for Chanoyu Documents.

Provides translation services using DeepL API, with special handling for:
- Japanese → English translation
- Preserving markdown formatting
- Chunking large documents to stay within API limits

Usage:
    # Translate a file
    uv run python scripts/chanoyu/translate.py input.md output.md

    # Translate with specific languages
    uv run python scripts/chanoyu/translate.py input.md output.md --source JA --target EN-US

Author: Claude (Amplifier)
Date: 2026-01-03
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from amplifier.utils.logger import get_logger
from amplifier.utils.secrets import get_deepl_api_key

logger = get_logger(__name__)

# DeepL API limits
MAX_CHARS_PER_REQUEST = 50000  # Conservative limit (actual is higher)


@dataclass
class TranslationResult:
    """Result of a translation operation."""

    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    chars_used: int
    success: bool
    error: str | None = None


def get_deepl_key() -> str:
    """Get DeepL API key from unified secrets cache or environment."""
    import os

    # Check environment first
    key = os.environ.get("DEEPL_AUTH_KEY")
    if key:
        return key

    # Use unified secrets cache (falls back to 1Password)
    try:
        return get_deepl_api_key()
    except RuntimeError as e:
        raise ValueError(
            "DeepL API key not found. Set DEEPL_AUTH_KEY environment variable "
            f"or ensure 1Password CLI is configured: {e}"
        ) from e


class DeepLTranslator:
    """Translator using DeepL API."""

    def __init__(self, auth_key: str | None = None) -> None:
        """Initialize translator with API key."""
        self.auth_key = auth_key or get_deepl_key()
        self._translator = None

    @property
    def translator(self):
        """Lazy-load DeepL translator."""
        if self._translator is None:
            import deepl
            self._translator = deepl.Translator(self.auth_key)
        return self._translator

    def translate_text(
        self,
        text: str,
        source_lang: str = "JA",
        target_lang: str = "EN-US",
        preserve_formatting: bool = True,
    ) -> TranslationResult:
        """Translate text using DeepL.

        Args:
            text: Text to translate
            source_lang: Source language code (e.g., "JA", "EN")
            target_lang: Target language code (e.g., "EN-US", "JA")
            preserve_formatting: Whether to preserve markdown formatting

        Returns:
            TranslationResult with translated text
        """
        if not text.strip():
            return TranslationResult(
                source_text=text,
                translated_text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                chars_used=0,
                success=True,
            )

        try:
            result = self.translator.translate_text(
                text,
                source_lang=source_lang,
                target_lang=target_lang,
                preserve_formatting=preserve_formatting,
            )

            return TranslationResult(
                source_text=text,
                translated_text=result.text,
                source_lang=source_lang,
                target_lang=target_lang,
                chars_used=len(text),
                success=True,
            )

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return TranslationResult(
                source_text=text,
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                chars_used=0,
                success=False,
                error=str(e),
            )

    def translate_markdown(
        self,
        markdown_text: str,
        source_lang: str = "JA",
        target_lang: str = "EN-US",
    ) -> TranslationResult:
        """Translate markdown while preserving structure.

        Handles:
        - YAML frontmatter (preserved, not translated)
        - Page markers (<!-- PAGE: X --> preserved)
        - Headers, lists, tables (structure preserved)

        Args:
            markdown_text: Full markdown document
            source_lang: Source language
            target_lang: Target language

        Returns:
            TranslationResult with translated markdown
        """
        lines = markdown_text.split("\n")
        translated_lines = []
        in_frontmatter = False
        frontmatter_count = 0
        total_chars = 0

        i = 0
        while i < len(lines):
            line = lines[i]

            # Handle YAML frontmatter
            if line.strip() == "---":
                frontmatter_count += 1
                if frontmatter_count == 1:
                    in_frontmatter = True
                elif frontmatter_count == 2:
                    in_frontmatter = False
                translated_lines.append(line)
                i += 1
                continue

            if in_frontmatter:
                translated_lines.append(line)
                i += 1
                continue

            # Preserve page markers
            if line.strip().startswith("<!-- PAGE:"):
                translated_lines.append(line)
                i += 1
                continue

            # Preserve empty lines
            if not line.strip():
                translated_lines.append(line)
                i += 1
                continue

            # Preserve code blocks
            if line.strip().startswith("```"):
                translated_lines.append(line)
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    translated_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    translated_lines.append(lines[i])
                i += 1
                continue

            # Collect paragraph/content block for translation
            block_lines = []
            while i < len(lines):
                current = lines[i]
                # Stop at structural elements
                if (current.strip() == "" or
                    current.strip().startswith("<!-- ") or
                    current.strip() == "---" or
                    current.strip().startswith("```")):
                    break
                block_lines.append(current)
                i += 1

            if block_lines:
                block_text = "\n".join(block_lines)
                result = self.translate_text(
                    block_text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    preserve_formatting=True,
                )

                if result.success:
                    translated_lines.append(result.translated_text)
                    total_chars += result.chars_used
                else:
                    # Keep original if translation fails
                    translated_lines.append(block_text)
                    logger.warning(f"Block translation failed: {result.error}")

        return TranslationResult(
            source_text=markdown_text,
            translated_text="\n".join(translated_lines),
            source_lang=source_lang,
            target_lang=target_lang,
            chars_used=total_chars,
            success=True,
        )

    def translate_file(
        self,
        input_path: Path,
        output_path: Path,
        source_lang: str = "JA",
        target_lang: str = "EN-US",
    ) -> TranslationResult:
        """Translate a markdown file.

        Args:
            input_path: Path to input file
            output_path: Path for translated output
            source_lang: Source language
            target_lang: Target language

        Returns:
            TranslationResult
        """
        if not input_path.exists():
            raise ValueError(f"Input file not found: {input_path}")

        logger.info(f"Translating: {input_path.name}")
        logger.info(f"Direction: {source_lang} → {target_lang}")

        content = input_path.read_text(encoding="utf-8")
        result = self.translate_markdown(content, source_lang, target_lang)

        if result.success:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.translated_text, encoding="utf-8")
            logger.info(f"Saved: {output_path}")
            logger.info(f"Characters translated: {result.chars_used:,}")

        return result

    def get_usage(self) -> dict:
        """Get API usage statistics."""
        usage = self.translator.get_usage()
        return {
            "character_count": usage.character.count,
            "character_limit": usage.character.limit,
            "percent_used": usage.character.count / usage.character.limit * 100
            if usage.character.limit
            else 0,
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Translate documents using DeepL API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Language codes:
  Source: JA (Japanese), EN (English), ZH (Chinese), etc.
  Target: EN-US, EN-GB, JA, ZH, etc.

Examples:
  # Translate Japanese markdown to English
  uv run python scripts/chanoyu/translate.py input.md output.md

  # Translate with explicit languages
  uv run python scripts/chanoyu/translate.py input.md output.md --source JA --target EN-US

  # Check API usage
  uv run python scripts/chanoyu/translate.py --usage
""",
    )

    parser.add_argument("input", type=Path, nargs="?", help="Input file path")
    parser.add_argument("output", type=Path, nargs="?", help="Output file path")
    parser.add_argument(
        "--source",
        type=str,
        default="JA",
        help="Source language (default: JA)",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="EN-US",
        help="Target language (default: EN-US)",
    )
    parser.add_argument(
        "--usage",
        action="store_true",
        help="Show API usage statistics",
    )

    args = parser.parse_args()

    translator = DeepLTranslator()

    if args.usage:
        usage = translator.get_usage()
        print(f"DeepL API Usage:")
        print(f"  Characters: {usage['character_count']:,} / {usage['character_limit']:,}")
        print(f"  Used: {usage['percent_used']:.2f}%")
        return

    if not args.input or not args.output:
        parser.error("Both input and output paths are required")

    try:
        result = translator.translate_file(
            args.input,
            args.output,
            source_lang=args.source,
            target_lang=args.target,
        )

        if result.success:
            print(f"\n✅ Translation complete: {args.output}")
            print(f"   Characters: {result.chars_used:,}")
        else:
            print(f"\n❌ Translation failed: {result.error}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Translation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
