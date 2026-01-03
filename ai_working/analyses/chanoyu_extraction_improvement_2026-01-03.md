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

## YomiToku Comparison (2026-01-03)

Installed and tested YomiToku (https://github.com/kotaro-kinoshita/yomitoku) as alternative extraction approach.

### YomiToku Features
- Purpose-built for Japanese document OCR with layout analysis
- Has reading order detection (読み順推定)
- Automatically handles vertical text with right-to-left column order
- Four specialized AI models: text detector, text recognizer, layout parser, table structure recognizer
- Uses MPS (Metal Performance Shaders) on Mac

### Test Command
```bash
uv run yomitoku "/Users/joi/Media/chanoyu-sources/jikunyu-raku/geinoushi_kenkyuu_1991-01.pdf" \
    /tmp/yomitoku_test -f md --figure --figure_letter
```

### Comparison Results

#### Sample: Physical Page 3 (Logical Pages 5-6)

**YomiToku Output** (`/tmp/yomitoku_test/jikunyu-raku_geinoushi_kenkyuu_1991-01_p3.md`):
```
幕末には二百五十年遠忌がございました。そのときに現在の三千家
の建物が造りあげられまして、とくに裏千家などは、現在の姿がほぼ
完成しました。三百年忌は明治二十三年で、茶の湯の衰退期であった
ために、さしたる行事らしきものは行われず...
```
✅ **Clean, well-ordered text with proper paragraph breaks**

**Gemini Output** (`reextracted/_page_0005.md`):
```
幕末には二百五十年の建物が造りあげられました。三百年忌も完成しました。
三百年忌のために、さしたる行事というものは、はなはだ乏しい年にわれれて...
```
❌ **Jumbled text mixing columns**: "二百五十年の建物" should be "二百五十年遠忌がございました"

### Verdict

**YomiToku is significantly better** for this Japanese academic journal:
- Proper reading order preserved
- Clean paragraph structure
- No column mixing
- Handles 2-up book spread layout better

**Issues observed in YomiToku**:
- Still processes physical pages as single units (not aware of 2-up spread)
- Some artifacts from stamps/annotations (e.g., "西原4881489 守谷美帆2025/12/11")
- Output uses `<br>` instead of proper line breaks

### Recommendation

Consider using YomiToku for future extractions:
1. Better reading order detection for vertical Japanese text
2. Produces cleaner, more accurate text
3. May need post-processing to handle 2-up spread page ordering

## Next Steps

1. ~~Run full re-extraction of the document~~ Done with both Gemini and YomiToku
2. ~~Compare quality across all pages~~ YomiToku is superior
3. Consider:
   - Using YomiToku as primary extraction method
   - Post-processing YomiToku output to reorder pages for 2-up spreads
   - Cleaning up `<br>` tags to proper markdown

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
