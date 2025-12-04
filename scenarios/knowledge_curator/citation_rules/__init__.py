"""
Citation Rules - Domain-specific citation filtering rules.

Each directory in the vault can have a `.citation-rules.yaml` file that defines:
- domain_qualifier: Search terms to add to all queries (e.g., "tea ceremony OR chanoyu")
- term_mappings: English→Japanese or other language mappings
- irrelevant_keywords: Terms that indicate off-topic results (get -0.7 penalty)
- generic_patterns: Additional penalty patterns (-0.5 penalty)
- relevance_threshold: Minimum score to keep a citation (default 0.3)
- search_sources: Which APIs to use (semantic_scholar, crossref, arxiv, cinii)
"""

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

import yaml

from amplifier.utils.logger import get_logger

logger = get_logger(__name__)

CONFIG_FILENAME = ".citation-rules.yaml"


@dataclass
class CitationRules:
    """Domain-specific citation filtering rules."""

    domain_name: str | None = None
    domain_qualifier: str | None = None
    term_mappings: dict[str, str] = field(default_factory=dict)
    irrelevant_keywords: list[str] = field(default_factory=list)
    generic_patterns: list[str] = field(default_factory=list)
    relevance_threshold: float = 0.3
    search_sources: list[str] = field(default_factory=lambda: ["semantic_scholar", "crossref", "arxiv"])

    def has_domain_content(self, text: str) -> bool:
        """Check if text contains domain-specific content based on term_mappings."""
        if not self.term_mappings:
            return False
        text_lower = text.lower()
        return any(term in text_lower for term in self.term_mappings)

    def translate_to_target_language(self, text: str) -> str:
        """Translate known terms to their target language equivalents."""
        if not self.term_mappings:
            return ""

        result = text.lower()
        translated_terms: list[str] = []

        # Sort by length (longest first) to match multi-word terms first
        sorted_terms = sorted(self.term_mappings.keys(), key=len, reverse=True)

        for eng_term in sorted_terms:
            if eng_term in result:
                translated_terms.append(self.term_mappings[eng_term])
                result = result.replace(eng_term, "")  # Avoid double-matching

        return " ".join(translated_terms) if translated_terms else ""


# Default rules when no config file exists
DEFAULT_RULES = CitationRules(
    domain_name=None,
    domain_qualifier=None,
    term_mappings={},
    irrelevant_keywords=[],
    generic_patterns=[],
    relevance_threshold=0.3,
    search_sources=["semantic_scholar", "crossref", "arxiv"],
)


def load_rules(directory: Path) -> CitationRules:
    """Load citation rules from directory's .citation-rules.yaml or return defaults.

    Args:
        directory: Path to directory to check for config file

    Returns:
        CitationRules loaded from config or DEFAULT_RULES
    """
    config_path = directory / CONFIG_FILENAME

    if not config_path.exists():
        logger.debug(f"No {CONFIG_FILENAME} found in {directory}, using defaults")
        return DEFAULT_RULES

    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            logger.warning(f"Empty {CONFIG_FILENAME} in {directory}, using defaults")
            return DEFAULT_RULES

        return _parse_rules(data, config_path)

    except yaml.YAMLError as e:
        logger.warning(f"Invalid YAML in {config_path}: {e}, using defaults")
        return DEFAULT_RULES
    except Exception as e:
        logger.warning(f"Error loading {config_path}: {e}, using defaults")
        return DEFAULT_RULES


def _parse_rules(data: dict[str, Any], config_path: Path) -> CitationRules:
    """Parse YAML data into CitationRules."""
    domain = data.get("domain", {})

    rules = CitationRules(
        domain_name=domain.get("name"),
        domain_qualifier=domain.get("qualifier"),
        term_mappings=data.get("term_mappings", {}),
        irrelevant_keywords=data.get("irrelevant_keywords", []),
        generic_patterns=data.get("generic_patterns", []),
        relevance_threshold=data.get("relevance_threshold", 0.3),
        search_sources=data.get("search_sources", ["semantic_scholar", "crossref", "arxiv"]),
    )

    logger.info(
        f"Loaded citation rules from {config_path}: domain={rules.domain_name}, "
        f"{len(rules.term_mappings)} term mappings, "
        f"threshold={rules.relevance_threshold}"
    )

    return rules


__all__ = ["CitationRules", "load_rules", "DEFAULT_RULES", "CONFIG_FILENAME"]
