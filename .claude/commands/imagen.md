---
description: Generate images using Google's Gemini image generation
category: creative
allowed-tools: Bash
---

# Claude Command: Imagen

Generate images using Google's Gemini image generation API (Nano Banana Pro / Nano Banana).

## Usage

```
/imagen <prompt>
/imagen <prompt> --size 4K --aspect-ratio 16:9
/imagen <prompt> --input photo.jpg
/imagen <prompt> --model flash
```

## Examples

```
/imagen A serene mountain landscape at sunset
/imagen A cat playing in a garden --size 2K --aspect-ratio 16:9
/imagen Transform this into a watercolor painting --input ~/Photos/photo.jpg
/imagen A logo with the text 'Hello World' --model pro --size 4K
/imagen Quick sketch of a robot --model flash
```

## What This Command Does

1. Parses the user's prompt and options
2. Calls Google's Gemini image generation API
3. Saves the generated image to `~/Downloads/imagen/`
4. Returns the path to the generated image

## Options

| Option | Shorthand | Description | Default |
|--------|-----------|-------------|---------|
| `--model` | `-m` | Model: `pro` (Nano Banana Pro) or `flash` (Nano Banana) | `pro` |
| `--size` | `-s` | Image size: `1K`, `2K`, `4K` (pro only, flash is fixed at 1K) | `2K` |
| `--aspect-ratio` | `-a` | Aspect ratio: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, etc. | `1:1` |
| `--input` | `-i` | Input image for editing/transformation (can be used multiple times) | none |
| `--output-dir` | `-o` | Output directory | `~/Downloads/imagen` |

## Available Aspect Ratios

`1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`

## Models

- **pro** (Nano Banana Pro / `gemini-3-pro-image-preview`): Higher quality, supports 1K/2K/4K sizes
- **flash** (Nano Banana / `gemini-2.5-flash-image`): Faster, fixed 1K size

## Technical Implementation

Run the imagen.py tool:

```bash
python "$CLAUDE_PROJECT_DIR/.claude/tools/imagen.py" $ARGUMENTS
```

## Requirements

- `google-genai` package installed (`uv add google-genai`)
- Gemini API key configured in the secrets system

## Output

Images are saved to `~/Downloads/imagen/` with timestamp-based filenames:
- `imagen_20260106_123456.png`
