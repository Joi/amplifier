#!/usr/bin/env python3
"""
Google Slides Standardization Tool using Nano Banana Pro (Gemini 3 Pro Image).

Analyzes a Google Slides presentation for visual inconsistencies and
standardizes the look across all slides while preserving editability.

Usage:
    uv run python scripts/standardize_slides.py <google-slides-url>
    uv run python scripts/standardize_slides.py  # Interactive mode

Prerequisites:
    - Google Cloud Project with Slides API + Drive API enabled
    - OAuth credentials in ~/.config/amplifier/google/credentials.json
    - GEMINI_API_KEY environment variable set

Author: Claude (Amplifier)
Date: 2026-01-04
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "amplifier" / "google"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"

# Google API scopes needed
SCOPES = [
    "https://www.googleapis.com/auth/presentations",  # Read/write slides
    "https://www.googleapis.com/auth/drive",  # Full Drive access (export + upload)
]


@dataclass
class SlideStyle:
    """Detected style for a single slide."""

    slide_id: str
    slide_index: int
    title_font: str | None = None
    title_size: float | None = None
    title_color: str | None = None
    body_font: str | None = None
    body_size: float | None = None
    body_color: str | None = None
    background_color: str | None = None


@dataclass
class StyleAnalysis:
    """Aggregated style analysis across all slides."""

    slide_styles: list[SlideStyle] = field(default_factory=list)
    title_fonts: Counter = field(default_factory=Counter)
    title_sizes: Counter = field(default_factory=Counter)
    title_colors: Counter = field(default_factory=Counter)
    body_fonts: Counter = field(default_factory=Counter)
    body_sizes: Counter = field(default_factory=Counter)
    body_colors: Counter = field(default_factory=Counter)
    background_colors: Counter = field(default_factory=Counter)

    def add_slide(self, style: SlideStyle) -> None:
        """Add a slide's style to the analysis."""
        self.slide_styles.append(style)
        if style.title_font:
            self.title_fonts[style.title_font] += 1
        if style.title_size:
            self.title_sizes[style.title_size] += 1
        if style.title_color:
            self.title_colors[style.title_color] += 1
        if style.body_font:
            self.body_fonts[style.body_font] += 1
        if style.body_size:
            self.body_sizes[style.body_size] += 1
        if style.body_color:
            self.body_colors[style.body_color] += 1
        if style.background_color:
            self.background_colors[style.background_color] += 1

    def get_recommended_style(self, reference_slides: list[int] | None = None) -> dict[str, Any]:
        """Get recommended standard style.

        Args:
            reference_slides: If provided, use these slide numbers (1-based) as the basis.
                             Otherwise, use the most common values across all slides.
        """
        if reference_slides:
            # Build style from reference slides only
            ref_styles = [s for s in self.slide_styles if s.slide_index in reference_slides]
            if not ref_styles:
                logger.warning(f"No styles found for reference slides {reference_slides}")
                return self.get_recommended_style(None)  # Fall back to majority

            # Use first non-None value from reference slides for each property
            result: dict[str, Any] = {}
            for key in [
                "title_font",
                "title_size",
                "title_color",
                "body_font",
                "body_size",
                "body_color",
                "background_color",
            ]:
                for style in ref_styles:
                    val = getattr(style, key, None)
                    if val is not None:
                        result[key] = val
                        break
                if key not in result:
                    result[key] = None
            return result

        # Default: use most common values
        return {
            "title_font": self.title_fonts.most_common(1)[0][0] if self.title_fonts else None,
            "title_size": self.title_sizes.most_common(1)[0][0] if self.title_sizes else None,
            "title_color": self.title_colors.most_common(1)[0][0] if self.title_colors else None,
            "body_font": self.body_fonts.most_common(1)[0][0] if self.body_fonts else None,
            "body_size": self.body_sizes.most_common(1)[0][0] if self.body_sizes else None,
            "body_color": self.body_colors.most_common(1)[0][0] if self.body_colors else None,
            "background_color": (self.background_colors.most_common(1)[0][0] if self.background_colors else None),
        }

    def find_inconsistencies(self, recommended: dict[str, Any]) -> list[dict[str, Any]]:
        """Find slides that don't match the recommended style."""
        issues = []
        for style in self.slide_styles:
            slide_issues = []
            if style.title_font and style.title_font != recommended.get("title_font"):
                slide_issues.append(f"title font: {style.title_font}")
            if style.title_size and style.title_size != recommended.get("title_size"):
                slide_issues.append(f"title size: {style.title_size}pt")
            if style.title_color and style.title_color != recommended.get("title_color"):
                slide_issues.append(f"title color: {style.title_color}")
            if style.body_font and style.body_font != recommended.get("body_font"):
                slide_issues.append(f"body font: {style.body_font}")
            if style.body_size and style.body_size != recommended.get("body_size"):
                slide_issues.append(f"body size: {style.body_size}pt")
            if style.background_color and style.background_color != recommended.get("background_color"):
                slide_issues.append(f"background: {style.background_color}")

            if slide_issues:
                issues.append(
                    {
                        "slide_index": style.slide_index,
                        "slide_id": style.slide_id,
                        "issues": slide_issues,
                    }
                )
        return issues


class GoogleSlidesClient:
    """Client for Google Slides API operations."""

    def __init__(self) -> None:
        """Initialize the client."""
        self._slides_service = None
        self._drive_service = None
        self._credentials = None

    def _get_credentials(self):
        """Get or refresh Google OAuth credentials."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = None

        # Load existing token
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Google credentials...")
                creds.refresh(Request())
            else:
                if not CREDENTIALS_FILE.exists():
                    raise FileNotFoundError(
                        f"Google OAuth credentials not found at {CREDENTIALS_FILE}\n"
                        "Please download from Google Cloud Console and save there."
                    )
                logger.info("Starting OAuth flow - browser will open...")
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            TOKEN_FILE.write_text(creds.to_json())
            logger.info(f"Saved credentials to {TOKEN_FILE}")

        self._credentials = creds
        return creds

    @property
    def slides_service(self):
        """Get Google Slides API service."""
        if self._slides_service is None:
            from googleapiclient.discovery import build

            creds = self._get_credentials()
            self._slides_service = build("slides", "v1", credentials=creds)
        return self._slides_service

    @property
    def drive_service(self):
        """Get Google Drive API service."""
        if self._drive_service is None:
            from googleapiclient.discovery import build

            creds = self._get_credentials()
            self._drive_service = build("drive", "v3", credentials=creds)
        return self._drive_service

    def get_presentation(self, presentation_id: str) -> dict[str, Any]:
        """Fetch presentation metadata and structure."""
        logger.info(f"Fetching presentation: {presentation_id}")
        return self.slides_service.presentations().get(presentationId=presentation_id).execute()

    def export_slide_as_image(self, presentation_id: str, slide_id: str, output_path: Path) -> Path:
        """Export a single slide as PNG image."""
        # Get slide thumbnail
        response = (
            self.slides_service.presentations()
            .pages()
            .getThumbnail(
                presentationId=presentation_id,
                pageObjectId=slide_id,
                thumbnailProperties_mimeType="PNG",
                thumbnailProperties_thumbnailSize="LARGE",
            )
            .execute()
        )

        # Download the image
        import urllib.request

        thumbnail_url = response.get("contentUrl")
        if thumbnail_url:
            urllib.request.urlretrieve(thumbnail_url, output_path)
            logger.debug(f"Exported slide {slide_id} to {output_path}")
            return output_path

        raise RuntimeError(f"Failed to get thumbnail for slide {slide_id}")

    def export_as_pdf(self, presentation_id: str, output_path: Path) -> Path:
        """Export entire presentation as PDF (captures actual visual appearance)."""
        import io

        logger.info("Exporting presentation as PDF...")

        # Use Drive API to export as PDF
        request = self.drive_service.files().export_media(fileId=presentation_id, mimeType="application/pdf")

        # Download the PDF
        from googleapiclient.http import MediaIoBaseDownload

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                logger.debug(f"Download {int(status.progress() * 100)}%")

        # Write to file
        output_path.write_bytes(fh.getvalue())
        logger.info(f"Exported PDF to {output_path} ({output_path.stat().st_size:,} bytes)")
        return output_path

    def pdf_to_images(self, pdf_path: Path, output_dir: Path, dpi: int = 150) -> list[Path]:
        """Convert PDF pages to PNG images using pdftoppm."""
        import subprocess

        cmd = [
            "pdftoppm",
            "-png",
            "-r",
            str(dpi),
            str(pdf_path),
            str(output_dir / "slide"),
        ]

        logger.info("Converting PDF to images...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"pdftoppm failed: {result.stderr}")

        # Find generated images
        images = sorted(output_dir.glob("slide-*.png"))
        logger.info(f"Generated {len(images)} slide images from PDF")
        return images

    def apply_updates(self, presentation_id: str, requests: list[dict]) -> dict:
        """Apply batch updates to presentation."""
        if not requests:
            logger.info("No updates to apply")
            return {}

        logger.info(f"Applying {len(requests)} updates...")
        body = {"requests": requests}
        response = self.slides_service.presentations().batchUpdate(presentationId=presentation_id, body=body).execute()
        return response

    def upload_image_to_drive(self, image_path: Path) -> str:
        """Upload an image to Google Drive and return the file ID."""
        from googleapiclient.http import MediaFileUpload

        file_metadata = {
            "name": image_path.name,
            "mimeType": "image/png",
        }

        media = MediaFileUpload(
            str(image_path),
            mimetype="image/png",
            resumable=True,
        )

        file = (
            self.drive_service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id,webContentLink",
            )
            .execute()
        )

        file_id = file.get("id")
        logger.info(f"Uploaded image to Drive: {file_id}")

        # Make file publicly accessible (required for Slides API to use it)
        self.drive_service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        return file_id

    def insert_fullsize_image(
        self,
        presentation_id: str,
        slide_id: str,
        image_url: str,
        presentation: dict,
    ) -> dict:
        """Insert a full-slide image overlay on a slide.

        Args:
            presentation_id: Google Slides presentation ID
            slide_id: Target slide object ID
            image_url: Public URL of the image to insert
            presentation: Presentation data (for getting slide dimensions)

        Returns:
            API response
        """
        # Get slide dimensions from presentation
        page_size = presentation.get("pageSize", {})
        width = page_size.get("width", {}).get("magnitude", 9144000)  # Default 10 inches
        height = page_size.get("height", {}).get("magnitude", 5143500)  # Default ~5.6 inches
        unit = page_size.get("width", {}).get("unit", "EMU")

        requests = [
            {
                "createImage": {
                    "url": image_url,
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": width, "unit": unit},
                            "height": {"magnitude": height, "unit": unit},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 0,
                            "translateY": 0,
                            "unit": unit,
                        },
                    },
                }
            }
        ]

        return self.apply_updates(presentation_id, requests)


class NanoBananaAnalyzer:
    """Analyze and generate slides using Nano Banana Pro (Gemini 3 Pro Image)."""

    # Use Gemini 3 Pro Image (Nano Banana Pro) for best quality
    MODEL = "gemini-3-pro-image-preview"
    # Fallback to 2.5 Flash for speed/cost
    FALLBACK_MODEL = "gemini-2.5-flash"

    def __init__(self) -> None:
        """Initialize the analyzer."""
        self._client = None

    @property
    def client(self):
        """Lazy-load Gemini client."""
        if self._client is None:
            from google import genai

            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def generate_slide_image(
        self,
        original_image: Path,
        style_guide: str,
        slide_index: int,
        output_path: Path,
    ) -> Path | None:
        """Generate a standardized 16:9 slide image using Nano Banana Pro.

        Args:
            original_image: Path to the original slide image
            style_guide: Description of the desired style
            slide_index: Slide number for logging
            output_path: Where to save the generated image

        Returns:
            Path to generated image, or None if generation failed
        """
        prompt = f"""Recreate this presentation slide with the following style guidelines:

{style_guide}

IMPORTANT:
- Maintain the same content and message as the original
- Output a clean, professional 16:9 presentation slide
- Use consistent typography, colors, and layout
- Make it visually cohesive with the style guide
- Keep text legible and well-positioned
- Preserve any key data, charts, or information

Generate a high-quality presentation slide image."""

        try:
            # Upload original image for reference
            uploaded = self.client.files.upload(file=str(original_image))

            # Generate new slide image
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=[uploaded, prompt],
                config={
                    "response_modalities": ["image", "text"],
                },
            )

            # Extract generated image
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        # Save the generated image
                        image_data = part.inline_data.data
                        output_path.write_bytes(image_data)
                        logger.info(f"Generated slide {slide_index}: {output_path}")
                        return output_path

            logger.warning(f"No image generated for slide {slide_index}")
            return None

        except Exception as e:
            logger.error(f"Failed to generate slide {slide_index}: {e}")
            return None

    def analyze_slide_style(self, image_path: Path, slide_index: int) -> dict[str, Any]:
        """Analyze a single slide image for style properties."""
        prompt = """Analyze this presentation slide and extract the following style properties.
Return a JSON object with these fields (use null if not detectable):

{
    "title_font": "font family name for the title/header",
    "title_size": approximate font size in points (number),
    "title_color": hex color code like "#333333",
    "body_font": "font family name for body text",
    "body_size": approximate font size in points (number),
    "body_color": hex color code,
    "background_color": hex color code for slide background,
    "has_title": true/false,
    "has_body_text": true/false,
    "notes": "any relevant observations about the design"
}

Be precise about font identification. Common presentation fonts include:
- Sans-serif: Arial, Helvetica, Open Sans, Roboto, Montserrat, Lato, Source Sans Pro
- Serif: Times New Roman, Georgia, Playfair Display
- Display: Impact, Oswald

Return ONLY the JSON object, no other text."""

        try:
            # Upload image
            uploaded = self.client.files.upload(file=str(image_path))

            # Generate analysis
            response = self.client.models.generate_content(
                model=self.FALLBACK_MODEL,  # Use faster model for style extraction
                contents=[uploaded, prompt],
            )

            # Parse JSON response
            if response.text:
                # Extract JSON from response (handle markdown code blocks)
                text = response.text.strip()
                if text.startswith("```"):
                    text = re.sub(r"```(?:json)?\n?", "", text)
                    text = text.rstrip("`").strip()

                return json.loads(text)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse style analysis for slide {slide_index}: {e}")
        except Exception as e:
            logger.warning(f"Style analysis failed for slide {slide_index}: {e}")

        return {}

    def analyze_presentation_holistically(self, image_paths: list[Path]) -> dict[str, Any]:
        """Analyze all slides together for comprehensive style assessment."""
        if not image_paths:
            return {}

        # For holistic analysis, sample a few slides
        sample_paths = image_paths[:5] if len(image_paths) > 5 else image_paths

        prompt = """Analyze these presentation slides as a collection and identify:

1. STYLE CONSISTENCY: What visual elements are consistent vs inconsistent?
2. DOMINANT STYLE: What appears to be the intended design system?
3. RECOMMENDATIONS: What changes would make the presentation more cohesive?

Return a JSON object:
{
    "dominant_style": {
        "title_font": "most common title font",
        "title_size": most common size (number),
        "title_color": "#hex",
        "body_font": "most common body font",
        "body_size": most common size (number),
        "body_color": "#hex",
        "background_color": "#hex"
    },
    "consistency_score": 1-10 rating,
    "inconsistencies": [
        "description of inconsistency 1",
        "description of inconsistency 2"
    ],
    "recommendations": [
        "recommendation 1",
        "recommendation 2"
    ]
}

Return ONLY the JSON object."""

        try:
            # Upload all sample images
            uploads = [self.client.files.upload(file=str(p)) for p in sample_paths]

            # Generate analysis
            response = self.client.models.generate_content(
                model=self.MODEL,  # Use Nano Banana Pro for holistic analysis
                contents=[*uploads, prompt],
            )

            if response.text:
                text = response.text.strip()
                if text.startswith("```"):
                    text = re.sub(r"```(?:json)?\n?", "", text)
                    text = text.rstrip("`").strip()
                return json.loads(text)

        except Exception as e:
            logger.warning(f"Holistic analysis failed: {e}")

        return {}


def extract_presentation_id(url: str) -> str:
    """Extract presentation ID from Google Slides URL."""
    # Handle various URL formats
    patterns = [
        r"/presentation/d/([a-zA-Z0-9_-]+)",  # Standard format
        r"/d/([a-zA-Z0-9_-]+)",  # Shortened format
        r"^([a-zA-Z0-9_-]{20,})$",  # Direct ID
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract presentation ID from: {url}")


def extract_styles_from_presentation(presentation: dict) -> StyleAnalysis:
    """Extract style information directly from presentation structure."""
    analysis = StyleAnalysis()

    slides = presentation.get("slides", [])

    for idx, slide in enumerate(slides):
        slide_id = slide.get("objectId", "")
        style = SlideStyle(slide_id=slide_id, slide_index=idx + 1)

        # Extract background color
        bg = slide.get("slideProperties", {}).get("notesPage", {})
        page_bg = slide.get("slideProperties", {}).get("pageBackgroundFill", {})
        if page_bg:
            solid_fill = page_bg.get("solidFill", {})
            if solid_fill:
                color = solid_fill.get("color", {}).get("rgbColor", {})
                if color:
                    r = int(color.get("red", 0) * 255)
                    g = int(color.get("green", 0) * 255)
                    b = int(color.get("blue", 0) * 255)
                    style.background_color = f"#{r:02x}{g:02x}{b:02x}"

        # Extract text styles from page elements
        for element in slide.get("pageElements", []):
            shape = element.get("shape", {})
            if not shape:
                continue

            placeholder = shape.get("placeholder", {})
            placeholder_type = placeholder.get("type", "")

            text = shape.get("text", {})
            text_elements = text.get("textElements", [])

            for te in text_elements:
                text_run = te.get("textRun", {})
                text_style = text_run.get("style", {})

                if text_style:
                    font_family = text_style.get("fontFamily")
                    font_size = text_style.get("fontSize", {}).get("magnitude")
                    fg_color = text_style.get("foregroundColor", {}).get("opaqueColor", {})
                    rgb = fg_color.get("rgbColor", {})

                    color_hex = None
                    if rgb:
                        r = int(rgb.get("red", 0) * 255)
                        g = int(rgb.get("green", 0) * 255)
                        b = int(rgb.get("blue", 0) * 255)
                        color_hex = f"#{r:02x}{g:02x}{b:02x}"

                    # Classify as title or body based on placeholder type
                    if placeholder_type in ("TITLE", "CENTERED_TITLE", "SUBTITLE"):
                        if font_family and not style.title_font:
                            style.title_font = font_family
                        if font_size and not style.title_size:
                            style.title_size = font_size
                        if color_hex and not style.title_color:
                            style.title_color = color_hex
                    elif placeholder_type in ("BODY", "OBJECT"):
                        if font_family and not style.body_font:
                            style.body_font = font_family
                        if font_size and not style.body_size:
                            style.body_size = font_size
                        if color_hex and not style.body_color:
                            style.body_color = color_hex

        analysis.add_slide(style)

    return analysis


def generate_update_requests(
    presentation: dict,
    recommended_style: dict[str, Any],
    inconsistencies: list[dict],
) -> list[dict]:
    """Generate Slides API batchUpdate requests to fix inconsistencies."""
    requests = []

    for issue in inconsistencies:
        slide_id = issue["slide_id"]

        # Find the slide in presentation
        slide = None
        for s in presentation.get("slides", []):
            if s.get("objectId") == slide_id:
                slide = s
                break

        if not slide:
            continue

        # Generate requests for each page element
        for element in slide.get("pageElements", []):
            shape = element.get("shape", {})
            if not shape:
                continue

            object_id = element.get("objectId")
            placeholder = shape.get("placeholder", {})
            placeholder_type = placeholder.get("type", "")

            # Skip elements with no text content
            text_content = shape.get("text", {})
            text_elements = text_content.get("textElements", [])
            has_text = any(te.get("textRun", {}).get("content", "").strip() for te in text_elements)
            if not has_text:
                continue

            # Determine target style based on placeholder type
            if placeholder_type in ("TITLE", "CENTERED_TITLE", "SUBTITLE"):
                target_font = recommended_style.get("title_font")
                target_size = recommended_style.get("title_size")
                target_color = recommended_style.get("title_color")
            elif placeholder_type in ("BODY", "OBJECT"):
                target_font = recommended_style.get("body_font")
                target_size = recommended_style.get("body_size")
                target_color = recommended_style.get("body_color")
            else:
                continue

            # Build text style update
            text_style = {}
            fields = []

            if target_font:
                text_style["fontFamily"] = target_font
                fields.append("fontFamily")

            if target_size:
                text_style["fontSize"] = {"magnitude": target_size, "unit": "PT"}
                fields.append("fontSize")

            if target_color:
                # Parse hex color
                hex_color = target_color.lstrip("#")
                r = int(hex_color[0:2], 16) / 255
                g = int(hex_color[2:4], 16) / 255
                b = int(hex_color[4:6], 16) / 255
                text_style["foregroundColor"] = {"opaqueColor": {"rgbColor": {"red": r, "green": g, "blue": b}}}
                fields.append("foregroundColor")

            if text_style and fields:
                requests.append(
                    {
                        "updateTextStyle": {
                            "objectId": object_id,
                            "style": text_style,
                            "textRange": {"type": "ALL"},
                            "fields": ",".join(fields),
                        }
                    }
                )

        # Update background color if needed
        bg_color = recommended_style.get("background_color")
        if bg_color and "background" in str(issue.get("issues", [])):
            hex_color = bg_color.lstrip("#")
            r = int(hex_color[0:2], 16) / 255
            g = int(hex_color[2:4], 16) / 255
            b = int(hex_color[4:6], 16) / 255

            requests.append(
                {
                    "updatePageProperties": {
                        "objectId": slide_id,
                        "pageProperties": {
                            "pageBackgroundFill": {
                                "solidFill": {"color": {"rgbColor": {"red": r, "green": g, "blue": b}}}
                            }
                        },
                        "fields": "pageBackgroundFill",
                    }
                }
            )

    return requests


def print_analysis(
    analysis: StyleAnalysis,
    recommended: dict[str, Any],
    inconsistencies: list[dict],
    holistic: dict[str, Any] | None = None,
) -> None:
    """Print analysis results to console."""
    print("\n" + "=" * 60)
    print("STYLE ANALYSIS")
    print("=" * 60)

    print(f"\nAnalyzed {len(analysis.slide_styles)} slides\n")

    print("FONTS DETECTED:")
    if analysis.title_fonts:
        print("  Headers:", end=" ")
        for font, count in analysis.title_fonts.most_common(3):
            print(f"{font} ({count} slides)", end=", ")
        print()
    if analysis.body_fonts:
        print("  Body:", end=" ")
        for font, count in analysis.body_fonts.most_common(3):
            print(f"{font} ({count} slides)", end=", ")
        print()

    print("\nCOLORS DETECTED:")
    if analysis.background_colors:
        print("  Backgrounds:", end=" ")
        for color, count in analysis.background_colors.most_common(3):
            print(f"{color} ({count})", end=", ")
        print()
    if analysis.title_colors:
        print("  Title text:", end=" ")
        for color, count in analysis.title_colors.most_common(3):
            print(f"{color} ({count})", end=", ")
        print()

    if inconsistencies:
        print(f"\nINCONSISTENCIES FOUND ({len(inconsistencies)} slides):")
        for issue in inconsistencies[:10]:  # Show first 10
            print(f"  Slide {issue['slide_index']}: {', '.join(issue['issues'])}")
        if len(inconsistencies) > 10:
            print(f"  ... and {len(inconsistencies) - 10} more")

    print("\n" + "-" * 60)
    print("RECOMMENDED STANDARD (based on majority):")
    print("-" * 60)
    if recommended.get("title_font"):
        size = recommended.get("title_size", "?")
        color = recommended.get("title_color", "?")
        print(f"  Title: {recommended['title_font']} {size}pt {color}")
    if recommended.get("body_font"):
        size = recommended.get("body_size", "?")
        color = recommended.get("body_color", "?")
        print(f"  Body: {recommended['body_font']} {size}pt {color}")
    if recommended.get("background_color"):
        print(f"  Background: {recommended['background_color']}")

    if holistic:
        score = holistic.get("consistency_score", "?")
        print(f"\n  AI Consistency Score: {score}/10")
        if holistic.get("recommendations"):
            print("\n  AI Recommendations:")
            for rec in holistic["recommendations"][:3]:
                print(f"    - {rec}")

    print()


def interactive_confirm(recommended: dict[str, Any], inconsistencies: list[dict]) -> tuple[bool, dict[str, Any]]:
    """Interactively confirm or edit the recommended style."""
    if not inconsistencies:
        print("No inconsistencies found - presentation is already consistent!")
        return False, recommended

    print(f"\nThis will update {len(inconsistencies)} slides to match the recommended style.")
    response = input("Accept? [Y/n/edit] ").strip().lower()

    if response == "n" or response == "no":
        print("Aborted.")
        return False, recommended

    if response == "edit" or response == "e":
        print("\nEdit recommended style (press Enter to keep current value):\n")

        new_style = recommended.copy()

        for key in ["title_font", "body_font"]:
            current = recommended.get(key, "")
            new_val = input(f"  {key} [{current}]: ").strip()
            if new_val:
                new_style[key] = new_val

        for key in ["title_size", "body_size"]:
            current = recommended.get(key, "")
            new_val = input(f"  {key} [{current}]: ").strip()
            if new_val:
                try:
                    new_style[key] = float(new_val)
                except ValueError:
                    print(f"    Invalid number, keeping {current}")

        for key in ["title_color", "body_color", "background_color"]:
            current = recommended.get(key, "")
            new_val = input(f"  {key} [{current}]: ").strip()
            if new_val:
                if not new_val.startswith("#"):
                    new_val = "#" + new_val
                new_style[key] = new_val

        print("\nUpdated style:")
        for k, v in new_style.items():
            if v:
                print(f"  {k}: {v}")

        confirm = input("\nApply this style? [Y/n] ").strip().lower()
        if confirm == "n" or confirm == "no":
            return False, new_style
        return True, new_style

    return True, recommended


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Standardize Google Slides presentation style using AI analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze and standardize a presentation
    uv run python scripts/standardize_slides.py \\
        "https://docs.google.com/presentation/d/1abc.../edit"

    # Dry run (analyze only, don't apply changes)
    uv run python scripts/standardize_slides.py \\
        "https://docs.google.com/presentation/d/1abc.../edit" \\
        --dry-run

    # Use AI vision analysis for more accurate style detection
    uv run python scripts/standardize_slides.py \\
        "https://docs.google.com/presentation/d/1abc.../edit" \\
        --use-vision
""",
    )

    parser.add_argument(
        "url",
        nargs="?",
        help="Google Slides URL or presentation ID",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze only, don't apply changes",
    )
    parser.add_argument(
        "--use-vision",
        action="store_true",
        help="Use Nano Banana Pro vision analysis for more accurate detection",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--reference-slides",
        type=str,
        help="Comma-separated slide numbers to use as style basis (e.g., '1,3,5')",
    )
    parser.add_argument(
        "--exclude-colors",
        type=str,
        help="Comma-separated hex colors to exclude/replace (e.g., '#FF0000,#FFA500')",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate new slide images with Nano Banana Pro and overlay them (replaces content)",
    )
    parser.add_argument(
        "--style-guide",
        type=str,
        help="Style description for image generation (e.g., 'dark blue tech theme, clean typography')",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to save generated images (for preview before applying)",
    )

    args = parser.parse_args()

    # Get URL interactively if not provided
    if not args.url:
        args.url = input("Enter Google Slides URL: ").strip()
        if not args.url:
            print("No URL provided. Exiting.")
            sys.exit(1)

    # Extract presentation ID
    try:
        presentation_id = extract_presentation_id(args.url)
        logger.info(f"Presentation ID: {presentation_id}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Initialize clients
    try:
        slides_client = GoogleSlidesClient()
    except Exception as e:
        print(f"Failed to initialize Google Slides client: {e}")
        print("\nMake sure you have:")
        print(f"  1. credentials.json in {CREDENTIALS_FILE}")
        print("  2. Google Slides API enabled in your Cloud project")
        sys.exit(1)

    # Fetch presentation
    try:
        presentation = slides_client.get_presentation(presentation_id)
        title = presentation.get("title", "Untitled")
        slides = presentation.get("slides", [])
        print(f"\nPresentation: {title}")
        print(f"Slides: {len(slides)}")
    except Exception as e:
        print(f"Failed to fetch presentation: {e}")
        sys.exit(1)

    # Parse reference slides if provided
    reference_slides = None
    if args.reference_slides:
        try:
            reference_slides = [int(s.strip()) for s in args.reference_slides.split(",")]
            print(f"\nUsing slides {reference_slides} as style reference")
        except ValueError:
            print(f"Invalid --reference-slides format: {args.reference_slides}")
            print("Expected comma-separated numbers like: 1,3,5")
            sys.exit(1)

    # Parse excluded colors if provided
    exclude_colors = set()
    if args.exclude_colors:
        for color in args.exclude_colors.split(","):
            color = color.strip().lower()
            if not color.startswith("#"):
                color = "#" + color
            exclude_colors.add(color)
        print(f"Excluding colors: {exclude_colors}")

    # Analyze styles
    print("\nAnalyzing styles...")

    # Always do structural analysis
    analysis = extract_styles_from_presentation(presentation)
    recommended = analysis.get_recommended_style(reference_slides)

    # Remove excluded colors from recommendations
    if exclude_colors:
        for key in ["title_color", "body_color", "background_color"]:
            if recommended.get(key) and recommended[key].lower() in exclude_colors:
                # Find next most common color that's not excluded
                counter = getattr(analysis, key.replace("_color", "_colors") + "s", None)
                if counter:
                    for color, _ in counter.most_common():
                        if color.lower() not in exclude_colors:
                            recommended[key] = color
                            break

    inconsistencies = analysis.find_inconsistencies(recommended)

    # Optionally enhance with vision analysis
    holistic = None
    if args.use_vision:
        print("Running AI vision analysis (using PDF export for true visual appearance)...")
        try:
            analyzer = NanoBananaAnalyzer()

            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)
                image_paths = []

                # Export as PDF first (captures overlaid images correctly)
                pdf_path = tmpdir / "presentation.pdf"
                try:
                    slides_client.export_as_pdf(presentation_id, pdf_path)
                    # Convert PDF to images
                    image_paths = slides_client.pdf_to_images(pdf_path, tmpdir)
                except Exception as e:
                    logger.warning(f"PDF export failed: {e}")
                    print("  (Falling back to thumbnail export...)")
                    # Fallback to individual slide thumbnails
                    for i, slide in enumerate(slides[:10]):
                        slide_id = slide.get("objectId")
                        image_path = tmpdir / f"slide_{i + 1:03d}.png"
                        try:
                            slides_client.export_slide_as_image(presentation_id, slide_id, image_path)
                            image_paths.append(image_path)
                        except Exception as e2:
                            logger.warning(f"Failed to export slide {i + 1}: {e2}")

                if image_paths:
                    holistic = analyzer.analyze_presentation_holistically(image_paths)
                    # Merge holistic recommendations if available
                    if holistic and holistic.get("dominant_style"):
                        for key, value in holistic["dominant_style"].items():
                            if value and not recommended.get(key):
                                recommended[key] = value

        except Exception as e:
            logger.warning(f"Vision analysis failed: {e}")
            print("  (Falling back to structural analysis only)")

    # Print results
    print_analysis(analysis, recommended, inconsistencies, holistic)

    # Dry run stops here
    if args.dry_run:
        print("Dry run - no changes applied.")
        return

    # GENERATION MODE: Create new slides with Nano Banana Pro
    if args.generate:
        print("\n" + "=" * 60)
        print("GENERATION MODE: Creating standardized slide images")
        print("=" * 60)

        # Get style guide
        style_guide = args.style_guide
        if not style_guide:
            # Build default style guide from analysis
            style_parts = []
            if recommended.get("background_color"):
                style_parts.append(f"Background: {recommended['background_color']}")
            if recommended.get("title_font"):
                style_parts.append(f"Title font: {recommended['title_font']} {recommended.get('title_size', '')}pt")
            if recommended.get("title_color"):
                style_parts.append(f"Title color: {recommended['title_color']}")
            if holistic and holistic.get("recommendations"):
                style_parts.extend(holistic["recommendations"][:2])

            style_guide = "\n".join(style_parts) if style_parts else "Clean, professional, consistent styling"
            print(f"\nUsing auto-generated style guide:\n{style_guide}\n")

        # Setup output directory
        output_dir = args.output_dir or Path(tempfile.mkdtemp(prefix="slides_gen_"))
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")

        analyzer = NanoBananaAnalyzer()
        generated_images = []

        # Export slides as images for reference
        print("\nExporting current slides...")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Try PDF export first, fall back to thumbnails
            try:
                pdf_path = tmpdir / "presentation.pdf"
                slides_client.export_as_pdf(presentation_id, pdf_path)
                source_images = slides_client.pdf_to_images(pdf_path, tmpdir)
            except Exception as e:
                logger.warning(f"PDF export failed: {e}")
                print("  Using thumbnail export...")
                source_images = []
                for i, slide in enumerate(slides):
                    slide_id = slide.get("objectId")
                    image_path = tmpdir / f"slide_{i + 1:03d}.png"
                    try:
                        slides_client.export_slide_as_image(presentation_id, slide_id, image_path)
                        source_images.append(image_path)
                    except Exception as e2:
                        logger.warning(f"Failed to export slide {i + 1}: {e2}")

            # Generate new images for each slide
            print(f"\nGenerating {len(source_images)} new slide images with Nano Banana Pro...")
            for i, source_image in enumerate(source_images):
                slide_index = i + 1
                output_path = output_dir / f"slide_{slide_index:03d}.png"

                # Skip if already generated
                if output_path.exists() and output_path.stat().st_size > 10000:
                    print(f"  Slide {slide_index}/{len(source_images)}: using existing ✓")
                    generated_images.append((slide_index, output_path))
                    continue

                print(f"  Generating slide {slide_index}/{len(source_images)}...", end=" ", flush=True)
                result = analyzer.generate_slide_image(
                    original_image=source_image,
                    style_guide=style_guide,
                    slide_index=slide_index,
                    output_path=output_path,
                )

                if result:
                    generated_images.append((slide_index, result))
                    print("✓")
                else:
                    print("✗ (failed)")

        print(f"\n✅ Generated {len(generated_images)} slide images")
        print(f"   Preview them in: {output_dir}")

        if not generated_images:
            print("No images generated. Exiting.")
            return

        # Ask to apply
        if not args.yes:
            response = input("\nApply these images to the presentation? [y/N] ").strip().lower()
            if response not in ("y", "yes"):
                print(f"Images saved to {output_dir} - you can apply them manually.")
                return

        # Upload and insert images
        print("\nUploading and inserting images...")
        for slide_index, image_path in generated_images:
            slide_id = slides[slide_index - 1].get("objectId")
            print(f"  Slide {slide_index}: uploading...", end=" ", flush=True)

            try:
                # Upload to Drive
                file_id = slides_client.upload_image_to_drive(image_path)
                image_url = f"https://drive.google.com/uc?id={file_id}"

                # Insert as full-slide image
                slides_client.insert_fullsize_image(presentation_id, slide_id, image_url, presentation)
                print("✓")
            except Exception as e:
                print(f"✗ ({e})")

        print("\n" + "=" * 60)
        print("SUCCESS! Presentation has been updated with generated images.")
        print("=" * 60)
        print(f"\nView: https://docs.google.com/presentation/d/{presentation_id}/edit")
        return

    # Interactive confirmation
    if args.yes:
        apply_changes = bool(inconsistencies)
        final_style = recommended
    else:
        apply_changes, final_style = interactive_confirm(recommended, inconsistencies)

    if not apply_changes:
        return

    # Recalculate inconsistencies if style was edited
    if final_style != recommended:
        inconsistencies = analysis.find_inconsistencies(final_style)

    # Generate and apply updates
    requests = generate_update_requests(presentation, final_style, inconsistencies)

    if not requests:
        print("No updates to apply.")
        return

    print(f"\nApplying {len(requests)} updates...")
    try:
        slides_client.apply_updates(presentation_id, requests)
        print("\n" + "=" * 60)
        print("SUCCESS! Presentation has been standardized.")
        print("=" * 60)
        print(f"\nView: https://docs.google.com/presentation/d/{presentation_id}/edit")
    except Exception as e:
        print(f"Failed to apply updates: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
