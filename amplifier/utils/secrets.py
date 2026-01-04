"""Unified secrets caching for 1Password-stored credentials.

Provides a single cache location and consistent interface for both
Python and shell scripts to access secrets without repeated biometric auth.

Cache location: ~/.cache/amplifier/secrets/
Default TTL: 4 hours (14400 seconds)

## 1Password Path Format

All API keys are stored in the "Employee" vault with this path format:
    op://Employee/<Item Name>/credential

IMPORTANT: API keys are stored as "credential" fields, NOT "password" fields.
In 1Password, you must use "credential" (which requires "reveal" to view).

Examples (single credential per item):
    op://Employee/Amplifier Gemini Key/credential
    op://Employee/OpenAI API Key/credential
    op://Employee/Anthropic API Key/credential
    op://Employee/DeepL API Key/credential

Examples (multiple credentials per item - e.g., Supabase):
    op://Employee/Supabase Chanoyu/service_role_key
    op://Employee/Supabase Chanoyu/access_token
    op://Employee/Supabase Chanoyu/db_password

To add a new API key in 1Password:
1. Create item in "Employee" vault
2. Add field named "credential" (for simple API keys) or descriptive name (for multi-field items)
3. Paste the API key value
4. Add convenience function below following the pattern
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


def _read_from_1password(op_path: str) -> str:
    """Retrieve secret from 1Password CLI."""
    try:
        result = subprocess.run(
            ["op", "read", op_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to read secret from 1Password: {e.stderr.strip()}"
        ) from e
    except FileNotFoundError:
        raise RuntimeError(
            "1Password CLI (op) not found. Install from https://1password.com/downloads/command-line/"
        )


def get_secret(name: str, op_path: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get secret from cache or 1Password.

    Args:
        name: Cache filename (e.g., "gemini_api_key")
        op_path: 1Password path (e.g., "op://Development/Gemini API/credential")
        ttl_seconds: Cache lifetime (default 4 hours)

    Returns:
        Secret value as string

    Raises:
        RuntimeError: If 1Password retrieval fails
    """
    _ensure_cache_dir()
    cache_file = CACHE_DIR / name

    # Return cached value if valid
    if not _is_expired(cache_file, ttl_seconds):
        logger.debug(f"Using cached secret: {name}")
        return cache_file.read_text().strip()

    # Fetch from 1Password and cache
    logger.debug(f"Fetching secret from 1Password: {name}")
    secret = _read_from_1password(op_path)

    # Write with secure permissions
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
    """Remove all cached secrets.

    Returns:
        Count of secrets removed
    """
    if not CACHE_DIR.exists():
        return 0

    count = 0
    for cache_file in CACHE_DIR.iterdir():
        if cache_file.is_file():
            cache_file.unlink()
            count += 1

    logger.debug(f"Cleared {count} cached secrets")
    return count


# Common secret shortcuts for convenience
def get_gemini_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Gemini/Google API key."""
    return get_secret(
        "gemini_api_key",
        "op://Employee/Amplifier Gemini Key/credential",
        ttl_seconds,
    )


def get_openai_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get OpenAI API key."""
    return get_secret(
        "openai_api_key",
        "op://Employee/OpenAI API Key/credential",
        ttl_seconds,
    )


def get_anthropic_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Anthropic API key."""
    return get_secret(
        "anthropic_api_key",
        "op://Employee/Anthropic API Key/credential",
        ttl_seconds,
    )


def get_deepl_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get DeepL API key."""
    return get_secret(
        "deepl_api_key",
        "op://Employee/DeepL API Key/credential",
        ttl_seconds,
    )


# Supabase Chanoyu - multiple secrets from one 1Password item
# 1Password item: "Supabase Chanoyu" in Employee vault
# Fields: service_role_key, access_token, db_password

def get_supabase_service_role_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Supabase service role key (server-side admin access)."""
    return get_secret(
        "supabase_service_role_key",
        "op://Employee/Supabase Chanoyu/service_role_key",
        ttl_seconds,
    )


def get_supabase_access_token(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Supabase access token (CLI operations, migrations)."""
    return get_secret(
        "supabase_access_token",
        "op://Employee/Supabase Chanoyu/access_token",
        ttl_seconds,
    )


def get_supabase_db_password(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Supabase database password (direct PostgreSQL connections)."""
    return get_secret(
        "supabase_db_password",
        "op://Employee/Supabase Chanoyu/db_password",
        ttl_seconds,
    )


# Supabase Health Tracker - single secret needed
# 1Password item: "Supabase Health Tracker" in Employee vault
# Field: service_role_key

def get_health_tracker_service_role_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Health Tracker Supabase service role key (server-side admin access)."""
    return get_secret(
        "health_tracker_service_role_key",
        "op://Employee/Supabase Health Tracker/service_role_key",
        ttl_seconds,
    )
