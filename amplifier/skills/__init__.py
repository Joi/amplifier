"""Amplifier Skills - Native tool integrations.

Skills are self-contained modules that integrate with external services
using the Amplifier secrets management system. They work everywhere:
main Claude Code session, subagents, SDK, scripts, and cron jobs.

Available Skills:
    - academic_search: Search academic papers via Semantic Scholar
    - notion: Notion workspace integration (pages, databases, search)
    - browser: Browser automation via Playwright
"""

# Academic Search
from .academic_search import Paper
from .academic_search import get_paper
from .academic_search import search_author
from .academic_search import search_papers
from .academic_search import search_recent

# Notion
from .notion import NotionDatabase
from .notion import NotionPage
from .notion import append_blocks
from .notion import create_page
from .notion import extract_plain_text
from .notion import get_database
from .notion import get_page
from .notion import query_database
from .notion import search as notion_search
from .notion import update_page

# Browser
from .browser import Browser
from .browser import BrowserConfig
from .browser import PageSnapshot
from .browser import fetch_page
from .browser import screenshot_url

__all__ = [
    # Academic Search
    "Paper",
    "get_paper",
    "search_author",
    "search_papers",
    "search_recent",
    # Notion
    "NotionDatabase",
    "NotionPage",
    "append_blocks",
    "create_page",
    "extract_plain_text",
    "get_database",
    "get_page",
    "notion_search",
    "query_database",
    "update_page",
    # Browser
    "Browser",
    "BrowserConfig",
    "PageSnapshot",
    "fetch_page",
    "screenshot_url",
]
