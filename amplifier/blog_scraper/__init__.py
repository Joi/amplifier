"""Blog scraper for joi.ito.com.

Extracts blog posts from joi.ito.com to markdown with YAML frontmatter.
Supports both English (/weblog/) and Japanese (/jp/archives/) sections.
"""

from amplifier.blog_scraper.models import BlogPost
from amplifier.blog_scraper.models import ScrapeResult
from amplifier.blog_scraper.scraper import scrape_blog
from amplifier.blog_scraper.scraper import scrape_post

__all__ = ["BlogPost", "ScrapeResult", "scrape_blog", "scrape_post"]
