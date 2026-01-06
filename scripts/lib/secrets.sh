#!/bin/bash
# Unified secrets management with SSH-compatible fallback chain.
#
# Provides shell functions matching the Python amplifier.utils.secrets module.
# Source this file in your scripts to use the caching system.
#
# Usage:
#   source "$(dirname "$0")/lib/secrets.sh"
#   API_KEY=$(get_secret gemini_api_key "Amplifier Gemini API Key")
#
# Fallback Chain (in order):
#   1. Local Cache - ~/.cache/amplifier/secrets/ (fastest, 4h TTL)
#   2. Apple Keychain - macOS security command (requires GUI or unlocked keychain)
#   3. age-encrypted dotfiles - ~/dotfiles-private/amplifier-secrets.env.age (SSH-compatible)
#   4. Environment Variables - Standard env vars (fallback)
#
# SSH Access:
#   The age-encrypted fallback enables full SSH access without GUI authentication:
#   - Key file: ~/.config/age/secrets.key (must be synced to remote machines)
#   - Encrypted secrets: ~/dotfiles-private/amplifier-secrets.env.age
#
# Adding/Updating Secrets:
#   Method 1: Apple Keychain (local machine)
#       security add-generic-password -s "Amplifier <Name>" -a "$USER" -w "<secret>"
#
#   Method 2: age-encrypted file (synced across machines)
#       # Decrypt, edit, re-encrypt:
#       age -d -i ~/.config/age/secrets.key ~/dotfiles-private/amplifier-secrets.env.age > /tmp/secrets.env
#       # Edit /tmp/secrets.env
#       AGE_PUB=$(grep "public key:" ~/.config/age/secrets.key | tail -1 | cut -d: -f2 | tr -d ' ')
#       age -r "$AGE_PUB" -o ~/dotfiles-private/amplifier-secrets.env.age /tmp/secrets.env
#       rm /tmp/secrets.env

SECRETS_CACHE_DIR="$HOME/.cache/amplifier/secrets"
SECRETS_DEFAULT_TTL=14400  # 4 hours

# age encryption paths
AGE_KEY_FILE="$HOME/.config/age/secrets.key"
AGE_SECRETS_FILE="$HOME/dotfiles-private/amplifier-secrets.env.age"

# In-memory cache of decrypted age secrets (file path for this session)
_AGE_SECRETS_CACHE_FILE=""

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

# Load age-encrypted secrets into a temp file (cached for this session)
# Returns: path to decrypted secrets file, or empty if unavailable
_load_age_secrets() {
    # Return cached path if already loaded
    if [ -n "$_AGE_SECRETS_CACHE_FILE" ] && [ -f "$_AGE_SECRETS_CACHE_FILE" ]; then
        echo "$_AGE_SECRETS_CACHE_FILE"
        return 0
    fi

    # Check prerequisites
    if [ ! -f "$AGE_KEY_FILE" ]; then
        return 1
    fi

    if [ ! -f "$AGE_SECRETS_FILE" ]; then
        return 1
    fi

    if ! command -v age &> /dev/null; then
        return 1
    fi

    # Create secure temp file
    _AGE_SECRETS_CACHE_FILE=$(mktemp -t amplifier-secrets.XXXXXX)
    chmod 600 "$_AGE_SECRETS_CACHE_FILE"

    # Decrypt
    if ! age -d -i "$AGE_KEY_FILE" "$AGE_SECRETS_FILE" > "$_AGE_SECRETS_CACHE_FILE" 2>/dev/null; then
        rm -f "$_AGE_SECRETS_CACHE_FILE"
        _AGE_SECRETS_CACHE_FILE=""
        return 1
    fi

    echo "$_AGE_SECRETS_CACHE_FILE"
}

# Read secret from age-encrypted file
# Args: $1 = env_name (e.g., GEMINI_API_KEY)
# Outputs: secret value or empty if not found
_read_from_age() {
    local env_name="$1"
    local secrets_file

    secrets_file=$(_load_age_secrets) || return 1

    # Parse .env format: KEY=VALUE
    grep "^${env_name}=" "$secrets_file" 2>/dev/null | cut -d= -f2-
}

# Get secret using fallback chain: cache → Keychain → age → env var
# Args: $1 = name, $2 = keychain_service, $3 = ttl_seconds (optional), $4 = env_name (optional)
# Outputs: secret value
get_secret() {
    local name="$1"
    local keychain_service="$2"
    local ttl="${3:-$SECRETS_DEFAULT_TTL}"
    local env_name="${4:-$(echo "$name" | tr '[:lower:]' '[:upper:]')}"

    _ensure_secrets_cache_dir
    local cache_file="$SECRETS_CACHE_DIR/$name"

    # 1. Return cached value if valid
    if ! _is_secret_expired "$cache_file" "$ttl"; then
        cat "$cache_file"
        return 0
    fi

    local secret=""

    # 2. Try Apple Keychain (skip if over SSH - it hangs waiting for biometric)
    if [ -z "$SSH_TTY" ] && [ -z "$SSH_CONNECTION" ]; then
        secret=$(security find-generic-password -s "$keychain_service" -w 2>/dev/null)
        if [ -n "$secret" ]; then
            # Cache and return
            echo -n "$secret" > "$cache_file"
            chmod 600 "$cache_file"
            echo "$secret"
            return 0
        fi
    fi

    # 3. Try age-encrypted file (SSH-compatible)
    secret=$(_read_from_age "$env_name")
    if [ -n "$secret" ]; then
        # Cache and return
        echo -n "$secret" > "$cache_file"
        chmod 600 "$cache_file"
        echo "$secret"
        return 0
    fi

    # 4. Try environment variable
    secret="${!env_name}"
    if [ -n "$secret" ]; then
        # Cache and return
        echo -n "$secret" > "$cache_file"
        chmod 600 "$cache_file"
        echo "$secret"
        return 0
    fi

    # No secret found
    echo "Error: Secret '$name' not found. Checked:" >&2
    echo "  - Cache: $cache_file" >&2
    echo "  - Keychain: $keychain_service" >&2
    echo "  - age file: $AGE_SECRETS_FILE (env: $env_name)" >&2
    echo "  - Environment: $env_name" >&2
    return 1
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

# Remove all cached secrets (including age session cache)
# Outputs: count of secrets removed
clear_all_secrets() {
    # Clear age session cache
    if [ -n "$_AGE_SECRETS_CACHE_FILE" ] && [ -f "$_AGE_SECRETS_CACHE_FILE" ]; then
        rm -f "$_AGE_SECRETS_CACHE_FILE"
        _AGE_SECRETS_CACHE_FILE=""
    fi

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

# Force reload of age-encrypted secrets
refresh_age_secrets() {
    if [ -n "$_AGE_SECRETS_CACHE_FILE" ] && [ -f "$_AGE_SECRETS_CACHE_FILE" ]; then
        rm -f "$_AGE_SECRETS_CACHE_FILE"
        _AGE_SECRETS_CACHE_FILE=""
    fi
    _load_age_secrets > /dev/null 2>&1
}

# Cleanup handler for temp files
_secrets_cleanup() {
    if [ -n "$_AGE_SECRETS_CACHE_FILE" ] && [ -f "$_AGE_SECRETS_CACHE_FILE" ]; then
        rm -f "$_AGE_SECRETS_CACHE_FILE"
    fi
}
trap _secrets_cleanup EXIT

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

# Chanoyu Supabase - multiple secrets from one service

get_chanoyu_sb_service_role_key() {
    get_secret "chanoyu_sb_service_role_key" "Amplifier Supabase Chanoyu Service Role Key" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_chanoyu_sb_access_token() {
    get_secret "chanoyu_sb_access_token" "Amplifier Supabase Chanoyu Access Token" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_chanoyu_sb_db_password() {
    get_secret "chanoyu_sb_db_password" "Amplifier Supabase Chanoyu DB Password" "${1:-$SECRETS_DEFAULT_TTL}"
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

# Notion API

get_notion_token() {
    get_secret "notion_token" "Amplifier Notion Token" "${1:-$SECRETS_DEFAULT_TTL}"
}

# Slack API (Chanoyu Adventure)

get_slack_bot_token() {
    get_secret "slack_bot_token" "Amplifier Slack Bot Token" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_slack_signing_secret() {
    get_secret "slack_signing_secret" "Amplifier Slack Signing Secret" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_slack_app_token() {
    get_secret "slack_app_token" "Amplifier Slack App Token" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_slack_sensei_bot_token() {
    get_secret "slack_sensei_bot_token" "Amplifier Slack Sensei Bot Token" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_slack_sensei_app_token() {
    get_secret "slack_sensei_app_token" "Amplifier Slack Sensei App Token" "${1:-$SECRETS_DEFAULT_TTL}"
}

# Whoop API

get_whoop_client_id() {
    get_secret "whoop_client_id" "Amplifier Whoop Client ID" "${1:-$SECRETS_DEFAULT_TTL}"
}

get_whoop_client_secret() {
    get_secret "whoop_client_secret" "Amplifier Whoop Client Secret" "${1:-$SECRETS_DEFAULT_TTL}"
}
