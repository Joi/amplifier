"""Blog configuration management."""

import json
from pathlib import Path

from pydantic import BaseModel, Field


class BlogSchema(BaseModel):
    """Schema mapping for a blog database."""

    title: str = "Title"
    date: str = "Publish Date"
    photographer: str | None = None
    writer: str | None = None
    language: str | None = None
    tags: str | None = None


class BlogDefaults(BaseModel):
    """Default values for blog properties."""

    photographer: str | None = None
    writer: str | None = None
    language: str | None = None


class BlogConfig(BaseModel):
    """Configuration for a single blog."""

    name: str = Field(description="Human-readable blog name")
    description: str | None = Field(default=None, description="Blog description")
    data_source: str = Field(description="Notion collection:// URL")
    database_id: str = Field(description="Notion database ID")
    main_page: str | None = Field(default=None, description="Main page ID for navigation")
    schema_mapping: BlogSchema = Field(default_factory=BlogSchema, alias="schema")
    languages: list[str] = Field(default_factory=list, description="Available language options")
    defaults: BlogDefaults = Field(default_factory=BlogDefaults)
    navigation_synced_block: str | None = Field(default=None, description="Synced block ID for navigation")

    class Config:
        """Pydantic config."""

        populate_by_name = True


def load_blogs(config_path: Path | None = None) -> dict[str, BlogConfig]:
    """Load blog configurations from JSON file.

    Args:
        config_path: Path to blogs.json. Defaults to same directory as this module.

    Returns:
        Dictionary mapping blog slug to BlogConfig.
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "blogs.json"

    if not config_path.exists():
        return {}

    with open(config_path) as f:
        data = json.load(f)

    blogs = {}
    for slug, config in data.items():
        blogs[slug] = BlogConfig(**config)

    return blogs


def save_blogs(blogs: dict[str, BlogConfig], config_path: Path | None = None) -> None:
    """Save blog configurations to JSON file.

    Args:
        blogs: Dictionary of blog configs to save.
        config_path: Path to blogs.json.
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "blogs.json"

    data = {}
    for slug, config in blogs.items():
        data[slug] = config.model_dump(by_alias=True, exclude_none=True)

    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)


def get_blog(slug: str, config_path: Path | None = None) -> BlogConfig | None:
    """Get a specific blog configuration.

    Args:
        slug: Blog identifier (e.g., "tea-journey")
        config_path: Path to blogs.json

    Returns:
        BlogConfig or None if not found.
    """
    blogs = load_blogs(config_path)
    return blogs.get(slug)
