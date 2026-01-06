#!/bin/bash
# Load Notion credentials into environment variables
#
# Usage:
#   source scripts/load_notion.sh
#   # or
#   eval "$(scripts/load_notion.sh)"
#
# This exports:
#   NOTION_TOKEN - Notion API token

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "$SCRIPT_DIR/lib/secrets.sh"

# Load secrets
NOTION_TOKEN=$(get_notion_token)

# Check if loaded successfully
if [ -z "$NOTION_TOKEN" ]; then
    echo "Error: Failed to load Notion token" >&2
    exit 1
fi

# Export for current shell (when sourced)
export NOTION_TOKEN="$NOTION_TOKEN"

# Also output for eval usage
echo "export NOTION_TOKEN='$NOTION_TOKEN'"

# Status message to stderr (doesn't affect eval)
echo "✓ Loaded Notion credentials (cached for 4 hours)" >&2
