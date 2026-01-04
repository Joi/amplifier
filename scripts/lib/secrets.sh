#!/bin/bash
# Unified secrets caching for 1Password-stored credentials.
#
# Provides shell functions matching the Python amplifier.utils.secrets module.
# Source this file in your scripts to use the caching system.
#
# Usage:
#   source "$(dirname "$0")/lib/secrets.sh"
#   API_KEY=$(get_secret gemini_api_key "op://Employee/Amplifier Gemini Key/credential")
#
# Cache location: ~/.cache/amplifier/secrets/
# Default TTL: 4 hours (14400 seconds)
#
# 1Password Path Format:
#   All API keys are stored in the "Employee" vault with this path format:
#       op://Employee/<Item Name>/credential
#
#   IMPORTANT: API keys are stored as "credential" fields, NOT "password" fields.
#   In 1Password, you must use "credential" (which requires "reveal" to view).
#
#   To add a new API key in 1Password:
#   1. Create item in "Employee" vault
#   2. Add field named "credential" (not password)
#   3. Paste the API key value
#   4. Add convenience function below following the pattern

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

# Get secret from cache or 1Password
# Args: $1 = name, $2 = op_path, $3 = ttl_seconds (optional)
# Outputs: secret value
get_secret() {
    local name="$1"
    local op_path="$2"
    local ttl="${3:-$SECRETS_DEFAULT_TTL}"

    _ensure_secrets_cache_dir
    local cache_file="$SECRETS_CACHE_DIR/$name"

    # Return cached value if valid
    if ! _is_secret_expired "$cache_file" "$ttl"; then
        cat "$cache_file"
        return 0
    fi

    # Fetch from 1Password and cache
    local secret
    secret=$(op read "$op_path" 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "Error: Failed to read secret from 1Password" >&2
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

# Convenience functions for common secrets
get_gemini_api_key() {
    get_secret "gemini_api_key" "op://Employee/Amplifier Gemini Key/credential" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_openai_api_key() {
    get_secret "openai_api_key" "op://Employee/OpenAI API Key/credential" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_anthropic_api_key() {
    get_secret "anthropic_api_key" "op://Employee/Anthropic API Key/credential" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_deepl_api_key() {
    get_secret "deepl_api_key" "op://Employee/DeepL API Key/credential" "${1:-$SECRETS_DEFAULT_TTL}"
}

# Supabase Chanoyu - multiple secrets from one 1Password item
# 1Password item: "Supabase Chanoyu" in Employee vault
# Fields: service_role_key, access_token, db_password

get_supabase_service_role_key() {
    get_secret "supabase_service_role_key" "op://Employee/Supabase Chanoyu/service_role_key" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_supabase_access_token() {
    get_secret "supabase_access_token" "op://Employee/Supabase Chanoyu/access_token" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_supabase_db_password() {
    get_secret "supabase_db_password" "op://Employee/Supabase Chanoyu/db_password" "${1:-$SECRETS_DEFAULT_TTL}"
}

# Supabase Health Tracker - single secret needed
# 1Password item: "Supabase Health Tracker" in Employee vault
# Field: service_role_key

get_health_tracker_service_role_key() {
    get_secret "health_tracker_service_role_key" "op://Employee/Supabase Health Tracker/service_role_key" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_health_tracker_access_token() {
    get_secret "health_tracker_access_token" "op://Employee/Supabase Health Tracker/access_token" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_health_tracker_db_password() {
    get_secret "health_tracker_db_password" "op://Employee/Supabase Health Tracker/db_password" "${1:-$SECRETS_DEFAULT_TTL}"
}

# Withings API - OAuth credentials
# 1Password item: "Withings API" in Employee vault
# Fields: client_id, secret

get_withings_client_id() {
    get_secret "withings_client_id" "op://Employee/Withings API/client_id" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_withings_client_secret() {
    get_secret "withings_client_secret" "op://Employee/Withings API/secret" "${1:-$SECRETS_DEFAULT_TTL}"
}
