"""Citation Verifier - Validates that sources actually support claims."""

from .core import CitationVerifier
from .core import VerificationOutcome
from .core import VerificationResult

__all__ = ["CitationVerifier", "VerificationResult", "VerificationOutcome"]
