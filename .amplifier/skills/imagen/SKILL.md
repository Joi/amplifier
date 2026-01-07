---
name: imagen
description: Generate images using Google's Imagen model. Use when user wants to create, generate, or make images from text descriptions.
version: 1.0.0
---

# Imagen - Image Generation Tool

Generate images using Google's Imagen model (via Gemini API).

## When to Use

- User asks to "generate an image" or "create a picture"
- User wants to visualize something
- User asks for illustrations, diagrams, or artwork
- User wants to transform or edit an existing image

## Tool Location

```bash
python /Users/joi/amplifier/tools/imagen.py "<prompt>" [options]
```

## Basic Usage

```bash
# Simple image generation
python /Users/joi/amplifier/tools/imagen.py "A serene mountain landscape at sunset"

# With specific size
python /Users/joi/amplifier/tools/imagen.py "A cat in a garden" --size 2K

# With aspect ratio
python /Users/joi/amplifier/tools/imagen.py "A panoramic city skyline" --aspect-ratio 16:9

# Save to specific location
python /Users/joi/amplifier/tools/imagen.py "A logo design" --output ~/Desktop/logo.png
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--size` | Image size: 1K, 2K, 4K | 1K |
| `--aspect-ratio` | Aspect ratio: 1:1, 16:9, 9:16, 4:3, 3:4 | 1:1 |
| `--output` | Output file path | Auto-generated |
| `--model` | Model variant: flash, pro | flash |
| `--input` | Input image for editing/transformation | None |

## Image Editing

Transform or edit existing images:

```bash
# Transform style
python /Users/joi/amplifier/tools/imagen.py "Transform into watercolor painting" --input photo.jpg

# Edit specific elements
python /Users/joi/amplifier/tools/imagen.py "Add a rainbow in the sky" --input landscape.jpg
```

## Prompt Tips

For best results:
- Be specific about style: "digital art", "photorealistic", "watercolor", "sketch"
- Describe lighting: "soft morning light", "dramatic shadows", "golden hour"
- Mention composition: "close-up", "wide angle", "bird's eye view"
- Include mood: "peaceful", "energetic", "mysterious"

## Examples

```bash
# Blog post illustration
python /Users/joi/amplifier/tools/imagen.py "A minimalist illustration of AI and human collaboration, soft blue tones, modern tech aesthetic"

# Icon design
python /Users/joi/amplifier/tools/imagen.py "A simple app icon for a note-taking app, flat design, purple gradient" --aspect-ratio 1:1

# Header image
python /Users/joi/amplifier/tools/imagen.py "Abstract geometric pattern representing data flow, dark background with cyan accents" --aspect-ratio 16:9 --size 2K
```

## Output

The tool:
1. Generates the image
2. Saves it to the specified path (or auto-generates a path)
3. Returns the file path

Images are saved as PNG by default.

## Requirements

- `GOOGLE_API_KEY` environment variable or configured in Amplifier secrets
