#!/bin/bash
# Load Chanoyu Adventure credentials into environment variables
#
# Usage:
#   source scripts/load_chanoyu_adventure.sh
#   # or
#   eval "$(scripts/load_chanoyu_adventure.sh)"
#
# This exports:
#   OPENAI_API_KEY - OpenAI API access
#   SLACK_BOT_TOKEN - Slack bot token
#   SLACK_SIGNING_SECRET - Slack signing secret
#   SLACK_APP_TOKEN - Slack app token
#   SLACK_SENSEI_BOT_TOKEN - Slack Sensei bot token
#   SLACK_SENSEI_APP_TOKEN - Slack Sensei app token

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "$SCRIPT_DIR/lib/secrets.sh"

# Load secrets
OPENAI_API_KEY=$(get_openai_api_key)
SLACK_BOT_TOKEN=$(get_slack_bot_token)
SLACK_SIGNING_SECRET=$(get_slack_signing_secret)
SLACK_APP_TOKEN=$(get_slack_app_token)
SLACK_SENSEI_BOT_TOKEN=$(get_slack_sensei_bot_token)
SLACK_SENSEI_APP_TOKEN=$(get_slack_sensei_app_token)

# Check if all loaded successfully
if [ -z "$OPENAI_API_KEY" ] || [ -z "$SLACK_BOT_TOKEN" ]; then
    echo "Error: Failed to load one or more Chanoyu Adventure secrets" >&2
    exit 1
fi

# Export for current shell (when sourced)
export OPENAI_API_KEY="$OPENAI_API_KEY"
export SLACK_BOT_TOKEN="$SLACK_BOT_TOKEN"
export SLACK_SIGNING_SECRET="$SLACK_SIGNING_SECRET"
export SLACK_APP_TOKEN="$SLACK_APP_TOKEN"
export SLACK_SENSEI_BOT_TOKEN="$SLACK_SENSEI_BOT_TOKEN"
export SLACK_SENSEI_APP_TOKEN="$SLACK_SENSEI_APP_TOKEN"

# Also output for eval usage
echo "export OPENAI_API_KEY='$OPENAI_API_KEY'"
echo "export SLACK_BOT_TOKEN='$SLACK_BOT_TOKEN'"
echo "export SLACK_SIGNING_SECRET='$SLACK_SIGNING_SECRET'"
echo "export SLACK_APP_TOKEN='$SLACK_APP_TOKEN'"
echo "export SLACK_SENSEI_BOT_TOKEN='$SLACK_SENSEI_BOT_TOKEN'"
echo "export SLACK_SENSEI_APP_TOKEN='$SLACK_SENSEI_APP_TOKEN'"

# Status message to stderr (doesn't affect eval)
echo "✓ Loaded Chanoyu Adventure credentials (cached for 4 hours)" >&2
