"""Amplifier Skills - Native tool integrations.

Skills are self-contained modules that integrate with external services
using the Amplifier secrets management system. They work everywhere:
main Claude Code session, subagents, SDK, scripts, and cron jobs.

Available Skills:
    - academic_search: Search academic papers via Semantic Scholar
    - notion: Notion workspace integration (pages, databases, search)
    - browser: Browser automation via Playwright
    - apple_reminders: Create, list, complete Apple Reminders
    - apple_notes: Create, read, search Apple Notes
    - imagen: Generate images via Google Imagen/Gemini
    - sync_repos: Sync all tracked git repositories
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

# Apple Reminders
from .apple_reminders import Reminder
from .apple_reminders import ReminderList
from .apple_reminders import add_reminder
from .apple_reminders import complete_reminder
from .apple_reminders import get_lists as get_reminder_lists
from .apple_reminders import list_reminders
from .apple_reminders import search_reminders

# Apple Notes
from .apple_notes import Note
from .apple_notes import create_note
from .apple_notes import delete_note
from .apple_notes import list_notes
from .apple_notes import markdown_to_html
from .apple_notes import read_note
from .apple_notes import search_notes

# Imagen
from .imagen import GeneratedImage
from .imagen import ImageConfig
from .imagen import generate_image
from .imagen import generate_image_sync

# Sync Repos
from .sync_repos import Repo
from .sync_repos import SyncResult
from .sync_repos import get_repos
from .sync_repos import get_status as get_repo_status
from .sync_repos import sync_all
from .sync_repos import sync_all_sync
from .sync_repos import sync_repo

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
    # Apple Reminders
    "Reminder",
    "ReminderList",
    "add_reminder",
    "complete_reminder",
    "get_reminder_lists",
    "list_reminders",
    "search_reminders",
    # Apple Notes
    "Note",
    "create_note",
    "delete_note",
    "list_notes",
    "markdown_to_html",
    "read_note",
    "search_notes",
    # Imagen
    "GeneratedImage",
    "ImageConfig",
    "generate_image",
    "generate_image_sync",
    # Sync Repos
    "Repo",
    "SyncResult",
    "get_repos",
    "get_repo_status",
    "sync_all",
    "sync_all_sync",
    "sync_repo",
]
