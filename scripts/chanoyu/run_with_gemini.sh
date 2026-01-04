#!/bin/bash
# Wrapper script to run commands with Gemini API key
# Uses unified secrets caching from scripts/lib/secrets.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../lib/secrets.sh"

# Get cached key (or fetch from 1Password)
API_KEY=$(get_gemini_api_key)
if [ $? -ne 0 ]; then
    echo "Failed to get Gemini API key. Falling back to op run..."
    exec op run --env-file=.env.local -- "$@"
fi

export GOOGLE_API_KEY="$API_KEY"
export GEMINI_API_KEY="$API_KEY"
exec "$@"
