#!/usr/bin/env python3
"""Combine all AI Driven book chunks into final full-text file."""

from pathlib import Path

output_dir = Path("/Users/joi/switchboard/joi-writing/books/ai-driven-nen")

# Define the chunks in page order
chunks_in_order = [
    "_chunk_001-005.md",  # pages 1-5 (re-extracted)
    "_chunk_006-010.md",  # pages 6-10 (re-extracted)
    "_chunk_011-020.md",  # pages 11-20
    "_chunk_021-030.md",  # pages 21-30
    "_chunk_031-040.md",  # pages 31-40
    "_chunk_041-045.md",  # pages 41-45 (re-extracted)
    "_chunk_046-050.md",  # pages 46-50 (re-extracted)
    "_chunk_051-060.md",  # pages 51-60
    "_chunk_061-070.md",  # pages 61-70
    "_chunk_071-080.md",  # pages 71-80
    "_chunk_081-090.md",  # pages 81-90
    "_chunk_091-100.md",  # pages 91-100
    "_chunk_101-110.md",  # pages 101-110
    "_chunk_111-120.md",  # pages 111-120
    "_chunk_121-130.md",  # pages 121-130
    "_chunk_131-135.md",  # pages 131-135 (re-extracted)
    "_chunk_136-140.md",  # pages 136-140 (re-extracted)
    "_chunk_141-141.md",  # page 141
]

# Combine chunks
combined = []
total_pages_covered = 0
for chunk_name in chunks_in_order:
    chunk_path = output_dir / chunk_name
    if chunk_path.exists():
        content = chunk_path.read_text(encoding="utf-8")
        # Count page markers
        page_count = content.count("<!-- PAGE:")
        combined.append(f"\n\n<!-- CHUNK: {chunk_name} -->\n")
        combined.append(content)
        total_pages_covered += page_count
        print(f"✓ {chunk_name}: {page_count} pages, {len(content):,} chars")
    else:
        print(f"✗ {chunk_name}: MISSING")

# Write combined output
output_file = output_dir / "_full-text.md"
header = """---
title: "AI Driven 年 - Full Text"
title_romanized: "AI Driven Nen"
english_title: "AI Driven Year/Era"
source: ai_driven_nen.pdf
extraction_date: 2025-12-26
extraction_method: gemini-2.5-flash chunked
total_pages: 141
---

# AI Driven 年
## AI Driven Nen

Full text extraction from PDF using Gemini AI.

---

"""
output_file.write_text(header + "".join(combined), encoding="utf-8")

print(f"\n✅ Combined into {output_file}")
print(f"   Total pages with markers: {total_pages_covered}")
print(f"   Total size: {output_file.stat().st_size:,} bytes")
