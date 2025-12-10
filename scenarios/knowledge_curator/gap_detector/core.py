"""
Gap Detector Core - Detection logic for knowledge gaps.

Implements Tier 1 detection (bulk, automated):
- Undefined concepts: Terms mentioned but never explained
- Stale content: Files not updated in N months
- Orphan pages: Files not linked from anywhere
- Thin sections: Topics with < 100 words that deserve more

Detection follows Wikipedia editor philosophy: flag issues, don't fix them.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


class GapType(str, Enum):
    """Types of knowledge gaps."""

    UNDEFINED_CONCEPT = "undefined_concept"
    STALE_CONTENT = "stale_content"
    ORPHAN_PAGE = "orphan_page"
    THIN_SECTION = "thin_section"


class GapSeverity(str, Enum):
    """Severity levels for gaps."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class GapLocation:
    """Location of a gap in the vault."""

    file: str
    line: int | None = None
    context: str | None = None


@dataclass
class Gap:
    """A detected knowledge gap."""

    id: str
    type: GapType
    severity: GapSeverity
    location: GapLocation
    description: str
    detected_at: datetime = field(default_factory=datetime.now)
    dismissed: bool = False
    dismiss_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "severity": self.severity.value,
            "location": {
                "file": self.location.file,
                "line": self.location.line,
                "context": self.location.context,
            },
            "description": self.description,
            "detected_at": self.detected_at.isoformat(),
            "dismissed": self.dismissed,
            "dismiss_reason": self.dismiss_reason,
        }


@dataclass
class GapReport:
    """Report of all detected gaps."""

    vault: str
    domain: str | None
    generated_at: datetime
    gaps: list[Gap]

    @property
    def summary(self) -> dict[str, Any]:
        """Generate summary statistics."""
        by_type: dict[str, int] = defaultdict(int)
        by_severity: dict[str, int] = defaultdict(int)

        for gap in self.gaps:
            if not gap.dismissed:
                by_type[gap.type.value] += 1
                by_severity[gap.severity.value] += 1

        return {
            "total": len([g for g in self.gaps if not g.dismissed]),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "vault": self.vault,
            "domain": self.domain,
            "generated_at": self.generated_at.isoformat(),
            "gaps": [g.to_dict() for g in self.gaps],
            "summary": self.summary,
        }


class GapDetector:
    """
    Detects knowledge gaps in a markdown vault.

    Implements Wikipedia editor philosophy: flag issues, don't fix them.
    Detection is cheap and should run weekly.
    """

    # Patterns for extracting potential concepts from markdown
    CONCEPT_PATTERNS = [
        # [[wiki links]]
        r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]",
        # Bold text often indicates key concepts
        r"\*\*([^*]+)\*\*",
        # Headers (H2-H4) often define concepts
        r"^#{2,4}\s+(.+)$",
    ]

    # Patterns to skip (not concepts)
    SKIP_PATTERNS = [
        r"^http",  # URLs
        r"^\d+$",  # Pure numbers
        r"^[A-Z]{2,}$",  # Acronyms
        r"^(the|a|an|and|or|but|in|on|at|to|for|of|with)$",  # Common words
        r"related[-/]?concept",  # Placeholder patterns
        r"example[-/]?",  # Placeholder patterns
        r"display[-/]?name",  # Placeholder patterns
        r".*\\",  # Backslash-escaped paths (Obsidian escaping)
    ]

    # Minimum words for a "complete" section
    MIN_SECTION_WORDS = 100

    # Default staleness threshold (months)
    DEFAULT_STALE_MONTHS = 6

    def __init__(
        self,
        stale_months: int = DEFAULT_STALE_MONTHS,
        min_section_words: int = MIN_SECTION_WORDS,
    ):
        """
        Initialize the gap detector.

        Args:
            stale_months: Number of months before content is considered stale
            min_section_words: Minimum words for a section to be "complete"
        """
        self.stale_months = stale_months
        self.min_section_words = min_section_words
        self._concept_cache: dict[str, set[str]] = {}
        self._link_cache: dict[str, set[str]] = {}

    def detect_gaps(
        self,
        vault_path: Path,
        domain: str | None = None,
    ) -> GapReport:
        """
        Detect all knowledge gaps in a vault or domain.

        Args:
            vault_path: Path to the knowledge vault
            domain: Optional domain folder to limit detection

        Returns:
            GapReport with all detected gaps
        """
        target_path = vault_path / domain if domain else vault_path
        logger.info(f"Detecting gaps in: {target_path}")

        # Find all markdown files
        md_files = list(target_path.glob("**/*.md"))
        logger.info(f"Found {len(md_files)} markdown files")

        if not md_files:
            return GapReport(
                vault=str(vault_path),
                domain=domain,
                generated_at=datetime.now(),
                gaps=[],
            )

        # Build indices
        self._build_concept_index(md_files, vault_path)
        self._build_link_index(md_files, vault_path)

        # Detect gaps
        gaps: list[Gap] = []

        # 1. Undefined concepts (P1)
        undefined = self._detect_undefined_concepts(md_files, vault_path)
        gaps.extend(undefined)
        logger.info(f"Found {len(undefined)} undefined concepts")

        # 2. Stale content (P1)
        stale = self._detect_stale_content(md_files, vault_path)
        gaps.extend(stale)
        logger.info(f"Found {len(stale)} stale files")

        # 3. Orphan pages (P2)
        orphans = self._detect_orphan_pages(md_files, vault_path)
        gaps.extend(orphans)
        logger.info(f"Found {len(orphans)} orphan pages")

        # 4. Thin sections (P2)
        thin = self._detect_thin_sections(md_files, vault_path)
        gaps.extend(thin)
        logger.info(f"Found {len(thin)} thin sections")

        return GapReport(
            vault=str(vault_path),
            domain=domain,
            generated_at=datetime.now(),
            gaps=gaps,
        )

    def _build_concept_index(self, md_files: list[Path], vault_path: Path) -> None:
        """Build index of concepts defined in each file."""
        self._concept_cache.clear()

        for md_file in md_files:
            rel_path = str(md_file.relative_to(vault_path))
            defined_concepts: set[str] = set()

            try:
                content = md_file.read_text(encoding="utf-8")

                # File name itself is a defined concept
                stem = md_file.stem.lower().replace("-", " ").replace("_", " ")
                defined_concepts.add(stem)

                # H1 header is a defined concept
                h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                if h1_match:
                    defined_concepts.add(h1_match.group(1).lower().strip())

                # H2 headers define concepts within the file
                for match in re.finditer(r"^##\s+(.+)$", content, re.MULTILINE):
                    concept = match.group(1).lower().strip()
                    if len(concept) > 2:
                        defined_concepts.add(concept)

            except Exception as e:
                logger.debug(f"Error reading {rel_path}: {e}")

            self._concept_cache[rel_path] = defined_concepts

    def _build_link_index(self, md_files: list[Path], vault_path: Path) -> None:
        """Build index of which files link to which."""
        self._link_cache.clear()

        for md_file in md_files:
            rel_path = str(md_file.relative_to(vault_path))
            linked_files: set[str] = set()

            try:
                content = md_file.read_text(encoding="utf-8")

                # Find wiki links [[target]] or [[target|alias]]
                for match in re.finditer(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", content):
                    target = match.group(1).strip()
                    # Normalize: could be full path or just name
                    linked_files.add(target.lower())

                # Find markdown links [text](path.md)
                for match in re.finditer(r"\[([^\]]+)\]\(([^)]+\.md)\)", content):
                    target = match.group(2).strip()
                    linked_files.add(target.lower())

            except Exception as e:
                logger.debug(f"Error reading {rel_path}: {e}")

            self._link_cache[rel_path] = linked_files

    def _detect_undefined_concepts(self, md_files: list[Path], vault_path: Path) -> list[Gap]:
        """
        Detect concepts mentioned but never defined.

        A concept is "mentioned" if it appears in [[links]] or bold.
        A concept is "defined" if it's a file name or H1/H2 header.
        """
        gaps: list[Gap] = []

        # Collect all defined concepts
        all_defined: set[str] = set()
        for concepts in self._concept_cache.values():
            all_defined.update(concepts)

        # Find mentioned but undefined concepts
        seen_undefined: set[str] = set()  # Dedupe across files

        for md_file in md_files:
            rel_path = str(md_file.relative_to(vault_path))

            # Skip template/structure files (start with _)
            if md_file.name.startswith("_"):
                continue

            try:
                content = md_file.read_text(encoding="utf-8")

                # Find [[wiki links]]
                for match in re.finditer(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", content):
                    concept = match.group(1).strip().lower()

                    # Skip if already seen or defined
                    if concept in seen_undefined or concept in all_defined:
                        continue

                    # Skip patterns we don't want
                    if self._should_skip_concept(concept):
                        continue

                    # Check if this link resolves to a file
                    if self._concept_has_file(concept, vault_path):
                        continue

                    seen_undefined.add(concept)

                    # Get line number and context
                    line_num = content[: match.start()].count("\n") + 1
                    line_start = content.rfind("\n", 0, match.start()) + 1
                    line_end = content.find("\n", match.end())
                    if line_end == -1:
                        line_end = len(content)
                    context = content[line_start:line_end].strip()[:100]

                    gaps.append(
                        Gap(
                            id=self._make_gap_id("undefined_concept", concept),
                            type=GapType.UNDEFINED_CONCEPT,
                            severity=GapSeverity.HIGH,
                            location=GapLocation(
                                file=rel_path,
                                line=line_num,
                                context=context,
                            ),
                            description=f"Concept '{concept}' mentioned but never defined in vault",
                        )
                    )

            except Exception as e:
                logger.debug(f"Error detecting undefined concepts in {rel_path}: {e}")

        return gaps

    def _detect_stale_content(self, md_files: list[Path], vault_path: Path) -> list[Gap]:
        """Detect files not updated in N months."""
        gaps: list[Gap] = []
        now = datetime.now(tz=UTC)
        stale_threshold = now - timedelta(days=self.stale_months * 30)

        for md_file in md_files:
            rel_path = str(md_file.relative_to(vault_path))

            try:
                # Use file modification time
                mtime = datetime.fromtimestamp(md_file.stat().st_mtime, tz=UTC)

                if mtime < stale_threshold:
                    months_old = (now - mtime).days // 30

                    # Higher severity for older files
                    if months_old > 12:
                        severity = GapSeverity.HIGH
                    elif months_old > 6:
                        severity = GapSeverity.MEDIUM
                    else:
                        severity = GapSeverity.LOW

                    gaps.append(
                        Gap(
                            id=self._make_gap_id("stale_content", rel_path),
                            type=GapType.STALE_CONTENT,
                            severity=severity,
                            location=GapLocation(file=rel_path),
                            description=f"File not updated in {months_old} months (last: {mtime.strftime('%Y-%m')})",
                        )
                    )

            except Exception as e:
                logger.debug(f"Error checking staleness for {rel_path}: {e}")

        return gaps

    def _detect_orphan_pages(self, md_files: list[Path], vault_path: Path) -> list[Gap]:
        """Detect files not linked from anywhere."""
        gaps: list[Gap] = []

        # Build set of all linked targets
        all_linked: set[str] = set()
        for linked in self._link_cache.values():
            all_linked.update(linked)

        for md_file in md_files:
            rel_path = str(md_file.relative_to(vault_path))
            file_stem = md_file.stem.lower()

            # Skip special files
            if file_stem.startswith("_") or file_stem in ("readme", "index"):
                continue

            # Check if this file is linked from anywhere
            is_linked = False

            for target in all_linked:
                # Check various matching patterns
                if (
                    target == file_stem
                    or target == rel_path.lower()
                    or target.endswith(f"/{file_stem}")
                    or target.endswith(f"/{file_stem}.md")
                ):
                    is_linked = True
                    break

            if not is_linked:
                gaps.append(
                    Gap(
                        id=self._make_gap_id("orphan_page", rel_path),
                        type=GapType.ORPHAN_PAGE,
                        severity=GapSeverity.MEDIUM,
                        location=GapLocation(file=rel_path),
                        description="File not linked from anywhere in the vault",
                    )
                )

        return gaps

    def _detect_thin_sections(self, md_files: list[Path], vault_path: Path) -> list[Gap]:
        """Detect topics with very little content."""
        gaps: list[Gap] = []

        for md_file in md_files:
            rel_path = str(md_file.relative_to(vault_path))

            try:
                content = md_file.read_text(encoding="utf-8")

                # Count words (excluding code blocks and metadata)
                text = self._extract_prose(content)
                word_count = len(text.split())

                if word_count < self.min_section_words:
                    # Skip very short files that might be stubs or indexes
                    if word_count < 20:
                        severity = GapSeverity.LOW
                    else:
                        severity = GapSeverity.MEDIUM

                    gaps.append(
                        Gap(
                            id=self._make_gap_id("thin_section", rel_path),
                            type=GapType.THIN_SECTION,
                            severity=severity,
                            location=GapLocation(file=rel_path),
                            description=f"File has only {word_count} words (minimum: {self.min_section_words})",
                        )
                    )

            except Exception as e:
                logger.debug(f"Error checking thin sections in {rel_path}: {e}")

        return gaps

    def _extract_prose(self, content: str) -> str:
        """Extract prose text from markdown, excluding code and metadata."""
        # Remove YAML frontmatter
        content = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL)

        # Remove code blocks
        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)

        # Remove inline code
        content = re.sub(r"`[^`]+`", "", content)

        # Remove links but keep text
        content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
        content = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", r"\1", content)

        # Remove headers markers
        content = re.sub(r"^#+\s*", "", content, flags=re.MULTILINE)

        # Remove list markers
        content = re.sub(r"^\s*[-*+]\s*", "", content, flags=re.MULTILINE)
        content = re.sub(r"^\s*\d+\.\s*", "", content, flags=re.MULTILINE)

        return content

    def _should_skip_concept(self, concept: str) -> bool:
        """Check if a concept should be skipped."""
        for pattern in self.SKIP_PATTERNS:
            if re.match(pattern, concept, re.IGNORECASE):
                return True
        return len(concept) < 3

    def _concept_has_file(self, concept: str, vault_path: Path) -> bool:
        """Check if a concept corresponds to an existing file."""
        # Try various file patterns
        patterns = [
            f"**/{concept}.md",
            f"**/{concept.replace(' ', '-')}.md",
            f"**/{concept.replace(' ', '_')}.md",
        ]

        return any(list(vault_path.glob(pattern)) for pattern in patterns)

    def _make_gap_id(self, gap_type: str, identifier: str) -> str:
        """Generate a unique ID for a gap."""
        hash_input = f"{gap_type}:{identifier}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:8]
