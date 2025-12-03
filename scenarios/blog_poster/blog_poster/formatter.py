"""Format content for Notion blog posts."""

import re
from dataclasses import dataclass, field


@dataclass
class ImageRef:
    """Reference to an image in a blog post."""

    url: str
    caption: str = ""
    position: int = 0


@dataclass
class ContentSection:
    """A section of blog content."""

    text: str
    image: ImageRef | None = None
    is_heading: bool = False
    heading_level: int = 2


@dataclass
class BlogContent:
    """Structured blog content ready for Notion."""

    title: str
    sections: list[ContentSection] = field(default_factory=list)
    publish_date: str | None = None
    photographer: str | None = None
    writer: str | None = None
    language: str = "English"

    def to_notion_markdown(self) -> str:
        """Convert to Notion-flavored markdown.

        Returns:
            Formatted markdown string for Notion.
        """
        lines = []

        for section in self.sections:
            if section.is_heading:
                prefix = "#" * section.heading_level
                lines.append(f"{prefix} {section.text}")
                lines.append("<empty-block/>")
            elif section.image:
                # Add image with empty blocks for spacing
                lines.append("<empty-block/>")
                if section.image.caption:
                    lines.append(f'<image source="{section.image.url}">{section.image.caption}</image>')
                else:
                    lines.append(f'<image source="{section.image.url}"></image>')
                lines.append("<empty-block/>")
                if section.text:
                    lines.append(section.text)
                    lines.append("<empty-block/>")
            else:
                lines.append(section.text)
                lines.append("<empty-block/>")

        return "\n".join(lines)

    def to_properties(self, schema: dict[str, str]) -> dict:
        """Convert to Notion properties dict.

        Args:
            schema: Mapping of property names in the blog schema.

        Returns:
            Properties dict for notion-create-pages.
        """
        props = {schema.get("title", "Title"): self.title}

        if self.publish_date and schema.get("date"):
            props[f"date:{schema['date']}:start"] = self.publish_date
            props[f"date:{schema['date']}:is_datetime"] = 0

        if self.photographer and schema.get("photographer"):
            props[schema["photographer"]] = self.photographer

        if self.writer and schema.get("writer"):
            props[schema["writer"]] = self.writer

        if self.language and schema.get("language"):
            props[schema["language"]] = self.language

        return props


def parse_content_file(content: str) -> BlogContent:
    """Parse a markdown content file into structured BlogContent.

    Expected format:
    ```
    # Post Title

    Opening paragraph...

    [IMAGE: url-or-filename]
    Description of the image...

    ## Optional Heading

    More text...
    ```

    Args:
        content: Raw markdown content

    Returns:
        Structured BlogContent object
    """
    lines = content.strip().split("\n")
    blog = BlogContent(title="Untitled")
    sections: list[ContentSection] = []

    current_text: list[str] = []
    pending_image: ImageRef | None = None
    image_index = 0

    for line in lines:
        line = line.rstrip()

        # Title (H1)
        if line.startswith("# ") and blog.title == "Untitled":
            blog.title = line[2:].strip()
            continue

        # Heading (H2, H3)
        heading_match = re.match(r"^(#{2,3})\s+(.+)$", line)
        if heading_match:
            # Save any pending text
            if current_text:
                text = "\n".join(current_text).strip()
                if text:
                    sections.append(ContentSection(text=text, image=pending_image))
                    pending_image = None
                current_text = []

            level = len(heading_match.group(1))
            sections.append(ContentSection(text=heading_match.group(2), is_heading=True, heading_level=level))
            continue

        # Image reference
        image_match = re.match(r"^\[IMAGE:\s*(.+?)\]$", line, re.IGNORECASE)
        if image_match:
            # Save any pending text first
            if current_text:
                text = "\n".join(current_text).strip()
                if text:
                    sections.append(ContentSection(text=text, image=pending_image))
                    pending_image = None
                current_text = []

            pending_image = ImageRef(url=image_match.group(1).strip(), position=image_index)
            image_index += 1
            continue

        # Regular text
        current_text.append(line)

    # Handle remaining text
    if current_text:
        text = "\n".join(current_text).strip()
        if text:
            sections.append(ContentSection(text=text, image=pending_image))

    blog.sections = sections
    return blog


def format_blog_content(
    title: str,
    paragraphs: list[str],
    images: list[str] | None = None,
    image_positions: list[int] | None = None,
) -> str:
    """Format blog content with images interspersed.

    This is a simpler alternative to parse_content_file for programmatic use.

    Args:
        title: Blog post title (not included in output, just for reference)
        paragraphs: List of text paragraphs
        images: List of image URLs
        image_positions: Which paragraph index each image should precede.
                        If None, images are placed before paragraphs 1, 2, 3, etc.

    Returns:
        Notion-flavored markdown string
    """
    images = images or []
    if image_positions is None:
        image_positions = list(range(1, len(images) + 1))

    # Create mapping of position -> image
    image_map = dict(zip(image_positions, images))

    lines = []
    for i, para in enumerate(paragraphs):
        # Check if an image goes before this paragraph
        if i in image_map:
            lines.append("<empty-block/>")
            lines.append(f'<image source="{image_map[i]}"></image>')
            lines.append("<empty-block/>")

        lines.append(para)
        lines.append("<empty-block/>")

    # Any remaining images go at the end
    for pos, url in image_map.items():
        if pos >= len(paragraphs):
            lines.append("<empty-block/>")
            lines.append(f'<image source="{url}"></image>')
            lines.append("<empty-block/>")

    return "\n".join(lines)
