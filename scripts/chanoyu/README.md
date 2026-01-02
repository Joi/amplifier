# Chanoyu PDF Extraction Tools

Tools for extracting text from scanned Japanese academic PDFs with complex layouts.

## Layout-Aware PDF Extractor

`extract_4up_pdf.py` handles PDFs where multiple logical pages are combined on each physical page (common in scanned academic journals).

### Supported Layouts

| Layout Type | Description | Reading Order |
|-------------|-------------|---------------|
| `japanese-book-spread` | Open book scans (2 pages per physical page) | Right → Left |
| `western-book-spread` | Open book scans (2 pages per physical page) | Left → Right |
| `japanese-4up` | 4 logical pages per physical page | UR → LR → UL → LL |
| `western-4up` | 4 logical pages per physical page | UL → UR → LL → LR |

### Prerequisites

```bash
# Required Python packages (in amplifier virtualenv)
uv add pdf2image google-genai pillow

# System dependency for pdf2image
brew install poppler  # macOS
# or: apt-get install poppler-utils  # Linux
```

### Environment Setup

The tool uses Google's Gemini Vision API. Set up your API key:

```bash
# Option 1: Direct environment variable
export GOOGLE_API_KEY="your-api-key"

# Option 2: Use 1Password CLI (recommended)
# Add to .env.local:
GOOGLE_API_KEY="op://Employee/Amplifier Gemini Key/credential"
```

### Usage

```bash
# Basic usage with 1Password
op run --env-file=.env.local -- uv run python scripts/chanoyu/extract_4up_pdf.py \
    /path/to/input.pdf \
    /path/to/output/ \
    --reading-order japanese-book-spread

# Skip cover page (common for scanned journals)
op run --env-file=.env.local -- uv run python scripts/chanoyu/extract_4up_pdf.py \
    /path/to/input.pdf \
    /path/to/output/ \
    --reading-order japanese-book-spread \
    --start-page 2

# Process only specific pages
op run --env-file=.env.local -- uv run python scripts/chanoyu/extract_4up_pdf.py \
    /path/to/input.pdf \
    /path/to/output/ \
    --reading-order japanese-book-spread \
    --start-page 2 \
    --end-page 10
```

### Output

The tool generates:

1. **Individual page files**: `_page_0001.md`, `_page_0002.md`, etc.
2. **Combined file**: `_full-text.md` with all pages concatenated
3. **YAML frontmatter** with extraction metadata

Example output structure:
```
output/
├── _full-text.md      # Combined text (all pages)
├── _page_0001.md      # Logical page 1
├── _page_0002.md      # Logical page 2
└── ...
```

### Example: Geinoushi Kenkyuu 1991-01

This is a Japanese academic journal with 2-up book spread layout:

```bash
op run --env-file=.env.local -- uv run python scripts/chanoyu/extract_4up_pdf.py \
    /Users/joi/Media/chanoyu-sources/jikunyu-raku/geinoushi_kenkyuu_1991-01.pdf \
    /Users/joi/switchboard/chanoyu/sources/jikunyu-raku/geinoushi_kenkyuu_1991-01/reextracted/ \
    --reading-order japanese-book-spread \
    --start-page 2
```

**Result**: 24 logical pages extracted in correct reading order (13 physical pages, skipping cover).

### How It Works

1. **PDF to Images**: Converts each physical page to a high-resolution image (300 DPI)
2. **Page Splitting**: Divides each image into logical page regions based on layout type
3. **Vision OCR**: Uses Gemini Vision API to extract Japanese text with furigana
4. **Assembly**: Combines pages in correct reading order with page markers

### Troubleshooting

**"Both GOOGLE_API_KEY and GEMINI_API_KEY are set"**
- This is just a warning, extraction still works
- The tool prefers GOOGLE_API_KEY

**Slow extraction (~30-60s per page)**
- This is normal for Gemini Vision API
- Each logical page requires a separate API call

**Missing text or garbled characters**
- Check if the scan quality is sufficient (300 DPI recommended)
- The tool works best with clear, high-contrast scans

### Technical Details

- **Model**: `gemini-2.5-flash` (fast, good for OCR)
- **Image format**: PNG at 300 DPI
- **Prompt**: Specialized for Japanese academic text with furigana preservation
- **Rate limiting**: 1.5s delay between API calls to avoid throttling
