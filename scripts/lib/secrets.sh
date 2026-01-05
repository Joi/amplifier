#!/bin/bash
# Unified secrets caching for Apple Keychain-stored credentials.
#
# Provides shell functions matching the Python amplifier.utils.secrets module.
# Source this file in your scripts to use the caching system.
#
# Usage:
#   source "$(dirname "$0")/lib/secrets.sh"
#   API_KEY=$(get_secret gemini_api_key "Amplifier Gemini API Key")
#
# Cache location: ~/.cache/amplifier/secrets/
# Default TTL: 4 hours (14400 seconds)
#
# Apple Keychain Storage:
#   All API keys are stored in the login keychain with the service name format:
#       Amplifier <Service> <Type>
#
#   Examples:
#       Amplifier Gemini API Key
#       Amplifier OpenAI API Key
#       Amplifier Supabase Chanoyu Service Role Key
#
# SSH Access:
#   Unlike 1Password, Apple Keychain secrets are accessible via SSH when:
#   - You are logged into the Mac (GUI session active)
#   - The login keychain is unlocked (happens automatically on login)
#
# Adding New Secrets:
#   To add a new secret to Apple Keychain:
#       security add-generic-password -s "Amplifier <Name>" -a "$USER" -w "<secret>"
#
#   To retrieve:
#       security find-generic-password -s "Amplifier <Name>" -w
#
#   To update (delete then add):
#       security delete-generic-password -s "Amplifier <Name>"
#       security add-generic-password -s "Amplifier <Name>" -a "$USER" -w "<new_secret>"

SECRETS_CACHE_DIR="$HOME/.cache/amplifier/secrets"
SECRETS_DEFAULT_TTL=14400  # 4 hours

# Ensure cache directory exists with secure permissions
_ensure_secrets_cache_dir() {
    if [ ! -d "$SECRETS_CACHE_DIR" ]; then
        mkdir -p "$SECRETS_CACHE_DIR"
        chmod 700 "$SECRETS_CACHE_DIR"
    fi
}

# Check if cached secret has expired
# Args: $1 = cache file path, $2 = ttl in seconds
# Returns: 0 if expired or doesn't exist, 1 if valid
_is_secret_expired() {
    local cache_file="$1"
    local ttl="${2:-$SECRETS_DEFAULT_TTL}"

    if [ ! -f "$cache_file" ]; then
        return 0  # Expired (doesn't exist)
    fi

    local now=$(date +%s)
    local mtime=$(stat -f %m "$cache_file" 2>/dev/null || stat -c %Y "$cache_file" 2>/dev/null)
    local age=$((now - mtime))

    if [ "$age" -gt "$ttl" ]; then
        return 0  # Expired
    fi

    return 1  # Still valid
}

# Get secret from cache or Apple Keychain
# Args: $1 = name, $2 = keychain_service, $3 = ttl_seconds (optional)
# Outputs: secret value
get_secret() {
    local name="$1"
    local keychain_service="$2"
    local ttl="${3:-$SECRETS_DEFAULT_TTL}"

    _ensure_secrets_cache_dir
    local cache_file="$SECRETS_CACHE_DIR/$name"

    # Return cached value if valid
    if ! _is_secret_expired "$cache_file" "$ttl"; then
        cat "$cache_file"
        return 0
    fi

    # Fetch from Apple Keychain and cache
    local secret
    secret=$(security find-generic-password -s "$keychain_service" -w 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "Error: Failed to read secret from Keychain: $keychain_service" >&2
        return 1
    fi

    # Write with secure permissions
    echo -n "$secret" > "$cache_file"
    chmod 600 "$cache_file"

    echo "$secret"
}

# Remove a cached secret
# Args: $1 = name
# Returns: 0 if removed, 1 if didn't exist
clear_secret() {
    local name="$1"
    local cache_file="$SECRETS_CACHE_DIR/$name"

    if [ -f "$cache_file" ]; then
        rm -f "$cache_file"
        return 0
    fi
    return 1
}

# Remove all cached secrets
# Outputs: count of secrets removed
clear_all_secrets() {
    if [ ! -d "$SECRETS_CACHE_DIR" ]; then
        echo 0
        return
    fi

    local count=0
    for f in "$SECRETS_CACHE_DIR"/*; do
        if [ -f "$f" ]; then
            rm -f "$f"
            count=$((count + 1))
        fi
    done

    echo "$count"
}

# =============================================================================
# Convenience functions for common secrets
# =============================================================================

# API Keys (single credential items)

get_gemini_api_key() {
    get_secret "gemini_api_key" "Amplifier Gemini API Key" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_openai_api_key() {
    get_secret "openai_api_key" "Amplifier OpenAI API Key" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_anthropic_api_key() {
    get_secret "anthropic_api_key" "Amplifier Anthropic API Key" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_deepl_api_key() {
    get_secret "deepl_api_key" "Amplifier DeepL API Key" "${1:-$SECRETS_DEFAULT_TTL}"
}

# Supabase Chanoyu - multiple secrets from one service

get_supabase_service_role_key() {
    get_secret "supabase_service_role_key" "Amplifier Supabase Chanoyu Service Role Key" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_supabase_access_token() {
    get_secret "supabase_access_token" "Amplifier Supabase Chanoyu Access Token" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_supabase_db_password() {
    get_secret "supabase_db_password" "Amplifier Supabase Chanoyu DB Password" "${1:-$SECRETS_DEFAULT_TTL}"
}

# Supabase Health Tracker

get_health_tracker_service_role_key() {
    get_secret "health_tracker_service_role_key" "Amplifier Health Tracker Service Role Key" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_health_tracker_access_token() {
    get_secret "health_tracker_access_token" "Amplifier Health Tracker Access Token" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_health_tracker_db_password() {
    get_secret "health_tracker_db_password" "Amplifier Health Tracker DB Password" "${1:-$SECRETS_DEFAULT_TTL}"
}

# Withings API

get_withings_client_id() {
    get_secret "withings_client_id" "Amplifier Withings Client ID" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_withings_client_secret() {
    get_secret "withings_client_secret" "Amplifier Withings Client Secret" "${1:-$SECRETS_DEFAULT_TTL}"
}
