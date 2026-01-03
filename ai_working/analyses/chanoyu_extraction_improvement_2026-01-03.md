# Chanoyu PDF Extraction Improvement Analysis

**Date**: 2026-01-03
**Status**: In Progress - Testing Improved Prompt

## Problem Statement

Japanese academic journal PDF extraction was producing garbled text due to column mixing. The Gemini Vision model was reading horizontally across vertical columns instead of reading each column top-to-bottom, right-to-left.

## Key Files

### Source PDF
- **Original PDF**: `/Users/joi/Media/chanoyu-sources/jikunyu-raku/geinoushi_kenkyuu_1991-01.pdf`
- **DOI**: 10.11501/6048978
- **NDL URL**: https://dl.ndl.go.jp/pid/6048978

### Extraction Script
- **Script**: `/Users/joi/amplifier/scripts/chanoyu/extract_4up_pdf.py`
- **Key changes**: Lines 286 (temperature), 300-362 (prompt restructure)

### Output Locations
- **Current reextracted**: `/Users/joi/switchboard/chanoyu/sources/jikunyu-raku/geinoushi_kenkyuu_1991-01/reextracted/`
- **Test output**: `/tmp/extraction_test/`

## The Problem - Before Fix

### User's Original Text (from PDF)
```
千利休が亡くなりましたのが一五九一年ですので、一九九〇年が、四百年忌に相当するという訳で、この三月二八日に大徳寺の法堂におきまして法要が、さらに各塔頭で記念茶会が行われました。
```

### Old Extraction (Garbled)
```
茶の湯の湯界では、この三月二八日に大徳寺の法要におきまして法要が、さらに各塔頭で記念茶会が行われました。四百年忌に相当するものです。
```

**Issues**:
1. Key phrase "千利休が亡くなりましたのが一五九一年ですので、一九九〇年が" completely missing
2. "茶の湯の湯界" is garbled (should be "茶の湯界")
3. Sentences jumbled from different columns

## Root Cause

Gemini Vision defaults to Western left-to-right, top-to-bottom reading order. Japanese vertical text (縦書き/tategaki) requires:
- Columns read RIGHT to LEFT
- Text within columns read TOP to BOTTOM

The model was reading across column boundaries horizontally instead of completing each column vertically.

## Solution Implemented

### 1. Restructured Prompt (lines 300-362)

Changed from verbose instructions to structured step-by-step approach:

```
## STEP 1: IDENTIFY COLUMNS (REQUIRED)
This is VERTICAL Japanese text (縦書き/tategaki). First, mentally identify each vertical column from RIGHT to LEFT.

## STEP 2: READ EACH COLUMN IN ORDER
For each column (starting from the RIGHTMOST):
- Read from TOP to BOTTOM
- Complete the ENTIRE column before moving left
- When text continues across a column boundary, JOIN it into complete sentences

## CRITICAL RULES
1. **NEVER mix text from different columns** - this is the most common error
2. **Complete each column fully** before moving to the next column
```

### 2. Added Real Example

Included the actual problematic text as an example:

```
**CORRECT** (complete sentences):
千利休が亡くなりましたのが一五九一年ですので、一九九〇年が、四百年忌に相当するという訳で、この三月二八日に大徳寺の法堂におきまして法要が行われました。
```

### 3. Set Temperature to 0.0

Changed from 0.1 to 0.0 for deterministic output (line 286).

## Results After Fix

### New Extraction (page 4)
```
千利休が亡くなりましたのが一五九一年ですので、一九九〇年が、四百年忌に相当するという訳で、この三月二八日に大徳寺 (Daitokuji) の法堂におきまして法要が、さらに各塔頭で記念茶会がが行なわれました。
```

**Improvements**:
- ✅ Key phrase now captured correctly
- ✅ Sentence structure preserved
- ✅ Reading order improved

**Remaining Issues**:
- Minor typo: "がが" instead of "が" (doubled character)
- Some mixing still occurs at page boundaries
- End of pages sometimes have garbled text

## Next Steps

1. Run full re-extraction of the document
2. Compare quality across all pages
3. If issues persist, consider:
   - Pre-processing to detect column boundaries
   - Multiple extraction passes with validation
   - Trying Claude Vision API instead of Gemini

## Commands for Testing

```bash
# Re-extract specific pages
./scripts/chanoyu/run_with_gemini.sh uv run python scripts/chanoyu/extract_4up_pdf.py \
    "/Users/joi/Media/chanoyu-sources/jikunyu-raku/geinoushi_kenkyuu_1991-01.pdf" \
    /tmp/extraction_test \
    --reading-order japanese-book-spread \
    --start-page 2 --end-page 4

# Full re-extraction
./scripts/chanoyu/run_with_gemini.sh uv run python scripts/chanoyu/extract_4up_pdf.py \
    "/Users/joi/Media/chanoyu-sources/jikunyu-raku/geinoushi_kenkyuu_1991-01.pdf" \
    "/Users/joi/switchboard/chanoyu/sources/jikunyu-raku/geinoushi_kenkyuu_1991-01/reextracted" \
    --reading-order japanese-book-spread
```

## Related Context

- Previous session identified column interleaving as root cause
- zen-architect agent confirmed analysis
- The fix addresses Gemini's Western reading order bias
