#!/usr/bin/env python3
"""
Claude tool for Google's Nano Banana Pro (Gemini 3 Pro Image) generation.

Usage:
    python imagen.py <prompt> [options]

Examples:
    python imagen.py "A serene mountain landscape at sunset"
    python imagen.py "A cat in a garden" --size 2K --aspect-ratio 16:9
    python imagen.py "Transform this into watercolor" --input photo.jpg
    python imagen.py "A logo with the text 'Hello World'" --model pro
"""

from __future__ import annotations

import argparse
import base64
import sys
from datetime import datetime
from pathlib import Path

# Add amplifier to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from amplifier.utils.secrets import get_gemini_api_key

try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]
    GENAI_AVAILABLE = False


# Model configurations
MODELS = {
    "pro": {
        "id": "gemini-3-pro-image-preview",
        "name": "Nano Banana Pro",
        "sizes": ["1K", "2K", "4K"],
        "default_size": "2K",
    },
    "flash": {
        "id": "gemini-2.5-flash-image",
        "name": "Nano Banana",
        "sizes": ["1K"],  # Fixed size
        "default_size": "1K",
    },
}

ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]

# Default output directory
OUTPUT_DIR = Path.home() / "Downloads" / "imagen"


def get_client() -> genai.Client:
    """Initialize Google Genai client with API key from secrets."""
    if not GENAI_AVAILABLE:
        print("Error: google-genai package not installed.")
        print("Install with: uv add google-genai")
        sys.exit(1)

    api_key = get_gemini_api_key()
    return genai.Client(api_key=api_key)


def load_input_file(file_path: Path) -> types.Part:
    """Load an input file (image) for editing/transformation."""
    if not file_path.exists():
        print(f"Error: Input file not found: {file_path}")
        sys.exit(1)

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


def generate_image(
    prompt: str,
    model_key: str = "pro",
    size: str | None = None,
    aspect_ratio: str = "1:1",
    input_files: list[Path] | None = None,
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    """Generate an image using Google's Gemini image generation API.

    Args:
        prompt: Text description for image generation
        model_key: "pro" for Nano Banana Pro, "flash" for Nano Banana
        size: Image size (1K, 2K, 4K) - Pro only, flash is fixed
        aspect_ratio: Aspect ratio (e.g., "16:9", "1:1")
        input_files: Optional input images for editing/transformation
        output_dir: Directory to save the output

    Returns:
        Path to the generated image
    """
    if not types:
        print("Error: google-genai package not available")
        sys.exit(1)

    model_config = MODELS.get(model_key, MODELS["pro"])
    model_id = model_config["id"]

    # Validate and set size
    if size is None:
        size = model_config["default_size"]
    elif size not in model_config["sizes"]:
        print(f"Warning: Size '{size}' not supported for {model_config['name']}.")
        print(f"Using default: {model_config['default_size']}")
        size = model_config["default_size"]

    # Validate aspect ratio
    if aspect_ratio not in ASPECT_RATIOS:
        print(f"Warning: Aspect ratio '{aspect_ratio}' not supported.")
        print(f"Using default: 1:1")
        aspect_ratio = "1:1"

    print(f"Model: {model_config['name']} ({model_id})")
    print(f"Size: {size}, Aspect Ratio: {aspect_ratio}")
    print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

    client = get_client()

    # Build content parts
    contents: list = []

    # Add input files if provided
    if input_files:
        for file_path in input_files:
            print(f"Loading input: {file_path}")
            contents.append(load_input_file(file_path))

    # Add text prompt
    contents.append(prompt)

    # Build image config - only include image_size for pro model
    image_config_kwargs: dict = {"aspect_ratio": aspect_ratio}
    if model_key == "pro":
        image_config_kwargs["image_size"] = size

    # Generate
    print("Generating image...")
    response = client.models.generate_content(
        model=model_id,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(**image_config_kwargs),
        ),
    )

    # Extract image from response
    image_data = None
    response_text = None

    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data:
            image_data = part.inline_data.data
        elif hasattr(part, "text") and part.text:
            response_text = part.text

    if response_text:
        print(f"Response text: {response_text}")

    if not image_data:
        print("Error: No image data in response")
        if response_text:
            print(f"Model response: {response_text}")
        sys.exit(1)

    # Save image
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"imagen_{timestamp}.png"

    # Handle base64 encoded data if needed
    if isinstance(image_data, str):
        image_bytes = base64.b64decode(image_data)
    else:
        image_bytes = image_data

    output_path.write_bytes(image_bytes)
    print(f"Image saved: {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate images with Google's Nano Banana Pro (Gemini 3 Pro Image)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "A serene mountain landscape at sunset"
  %(prog)s "A cat playing in a garden" --size 2K --aspect-ratio 16:9
  %(prog)s "Transform this into a watercolor painting" --input photo.jpg
  %(prog)s "A logo with 'Hello World' text" --model pro --size 4K
  %(prog)s "Quick sketch of a robot" --model flash
        """,
    )

    parser.add_argument("prompt", help="Text prompt for image generation")
    parser.add_argument(
        "--model",
        "-m",
        choices=["pro", "flash"],
        default="pro",
        help="Model: 'pro' (Nano Banana Pro) or 'flash' (Nano Banana). Default: pro",
    )
    parser.add_argument(
        "--size",
        "-s",
        choices=["1K", "2K", "4K"],
        default=None,
        help="Image size (pro only: 1K/2K/4K, flash is fixed at 1K). Default: 2K for pro",
    )
    parser.add_argument(
        "--aspect-ratio",
        "-a",
        choices=ASPECT_RATIOS,
        default="1:1",
        help="Aspect ratio. Default: 1:1",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        action="append",
        dest="input_files",
        help="Input image file for editing/transformation (can be used multiple times)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory. Default: {OUTPUT_DIR}",
    )

    args = parser.parse_args()

    try:
        output_path = generate_image(
            prompt=args.prompt,
            model_key=args.model,
            size=args.size,
            aspect_ratio=args.aspect_ratio,
            input_files=args.input_files,
            output_dir=args.output_dir,
        )
        print(f"\nSuccess! Image saved to: {output_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
