"""Amplifier Skills - Native tool integrations.

Skills are self-contained modules that integrate with external services
using the Amplifier secrets management system. They work everywhere:
main Claude Code session, subagents, SDK, scripts, and cron jobs.

Available Skills:
    - academic_search: Search academic papers via Semantic Scholar
"""

from .academic_search import Paper
from .academic_search import get_paper
from .academic_search import search_author
from .academic_search import search_papers
from .academic_search import search_recent

__all__ = [
    "Paper",
    "get_paper",
    "search_author",
    "search_papers",
    "search_recent",
]
