"""Integrate blog extractions with vault content via cross-linking."""

import json
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EntityMatch:
    """A matched entity between extraction and vault."""

    entity_name: str
    entity_type: str  # people, organizations
    vault_file: Path
    blog_posts: list[dict] = field(default_factory=list)


@dataclass
class TopicMatch:
    """A matched topic between blog and vault concepts."""

    topic_name: str
    concept_file: Path
    post_count: int


class BlogIntegrator:
    """Cross-link blog extractions with vault content."""

    def __init__(
        self,
        extractions_dir: Path,
        vault_dir: Path,
        blog_topics_dir: Path,
    ):
        """Initialize integrator.

        Args:
            extractions_dir: Directory containing extraction JSON files
            vault_dir: Root switchboard vault directory
            blog_topics_dir: Directory containing generated topic pages
        """
        self.extractions_dir = extractions_dir
        self.vault_dir = vault_dir
        self.blog_topics_dir = blog_topics_dir

        # Vault directories to scan
        self.people_dir = vault_dir / "people"
        self.orgs_dir = vault_dir / "organizations"
        self.concepts_dir = vault_dir / "concepts"

        # Loaded data
        self.extractions: list[dict] = []
        self.vault_people: dict[str, Path] = {}  # lowercase name -> file path
        self.vault_orgs: dict[str, Path] = {}
        self.vault_concepts: dict[str, Path] = {}

        # Matches found
        self.entity_matches: list[EntityMatch] = []
        self.topic_matches: list[TopicMatch] = []

    def load_extractions(self) -> int:
        """Load all extraction files."""
        count = 0
        for json_path in self.extractions_dir.glob("**/*.json"):
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                self.extractions.append(data)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to load {json_path}: {e}")
        logger.info(f"Loaded {count} extractions")
        return count

    def load_vault_index(self) -> None:
        """Index vault files for matching."""
        # Index people
        if self.people_dir.exists():
            for md_file in self.people_dir.glob("*.md"):
                name = md_file.stem.lower()
                self.vault_people[name] = md_file
            logger.info(f"Indexed {len(self.vault_people)} people files")

        # Index organizations
        if self.orgs_dir.exists():
            for md_file in self.orgs_dir.glob("*.md"):
                name = md_file.stem.lower()
                self.vault_orgs[name] = md_file
            logger.info(f"Indexed {len(self.vault_orgs)} organization files")

        # Index concepts
        if self.concepts_dir.exists():
            for md_file in self.concepts_dir.glob("*.md"):
                name = md_file.stem.lower()
                self.vault_concepts[name] = md_file
            logger.info(f"Indexed {len(self.vault_concepts)} concept files")

    def find_entity_matches(self) -> list[EntityMatch]:
        """Find entities in extractions that match vault files."""
        # Aggregate entities across all extractions
        people_mentions: dict[str, list[dict]] = defaultdict(list)
        org_mentions: dict[str, list[dict]] = defaultdict(list)

        for ext in self.extractions:
            post_info = {
                "title": ext.get("title", ""),
                "date": ext.get("date", ""),
                "permalink": ext.get("permalink", ""),
            }

            entities = ext.get("entities", {})

            for person in entities.get("people", []):
                people_mentions[person.lower()].append(post_info)

            for org in entities.get("organizations", []):
                org_mentions[org.lower()].append(post_info)

        # Match with vault
        for name, posts in people_mentions.items():
            if name in self.vault_people:
                self.entity_matches.append(
                    EntityMatch(
                        entity_name=name,
                        entity_type="people",
                        vault_file=self.vault_people[name],
                        blog_posts=posts,
                    )
                )

        for name, posts in org_mentions.items():
            if name in self.vault_orgs:
                self.entity_matches.append(
                    EntityMatch(
                        entity_name=name,
                        entity_type="organizations",
                        vault_file=self.vault_orgs[name],
                        blog_posts=posts,
                    )
                )

        logger.info(f"Found {len(self.entity_matches)} entity matches")
        return self.entity_matches

    def find_topic_matches(self) -> list[TopicMatch]:
        """Find topics that match vault concepts."""
        # Get all topic files
        if not self.blog_topics_dir.exists():
            return []

        for topic_file in self.blog_topics_dir.glob("*.md"):
            if topic_file.name.startswith("_"):
                continue

            topic_name = topic_file.stem

            # Check if concept exists with same or similar name
            if topic_name in self.vault_concepts:
                # Count posts in topic
                content = topic_file.read_text()
                post_count = content.count("](https://joi.ito.com/")

                self.topic_matches.append(
                    TopicMatch(
                        topic_name=topic_name,
                        concept_file=self.vault_concepts[topic_name],
                        post_count=post_count,
                    )
                )

        logger.info(f"Found {len(self.topic_matches)} topic-concept matches")
        return self.topic_matches

    def generate_report(self) -> str:
        """Generate integration report."""
        lines = [
            "# Blog Integration Report",
            "",
            f"Generated from {len(self.extractions)} blog post extractions.",
            "",
            "---",
            "",
            "## Entity Matches",
            "",
            f"Found {len(self.entity_matches)} entities mentioned in blog posts that have vault files.",
            "",
        ]

        if self.entity_matches:
            lines.append("### People")
            people_matches = [m for m in self.entity_matches if m.entity_type == "people"]
            if people_matches:
                for match in sorted(people_matches, key=lambda m: len(m.blog_posts), reverse=True)[:20]:
                    lines.append(f"- **{match.entity_name.title()}** ({len(match.blog_posts)} mentions)")
            else:
                lines.append("*No people matches found*")
            lines.append("")

            lines.append("### Organizations")
            org_matches = [m for m in self.entity_matches if m.entity_type == "organizations"]
            if org_matches:
                for match in sorted(org_matches, key=lambda m: len(m.blog_posts), reverse=True)[:20]:
                    lines.append(f"- **{match.entity_name.title()}** ({len(match.blog_posts)} mentions)")
            else:
                lines.append("*No organization matches found*")
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## Topic-Concept Matches",
                "",
                f"Found {len(self.topic_matches)} blog topics that match existing vault concepts.",
                "",
            ]
        )

        if self.topic_matches:
            for match in sorted(self.topic_matches, key=lambda m: m.post_count, reverse=True):
                lines.append(
                    f"- **{match.topic_name}** ({match.post_count} posts) → [[concepts/{match.concept_file.stem}]]"
                )
        else:
            lines.append("*No topic-concept matches found*")

        lines.extend(
            [
                "",
                "---",
                "",
                "## Suggested Actions",
                "",
                "1. Add blog mention sections to matched people/organization files",
                "2. Cross-link topics with matching concepts",
                "3. Review unmatched high-frequency entities for potential new vault entries",
            ]
        )

        return "\n".join(lines)

    def _generate_blog_mentions_section(self, match: EntityMatch) -> str:
        """Generate a Blog Mentions section for a vault file."""
        # Sort posts by date descending
        posts = sorted(match.blog_posts, key=lambda p: p.get("date", ""), reverse=True)
        total = len(posts)

        lines = [
            "",
            "## Blog Mentions",
            "",
            f"*{total} mention{'s' if total != 1 else ''} in Joi's blog*",
            "",
        ]

        # Show up to 10 most recent posts
        shown = posts[:10]
        for post in shown:
            title = post.get("title", "Untitled")
            date = post.get("date", "")
            permalink = post.get("permalink", "")
            if permalink:
                lines.append(f"- [{title}]({permalink}) ({date})")
            else:
                lines.append(f"- {title} ({date})")

        if total > 10:
            lines.append(f"- *...and {total - 10} more*")

        lines.append("")
        return "\n".join(lines)

    def update_vault_files(self) -> int:
        """Add blog mentions to vault files.

        Returns:
            Number of files updated
        """
        updated = 0
        for match in self.entity_matches:
            vault_file = match.vault_file
            try:
                content = vault_file.read_text(encoding="utf-8")

                # Skip if already has blog mentions section
                if "## Blog Mentions" in content:
                    logger.debug(f"Skipping {vault_file.name} - already has blog mentions")
                    continue

                # Generate and append the section
                section = self._generate_blog_mentions_section(match)
                new_content = content.rstrip() + "\n" + section

                vault_file.write_text(new_content, encoding="utf-8")
                logger.info(f"Updated {vault_file.name} with {len(match.blog_posts)} blog mentions")
                updated += 1

            except Exception as e:
                logger.error(f"Failed to update {vault_file.name}: {e}")

        return updated

    def integrate(self, dry_run: bool = True) -> dict:
        """Run full integration.

        Args:
            dry_run: If True, only report matches without modifying files

        Returns:
            Summary statistics
        """
        self.load_extractions()
        self.load_vault_index()
        self.find_entity_matches()
        self.find_topic_matches()

        report = self.generate_report()

        # Save report
        report_path = self.blog_topics_dir.parent / "_INTEGRATION_REPORT.md"
        report_path.write_text(report, encoding="utf-8")
        logger.info(f"Report saved to: {report_path}")

        # Update vault files if not dry run
        files_updated = 0
        if not dry_run:
            files_updated = self.update_vault_files()
            logger.info(f"Updated {files_updated} vault files with blog mentions")

        return {
            "extractions": len(self.extractions),
            "entity_matches": len(self.entity_matches),
            "topic_matches": len(self.topic_matches),
            "files_updated": files_updated,
            "dry_run": dry_run,
        }
