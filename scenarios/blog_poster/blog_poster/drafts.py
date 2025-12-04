"""Draft workspace management for blog posts."""

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class PhotoNote:
    """A photo with its context."""

    filename: str
    caption: str = ""
    context: str = ""  # What's happening, why it matters
    order: int = 0  # Suggested position in post


@dataclass
class DraftWorkspace:
    """Workspace for collecting blog post materials."""

    # Metadata
    blog_slug: str
    working_title: str
    event_date: str = ""
    language: str = "English"

    # Context for the AI to understand
    event_type: str = ""  # e.g., "tea gathering", "practice session", "seasonal event"
    occasion: str = ""  # e.g., "New Year's first tea", "memorial gathering"
    location: str = ""
    participants: str = ""  # Who was there, their roles

    # Tea ceremony specifics
    tea_details: str = ""  # Type of tea, preparation style
    sweets: str = ""  # Wagashi served
    utensils: str = ""  # Notable tea ware
    seasonal_elements: str = ""  # Flowers, scroll, seasonal references

    # Content
    key_moments: str = ""  # What stood out, memorable moments
    reflections: str = ""  # Personal thoughts, what you learned
    mood: str = ""  # The atmosphere, feeling of the event

    # Photos
    photos: list[PhotoNote] = field(default_factory=list)

    # Additional notes
    raw_notes: str = ""  # Any other notes, stream of consciousness

    def save(self, path: Path) -> None:
        """Save workspace to JSON file."""
        data = asdict(self)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path) -> "DraftWorkspace":
        """Load workspace from JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        photos = [PhotoNote(**p) for p in data.pop("photos", [])]
        return cls(**data, photos=photos)

    def to_prompt_context(self) -> str:
        """Generate context string for AI draft generation."""
        lines = [
            "# Blog Post Draft Context",
            "",
            f"**Blog:** {self.blog_slug}",
            f"**Working Title:** {self.working_title}",
            f"**Event Date:** {self.event_date}",
            f"**Language:** {self.language}",
            "",
        ]

        if self.event_type or self.occasion:
            lines.append("## Event")
            if self.event_type:
                lines.append(f"- Type: {self.event_type}")
            if self.occasion:
                lines.append(f"- Occasion: {self.occasion}")
            if self.location:
                lines.append(f"- Location: {self.location}")
            if self.participants:
                lines.append(f"- Participants: {self.participants}")
            lines.append("")

        if any([self.tea_details, self.sweets, self.utensils, self.seasonal_elements]):
            lines.append("## Tea Ceremony Details")
            if self.tea_details:
                lines.append(f"- Tea: {self.tea_details}")
            if self.sweets:
                lines.append(f"- Sweets: {self.sweets}")
            if self.utensils:
                lines.append(f"- Utensils: {self.utensils}")
            if self.seasonal_elements:
                lines.append(f"- Seasonal elements: {self.seasonal_elements}")
            lines.append("")

        if self.key_moments:
            lines.append("## Key Moments")
            lines.append(self.key_moments)
            lines.append("")

        if self.reflections:
            lines.append("## Reflections")
            lines.append(self.reflections)
            lines.append("")

        if self.mood:
            lines.append("## Mood/Atmosphere")
            lines.append(self.mood)
            lines.append("")

        if self.photos:
            lines.append("## Photos")
            for i, photo in enumerate(sorted(self.photos, key=lambda p: p.order), 1):
                lines.append(f"### Photo {i}: {photo.filename}")
                if photo.caption:
                    lines.append(f"Caption: {photo.caption}")
                if photo.context:
                    lines.append(f"Context: {photo.context}")
                lines.append("")

        if self.raw_notes:
            lines.append("## Additional Notes")
            lines.append(self.raw_notes)
            lines.append("")

        return "\n".join(lines)


def create_workspace_template(
    blog_slug: str,
    title: str = "Untitled Post",
    event_date: str | None = None,
) -> DraftWorkspace:
    """Create a new draft workspace with defaults."""
    return DraftWorkspace(
        blog_slug=blog_slug,
        working_title=title,
        event_date=event_date or date.today().isoformat(),
    )
