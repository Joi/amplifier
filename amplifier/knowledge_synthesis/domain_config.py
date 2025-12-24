"""
Domain configuration loader for multi-domain knowledge extraction.

Loads domain-specific configuration from:
1. User's vault: ~/switchboard/{domain}/.extraction-config.yaml
2. Bundled defaults: amplifier/knowledge_synthesis/domains/{domain}.yaml

Domain configs customize extraction prompts with domain-specific focus,
key concepts, and relationship types.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default locations to search for domain configs
VAULT_BASE = Path.home() / "switchboard"
BUNDLED_DOMAINS = Path(__file__).parent / "domains"


def load_domain_config(domain_id: str) -> dict[str, Any] | None:
    """
    Load domain configuration by ID.

    Search order:
    1. ~/switchboard/{domain}/.extraction-config.yaml
    2. amplifier/knowledge_synthesis/domains/{domain}.yaml

    Args:
        domain_id: Domain identifier (e.g., "chanoyu", "poa")

    Returns:
        Dict with domain config or None if not found
    """
    # Try vault location first
    vault_config = VAULT_BASE / domain_id / ".extraction-config.yaml"
    if vault_config.exists():
        try:
            with open(vault_config, encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logger.debug(f"Loaded domain config from vault: {vault_config}")
                return config
        except Exception as e:
            logger.warning(f"Failed to load domain config from {vault_config}: {e}")

    # Fall back to bundled defaults
    bundled_config = BUNDLED_DOMAINS / f"{domain_id}.yaml"
    if bundled_config.exists():
        try:
            with open(bundled_config, encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logger.debug(f"Loaded bundled domain config: {bundled_config}")
                return config
        except Exception as e:
            logger.warning(f"Failed to load bundled domain config from {bundled_config}: {e}")

    logger.debug(f"No domain config found for '{domain_id}'")
    return None


def list_available_domains() -> list[str]:
    """
    List all available domain IDs.

    Searches both vault and bundled locations.

    Returns:
        List of domain IDs
    """
    domains = set()

    # Check vault directories for .extraction-config.yaml
    if VAULT_BASE.exists():
        for subdir in VAULT_BASE.iterdir():
            if subdir.is_dir():
                config_path = subdir / ".extraction-config.yaml"
                if config_path.exists():
                    domains.add(subdir.name)

    # Check bundled domains
    if BUNDLED_DOMAINS.exists():
        for yaml_file in BUNDLED_DOMAINS.glob("*.yaml"):
            domains.add(yaml_file.stem)

    return sorted(domains)


def build_domain_context(domain_config: dict[str, Any]) -> str:
    """
    Build domain context string to inject into extraction prompts.

    Args:
        domain_config: Loaded domain configuration dict

    Returns:
        Formatted domain context string for prompt injection
    """
    if not domain_config:
        return ""

    domain_info = domain_config.get("domain", {})
    extraction = domain_config.get("extraction", {})

    parts = []

    # Domain header
    domain_name = domain_info.get("name", "")
    if domain_name:
        parts.append(f"DOMAIN CONTEXT: {domain_name}")

    # Focus description
    focus = extraction.get("focus", "")
    if focus:
        parts.append(focus.strip())

    # Key concepts to look for
    key_concepts = extraction.get("key_concepts", [])
    if key_concepts:
        concept_list = "\n".join(f"- {c}" for c in key_concepts[:20])
        parts.append(f"\nKEY CONCEPTS TO LOOK FOR:\n{concept_list}")

    # Concept categories
    categories = extraction.get("concept_categories", [])
    if categories:
        parts.append(f"\nCONCEPT CATEGORIES: {', '.join(categories)}")

    # Relationship types
    rel_types = extraction.get("relationship_types", [])
    if rel_types:
        parts.append(f"\nRELATIONSHIP TYPES TO IDENTIFY: {', '.join(rel_types)}")

    return "\n".join(parts)


def get_domain_output_path(domain_config: dict[str, Any]) -> Path | None:
    """
    Get the output path for a domain's extracted knowledge.

    Args:
        domain_config: Loaded domain configuration dict

    Returns:
        Path to output directory or None if not specified
    """
    if not domain_config:
        return None

    extraction = domain_config.get("extraction", {})
    output_path = extraction.get("output_path")

    if output_path:
        # Expand ~ and make absolute
        return Path(output_path).expanduser()

    return None
