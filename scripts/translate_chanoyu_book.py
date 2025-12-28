#!/usr/bin/env python3
"""
Translate the chanoyu letter book from Japanese to English using Gemini.

Preserves important terms as kanji/romaji/English format.
Processes in chunks to handle the large file size.
"""

import os
import re
import time
from pathlib import Path

import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

SOURCE_FILE = Path.home() / "switchboard/chanoyu/sources/chanoyunotegamibureishu/_full-text.md"
OUTPUT_FILE = Path.home() / "switchboard/chanoyu/sources/chanoyunotegamibureishu/_full-text-english.md"

TRANSLATION_PROMPT = """You are translating a Japanese tea ceremony letter writing guide (決定版 茶の湯の手紙文例集) to English.

CRITICAL INSTRUCTIONS:
1. Translate all Japanese text to clear, readable English
2. For important tea ceremony terms, use this format: **English** (kanji / romaji)
   Example: **main guest** (正客 / shōkyaku)
3. Keep the original structure including page markers (<!-- PAGE: n -->)
4. Preserve any existing romaji annotations in parentheses
5. For letter examples, translate the content but keep the format/structure
6. Translate section headers and provide English equivalents
7. Keep table structures intact, translating content

IMPORTANT TERMS TO PRESERVE (always show kanji/romaji):
- Tea gathering terms: 茶事 (chaji), 茶会 (chakai), 炉開き (robiraki), 口切 (kuchikiri)
- Roles: 正客 (shōkyaku), 亭主 (teishu), 連客 (renkyaku), 詰 (tsume)
- Letter types: 案内状 (annaijō), 前礼 (zenrei), 後礼 (kōrei), 礼状 (reijō)
- Letter parts: 頭語 (tōgo), 結語 (ketsugo), 時候の挨拶 (jikō no aisatsu)
- Formality markers: 謹啓 (kinkei), 敬具 (keigu), かしこ (kashiko)

Translate the following section:

---
{content}
---

Provide the English translation maintaining all formatting:"""


def split_into_chunks(content: str, pages_per_chunk: int = 10) -> list[str]:
    """Split content by page markers into chunks."""
    # Split by page markers
    page_pattern = r'(<!-- PAGE: \d+ -->)'
    parts = re.split(page_pattern, content)

    # Reconstruct pages
    pages = []
    current_page = ""
    for part in parts:
        if re.match(page_pattern, part):
            if current_page:
                pages.append(current_page)
            current_page = part
        else:
            current_page += part
    if current_page:
        pages.append(current_page)

    # Group into chunks
    chunks = []
    for i in range(0, len(pages), pages_per_chunk):
        chunk = "".join(pages[i:i + pages_per_chunk])
        chunks.append(chunk)

    return chunks


def translate_chunk(chunk: str, model: genai.GenerativeModel, chunk_num: int, total: int) -> str:
    """Translate a single chunk using Gemini."""
    print(f"  Translating chunk {chunk_num}/{total}...")

    prompt = TRANSLATION_PROMPT.format(content=chunk)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=8192,
            )
        )
        return response.text
    except Exception as e:
        print(f"  Error on chunk {chunk_num}: {e}")
        # Return original with error note
        return f"<!-- TRANSLATION ERROR: {e} -->\n{chunk}"


def main():
    print("=" * 60)
    print("Chanoyu Letter Book Translation")
    print("=" * 60)

    # Check API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set")
        return

    # Read source file
    print(f"\nReading: {SOURCE_FILE}")
    content = SOURCE_FILE.read_text(encoding="utf-8")

    # Extract frontmatter and content
    frontmatter_match = re.match(r'^(---\n.*?\n---\n)', content, re.DOTALL)
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        body = content[len(frontmatter):]
    else:
        frontmatter = ""
        body = content

    # Update frontmatter for English version
    english_frontmatter = """---
title: "Definitive Edition: Tea Ceremony Letter Examples Collection"
title_japanese: "決定版 茶の湯の手紙文例集"
category: source
type: full-text-translation
source_language: Japanese
target_language: English
translation_method: gemini-2.5-flash
total_pages: 169
note: "Important terms preserved as English (kanji / romaji)"
---

"""

    # Split into chunks
    chunks = split_into_chunks(body, pages_per_chunk=10)
    print(f"Split into {len(chunks)} chunks")

    # Initialize model
    model = genai.GenerativeModel("gemini-2.0-flash")

    # Translate each chunk
    translated_chunks = []
    for i, chunk in enumerate(chunks, 1):
        translated = translate_chunk(chunk, model, i, len(chunks))
        translated_chunks.append(translated)

        # Rate limiting
        if i < len(chunks):
            time.sleep(1)

    # Combine translations
    full_translation = english_frontmatter + "\n".join(translated_chunks)

    # Write output
    print(f"\nWriting: {OUTPUT_FILE}")
    OUTPUT_FILE.write_text(full_translation, encoding="utf-8")

    # Summary
    print("\n" + "=" * 60)
    print("Translation complete!")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Lines: {len(full_translation.splitlines())}")
    print("=" * 60)


if __name__ == "__main__":
    main()
