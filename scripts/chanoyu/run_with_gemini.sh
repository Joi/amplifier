#!/bin/bash
# Wrapper script to run commands with Gemini API key
# Uses cached key from ~/.cache/amplifier/gemini_api_key
# Falls back to 1Password if cache doesn't exist

CACHE_FILE="$HOME/.cache/amplifier/gemini_api_key"

# Check for cached key first
if [ -f "$CACHE_FILE" ]; then
    export GOOGLE_API_KEY=$(cat "$CACHE_FILE")
    export GEMINI_API_KEY=$(cat "$CACHE_FILE")
    exec "$@"
else
    echo "No cached key found. Getting from 1Password..."
    mkdir -p "$(dirname "$CACHE_FILE")"
    op read "op://Employee/Amplifier Gemini Key/credential" > "$CACHE_FILE" 2>/dev/null
    if [ $? -eq 0 ]; then
        chmod 600 "$CACHE_FILE"
        export GOOGLE_API_KEY=$(cat "$CACHE_FILE")
        export GEMINI_API_KEY=$(cat "$CACHE_FILE")
        exec "$@"
    else
        echo "Failed to get key from 1Password. Using op run..."
        exec op run --env-file=.env.local -- "$@"
    fi
fi
