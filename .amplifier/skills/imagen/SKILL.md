---
name: imagen
description: Generate images using Google's Imagen/Gemini models. Use when user wants to create, generate, or make images from text descriptions.
version: 2.0.0
---

# Imagen Skill

Generate images using Google's Imagen 4.0 and Gemini Flash Image models.

## When to Use

- User says "generate an image of..."
- User wants to create visual content
- User asks for illustrations or artwork
- User wants to transform/edit an existing image

## Python API (Preferred)

```python
from amplifier.skills import generate_image, generate_image_sync, ImageConfig, GeneratedImage

# Simple generation (async)
result = await generate_image("A serene mountain landscape at sunset")
print(f"Saved to: {result.path}")

# Synchronous version
result = generate_image_sync("A cat playing in a garden")

# With configuration
config = ImageConfig(
    model="pro",        # "pro", "ultra", or "flash"
    size="2K",          # "1K", "2K", "4K" (pro/ultra only)
    aspect_ratio="16:9" # See ratios below
)
result = await generate_image("A futuristic cityscape", config=config)

# Transform an existing image
result = await generate_image(
    "Transform into a watercolor painting",
    input_file="photo.jpg"
)

# Custom output path
result = await generate_image(
    "A logo design",
    output_path="~/Desktop/logo.png"
)
```

## Data Classes

```python
@dataclass
class ImageConfig:
    model: Literal["pro", "ultra", "flash"] = "pro"
    size: Literal["1K", "2K", "4K"] | None = None
    aspect_ratio: str = "1:1"
    output_dir: Path = ~/Downloads/imagen

@dataclass
class GeneratedImage:
    path: Path
    prompt: str
    model: str
    size: str
    aspect_ratio: str
```

## Models

| Model | ID | Sizes | Best For |
|-------|-----|-------|----------|
| `pro` | Imagen 4.0 | 1K, 2K, 4K | High quality, general use |
| `ultra` | Imagen 4.0 Ultra | 1K, 2K, 4K | Maximum quality |
| `flash` | Gemini Flash | 1K only | Fast generation |

## Aspect Ratios

Supported: `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`

## CLI Interface

```bash
# Basic generation
python -m amplifier.skills.imagen "A mountain at sunset"

# With options
python -m amplifier.skills.imagen "A cat" --model pro --size 2K --aspect-ratio 16:9

# Transform image
python -m amplifier.skills.imagen "Make it look like a painting" --input photo.jpg

# Custom output
python -m amplifier.skills.imagen "A logo" --output ~/Desktop/logo.png
```

## Output Location

By default, images are saved to:
```
~/Downloads/imagen/imagen_YYYYMMDD_HHMMSS.png
```

## Requirements

- Google API key (stored via `age` secrets as `GEMINI_API_KEY`)
- `google-genai` package: `uv add google-genai`

## Advantages Over MCP

- ✅ Works in subagents (MCP tools don't inherit)
- ✅ Async-first with sync wrapper
- ✅ Works in scripts, cron jobs, SDK calls
- ✅ Returns proper Python dataclasses with paths
