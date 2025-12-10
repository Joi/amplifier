"""
Expansion Suggester Core - Generate content suggestions for knowledge gaps.

Implements lazy suggestion generation:
- User explicitly requests suggestions (not auto-generated during detection)
- Research via Tavily for authoritative content
- AI generates markdown expansions
- Staging area for user review
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from amplifier.utils.logger import get_logger

from ..gap_detector import Gap
from ..gap_detector import GapType

logger = get_logger(__name__)

# Default paths
DEFAULT_STAGING_DIR = Path.home() / ".data" / "knowledge_curator" / "staged"


class SuggestionType(str, Enum):
    """Types of expansion suggestions."""

    CREATE_PAGE = "create_page"  # For undefined concepts
    ADD_SECTION = "add_section"  # For thin sections
    UPDATE_CONTENT = "update_content"  # For stale content
    ADD_LINKS = "add_links"  # For orphan pages


class SuggestionStatus(str, Enum):
    """Status of a suggestion in the review workflow."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    APPLIED = "applied"


@dataclass
class ExpansionSuggestion:
    """A suggested expansion for a knowledge gap."""

    id: str
    gap_id: str
    gap_type: GapType
    suggestion_type: SuggestionType
    title: str
    description: str
    content: str  # Suggested markdown content
    target_file: str  # File to create or modify
    research_sources: list[str] = field(default_factory=list)
    confidence: float = 0.8
    status: SuggestionStatus = SuggestionStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    user_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "gap_id": self.gap_id,
            "gap_type": self.gap_type.value,
            "suggestion_type": self.suggestion_type.value,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "target_file": self.target_file,
            "research_sources": self.research_sources,
            "confidence": self.confidence,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "user_notes": self.user_notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpansionSuggestion:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            gap_id=data["gap_id"],
            gap_type=GapType(data["gap_type"]),
            suggestion_type=SuggestionType(data["suggestion_type"]),
            title=data["title"],
            description=data["description"],
            content=data["content"],
            target_file=data["target_file"],
            research_sources=data.get("research_sources", []),
            confidence=data.get("confidence", 0.8),
            status=SuggestionStatus(data.get("status", "pending")),
            created_at=datetime.fromisoformat(data["created_at"]),
            user_notes=data.get("user_notes"),
        )


class SuggestionStore:
    """Persistent storage for staged suggestions."""

    def __init__(self, staging_dir: Path = DEFAULT_STAGING_DIR):
        self.staging_dir = staging_dir
        self.staging_file = staging_dir / "suggestions.json"
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure staging directory exists."""
        self.staging_dir.mkdir(parents=True, exist_ok=True)

    def stage(self, suggestion: ExpansionSuggestion) -> None:
        """Add a suggestion to staging."""
        suggestions = self.load_all()

        # Replace if exists, otherwise append
        existing_ids = {s.id for s in suggestions}
        if suggestion.id in existing_ids:
            suggestions = [s if s.id != suggestion.id else suggestion for s in suggestions]
        else:
            suggestions.append(suggestion)

        self._save(suggestions)
        logger.debug(f"Staged suggestion: {suggestion.id}")

    def load_all(self) -> list[ExpansionSuggestion]:
        """Load all staged suggestions."""
        if not self.staging_file.exists():
            return []

        try:
            with open(self.staging_file, encoding="utf-8") as f:
                data = json.load(f)
            return [ExpansionSuggestion.from_dict(s) for s in data.get("suggestions", [])]
        except Exception as e:
            logger.error(f"Error loading staged suggestions: {e}")
            return []

    def load_pending(self) -> list[ExpansionSuggestion]:
        """Load only pending suggestions."""
        return [s for s in self.load_all() if s.status == SuggestionStatus.PENDING]

    def load_approved(self) -> list[ExpansionSuggestion]:
        """Load approved suggestions ready to apply."""
        return [s for s in self.load_all() if s.status == SuggestionStatus.APPROVED]

    def update_status(
        self,
        suggestion_id: str,
        status: SuggestionStatus,
        notes: str | None = None,
        content: str | None = None,
    ) -> bool:
        """Update suggestion status and optionally notes/content."""
        suggestions = self.load_all()

        for s in suggestions:
            if s.id == suggestion_id:
                s.status = status
                if notes is not None:
                    s.user_notes = notes
                if content is not None:
                    s.content = content
                    s.status = SuggestionStatus.MODIFIED
                self._save(suggestions)
                return True

        return False

    def clear_applied(self) -> int:
        """Remove applied suggestions from staging."""
        suggestions = self.load_all()
        original_count = len(suggestions)
        suggestions = [s for s in suggestions if s.status != SuggestionStatus.APPLIED]
        self._save(suggestions)
        return original_count - len(suggestions)

    def _save(self, suggestions: list[ExpansionSuggestion]) -> None:
        """Save suggestions to file."""
        data = {
            "suggestions": [s.to_dict() for s in suggestions],
            "updated_at": datetime.now(tz=UTC).isoformat(),
        }
        with open(self.staging_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class ExpansionSuggester:
    """
    Generate expansion suggestions for knowledge gaps.

    Uses Tavily for research and AI for content generation.
    Suggestions are staged for user review, never auto-applied.
    """

    def __init__(
        self,
        vault_path: Path,
        domain: str | None = None,
        store: SuggestionStore | None = None,
    ):
        self.vault_path = vault_path
        self.domain = domain
        self.store = store or SuggestionStore()
        self._tavily_client = None

    async def suggest_for_gap(self, gap: Gap) -> ExpansionSuggestion | None:
        """Generate a suggestion for a single gap."""
        try:
            if gap.type == GapType.UNDEFINED_CONCEPT:
                return await self._suggest_create_page(gap)
            if gap.type == GapType.THIN_SECTION:
                return await self._suggest_add_section(gap)
            if gap.type == GapType.STALE_CONTENT:
                return await self._suggest_update_content(gap)
            if gap.type == GapType.ORPHAN_PAGE:
                return await self._suggest_add_links(gap)
            logger.warning(f"Unknown gap type: {gap.type}")
            return None
        except Exception as e:
            logger.error(f"Error generating suggestion for gap {gap.id}: {e}")
            return None

    async def suggest_batch(
        self,
        gaps: list[Gap],
        limit: int = 5,
    ) -> list[ExpansionSuggestion]:
        """Generate suggestions for multiple gaps."""
        suggestions = []

        for gap in gaps[:limit]:
            suggestion = await self.suggest_for_gap(gap)
            if suggestion:
                self.store.stage(suggestion)
                suggestions.append(suggestion)
                logger.info(f"Generated suggestion: {suggestion.title}")

        return suggestions

    async def _suggest_create_page(self, gap: Gap) -> ExpansionSuggestion:
        """Suggest creating a new page for undefined concept."""
        concept = self._extract_concept_from_gap(gap)
        research = await self._research_concept(concept)

        # Generate page content
        content = await self._generate_page_content(concept, research)

        # Determine target file path
        target_file = self._concept_to_filepath(concept)

        return ExpansionSuggestion(
            id=self._make_suggestion_id(gap.id, "create_page"),
            gap_id=gap.id,
            gap_type=gap.type,
            suggestion_type=SuggestionType.CREATE_PAGE,
            title=f"Create page: {concept}",
            description=f"Create new page to define '{concept}' which is referenced but not explained",
            content=content,
            target_file=target_file,
            research_sources=research.get("sources", []),
            confidence=research.get("confidence", 0.7),
        )

    async def _suggest_add_section(self, gap: Gap) -> ExpansionSuggestion:
        """Suggest adding content to a thin section."""
        file_path = gap.location.file
        topic = Path(file_path).stem.replace("-", " ").replace("_", " ")

        # Read existing content
        full_path = self.vault_path / file_path
        existing_content = ""
        if full_path.exists():
            existing_content = full_path.read_text(encoding="utf-8")

        research = await self._research_topic_expansion(topic, existing_content)
        content = await self._generate_section_content(topic, existing_content, research)

        return ExpansionSuggestion(
            id=self._make_suggestion_id(gap.id, "add_section"),
            gap_id=gap.id,
            gap_type=gap.type,
            suggestion_type=SuggestionType.ADD_SECTION,
            title=f"Expand: {topic}",
            description=f"Add content to '{file_path}' which has insufficient depth",
            content=content,
            target_file=file_path,
            research_sources=research.get("sources", []),
            confidence=research.get("confidence", 0.7),
        )

    async def _suggest_update_content(self, gap: Gap) -> ExpansionSuggestion:
        """Suggest updating stale content."""
        file_path = gap.location.file
        topic = Path(file_path).stem.replace("-", " ").replace("_", " ")

        # Read existing content
        full_path = self.vault_path / file_path
        existing_content = ""
        if full_path.exists():
            existing_content = full_path.read_text(encoding="utf-8")

        research = await self._research_updates(topic, existing_content)
        content = await self._generate_update_content(topic, existing_content, research)

        return ExpansionSuggestion(
            id=self._make_suggestion_id(gap.id, "update_content"),
            gap_id=gap.id,
            gap_type=gap.type,
            suggestion_type=SuggestionType.UPDATE_CONTENT,
            title=f"Update: {topic}",
            description=f"Update stale content in '{file_path}'",
            content=content,
            target_file=file_path,
            research_sources=research.get("sources", []),
            confidence=research.get("confidence", 0.6),
        )

    async def _suggest_add_links(self, gap: Gap) -> ExpansionSuggestion:
        """Suggest adding links to orphan page."""
        file_path = gap.location.file
        topic = Path(file_path).stem.replace("-", " ").replace("_", " ")

        # Find related pages in vault
        related_pages = self._find_related_pages(file_path)
        content = self._generate_link_suggestions(file_path, related_pages)

        return ExpansionSuggestion(
            id=self._make_suggestion_id(gap.id, "add_links"),
            gap_id=gap.id,
            gap_type=gap.type,
            suggestion_type=SuggestionType.ADD_LINKS,
            title=f"Link: {topic}",
            description=f"Add links to orphan page '{file_path}' from related pages",
            content=content,
            target_file=file_path,
            research_sources=[],
            confidence=0.9,  # High confidence for internal linking
        )

    # Research methods

    async def _research_concept(self, concept: str) -> dict[str, Any]:
        """Research a concept using Tavily."""
        try:
            client = self._get_tavily_client()
            if not client:
                return {"content": "", "sources": [], "confidence": 0.5}

            # Build search query with domain context
            domain_context = self.domain.rstrip("/") if self.domain else ""
            query = f"{concept} {domain_context} definition meaning"

            response = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_raw_content=True,
            )

            sources = [r.get("url", "") for r in response.get("results", [])]
            content = "\n\n".join(r.get("content", "") for r in response.get("results", []))

            return {
                "content": content[:3000],  # Limit context
                "sources": sources,
                "confidence": 0.8 if sources else 0.5,
            }
        except Exception as e:
            logger.warning(f"Tavily research failed: {e}")
            return {"content": "", "sources": [], "confidence": 0.5}

    async def _research_topic_expansion(self, topic: str, existing_content: str) -> dict[str, Any]:
        """Research to expand a thin topic."""
        try:
            client = self._get_tavily_client()
            if not client:
                return {"content": "", "sources": [], "confidence": 0.5}

            domain_context = self.domain.rstrip("/") if self.domain else ""
            query = f"{topic} {domain_context} detailed explanation"

            response = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_raw_content=True,
            )

            sources = [r.get("url", "") for r in response.get("results", [])]
            content = "\n\n".join(r.get("content", "") for r in response.get("results", []))

            return {
                "content": content[:3000],
                "sources": sources,
                "confidence": 0.7 if sources else 0.5,
            }
        except Exception as e:
            logger.warning(f"Tavily research failed: {e}")
            return {"content": "", "sources": [], "confidence": 0.5}

    async def _research_updates(self, topic: str, existing_content: str) -> dict[str, Any]:
        """Research recent developments for stale content."""
        try:
            client = self._get_tavily_client()
            if not client:
                return {"content": "", "sources": [], "confidence": 0.5}

            domain_context = self.domain.rstrip("/") if self.domain else ""
            query = f"{topic} {domain_context} recent developments 2024 2025"

            response = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_raw_content=True,
            )

            sources = [r.get("url", "") for r in response.get("results", [])]
            content = "\n\n".join(r.get("content", "") for r in response.get("results", []))

            return {
                "content": content[:3000],
                "sources": sources,
                "confidence": 0.6 if sources else 0.4,
            }
        except Exception as e:
            logger.warning(f"Tavily research failed: {e}")
            return {"content": "", "sources": [], "confidence": 0.4}

    # Content generation methods

    async def _query_ai_content(self, prompt: str, content_type: str) -> str | None:
        """Query AI for content generation with graceful fallback.

        Returns generated content or None if AI unavailable/fails.
        """
        try:
            from amplifier.ccsdk_toolkit import ClaudeSession
            from amplifier.ccsdk_toolkit import SessionOptions

            # Domain-aware system prompt - be very explicit about output format
            domain_context = f" about {self.domain}" if self.domain else ""
            system_prompt = f"""You are a markdown content generator for an Obsidian vault{domain_context}.

CRITICAL: Output ONLY the raw markdown content. Do NOT:
- Explain what you're going to do
- Use any tools or read any files
- Add preamble like "I'll..." or "Let me..."
- Wrap content in code blocks

Just output the markdown directly, starting with the # heading.

Format guidelines:
- Use headers (##, ###) for structure
- Use [[wiki-links]] for related concepts
- Use bullet points for lists
- Keep content factual and well-organized"""

            options = SessionOptions(
                system_prompt=system_prompt,
                retry_attempts=2,
                max_turns=1,
            )

            async with ClaudeSession(options) as session:
                response = await session.query(prompt)
                if response.error:
                    logger.warning(f"AI generation error for {content_type}: {response.error}")
                    return None

                # Check for error messages in content (e.g., "Invalid API key")
                content = response.content
                if not content or "Invalid API key" in content or "API key" in content[:100]:
                    logger.warning(f"AI returned error in content for {content_type}")
                    return None

                # Filter out any preamble - find the first markdown heading
                content = self._clean_ai_response(content)
                return content

        except ImportError:
            logger.debug("Claude Code SDK not available, using template fallback")
            return None
        except Exception as e:
            logger.warning(f"AI generation failed for {content_type}: {e}")
            return None

    async def _generate_page_content(self, concept: str, research: dict[str, Any]) -> str:
        """Generate markdown page content for a concept."""
        research_text = research.get("content", "")
        sources = research.get("sources", [])

        # Build prompt for AI
        prompt = f"""Create a knowledge base page for the concept: "{concept}"

Research context:
{research_text[:2000] if research_text else "No research available."}

Generate a complete markdown page with:
1. Overview section explaining the concept
2. Key Points section with specific, factual bullet points
3. Related Concepts section with [[wiki-links]] to related topics

Output only the markdown content, starting with the # heading."""

        # Try AI generation
        ai_content = await self._query_ai_content(prompt, f"page:{concept}")
        if ai_content:
            # Append sources if available
            if sources:
                sources_section = "\n\n## Sources\n\n"
                for url in sources:
                    sources_section += f"- {url}\n"
                return ai_content + sources_section
            return ai_content

        # Fallback to template
        sources_section = ""
        if sources:
            sources_section = "\n## Sources\n\n"
            for url in sources:
                sources_section += f"- {url}\n"

        return f"""# {concept.title()}

## Overview

{research_text[:500] if research_text else f"[Add definition of {concept} here]"}

## Key Points

- [Add key point 1]
- [Add key point 2]
- [Add key point 3]

## Related Concepts

- [[related-concept-1]]
- [[related-concept-2]]
{sources_section}
"""

    async def _generate_section_content(self, topic: str, existing_content: str, research: dict[str, Any]) -> str:
        """Generate additional section content."""
        research_text = research.get("content", "")

        # Build prompt for AI
        prompt = f"""Expand the following knowledge base page about "{topic}".

Existing content (do not repeat):
{existing_content[:1500] if existing_content else "Empty page."}

Research to incorporate:
{research_text[:1500] if research_text else "No research available."}

Generate an additional section that:
1. Adds depth and detail not already covered
2. Includes specific key aspects as bullet points
3. Uses [[wiki-links]] for related concepts mentioned

Output only the markdown section, starting with ## heading."""

        # Try AI generation
        ai_content = await self._query_ai_content(prompt, f"section:{topic}")
        if ai_content:
            return ai_content

        # Fallback to template
        return f"""
## Additional Details

{research_text[:800] if research_text else f"[Add more details about {topic}]"}

### Key Aspects

- [Aspect 1]
- [Aspect 2]
- [Aspect 3]
"""

    async def _generate_update_content(self, topic: str, existing_content: str, research: dict[str, Any]) -> str:
        """Generate update suggestions for stale content."""
        research_text = research.get("content", "")
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")

        # Build prompt for AI
        prompt = f"""Update this knowledge base page about "{topic}" with recent developments.

Current content:
{existing_content[:1500] if existing_content else "Empty page."}

Recent research:
{research_text[:1500] if research_text else "No research available."}

Generate a "Recent Developments" section that:
1. Summarizes what has changed or is new
2. Notes the update date ({today})
3. Includes specific updates as bullet points

Output only the markdown section, starting with ## heading."""

        # Try AI generation
        ai_content = await self._query_ai_content(prompt, f"update:{topic}")
        if ai_content:
            return ai_content

        # Fallback to template
        return f"""
## Recent Developments

_Last updated: {today}_

{research_text[:800] if research_text else f"[Add recent developments about {topic}]"}

### Updates

- [Update 1]
- [Update 2]
"""

    def _find_related_pages(self, file_path: str) -> list[str]:
        """Find pages in vault that could link to this file."""
        related = []
        target_stem = Path(file_path).stem.lower()
        target_words = set(target_stem.replace("-", " ").replace("_", " ").split())

        target_path = self.vault_path / self.domain if self.domain else self.vault_path

        for md_file in target_path.glob("**/*.md"):
            if str(md_file.relative_to(self.vault_path)) == file_path:
                continue

            try:
                content = md_file.read_text(encoding="utf-8").lower()
                # Check if any target words appear in the content
                for word in target_words:
                    if len(word) > 3 and word in content:
                        related.append(str(md_file.relative_to(self.vault_path)))
                        break
            except Exception:
                pass

        return related[:10]  # Limit to 10

    def _generate_link_suggestions(self, file_path: str, related_pages: list[str]) -> str:
        """Generate link suggestion content."""
        file_stem = Path(file_path).stem
        link_name = file_stem.replace("-", " ").replace("_", " ").title()

        if not related_pages:
            return """
## Linking Suggestions

No related pages found. Consider:
- Adding a link from index or readme
- Mentioning this topic in related concept pages
- Adding to a "See Also" section in relevant pages
"""

        suggestions = f"""
## Suggested Links

Add link [[{file_stem}|{link_name}]] to these related pages:

"""
        for page in related_pages:
            suggestions += f"- {page}\n"

        return suggestions

    # Helper methods

    def _clean_ai_response(self, content: str) -> str:
        """Clean AI response by removing preamble and extracting markdown content.

        Some models may output thinking/planning text before the actual content.
        This extracts just the markdown portion.
        """
        import re

        # If content starts with a markdown heading, it's clean
        if content.strip().startswith("#"):
            return content.strip()

        # Try to find the first markdown heading
        heading_match = re.search(r"^(#{1,6}\s+.+)$", content, re.MULTILINE)
        if heading_match:
            # Return from the first heading onwards
            start_idx = heading_match.start()
            return content[start_idx:].strip()

        # If no heading found but content looks like it has structure, keep it
        if "##" in content or "- " in content:
            # Try to strip obvious preamble phrases
            preamble_patterns = [
                r"^I'll\s+.*?\.\s*",
                r"^Let me\s+.*?\.\s*",
                r"^Here's?\s+.*?:\s*",
                r"^I will\s+.*?\.\s*",
            ]
            cleaned = content
            for pattern in preamble_patterns:
                cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)
            return cleaned.strip()

        # Return as-is if we can't clean it
        return content.strip()

    def _extract_concept_from_gap(self, gap: Gap) -> str:
        """Extract concept name from gap description."""
        # Gap description format: "Concept 'X' mentioned but never defined..."
        desc = gap.description
        if "'" in desc:
            start = desc.find("'") + 1
            end = desc.find("'", start)
            if end > start:
                return desc[start:end]

        # Fallback: use context or file stem
        if gap.location.context:
            # Try to extract from [[link]]
            import re

            match = re.search(r"\[\[([^\]|]+)", gap.location.context)
            if match:
                return match.group(1).split("/")[-1]

        return Path(gap.location.file).stem

    def _concept_to_filepath(self, concept: str) -> str:
        """Convert concept name to file path.

        Preserves the original path structure from the wiki link when possible.
        """
        # Normalize: lowercase, replace spaces with hyphens
        filepath = concept.lower().replace(" ", "-").replace("'", "")

        # If concept already has a path structure, preserve it
        if "/" in filepath:
            # Ensure .md extension
            if not filepath.endswith(".md"):
                filepath = f"{filepath}.md"
            return filepath

        # Add domain path if set (for simple concept names)
        if self.domain:
            domain_path = self.domain.rstrip("/")
            return f"{domain_path}/concepts/{filepath}.md"

        return f"concepts/{filepath}.md"

    def _make_suggestion_id(self, gap_id: str, suggestion_type: str) -> str:
        """Generate unique suggestion ID."""
        hash_input = f"{gap_id}:{suggestion_type}:{datetime.now(tz=UTC).isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    def _get_tavily_client(self):
        """Get or create Tavily client."""
        if self._tavily_client is None:
            api_key = os.environ.get("TAVILY_API_KEY")
            if api_key:
                try:
                    from tavily import TavilyClient

                    self._tavily_client = TavilyClient(api_key=api_key)
                except ImportError:
                    logger.warning("Tavily not installed, research disabled")
                    return None
            else:
                logger.warning("TAVILY_API_KEY not set, research disabled")
                return None

        return self._tavily_client
