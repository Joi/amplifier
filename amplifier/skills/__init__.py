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
    - gmail: Read, search, send, and manage Gmail
    - google_calendar: Create, list, manage calendar events
    - tea_calendar: Tea ceremony calendar sync with Google Sheets
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

# Gmail
from .gmail import EmailAddress
from .gmail import EmailMessage
from .gmail import EmailThread
from .gmail import Label as GmailLabel
from .gmail import get_labels as get_gmail_labels
from .gmail import get_message
from .gmail import get_message_sync
from .gmail import get_unread_count
from .gmail import list_messages
from .gmail import list_messages_sync
from .gmail import mark_as_read
from .gmail import mark_as_unread
from .gmail import reply_to_message
from .gmail import search_messages
from .gmail import search_messages_sync
from .gmail import send_email
from .gmail import send_email_sync
from .gmail import star_message
from .gmail import trash_message
from .gmail import unstar_message

# Google Calendar
from .google_calendar import Attendee as CalendarAttendee
from .google_calendar import Calendar
from .google_calendar import CalendarEvent
from .google_calendar import create_event
from .google_calendar import create_event_sync
from .google_calendar import delete_event
from .google_calendar import get_calendars
from .google_calendar import get_event
from .google_calendar import get_event_sync
from .google_calendar import get_todays_events
from .google_calendar import get_todays_events_sync
from .google_calendar import get_upcoming_events
from .google_calendar import list_events
from .google_calendar import list_events_sync
from .google_calendar import quick_add
from .google_calendar import quick_add_sync
from .google_calendar import update_event

# Tea Calendar
from .tea_calendar import TeaEvent
from .tea_calendar import fetch_sheet as fetch_tea_sheet
from .tea_calendar import fetch_sheet_sync as fetch_tea_sheet_sync
from .tea_calendar import generate_kimono_table
from .tea_calendar import generate_kimono_table_sync
from .tea_calendar import get_kimono_events
from .tea_calendar import get_kimono_events_sync
from .tea_calendar import get_tea_events
from .tea_calendar import get_tea_events_sync
from .tea_calendar import sync_sheet_to_calendar as sync_tea_calendar
from .tea_calendar import sync_sheet_to_calendar_sync as sync_tea_calendar_sync

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
    # Gmail
    "EmailAddress",
    "EmailMessage",
    "EmailThread",
    "GmailLabel",
    "get_gmail_labels",
    "get_message",
    "get_message_sync",
    "get_unread_count",
    "list_messages",
    "list_messages_sync",
    "mark_as_read",
    "mark_as_unread",
    "reply_to_message",
    "search_messages",
    "search_messages_sync",
    "send_email",
    "send_email_sync",
    "star_message",
    "trash_message",
    "unstar_message",
    # Google Calendar
    "Calendar",
    "CalendarAttendee",
    "CalendarEvent",
    "create_event",
    "create_event_sync",
    "delete_event",
    "get_calendars",
    "get_event",
    "get_event_sync",
    "get_todays_events",
    "get_todays_events_sync",
    "get_upcoming_events",
    "list_events",
    "list_events_sync",
    "quick_add",
    "quick_add_sync",
    "update_event",
    # Tea Calendar
    "TeaEvent",
    "fetch_tea_sheet",
    "fetch_tea_sheet_sync",
    "generate_kimono_table",
    "generate_kimono_table_sync",
    "get_kimono_events",
    "get_kimono_events_sync",
    "get_tea_events",
    "get_tea_events_sync",
    "sync_tea_calendar",
    "sync_tea_calendar_sync",
]
