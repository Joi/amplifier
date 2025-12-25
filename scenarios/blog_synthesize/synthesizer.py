"""Synthesize blog extractions into topic pages and manifest."""

import json
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TopicPost:
    """A post associated with a topic."""

    id: str
    title: str
    date: str
    permalink: str
    language: str
    summary: str


@dataclass
class Topic:
    """Aggregated topic with all associated posts."""

    name: str
    posts: list[TopicPost] = field(default_factory=list)

    @property
    def post_count(self) -> int:
        return len(self.posts)

    @property
    def date_range(self) -> str:
        if not self.posts:
            return ""
        dates = [p.date for p in self.posts if p.date]
        if not dates:
            return ""
        years = sorted(set(d[:4] for d in dates))
        if len(years) == 1:
            return years[0]
        return f"{years[0]}-{years[-1]}"

    def to_markdown(self) -> str:
        """Generate markdown content for topic page."""
        lines = [
            "---",
            f"title: {self.name.replace('-', ' ').title()}",
            "type: blog-topic",
            f"post_count: {self.post_count}",
            f"date_range: {self.date_range}",
            "---",
            "",
            f"# {self.name.replace('-', ' ').title()}",
            "",
            f"Posts tagged with this topic: {self.post_count}",
            "",
            "---",
            "",
            f"## Posts ({self.post_count})",
            "",
        ]

        # Group posts by year
        posts_by_year: dict[str, list[TopicPost]] = defaultdict(list)
        for post in sorted(self.posts, key=lambda p: p.date, reverse=True):
            year = post.date[:4] if post.date else "Unknown"
            posts_by_year[year].append(post)

        for year in sorted(posts_by_year.keys(), reverse=True):
            lines.append(f"### {year}")
            for post in posts_by_year[year]:
                lang_marker = " 🇯🇵" if post.language == "jp" else ""
                lines.append(f"- [{post.title}]({post.permalink}) ({post.date}){lang_marker}")
                if post.summary:
                    # Truncate long summaries
                    summary = post.summary[:150] + "..." if len(post.summary) > 150 else post.summary
                    lines.append(f"  > {summary}")
            lines.append("")

        return "\n".join(lines)


class BlogSynthesizer:
    """Synthesize extractions into topic pages and manifest."""

    def __init__(self, extractions_dir: Path, output_dir: Path, min_posts: int = 3):
        """Initialize synthesizer.

        Args:
            extractions_dir: Directory containing extraction JSON files
            output_dir: Directory for topic output (joi-blog root)
            min_posts: Minimum posts required for a topic page
        """
        self.extractions_dir = extractions_dir
        self.output_dir = output_dir
        self.min_posts = min_posts
        self.topics: dict[str, Topic] = {}
        self.all_extractions: list[dict] = []

    def load_extractions(self) -> int:
        """Load all extraction files.

        Returns:
            Number of extractions loaded
        """
        count = 0
        for json_path in self.extractions_dir.glob("**/*.json"):
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                self.all_extractions.append(data)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to load {json_path}: {e}")

        logger.info(f"Loaded {count} extractions")
        return count

    def aggregate_topics(self) -> dict[str, Topic]:
        """Aggregate posts by topic.

        Returns:
            Dictionary of topic name -> Topic
        """
        for extraction in self.all_extractions:
            post = TopicPost(
                id=extraction.get("id", ""),
                title=extraction.get("title", ""),
                date=extraction.get("date", ""),
                permalink=extraction.get("permalink", ""),
                language=extraction.get("language", "en"),
                summary=extraction.get("summary", ""),
            )

            for topic_name in extraction.get("topics", []):
                if topic_name not in self.topics:
                    self.topics[topic_name] = Topic(name=topic_name)
                self.topics[topic_name].posts.append(post)

        logger.info(f"Found {len(self.topics)} unique topics")
        return self.topics

    def generate_topic_pages(self) -> int:
        """Generate topic markdown pages.

        Returns:
            Number of topic pages generated
        """
        topics_dir = self.output_dir / "topics"
        topics_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for topic_name, topic in self.topics.items():
            if topic.post_count < self.min_posts:
                continue

            # Write topic page
            topic_path = topics_dir / f"{topic_name}.md"
            topic_path.write_text(topic.to_markdown(), encoding="utf-8")
            count += 1

        logger.info(f"Generated {count} topic pages (min {self.min_posts} posts)")
        return count

    def generate_index(self) -> None:
        """Generate topic index page."""
        topics_dir = self.output_dir / "topics"

        # Sort topics by post count
        sorted_topics = sorted(
            [(name, topic) for name, topic in self.topics.items() if topic.post_count >= self.min_posts],
            key=lambda x: x[1].post_count,
            reverse=True,
        )

        lines = [
            "# Blog Topics Index",
            "",
            "Navigate Joi's blog by theme.",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "---",
            "",
            "## By Post Count",
            "",
            "| Topic | Posts | Years |",
            "|-------|-------|-------|",
        ]

        for name, topic in sorted_topics[:50]:  # Top 50
            display_name = name.replace("-", " ").title()
            lines.append(f"| [[joi-blog/topics/{name}\\|{display_name}]] | {topic.post_count} | {topic.date_range} |")

        # Group by era
        lines.extend([
            "",
            "---",
            "",
            "## By Era",
            "",
        ])

        # Define eras
        eras = {
            "MIT Era (2011-2019)": lambda d: d and "2011" <= d[:4] <= "2019",
            "Post-MIT (2020-present)": lambda d: d and d[:4] >= "2020",
            "Early Blogging (2002-2010)": lambda d: d and "2002" <= d[:4] <= "2010",
        }

        for era_name, date_filter in eras.items():
            lines.append(f"### {era_name}")

            # Find topics with posts in this era
            era_topics = []
            for name, topic in self.topics.items():
                if topic.post_count < self.min_posts:
                    continue
                era_posts = [p for p in topic.posts if date_filter(p.date)]
                if era_posts:
                    era_topics.append((name, len(era_posts)))

            era_topics.sort(key=lambda x: x[1], reverse=True)
            for name, count in era_topics[:10]:
                display_name = name.replace("-", " ").title()
                lines.append(f"- [[joi-blog/topics/{name}|{display_name}]] ({count})")
            lines.append("")

        index_path = topics_dir / "_INDEX.md"
        index_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Generated topic index")

    def generate_manifest(self) -> None:
        """Generate manifest JSON file."""
        # Count by language
        by_language = {"en": 0, "jp": 0}
        for ext in self.all_extractions:
            lang = ext.get("language", "en")
            by_language[lang] = by_language.get(lang, 0) + 1

        # Date range
        dates = [ext.get("date", "") for ext in self.all_extractions if ext.get("date")]
        date_range = {"start": min(dates) if dates else "", "end": max(dates) if dates else ""}

        # Top topics
        sorted_topics = sorted(
            [(name, topic.post_count) for name, topic in self.topics.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        manifest = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "corpus": {
                "source": str(self.extractions_dir),
                "total_posts": len(self.all_extractions),
                "by_language": by_language,
                "date_range": date_range,
            },
            "topics": {
                "total": len([t for t in self.topics.values() if t.post_count >= self.min_posts]),
                "min_posts": self.min_posts,
                "top_20": [{"name": name, "count": count} for name, count in sorted_topics[:20]],
            },
        }

        manifest_path = self.output_dir / "_MANIFEST.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"Generated manifest: {manifest_path}")

    def synthesize(self) -> dict:
        """Run full synthesis pipeline.

        Returns:
            Summary statistics
        """
        self.load_extractions()
        self.aggregate_topics()
        topic_count = self.generate_topic_pages()
        self.generate_index()
        self.generate_manifest()

        return {
            "extractions": len(self.all_extractions),
            "topics_total": len(self.topics),
            "topics_generated": topic_count,
            "min_posts": self.min_posts,
        }
