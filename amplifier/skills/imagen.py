"""Imagen skill - Generate images using Google's Imagen/Gemini models.

Native Amplifier skill for image generation. Works everywhere:
main session, subagents, SDK, scripts, cron jobs.

Usage:
    from amplifier.skills.imagen import generate_image, ImageConfig

    # Simple generation
    path = await generate_image("A serene mountain landscape at sunset")

    # With options
    config = ImageConfig(size="2K", aspect_ratio="16:9", model="pro")
    path = await generate_image("A cat in a garden", config=config)

    # Edit an existing image
    path = await generate_image(
        "Transform into watercolor painting",
        input_file="photo.jpg"
    )
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from amplifier.utils.secrets import get_gemini_api_key

# Lazy import for google-genai
_genai = None
_types = None


def _get_genai():
    """Lazy load google-genai package."""
    global _genai, _types
    if _genai is None:
        try:
            from google import genai
            from google.genai import types

            _genai = genai
            _types = types
        except ImportError:
            raise ImportError(
                "google-genai package not installed. Install with: uv add google-genai"
            )
    return _genai, _types


# Model configurations
MODELS = {
    "pro": {
        "id": "imagen-4.0-generate-001",
        "name": "Imagen 4.0",
        "sizes": ["1K", "2K", "4K"],
        "default_size": "2K",
    },
    "ultra": {
        "id": "imagen-4.0-ultra-generate-001",
        "name": "Imagen 4.0 Ultra",
        "sizes": ["1K", "2K", "4K"],
        "default_size": "2K",
    },
    "flash": {
        "id": "gemini-2.5-flash-image",
        "name": "Gemini Flash Image",
        "sizes": ["1K"],
        "default_size": "1K",
    },
}

ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]

# Default output directory
DEFAULT_OUTPUT_DIR = Path.home() / "Downloads" / "imagen"


@dataclass
class ImageConfig:
    """Configuration for image generation."""

    model: Literal["pro", "ultra", "flash"] = "pro"
    size: Literal["1K", "2K", "4K"] | None = None
    aspect_ratio: str = "1:1"
    output_dir: Path = field(default_factory=lambda: DEFAULT_OUTPUT_DIR)


@dataclass
class GeneratedImage:
    """Result of image generation."""

    path: Path
    prompt: str
    model: str
    size: str
    aspect_ratio: str


def _load_input_file(file_path: Path):
    """Load an input file (image) for editing/transformation."""
    _, types = _get_genai()

    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    suffix = file_path.suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }

    mime_type = mime_types.get(suffix, "image/jpeg")
    image_data = file_path.read_bytes()

    return types.Part.from_bytes(data=image_data, mime_type=mime_type)


async def generate_image(
    prompt: str,
    config: ImageConfig | None = None,
    input_file: str | Path | None = None,
    output_path: str | Path | None = None,
) -> GeneratedImage:
    """Generate an image using Google's Imagen/Gemini API.

    Args:
        prompt: Text description for image generation
        config: Image configuration (model, size, aspect ratio)
        input_file: Optional input image for editing/transformation
        output_path: Optional specific output path (auto-generated if None)

    Returns:
        GeneratedImage with path and metadata

    Raises:
        ImportError: If google-genai is not installed
        RuntimeError: If image generation fails
    """
    genai, types = _get_genai()
    config = config or ImageConfig()

    model_config = MODELS.get(config.model, MODELS["pro"])
    model_id = model_config["id"]

    # Validate and set size
    size = config.size
    if size is None:
        size = model_config["default_size"]
    elif size not in model_config["sizes"]:
        size = model_config["default_size"]

    # Validate aspect ratio
    aspect_ratio = config.aspect_ratio
    if aspect_ratio not in ASPECT_RATIOS:
        aspect_ratio = "1:1"

    # Initialize client
    api_key = get_gemini_api_key()
    client = genai.Client(api_key=api_key)

    # Build content parts
    contents = []

    # Add input file if provided
    if input_file:
        input_path = Path(input_file)
        contents.append(_load_input_file(input_path))

    # Add text prompt
    contents.append(prompt)

    # Build image config
    config_kwargs = {"aspect_ratio": aspect_ratio}
    if config.model in ["pro", "ultra"] and size:
        config_kwargs["image_size"] = size

    # Generate (run sync API in thread pool for async compatibility)
    def _generate():
        return client.models.generate_images(
            model=model_id,
            prompt=prompt,
            config=types.GenerateImagesConfig(**config_kwargs),
        )

    response = await asyncio.get_event_loop().run_in_executor(None, _generate)

    # Extract image from response
    image_data = None

    if response.generated_images and len(response.generated_images) > 0:
        generated_image = response.generated_images[0]
        if hasattr(generated_image, "image") and generated_image.image:
            if hasattr(generated_image.image, "image_bytes"):
                image_data = generated_image.image.image_bytes

    if not image_data:
        raise RuntimeError("No image data in response")

    # Determine output path
    if output_path:
        final_path = Path(output_path)
    else:
        config.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_path = config.output_dir / f"imagen_{timestamp}.png"

    # Handle base64 encoded data if needed
    if isinstance(image_data, str):
        image_bytes = base64.b64decode(image_data)
    else:
        image_bytes = image_data

    final_path.write_bytes(image_bytes)

    return GeneratedImage(
        path=final_path,
        prompt=prompt,
        model=model_config["name"],
        size=size,
        aspect_ratio=aspect_ratio,
    )


def generate_image_sync(
    prompt: str,
    config: ImageConfig | None = None,
    input_file: str | Path | None = None,
    output_path: str | Path | None = None,
) -> GeneratedImage:
    """Synchronous wrapper for generate_image.

    See generate_image() for full documentation.
    """
    return asyncio.run(
        generate_image(
            prompt=prompt,
            config=config,
            input_file=input_file,
            output_path=output_path,
        )
    )


# =============================================================================
# CLI Interface
# =============================================================================


def _cli_main() -> None:
    """CLI entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Generate images with Google Imagen/Gemini"
    )
    parser.add_argument("prompt", help="Text prompt for image generation")
    parser.add_argument(
        "--model",
        "-m",
        choices=["pro", "ultra", "flash"],
        default="pro",
        help="Model: pro, ultra, or flash (default: pro)",
    )
    parser.add_argument(
        "--size",
        "-s",
        choices=["1K", "2K", "4K"],
        default=None,
        help="Image size (default: 2K for pro/ultra, 1K for flash)",
    )
    parser.add_argument(
        "--aspect-ratio",
        "-a",
        choices=ASPECT_RATIOS,
        default="1:1",
        help="Aspect ratio (default: 1:1)",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        help="Input image for editing/transformation",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file path",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )

    args = parser.parse_args()

    try:
        config = ImageConfig(
            model=args.model,
            size=args.size,
            aspect_ratio=args.aspect_ratio,
            output_dir=args.output_dir,
        )

        print(f"Model: {MODELS[config.model]['name']}")
        print(f"Aspect Ratio: {config.aspect_ratio}")
        print(f"Prompt: {args.prompt[:100]}{'...' if len(args.prompt) > 100 else ''}")
        print("Generating image...")

        result = generate_image_sync(
            prompt=args.prompt,
            config=config,
            input_file=args.input,
            output_path=args.output,
        )

        print(f"\n✓ Image saved: {result.path}")
        print(f"  Size: {result.size}")

    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Install with: uv add google-genai", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
