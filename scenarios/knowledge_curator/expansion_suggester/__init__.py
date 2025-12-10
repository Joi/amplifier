"""
Expansion Suggester - Generate actionable content suggestions for knowledge gaps.

Bridges gap detection and content creation:
- Takes gaps from gap_detector
- Researches topics via Tavily
- Generates expansion suggestions with AI
- Stages for user review before application

User-driven workflow: detect → suggest → review → apply
"""

from .core import ExpansionSuggester
from .core import ExpansionSuggestion
from .core import SuggestionStatus
from .core import SuggestionStore
from .core import SuggestionType

__all__ = [
    "ExpansionSuggester",
    "ExpansionSuggestion",
    "SuggestionStore",
    "SuggestionStatus",
    "SuggestionType",
]
