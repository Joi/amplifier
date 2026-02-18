"""Unified secrets management with SSH-compatible fallback chain.

Provides a single cache location and consistent interface for both
Python and shell scripts to access secrets without repeated prompts.

## Fallback Chain (in order):

1. **Local Cache** - ~/.cache/amplifier/secrets/ (fastest, 4h TTL)
2. **age-encrypted dotfiles** - ~/dotfiles-private/amplifier-secrets.env.age (SSH-compatible)
3. **Environment Variables** - Standard env vars (fallback)

## SSH Access

The age-encrypted fallback enables full SSH access without GUI authentication:
- Key file: ~/.config/age/secrets.key (must be synced to remote machines)
- Encrypted secrets: ~/dotfiles-private/amplifier-secrets.env.age

## Adding/Updating Secrets

### Method 1: age-encrypted file (synced across machines)
    # Decrypt, edit, re-encrypt:
    age -d -i ~/.config/age/secrets.key ~/dotfiles-private/amplifier-secrets.env.age > /tmp/secrets.env
    # Edit /tmp/secrets.env
    AGE_PUB=$(grep "public key:" ~/.config/age/secrets.key | tail -1 | cut -d: -f2 | tr -d ' ')
    age -r "$AGE_PUB" -o ~/dotfiles-private/amplifier-secrets.env.age /tmp/secrets.env
    rm /tmp/secrets.env
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# XDG-compliant cache directory
CACHE_DIR = Path.home() / ".cache" / "amplifier" / "secrets"
DEFAULT_TTL_SECONDS = 14400  # 4 hours

# age encryption paths
AGE_KEY_FILE = Path.home() / ".config" / "age" / "secrets.key"
AGE_SECRETS_FILE = Path.home() / "dotfiles-private" / "amplifier-secrets.env.age"

# In-memory cache of decrypted age secrets (parsed once per session)
_age_secrets_cache: dict[str, str] | None = None


def _ensure_cache_dir() -> None:
    """Create cache directory with secure permissions if needed."""
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True, mode=0o700)
        logger.debug(f"Created secrets cache directory: {CACHE_DIR}")


def _is_expired(cache_file: Path, ttl_seconds: int) -> bool:
    """Check if cached secret has expired based on file mtime."""
    if not cache_file.exists():
        return True
    age = time.time() - cache_file.stat().st_mtime
    return age > ttl_seconds


def _load_age_secrets() -> dict[str, str]:
    """Load and parse secrets from age-encrypted file.

    Returns:
        Dictionary of SECRET_NAME -> value, empty dict if unavailable
    """
    global _age_secrets_cache

    if _age_secrets_cache is not None:
        return _age_secrets_cache

    _age_secrets_cache = {}

    if not AGE_KEY_FILE.exists():
        logger.debug(f"age key file not found: {AGE_KEY_FILE}")
        return _age_secrets_cache

    if not AGE_SECRETS_FILE.exists():
        logger.debug(f"age secrets file not found: {AGE_SECRETS_FILE}")
        return _age_secrets_cache

    try:
        result = subprocess.run(
            ["age", "-d", "-i", str(AGE_KEY_FILE), str(AGE_SECRETS_FILE)],
            capture_output=True,
            text=True,
            check=True,
        )
        # Parse the decrypted .env file
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                _age_secrets_cache[key.strip()] = value.strip()
        logger.debug(f"Loaded {len(_age_secrets_cache)} secrets from age-encrypted file")
    except subprocess.CalledProcessError as e:
        logger.debug(f"age decryption failed: {e.stderr.strip()}")
    except FileNotFoundError:
        logger.debug("age command not found - install with: brew install age")

    return _age_secrets_cache


def _read_from_age(env_name: str) -> str | None:
    """Retrieve secret from age-encrypted dotfiles.

    Args:
        env_name: Environment variable name (e.g., "GEMINI_API_KEY")

    Returns:
        The secret value, or None if not found
    """
    secrets = _load_age_secrets()
    return secrets.get(env_name)


def get_secret(
    name: str,
    keychain_service: str,
    env_name: str | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> str:
    """Get secret using fallback chain: cache → age → env var.

    Args:
        name: Cache filename (e.g., "gemini_api_key")
        keychain_service: Reserved for backward compatibility (unused)
        env_name: Environment variable name (e.g., "GEMINI_API_KEY"). If None, derived from name.
        ttl_seconds: Cache lifetime (default 4 hours)

    Returns:
        Secret value as string

    Raises:
        RuntimeError: If secret not found in any source
    """
    _ensure_cache_dir()
    cache_file = CACHE_DIR / name

    # Derive env name if not provided (gemini_api_key -> GEMINI_API_KEY)
    if env_name is None:
        env_name = name.upper()

    # 1. Return cached value if valid
    if not _is_expired(cache_file, ttl_seconds):
        logger.debug(f"Using cached secret: {name}")
        return cache_file.read_text().strip()

    secret: str | None = None

    # 2. Try age-encrypted file (SSH-compatible)
    if not secret:
        secret = _read_from_age(env_name)
        if secret:
            logger.debug(f"Got secret from age-encrypted file: {name}")

    # 3. Try environment variable
    if not secret:
        secret = os.environ.get(env_name)
        if secret:
            logger.debug(f"Got secret from environment: {env_name}")

    # No secret found anywhere
    if not secret:
        raise RuntimeError(
            f"Secret '{name}' not found. Checked:\n"
            f"  - Cache: {cache_file}\n"
            f"  - age file: {AGE_SECRETS_FILE} (env: {env_name})\n"
            f"  - Environment: {env_name}"
        )

    # Cache the secret for future use
    cache_file.write_text(secret)
    os.chmod(cache_file, 0o600)
    logger.debug(f"Cached secret: {name}")

    return secret


def clear_secret(name: str) -> bool:
    """Remove a cached secret.

    Args:
        name: Cache filename to remove

    Returns:
        True if secret existed and was removed, False otherwise
    """
    cache_file = CACHE_DIR / name
    if cache_file.exists():
        cache_file.unlink()
        logger.debug(f"Cleared cached secret: {name}")
        return True
    return False


def clear_all_secrets() -> int:
    """Remove all cached secrets (both file cache and age memory cache).

    Returns:
        Count of file-cached secrets removed
    """
    global _age_secrets_cache
    _age_secrets_cache = None  # Clear in-memory age cache

    if not CACHE_DIR.exists():
        return 0

    count = 0
    for cache_file in CACHE_DIR.iterdir():
        if cache_file.is_file():
            cache_file.unlink()
            count += 1

    logger.debug(f"Cleared {count} cached secrets")
    return count


def refresh_age_secrets() -> int:
    """Force reload of age-encrypted secrets.

    Useful when you've updated the encrypted file and want to pick up changes.

    Returns:
        Count of secrets loaded from age file
    """
    global _age_secrets_cache
    _age_secrets_cache = None
    secrets = _load_age_secrets()
    return len(secrets)


# =============================================================================
# Convenience functions for common secrets
# =============================================================================

# API Keys (single credential items)


def get_gemini_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Gemini/Google API key."""
    return get_secret(
        "gemini_api_key",
        "Amplifier Gemini API Key",
        ttl_seconds=ttl_seconds,
    )


def get_openai_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get OpenAI API key."""
    return get_secret(
        "openai_api_key",
        "Amplifier OpenAI API Key",
        ttl_seconds=ttl_seconds,
    )


def get_anthropic_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Anthropic API key."""
    return get_secret(
        "anthropic_api_key",
        "Amplifier Anthropic API Key",
        ttl_seconds=ttl_seconds,
    )


def get_deepl_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get DeepL API key."""
    return get_secret(
        "deepl_api_key",
        "Amplifier DeepL API Key",
        ttl_seconds=ttl_seconds,
    )


# Chanoyu Supabase - multiple secrets from one service


def get_chanoyu_sb_service_role_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Chanoyu Supabase service role key (server-side admin access)."""
    return get_secret(
        "chanoyu_sb_service_role_key",
        "Amplifier Supabase Chanoyu Service Role Key",
        ttl_seconds=ttl_seconds,
    )


def get_chanoyu_sb_access_token(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Chanoyu Supabase access token (CLI operations, migrations)."""
    return get_secret(
        "chanoyu_sb_access_token",
        "Amplifier Supabase Chanoyu Access Token",
        ttl_seconds=ttl_seconds,
    )


def get_chanoyu_sb_db_password(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Chanoyu Supabase database password (direct PostgreSQL connections)."""
    return get_secret(
        "chanoyu_sb_db_password",
        "Amplifier Supabase Chanoyu DB Password",
        ttl_seconds=ttl_seconds,
    )


# Supabase Health Tracker


def get_health_tracker_service_role_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Health Tracker Supabase service role key (server-side admin access)."""
    return get_secret(
        "health_tracker_service_role_key",
        "Amplifier Health Tracker Service Role Key",
        ttl_seconds=ttl_seconds,
    )


def get_health_tracker_access_token(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Health Tracker Supabase access token (CLI operations)."""
    return get_secret(
        "health_tracker_access_token",
        "Amplifier Health Tracker Access Token",
        ttl_seconds=ttl_seconds,
    )


def get_health_tracker_db_password(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Health Tracker Supabase database password."""
    return get_secret(
        "health_tracker_db_password",
        "Amplifier Health Tracker DB Password",
        ttl_seconds=ttl_seconds,
    )


# Withings API


def get_withings_client_id(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Withings API client ID."""
    return get_secret(
        "withings_client_id",
        "Amplifier Withings Client ID",
        ttl_seconds=ttl_seconds,
    )


def get_withings_client_secret(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Withings API client secret."""
    return get_secret(
        "withings_client_secret",
        "Amplifier Withings Client Secret",
        ttl_seconds=ttl_seconds,
    )


# Notion API


def get_notion_token(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Notion API token."""
    return get_secret(
        "notion_token",
        "Amplifier Notion Token",
        ttl_seconds=ttl_seconds,
    )


# Slack API (Chanoyu Adventure)


def get_slack_bot_token(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Slack bot token."""
    return get_secret(
        "slack_bot_token",
        "Amplifier Slack Bot Token",
        ttl_seconds=ttl_seconds,
    )


def get_slack_signing_secret(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Slack signing secret."""
    return get_secret(
        "slack_signing_secret",
        "Amplifier Slack Signing Secret",
        ttl_seconds=ttl_seconds,
    )


def get_slack_app_token(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Slack app token."""
    return get_secret(
        "slack_app_token",
        "Amplifier Slack App Token",
        ttl_seconds=ttl_seconds,
    )


def get_slack_sensei_bot_token(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Slack Sensei bot token."""
    return get_secret(
        "slack_sensei_bot_token",
        "Amplifier Slack Sensei Bot Token",
        ttl_seconds=ttl_seconds,
    )


def get_slack_sensei_app_token(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Slack Sensei app token."""
    return get_secret(
        "slack_sensei_app_token",
        "Amplifier Slack Sensei App Token",
        ttl_seconds=ttl_seconds,
    )


# Whoop API


def get_whoop_client_id(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Whoop OAuth client ID."""
    return get_secret(
        "whoop_client_id",
        "Amplifier Whoop Client ID",
        ttl_seconds=ttl_seconds,
    )


def get_whoop_client_secret(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Whoop OAuth client secret."""
    return get_secret(
        "whoop_client_secret",
        "Amplifier Whoop Client Secret",
        ttl_seconds=ttl_seconds,
    )


# Semantic Scholar API


def get_semantic_scholar_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Semantic Scholar API key."""
    return get_secret(
        "semantic_scholar_api_key",
        "Semantic Scholar API",
        env_name="SEMANTIC_SCHOLAR_API_KEY",
        ttl_seconds=ttl_seconds,
    )
