# YomiToku Extraction Integration Plan

**Date**: 2026-01-03
**Status**: Ready for Execution

## Executive Summary

This document outlines the plan to integrate YomiToku OCR for Japanese PDF extraction, replacing/supplementing the existing Gemini Vision approach which produces garbled text due to column mixing.

## Problem Statement

### Current Issues with Gemini Vision Extraction
1. **Column Mixing**: Gemini reads horizontally across vertical columns instead of completing each column top-to-bottom
2. **Garbled Sentences**: Text like "千利休が亡くなりましたのが一五九一年" becomes fragmented
3. **Knowledge Contamination**: Learnings extracted from garbled text have propagated into the knowledge base

### Example of Garbled Extraction (Gemini)
```
幕末には二百五十年の建物が造りあげられました。三百年忌も完成しました。
```

### Correct Text (YomiToku)
```
幕末には二百五十年遠忌がございました。そのときに現在の三千家の建物が造りあげられまして...
```

## Solution: YomiToku Integration

### Why YomiToku?
- Purpose-built for Japanese document OCR
- Reading order detection (読み順推定) for vertical text
- Proper column handling without mixing
- Uses MPS (Metal Performance Shaders) for fast processing on Mac

### Tools Created

| Tool | Purpose | Status |
|------|---------|--------|
| `scripts/chanoyu/extract_yomitoku.py` | Single PDF extraction | ✅ Complete |
| `scripts/chanoyu/batch_reextract_yomitoku.py` | Batch re-extraction | ✅ Complete |

## PDF Inventory

### Source Directories
| Directory | PDFs | Status |
|-----------|------|--------|
| `/Users/joi/Media/chanoyu-sources/jikunyu-raku/` | 22 | Primary |
| `/Users/joi/Media/chanoyu-sources/` | 1 | Primary |
| `/Users/joi/raku Sources/` | 22 | **DUPLICATES - Skip** |

### PDFs to Extract (22 total)

| # | Name | Year | Type |
|---|------|------|------|
| 1 | rakuyaki_ni_tsuite_1933 | 1933 | Book |
| 2 | raku_chawan__seibian_zuihitsu_1947 | 1947 | Book |
| 3 | sekai_touji_zenshuu_1955 | 1955 | Survey |
| 4 | tousetsu_1957-02 | 1957 | Journal |
| 5 | ocha_no_hanashi__chajin_no_wabi_to_sabi_1967 | 1967 | Book |
| 6 | gendai_no_tougei_1975 | 1975 | Survey |
| 7 | chatou_to_sono_kyoshou_1977 | 1977 | Catalog |
| 8 | gendai_no_chatou_raku_kichizaemon_ten_1985 | 1985 | Catalog |
| 9 | geinoushi_kenkyuu_1991-01 | 1991 | Journal |
| 10 | nihon_no_touji_1993 | 1993 | Survey |
| 11 | tou_1993 | 1993 | Journal |
| 12 | kyouto_no_kindai_kougei_1994 | 1994 | Catalog |
| 13-22 | tousetsu_* | 1997-2018 | Journals (11 issues) |
| 23 | dokumen (Pitelka book) | N/A | Book |

## Extraction Strategy

### Phase 1: YomiToku Extraction (Estimated: 1-2 hours)
1. Run batch extraction script
2. Output saved to `{source_dir}/yomitoku/` for each PDF
3. Clean markdown files saved to `{source_dir}/_page_NNNN.md`
4. Combined full-text saved to `{source_dir}/_full-text.md`

### Phase 2: Quality Comparison
1. Compare YomiToku output with existing Gemini extractions
2. Identify pages with significant differences
3. Create quality report

### Phase 3: Knowledge Base Cleanup (Requires Audit First)
1. Identify knowledge pages that cite garbled sources
2. Flag specific claims that may be incorrect
3. Re-extract learnings from clean YomiToku text
4. Update citations and fix errors

## Output Structure

Each extracted source will have:
```
sources/jikunyu-raku/{source_name}/
├── _book-info.md          # Metadata (existing)
├── _full-text.md          # YomiToku extraction (new)
├── _full-text-english.md  # English translation (may need re-translation)
├── yomitoku/              # Raw YomiToku output
│   ├── *.md               # Per-page files
│   └── figures/           # Extracted figures
├── _page_0001.md          # Cleaned per-page (new)
└── reextracted/           # Old Gemini re-extraction (preserved for comparison)
```

## Knowledge Base Impact Assessment

### Pages Potentially Affected
- `chanoyu/people/raku-lineage.md` - Raku family information
- `chanoyu/concepts/wabi.md` - Wabi philosophy
- `chanoyu/glossary.md` - Technical terms
- `chanoyu/people/chajin.md` - Tea masters

### High-Risk Areas (Need Verification)
1. **Quotes with page citations** - May contain garbled text
2. **Technical terminology** - OCR errors common in specialized vocabulary
3. **Names and dates** - Critical historical data
4. **Generation identifiers** - Raku family head names (十三代, etc.)

## Commands

### Test Single Extraction
```bash
uv run python scripts/chanoyu/extract_yomitoku.py \
    "/Users/joi/Media/chanoyu-sources/jikunyu-raku/rakuyaki_ni_tsuite_1933.pdf" \
    /tmp/test_output \
    --reading-order japanese-book-spread
```

### Dry Run Batch
```bash
uv run python scripts/chanoyu/batch_reextract_yomitoku.py --dry-run
```

### Execute Full Batch
```bash
uv run python scripts/chanoyu/batch_reextract_yomitoku.py
```

### Force Re-extraction
```bash
uv run python scripts/chanoyu/batch_reextract_yomitoku.py --force
```

## Next Steps

1. **Execute batch extraction** - Run on all 22 PDFs
2. **Review quality** - Sample comparison with Gemini output
3. **Audit knowledge base** - Find garbled text in promoted knowledge
4. **Re-translate** - English translations may need regeneration
5. **Update manifest** - Mark sources as re-extracted

## Notes

### Preservation Strategy
- Existing Gemini extractions preserved in `reextracted/` subdirectory
- English translations preserved (may need regeneration)
- YomiToku output added alongside, not replacing

### Known YomiToku Limitations
- Does not add furigana/readings for proper names
- Does not translate to English
- Some OCR errors remain (historical typefaces)
- Library watermarks sometimes included (cleaned in post-processing)
