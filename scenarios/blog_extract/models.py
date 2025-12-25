"""Data models for blog extraction."""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime


@dataclass
class Entities:
    """Named entities extracted from a blog post."""

    people: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    places: list[str] = field(default_factory=list)


@dataclass
class BlogExtraction:
    """Extraction result for a single blog post."""

    id: str
    source_file: str
    title: str
    date: str
    permalink: str
    language: str
    topics: list[str]
    entities: Entities
    summary: str
    key_quotes: list[str]
    extracted_at: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "source_file": self.source_file,
            "title": self.title,
            "date": self.date,
            "permalink": self.permalink,
            "language": self.language,
            "topics": self.topics,
            "entities": {
                "people": self.entities.people,
                "organizations": self.entities.organizations,
                "places": self.entities.places,
            },
            "summary": self.summary,
            "key_quotes": self.key_quotes,
            "extracted_at": self.extracted_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BlogExtraction":
        """Create from dictionary."""
        entities_data = data.get("entities", {})
        return cls(
            id=data["id"],
            source_file=data["source_file"],
            title=data["title"],
            date=data["date"],
            permalink=data["permalink"],
            language=data["language"],
            topics=data.get("topics", []),
            entities=Entities(
                people=entities_data.get("people", []),
                organizations=entities_data.get("organizations", []),
                places=entities_data.get("places", []),
            ),
            summary=data.get("summary", ""),
            key_quotes=data.get("key_quotes", []),
            extracted_at=data.get("extracted_at", datetime.now().isoformat()),
        )
