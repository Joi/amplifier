"""Unified secrets caching for Apple Keychain-stored credentials.

Provides a single cache location and consistent interface for both
Python and shell scripts to access secrets without repeated prompts.

Cache location: ~/.cache/amplifier/secrets/
Default TTL: 4 hours (14400 seconds)

## Apple Keychain Storage

All API keys are stored in the login keychain with the service name format:
    Amplifier <Service> <Type>

Examples:
    Amplifier Gemini API Key
    Amplifier OpenAI API Key
    Amplifier Anthropic API Key
    Amplifier DeepL API Key
    Amplifier Supabase Chanoyu Service Role Key
    Amplifier Health Tracker Service Role Key
    Amplifier Withings Client ID

## SSH Access

Unlike 1Password, Apple Keychain secrets are accessible via SSH when:
- You are logged into the Mac (GUI session active)
- The login keychain is unlocked (happens automatically on login)

## Adding New Secrets

To add a new secret to Apple Keychain:
    security add-generic-password -s "Amplifier <Name>" -a "$USER" -w "<secret>"

To retrieve:
    security find-generic-password -s "Amplifier <Name>" -w

To update (delete then add):
    security delete-generic-password -s "Amplifier <Name>"
    security add-generic-password -s "Amplifier <Name>" -a "$USER" -w "<new_secret>"
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


def _read_from_keychain(service_name: str) -> str:
    """Retrieve secret from Apple Keychain.

    Args:
        service_name: The keychain service name (e.g., "Amplifier Gemini API Key")

    Returns:
        The secret value

    Raises:
        RuntimeError: If secret not found or Keychain access fails
    """
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service_name, "-w"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if "could not be found" in e.stderr or e.returncode == 44:
            raise RuntimeError(f"Secret not found in Keychain: {service_name}") from e
        raise RuntimeError(f"Failed to read from Keychain: {e.stderr.strip()}") from e
    except FileNotFoundError:
        raise RuntimeError("macOS security command not found. This module requires macOS.")


def get_secret(name: str, keychain_service: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get secret from cache or Apple Keychain.

    Args:
        name: Cache filename (e.g., "gemini_api_key")
        keychain_service: Keychain service name (e.g., "Amplifier Gemini API Key")
        ttl_seconds: Cache lifetime (default 4 hours)

    Returns:
        Secret value as string

    Raises:
        RuntimeError: If Keychain retrieval fails
    """
    _ensure_cache_dir()
    cache_file = CACHE_DIR / name

    # Return cached value if valid
    if not _is_expired(cache_file, ttl_seconds):
        logger.debug(f"Using cached secret: {name}")
        return cache_file.read_text().strip()

    # Fetch from Keychain and cache
    logger.debug(f"Fetching secret from Keychain: {name}")
    secret = _read_from_keychain(keychain_service)

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


# =============================================================================
# Convenience functions for common secrets
# =============================================================================

# API Keys (single credential items)


def get_gemini_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Gemini/Google API key."""
    return get_secret(
        "gemini_api_key",
        "Amplifier Gemini API Key",
        ttl_seconds,
    )


def get_openai_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get OpenAI API key."""
    return get_secret(
        "openai_api_key",
        "Amplifier OpenAI API Key",
        ttl_seconds,
    )


def get_anthropic_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Anthropic API key."""
    return get_secret(
        "anthropic_api_key",
        "Amplifier Anthropic API Key",
        ttl_seconds,
    )


def get_deepl_api_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get DeepL API key."""
    return get_secret(
        "deepl_api_key",
        "Amplifier DeepL API Key",
        ttl_seconds,
    )


# Supabase Chanoyu - multiple secrets from one service


def get_supabase_service_role_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Supabase service role key (server-side admin access)."""
    return get_secret(
        "supabase_service_role_key",
        "Amplifier Supabase Chanoyu Service Role Key",
        ttl_seconds,
    )


def get_supabase_access_token(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Supabase access token (CLI operations, migrations)."""
    return get_secret(
        "supabase_access_token",
        "Amplifier Supabase Chanoyu Access Token",
        ttl_seconds,
    )


def get_supabase_db_password(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Supabase database password (direct PostgreSQL connections)."""
    return get_secret(
        "supabase_db_password",
        "Amplifier Supabase Chanoyu DB Password",
        ttl_seconds,
    )


# Supabase Health Tracker


def get_health_tracker_service_role_key(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Health Tracker Supabase service role key (server-side admin access)."""
    return get_secret(
        "health_tracker_service_role_key",
        "Amplifier Health Tracker Service Role Key",
        ttl_seconds,
    )


def get_health_tracker_access_token(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Health Tracker Supabase access token (CLI operations)."""
    return get_secret(
        "health_tracker_access_token",
        "Amplifier Health Tracker Access Token",
        ttl_seconds,
    )


def get_health_tracker_db_password(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Health Tracker Supabase database password."""
    return get_secret(
        "health_tracker_db_password",
        "Amplifier Health Tracker DB Password",
        ttl_seconds,
    )


# Withings API


def get_withings_client_id(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Withings API client ID."""
    return get_secret(
        "withings_client_id",
        "Amplifier Withings Client ID",
        ttl_seconds,
    )


def get_withings_client_secret(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Get Withings API client secret."""
    return get_secret(
        "withings_client_secret",
        "Amplifier Withings Client Secret",
        ttl_seconds,
    )
