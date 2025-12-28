#!/usr/bin/env python3
"""Combine all book chunks into final full-text file."""

from pathlib import Path

output_dir = Path("/Users/joi/switchboard/joi-writing/books/technology-mirai")

# Define the correct non-overlapping chunks in page order
# These are the best extractions for each page range
chunks_in_order = [
    "_chunk_001-025.md",  # pages 1-25
    "_chunk_026-035.md",  # pages 26-35 (new)
    "_chunk_036-045.md",  # pages 36-45 (new)
    "_chunk_046-050.md",  # pages 46-50 (new)
    "_chunk_051-060.md",  # pages 51-60 (new)
    "_chunk_061-070.md",  # pages 61-70 (new)
    "_chunk_071-075.md",  # pages 71-75 (new)
    "_chunk_076-085.md",  # pages 76-85 (re-extracted)
    "_chunk_086-095.md",  # pages 86-95 (re-extracted)
    "_chunk_096-100.md",  # pages 96-100 (re-extracted)
    "_chunk_101-125.md",  # pages 101-125
    "_chunk_126-150.md",  # pages 126-150
    "_chunk_151-160.md",  # pages 151-160 (new)
    "_chunk_161-170.md",  # pages 161-170 (new)
    "_chunk_171-175.md",  # pages 171-175 (new)
    "_chunk_176-200.md",  # pages 176-200
    "_chunk_201-210.md",  # pages 201-210 (new)
    "_chunk_211-220.md",  # pages 211-220 (new)
    "_chunk_221-225.md",  # pages 221-225 (new)
    "_chunk_226-230.md",  # pages 226-230
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
title: "テクノロジーが予測する未来 - Full Text"
source: technology-mirai.pdf
extraction_date: 2025-12-26
extraction_method: gemini-2.5-flash chunked
total_pages: 230
---

# テクノロジーが予測する未来
## Technology Predicts the Future

Full text extraction from PDF using Gemini AI.

---

"""
output_file.write_text(header + "".join(combined), encoding="utf-8")

print(f"\n✅ Combined into {output_file}")
print(f"   Total pages with markers: {total_pages_covered}")
print(f"   Total size: {output_file.stat().st_size:,} bytes")
