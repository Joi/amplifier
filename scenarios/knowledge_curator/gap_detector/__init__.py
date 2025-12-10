"""
Gap Detector - Detects knowledge gaps in markdown vaults.

Tier 1 (Detection): Automated gap detection for:
- Undefined concepts: Terms mentioned but never explained
- Stale content: Files not updated in N months
- Orphan pages: Files not linked from anywhere
- Thin sections: Topics with < 100 words that deserve more

Detection is cheap and runs weekly. Reports only, no staging.
"""

from .core import Gap
from .core import GapDetector
from .core import GapReport
from .core import GapSeverity
from .core import GapType

__all__ = ["GapDetector", "Gap", "GapReport", "GapType", "GapSeverity"]
