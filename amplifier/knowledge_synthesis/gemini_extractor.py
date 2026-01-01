"""
Gemini API client for PDF book extraction.

Uses Google's Gemini API to extract knowledge from large PDF books,
leveraging Gemini's large context window (1M+ tokens).

Enhancements (Dec 2025):
- Page count validation to catch missing pages
- NDL metadata integration
- Improved furigana handling
- Structural element preservation (diagrams, family trees)
"""

import asyncio
import json
import os
import re
from pathlib import Path

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)

# Import google-genai (optional dependency)
try:
    from google import genai  # type: ignore[import-untyped]
    from google.genai import types  # type: ignore[import-untyped]

    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]
    GENAI_AVAILABLE = False


class GeminiPdfExtractor:
    """Client for extracting knowledge from PDFs using Gemini API."""

    # Gemini 2.5 Flash - latest stable model with improved accuracy and reduced hallucinations
    # Updated Dec 2025: gemini-2.5-flash is the recommended production model
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self) -> None:
        """Initialize the Gemini client."""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.configured = bool(self.api_key and self.api_key.strip() and GENAI_AVAILABLE)
        self.client = None

        if self.configured and genai:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.debug("Gemini client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                self.configured = False
                self.client = None

    def check_availability(self) -> bool:
        """Check if Gemini API is configured and available."""
        if not GENAI_AVAILABLE:
            logger.error("google-genai package not installed. Run: uv add google-genai")
            return False

        if not self.api_key:
            logger.error("GOOGLE_API_KEY not set. Set it in your environment.")
            return False

        if not self.client:
            logger.error("Gemini client not initialized.")
            return False

        return True

    def load_ndl_metadata(self, source_dir: Path) -> dict | None:
        """Load NDL (National Diet Library) metadata if available.

        Args:
            source_dir: Directory containing ndl.json

        Returns:
            Metadata dict or None if not found
        """
        ndl_file = source_dir / "ndl.json"
        if ndl_file.exists():
            try:
                metadata = json.loads(ndl_file.read_text(encoding="utf-8"))
                logger.info(f"Loaded NDL metadata: {metadata.get('title', [{}])[0].get('value', 'Unknown')}")
                return metadata
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse ndl.json: {e}")
        return None

    def validate_page_extraction(
        self,
        text: str,
        expected_pages: int | None = None,
    ) -> tuple[bool, list[str]]:
        """Validate extracted text for completeness.

        Args:
            text: Extracted markdown text
            expected_pages: Expected number of pages (if known)

        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        page_pattern = re.compile(r'<!--\s*PAGE:\s*(\d+)\s*-->')
        pages = [int(m.group(1)) for m in page_pattern.finditer(text)]

        if not pages:
            issues.append("No page markers found in extraction")
            return False, issues

        # Check for gaps
        for i in range(1, len(pages)):
            expected = pages[i - 1] + 1
            if pages[i] != expected and pages[i] != pages[i - 1]:
                gap_start = pages[i - 1] + 1
                gap_end = pages[i] - 1
                if gap_start == gap_end:
                    issues.append(f"Missing page: {gap_start}")
                else:
                    issues.append(f"Missing pages: {gap_start}-{gap_end}")

        # Check against expected count
        if expected_pages:
            extracted_pages = len(set(pages))
            if extracted_pages < expected_pages * 0.9:  # Allow 10% tolerance
                issues.append(
                    f"Page count mismatch: extracted {extracted_pages}, expected ~{expected_pages}"
                )

        # Check for duplicates
        seen = set()
        for p in pages:
            if p in seen:
                issues.append(f"Duplicate page marker: {p}")
            seen.add(p)

        is_valid = len(issues) == 0
        if issues:
            logger.warning(f"Page validation issues: {issues}")
        else:
            logger.info(f"Page validation passed: {len(set(pages))} unique pages")

        return is_valid, issues

    def format_ndl_metadata_yaml(self, metadata: dict) -> str:
        """Format NDL metadata as YAML frontmatter.

        Args:
            metadata: NDL metadata dict

        Returns:
            YAML formatted string
        """
        lines = []

        # Title
        if "title" in metadata and metadata["title"]:
            title_entry = metadata["title"][0]
            lines.append(f'title: "{title_entry.get("value", "")}"')
            if "transcription" in title_entry:
                lines.append(f'title_reading: "{title_entry["transcription"]}"')

        # Creator/Author
        if "creator" in metadata and metadata["creator"]:
            creator = metadata["creator"][0]
            lines.append(f'author: "{creator.get("name", "")}"')
            if "transcription" in creator:
                lines.append(f'author_reading: "{creator["transcription"]}"')

        # Publisher
        if "publisher" in metadata and metadata["publisher"]:
            pub = metadata["publisher"][0]
            lines.append(f'publisher: "{pub.get("name", "")}"')
            if "location" in pub:
                lines.append(f'publisher_location: "{pub["location"]}"')

        # Date
        if "date" in metadata:
            lines.append(f'date: "{metadata["date"]}"')
        if "issued" in metadata:
            lines.append(f'year: {metadata["issued"]}')

        # Subject classifications
        if "subject" in metadata:
            subj = metadata["subject"]
            if "NDLSH" in subj:
                lines.append(f'subjects: {subj["NDLSH"]}')
            if "NDC" in subj:
                lines.append(f'ndc: "{subj["NDC"][0]}"')

        # Physical description
        if "extent" in metadata:
            lines.append(f'extent: "{metadata["extent"][0]}"')

        # NDL identifiers
        if "identifier" in metadata:
            if "NDLBibID" in metadata["identifier"]:
                lines.append(f'ndl_bib_id: "{metadata["identifier"]["NDLBibID"][0]}"')

        return "\n".join(lines)

    async def extract_from_file(
        self,
        file_path: Path,
        prompt: str,
        model: str | None = None,
    ) -> str:
        """Extract knowledge from a file (PDF or text) using Gemini.

        Args:
            file_path: Path to the file (PDF, TXT, MD, etc.)
            prompt: The extraction prompt to use
            model: Model to use (default: gemini-2.0-flash)

        Returns:
            Extracted text/markdown from Gemini

        Raises:
            ValueError: If API not configured or file not found
            RuntimeError: If extraction fails
        """
        if not self.check_availability():
            raise ValueError("Gemini API not configured. Set GOOGLE_API_KEY environment variable.")

        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")

        model = model or self.DEFAULT_MODEL

        logger.info(f"Uploading file to Gemini: {file_path.name}")
        logger.info(f"File size: {file_path.stat().st_size / 1024 / 1024:.1f} MB")

        try:
            # Run sync operations in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._extract_sync,
                file_path,
                prompt,
                model,
            )
            return result

        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            raise RuntimeError(f"Gemini extraction failed: {e}") from e

    # Alias for backwards compatibility
    async def extract_from_pdf(
        self,
        pdf_path: Path,
        prompt: str,
        model: str | None = None,
    ) -> str:
        """Extract knowledge from a PDF using Gemini. Alias for extract_from_file."""
        return await self.extract_from_file(pdf_path, prompt, model)

    def _extract_sync(self, file_path: Path, prompt: str, model: str) -> str:
        """Synchronous extraction helper."""
        if not self.client:
            raise RuntimeError("Gemini client not initialized")

        # Upload the file
        logger.info("Uploading file to Gemini File API...")
        uploaded_file = self.client.files.upload(file=str(file_path))
        logger.info(f"Upload complete. File ID: {uploaded_file.name}")

        # Wait for file to be processed (if needed)
        # The File API processes files asynchronously
        file_info = self.client.files.get(name=uploaded_file.name)
        logger.info(f"File state: {file_info.state}")

        # Generate content with the PDF and prompt
        logger.info(f"Sending extraction request to {model}...")

        response = self.client.models.generate_content(
            model=model,
            contents=[
                uploaded_file,
                prompt,
            ],
        )

        # Extract text from response
        if response.text:
            logger.info(f"Extraction complete. Response length: {len(response.text)} chars")
            return response.text
        raise RuntimeError("No text in Gemini response")

    async def extract_fulltext(
        self,
        pdf_path: Path,
        output_dir: Path,
        model: str | None = None,
    ) -> tuple[Path, Path]:
        """Extract full text from a PDF book.

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save output files
            model: Model to use

        Returns:
            Tuple of (book_info_path, fulltext_path)
        """

        # Get the fulltext extraction prompt
        # We need to generate it programmatically
        prompt = self._get_fulltext_prompt()

        # Extract using Gemini
        result = await self.extract_from_pdf(pdf_path, prompt, model)

        # Parse and save the results
        output_dir.mkdir(parents=True, exist_ok=True)

        # Split result into book-info and full-text
        # The prompt asks for these as separate files
        book_info_path = output_dir / "_book-info.md"
        fulltext_path = output_dir / "_full-text.md"

        # Try to split the response into two files
        if "### File 2:" in result or "## File 2:" in result or "_full-text.md" in result:
            # Response contains both files - try to split
            parts = self._split_gemini_response(result)
            book_info_path.write_text(parts.get("book_info", result))
            if "fulltext" in parts:
                fulltext_path.write_text(parts["fulltext"])
        else:
            # Single response - save as full-text
            fulltext_path.write_text(result)
            # Create minimal book-info
            book_info_path.write_text(
                f"---\ntitle: {pdf_path.stem}\ncategory: source\n---\n\nExtracted from {pdf_path.name}\n"
            )

        logger.info(f"Saved: {book_info_path}")
        logger.info(f"Saved: {fulltext_path}")

        return book_info_path, fulltext_path

    async def extract_with_domains(
        self,
        pdf_path: Path,
        domain_ids: list[str],
        output_dir: Path,
        model: str | None = None,
    ) -> Path:
        """Extract domain-specific knowledge from a PDF.

        Args:
            pdf_path: Path to the PDF file
            domain_ids: List of domain IDs for focused extraction
            output_dir: Directory to save output
            model: Model to use

        Returns:
            Path to the output file
        """
        from .domain_config import build_domain_context
        from .domain_config import load_domain_config

        # Build combined domain context
        domain_contexts = []
        for domain_id in domain_ids:
            config = load_domain_config(domain_id)
            if config:
                context = build_domain_context(config)
                if context:
                    domain_contexts.append(context)
                    logger.info(f"Loaded domain: {domain_id}")
            else:
                logger.warning(f"Domain config not found: {domain_id}")

        if not domain_contexts:
            raise ValueError("No valid domain configs found")

        combined_context = "\n\n---\n\n".join(domain_contexts)

        # Build the extraction prompt
        prompt = self._get_domain_extraction_prompt(domain_ids, combined_context)

        # Extract using Gemini
        result = await self.extract_from_pdf(pdf_path, prompt, model)

        # Save result
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{pdf_path.stem}-extraction.md"
        output_file.write_text(result)

        logger.info(f"Saved: {output_file}")
        return output_file

    def _get_fulltext_prompt(self) -> str:
        """Get the fulltext extraction prompt."""
        return """You are a precise text transcription specialist. Your task is to create a
complete, lossless markdown transcription of this PDF book.

## CRITICAL REQUIREMENTS

### 1. Page Markers (MOST IMPORTANT)
- Insert `<!-- PAGE: n -->` marker at the START of each page's content
- EVERY page boundary MUST be marked - do NOT skip pages
- Page numbers enable precise citations later
- If page numbers restart (e.g., roman numerals for preface), note: `<!-- PAGE: xii (preface) -->`

### 2. Complete Transcription
- Transcribe ALL text, not just "key points"
- This is a LOSSLESS extraction - nothing should be summarized or omitted
- Preserve paragraph structure
- Maintain heading hierarchy (use #, ##, ###)
- Keep original punctuation and formatting

### 3. Japanese/Original Language Text with Furigana
- Preserve ALL kanji, hiragana, katakana EXACTLY as written
- When furigana (reading aids) appear above kanji, integrate them inline:
  - Format: 茶道 (chadō) - the reading in parentheses immediately after
  - For complex terms with non-standard readings, preserve the exact reading
  - Example: 棟瓦 (munegawara) NOT (munagawara)
  - Example: 焼貫 (yakinuki) NOT (yakunuki)
- DO NOT create separate lines for furigana - always inline with the term
- When readings conflict with standard dictionary readings, PRESERVE THE PRINTED READING
- Keep original-language quotations intact

### 4. Tables and Lists
- Recreate tables in markdown format
- Preserve numbered and bulleted lists
- Maintain original ordering

### 5. Quotations
- Use blockquote (>) for quotations
- Preserve quotation attribution
- Note if translation vs original: > "Quote" [Author, p.X, translated]

### 6. Figures, Images, and Diagrams
- Insert placeholder: `[Figure X.Y: brief description]`
- Preserve captions exactly
- Note if figure has Japanese labels
- FOR FAMILY TREES / GENEALOGIES: Preserve structure using indentation or ASCII art:
  ```
  祖父 (Grandfather)
    ├── 父 (Father)
    │   ├── 長男 (Eldest Son)
    │   └── 次男 (Second Son)
    └── 叔父 (Uncle)
  ```
- FOR DIAGRAMS: Describe the structure, not just list elements linearly

### 7. Footnotes/Endnotes
- Preserve using markdown footnote syntax: [^1]
- Place footnote content at end of chapter or document
- Keep original numbering

### 8. Page Boundary Handling
- If a sentence continues across a page boundary, include the COMPLETE sentence
- Mark the page break but don't split mid-word or mid-sentence
- Better to include a few extra words than to cut off meaning

## OUTPUT FORMAT

Start with a YAML frontmatter block:

```yaml
---
title: "[Full title]"
japanese: "[日本語タイトル if applicable]"
category: source
type: full-text-extraction
extraction_date: "[Today's date]"
page_count: [n]
---
```

Then provide the complete transcription with page markers.

## QUALITY CHECKLIST

- [ ] Every page has a `<!-- PAGE: n -->` marker
- [ ] No pages were skipped - sequential numbering is complete
- [ ] No content was summarized - this is FULL transcription
- [ ] All Japanese/original characters preserved correctly
- [ ] Furigana readings integrated inline (not as separate lines)
- [ ] Paragraph structure maintained
- [ ] All headings use proper markdown hierarchy
- [ ] Family trees and diagrams preserve structural relationships"""

    def _get_domain_extraction_prompt(self, domain_ids: list[str], domain_context: str) -> str:
        """Get domain-specific extraction prompt."""
        return f"""You are a knowledge extraction specialist. Extract structured knowledge from this book for a personal knowledge vault.

## Domain Context

{domain_context}

## Output Format

Create markdown with this structure:

```yaml
---
title: [Book title in English]
japanese: [日本語タイトル if applicable]
category: source
extracted_date: [Today's date]
domains: [{", ".join(domain_ids)}]

citation:
  authors:
    - family: [Last name]
      given: [First name/initials]
  year: [Publication year]
  title: [Full title]
  publisher: [Publisher]
---
```

## Extraction Guidelines

1. **CRITICAL: Preserve page numbers throughout**
   - Include page number for EVERY quote, fact, or significant claim
   - Format: `[p.42]` inline or `(pp. 42-43)` for ranges

2. **Preserve original language terms**: Keep original with romaji/translation
   - Format: 茶碗 (chawan, tea bowl)

3. **Focus on domain-relevant content**: Extract concepts, relationships, and insights
   relevant to the specified domains

4. **Extract actionable knowledge**:
   - Key concepts with definitions
   - Relationships between concepts
   - Philosophical insights and principles
   - Practical techniques
   - Historical context

5. **Use tables for structured information**

6. **Note uncertainties**: If meaning is unclear:
   > [Extraction note: Original text unclear]

## Quality Checks

- [ ] All original language characters extracted correctly
- [ ] Frontmatter is valid YAML
- [ ] Every quote has a page number
- [ ] Content is tagged with relevant domains"""

    async def extract_fulltext_chunked(
        self,
        pdf_path: Path,
        output_dir: Path,
        total_pages: int,
        chunk_size: int = 25,
        model: str | None = None,
    ) -> tuple[Path, Path]:
        """Extract full text from a large PDF book using chunked extraction.

        For books that exceed Gemini's output token limit, this method extracts
        the PDF in smaller page-range chunks and combines them.

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save output files
            total_pages: Total number of pages in the PDF
            chunk_size: Number of pages per chunk (default: 25)
            model: Model to use (default: gemini-2.5-flash for 65K output tokens)

        Returns:
            Tuple of (book_info_path, fulltext_path)
        """
        if not self.check_availability():
            raise ValueError("Gemini API not configured. Set GOOGLE_API_KEY environment variable.")

        model = model or "gemini-2.5-flash"  # Use 2.5-flash for larger output window
        output_dir.mkdir(parents=True, exist_ok=True)

        # Calculate page ranges
        chunks: list[tuple[int, int]] = []
        start = 1
        while start <= total_pages:
            end = min(start + chunk_size - 1, total_pages)
            chunks.append((start, end))
            start = end + 1

        logger.info(f"Extracting {total_pages} pages in {len(chunks)} chunks of ~{chunk_size} pages each")

        # Extract each chunk
        chunk_files: list[Path] = []
        for start_page, end_page in chunks:
            chunk_file = await self._extract_page_range(pdf_path, start_page, end_page, output_dir, model)
            chunk_files.append(chunk_file)
            # Small delay between chunks to avoid rate limiting
            await asyncio.sleep(2)

        # Combine chunks
        logger.info("Combining chunks...")
        fulltext_path = output_dir / "_full-text.md"

        # Build frontmatter
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
                end_idx = content.find("---", 3)
                if end_idx > 0:
                    content = content[end_idx + 3 :].strip()
            combined_content.append(content)
            combined_content.append("\n\n")

        fulltext_path.write_text("\n".join(combined_content), encoding="utf-8")
        logger.info(f"Combined file: {fulltext_path} ({fulltext_path.stat().st_size} bytes)")

        # Create book-info
        book_info_path = output_dir / "_book-info.md"
        book_info_path.write_text(
            f"---\ntitle: {pdf_path.stem}\ncategory: source\ntype: book\npages: {total_pages}\n---\n\nExtracted from {pdf_path.name} using chunked extraction.\n"
        )

        return book_info_path, fulltext_path

    async def _extract_page_range(
        self,
        pdf_path: Path,
        start_page: int,
        end_page: int,
        output_dir: Path,
        model: str,
    ) -> Path:
        """Extract a specific page range from a PDF.

        Args:
            pdf_path: Path to the PDF file
            start_page: First page to extract (1-based)
            end_page: Last page to extract (inclusive)
            output_dir: Directory to save output
            model: Model to use

        Returns:
            Path to the chunk file
        """
        chunk_file = output_dir / f"_chunk_{start_page:03d}-{end_page:03d}.md"

        # Skip if already extracted with reasonable size
        if chunk_file.exists() and chunk_file.stat().st_size > 5000:
            logger.info(f"Chunk {start_page}-{end_page} exists ({chunk_file.stat().st_size} bytes), skipping")
            return chunk_file

        prompt = self._get_page_range_prompt(start_page, end_page)

        logger.info(f"Extracting pages {start_page}-{end_page}...")
        result = await self.extract_from_file(pdf_path, prompt, model)

        # Check for degenerate output (repetition pattern at end)
        if len(result) > 1000:
            last_chunk = result[-500:]
            lines = last_chunk.split("\n")
            if len(lines) > 3:
                # If last 3 lines are identical and substantial, likely hit MAX_TOKENS
                if lines[-1] == lines[-2] == lines[-3] and len(lines[-1]) > 10:
                    logger.warning(f"Chunk {start_page}-{end_page} may have hit MAX_TOKENS (repetitive ending)")

        chunk_file.write_text(result, encoding="utf-8")
        logger.info(f"Saved chunk: {chunk_file.name} ({len(result)} chars)")
        return chunk_file

    def _get_page_range_prompt(self, start_page: int, end_page: int) -> str:
        """Generate extraction prompt for a specific page range."""
        return f"""You are a precise text transcription specialist. Your task is to create a
complete, lossless markdown transcription of PAGES {start_page} to {end_page} from this PDF book.

## CRITICAL REQUIREMENTS

### 1. Page Markers (MOST IMPORTANT)
- Insert `<!-- PAGE: n -->` marker at the START of each page's content
- EVERY page from {start_page} to {end_page} MUST have a marker - do NOT skip any pages
- Page numbers enable precise citations later

### 2. Complete Transcription
- Transcribe ALL text from pages {start_page}-{end_page}, not just "key points"
- This is a LOSSLESS extraction - nothing should be summarized or omitted
- Preserve paragraph structure
- Maintain heading hierarchy (use #, ##, ###)
- Keep original punctuation and formatting

### 3. Japanese/Original Language Text with Furigana
- Preserve ALL kanji, hiragana, katakana EXACTLY as written
- When furigana (reading aids) appear above kanji, integrate them inline:
  - Format: 茶道 (chadō) - the reading in parentheses immediately after
  - Preserve non-standard readings exactly as printed
  - Example: 棟瓦 (munegawara), 焼貫 (yakinuki)
- DO NOT create separate lines for furigana - always inline
- Keep original-language quotations intact

### 4. Tables and Lists
- Recreate tables in markdown format
- Preserve numbered and bulleted lists
- Maintain original ordering

### 5. Quotations
- Use blockquote (>) for quotations
- Preserve quotation attribution

### 6. Figures, Images, and Diagrams
- Insert placeholder: `[Figure X.Y: brief description]`
- Preserve captions exactly
- FOR FAMILY TREES: Preserve hierarchy using indentation or ASCII art
- FOR DIAGRAMS: Describe structural relationships, not just linear text

### 7. Footnotes/Endnotes
- Preserve using markdown footnote syntax: [^1]
- Place footnote content at end of this section

### 8. Page Boundary Handling
- If a sentence continues across a page boundary, include the complete sentence
- Mark the page break but don't split mid-word or mid-sentence

## OUTPUT FORMAT

Start immediately with the page content. First line should be:
<!-- PAGE: {start_page} -->

Then provide the complete transcription of pages {start_page} to {end_page}.

## IMPORTANT
- Only transcribe pages {start_page} through {end_page}
- Do NOT skip any pages in this range
- Do NOT repeat content or enter loops
- Stop cleanly at page {end_page}
"""

    def _split_gemini_response(self, response: str) -> dict[str, str]:
        """Split Gemini response into book-info and fulltext parts."""
        result: dict[str, str] = {}

        # Look for file markers in the response
        markers = [
            ("_book-info.md", "_full-text.md"),
            ("### File 1:", "### File 2:"),
            ("## File 1:", "## File 2:"),
        ]

        for marker1, marker2 in markers:
            if marker1 in response and marker2 in response:
                idx1 = response.find(marker1)
                idx2 = response.find(marker2)

                if idx1 < idx2:
                    result["book_info"] = response[idx1:idx2].strip()
                    result["fulltext"] = response[idx2:].strip()
                else:
                    result["fulltext"] = response[idx2:idx1].strip()
                    result["book_info"] = response[idx1:].strip()
                return result

        # Couldn't split - return as single piece
        result["book_info"] = response
        return result
