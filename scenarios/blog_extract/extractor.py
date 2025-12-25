"""AI-powered blog post extraction."""

import json
import re
from datetime import datetime
from pathlib import Path

import anthropic

from amplifier.utils.logger import get_logger

from .models import BlogExtraction
from .models import Entities

logger = get_logger(__name__)

EXTRACTION_PROMPT = """Analyze this blog post and extract structured information.

<blog_post>
{content}
</blog_post>

Extract the following as JSON:

1. **topics**: 3-7 topic tags that categorize this post (lowercase, hyphenated). Focus on:
   - Main themes discussed
   - Technologies or concepts mentioned
   - Geographic/cultural context
   - Industry or domain areas

2. **entities**: Named entities mentioned:
   - **people**: Names of people mentioned (excluding the author Joi Ito unless discussing himself)
   - **organizations**: Companies, institutions, universities, governments
   - **places**: Cities, countries, specific locations

3. **summary**: A 1-2 sentence summary of the post's main point

4. **key_quotes**: 1-3 notable quotes or insights from the post (verbatim excerpts, max 150 chars each)

Respond with ONLY valid JSON in this exact format:
```json
{{
  "topics": ["topic-one", "topic-two", "topic-three"],
  "entities": {{
    "people": ["Person Name"],
    "organizations": ["Organization Name"],
    "places": ["Place Name"]
  }},
  "summary": "Brief summary of the post.",
  "key_quotes": ["Notable quote from the post."]
}}
```"""


class BlogExtractor:
    """Extract topics and entities from blog posts using Claude."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """Initialize extractor with Claude client.

        Args:
            model: Claude model to use
        """
        self.client = anthropic.Anthropic()
        self.model = model

    def extract(self, post_path: Path, metadata: dict) -> BlogExtraction | None:
        """Extract topics and entities from a blog post.

        Args:
            post_path: Path to the markdown file
            metadata: Parsed frontmatter metadata

        Returns:
            BlogExtraction or None if extraction fails
        """
        try:
            content = post_path.read_text(encoding="utf-8")

            # Remove YAML frontmatter for cleaner extraction
            if content.startswith("---"):
                end_marker = content.find("---", 3)
                if end_marker != -1:
                    content = content[end_marker + 3 :].strip()

            # Skip very short posts
            if len(content) < 100:
                logger.debug(f"Skipping short post: {post_path.name}")
                return None

            # Call Claude for extraction
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT.format(content=content[:8000]),
                    }
                ],
            )

            # Parse response
            response_text = response.content[0].text

            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try parsing the whole response as JSON
                json_str = response_text

            extracted = json.loads(json_str)

            # Build extraction object
            date_str = metadata.get("date", "")
            if isinstance(date_str, datetime):
                date_str = date_str.strftime("%Y-%m-%d")
            elif date_str:
                date_str = str(date_str)[:10]

            # Generate ID from date and slug
            slug = post_path.stem
            post_id = f"{date_str}-{slug}" if date_str else slug

            return BlogExtraction(
                id=post_id,
                source_file=str(post_path),
                title=metadata.get("title", post_path.stem),
                date=date_str,
                permalink=metadata.get("permalink", ""),
                language=metadata.get("language", "en"),
                topics=extracted.get("topics", []),
                entities=Entities(
                    people=extracted.get("entities", {}).get("people", []),
                    organizations=extracted.get("entities", {}).get("organizations", []),
                    places=extracted.get("entities", {}).get("places", []),
                ),
                summary=extracted.get("summary", ""),
                key_quotes=extracted.get("key_quotes", []),
                extracted_at=datetime.now().isoformat(),
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error for {post_path.name}: {e}")
            return None
        except anthropic.APIError as e:
            logger.error(f"API error for {post_path.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Extraction error for {post_path.name}: {e}")
            return None
