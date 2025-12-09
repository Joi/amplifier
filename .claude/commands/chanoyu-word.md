---
description: Convert a finalized tea ceremony letter from markdown to Word format
argument-hint: <path to .md file> or leave blank to select from recent letters
---

# Convert Letter to Word

Convert a finalized chanoyu letter to Microsoft Word format using the Japanese vertical layout template.

## User Input

{{PROMPT}}

## Step 1: Identify the Letter File

If a path was provided, use it directly.

If no path or "recent" provided, list recent letters for selection:
```bash
find ~/switchboard/chanoyu/chakai -name "korei_*.md" -o -name "annai_*.md" -o -name "zenrei_*.md" 2>/dev/null | xargs ls -t | head -10
```

Then ask the user which file to convert.

## Step 2: Preview the Letter

Read and display the letter content so the user can confirm it's finalized:
```
Read file: [selected-path]
```

Ask: "Is this letter finalized and ready for Word conversion?"

## Step 3: Run Conversion

Execute the Python conversion script with --open flag to automatically open in Word:
```bash
/Users/joi/switchboard/chanoyu/scripts/md-to-word.py --open "[selected-path]"
```

The script will:
- Strip YAML frontmatter and code blocks
- Remove the header line (# title) and ## Notes sections
- Auto-break long lines at natural Japanese word boundaries (禁則処理)
- Calculate max characters per line from actual font metrics
- Apply the Japanese letter template with vertical layout (縦書き)
- Preserve KouzanBrushFontOTF brush calligraphy font at 24pt
- Create a .docx file in the same directory
- Open the result in Microsoft Word

## Step 4: Report Results

After conversion, report:
- **Original:** [path to .md]
- **Word file:** [path to .docx]
- **Template:** japanese-letter-word-template.docx (縦書き vertical layout)
- **Font:** KouzanBrushFontOTF (24pt brush calligraphy)
- **Max chars/line:** Auto-calculated (~18 chars at 24pt)

## Script Location

The conversion script is at:
```
/Users/joi/switchboard/chanoyu/scripts/md-to-word.py
```

Usage:
```bash
md-to-word.py [options] <markdown-file> [output-file]

Options:
  -o, --open      Open the document in Word after conversion
  -t, --template  Path to custom template (default: japanese-letter-word-template.docx)
  -m, --max-chars Override max characters per line (default: auto-calculated)
  -h, --help      Show help message
```

## Notes

- Template: `~/switchboard/chanoyu/writing/templates/japanese-letter-word-template.docx`
- Output is created in the same directory as input
- Uses vertical text layout (縦書き) with KouzanBrushFontOTF
- Uses direct XML manipulation to preserve template formatting
- Auto-breaks lines at particles (を、に、で、は、が) and punctuation to prevent awkward mid-word wraps
- Uses PIL to measure actual font metrics for accurate line length calculation
