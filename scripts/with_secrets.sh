#!/bin/bash
# Run a command with secrets loaded from the amplifier secrets infrastructure
#
# Usage:
#   scripts/with_secrets.sh <profile> <command...>
#
# Profiles:
#   chanoyu-adventure - Load OpenAI + Slack secrets
#   chanoyu-sb        - Load Chanoyu Supabase secrets
#   health-tracker    - Load Health Tracker + Withings secrets
#   notion            - Load Notion token
#   all               - Load all available secrets
#
# Examples:
#   scripts/with_secrets.sh chanoyu-adventure npm run dev
#   scripts/with_secrets.sh chanoyu-sb npx supabase db push
#   scripts/with_secrets.sh notion node scripts/sync.js

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "$SCRIPT_DIR/lib/secrets.sh"

if [ $# -lt 2 ]; then
    echo "Usage: $0 <profile> <command...>" >&2
    echo "" >&2
    echo "Profiles: chanoyu-adventure, chanoyu-sb, health-tracker, notion, all" >&2
    exit 1
fi

PROFILE="$1"
shift

case "$PROFILE" in
    chanoyu-adventure)
        export OPENAI_API_KEY=$(get_openai_api_key)
        export SLACK_BOT_TOKEN=$(get_slack_bot_token)
        export SLACK_SIGNING_SECRET=$(get_slack_signing_secret)
        export SLACK_APP_TOKEN=$(get_slack_app_token)
        export SLACK_SENSEI_BOT_TOKEN=$(get_slack_sensei_bot_token)
        export SLACK_SENSEI_APP_TOKEN=$(get_slack_sensei_app_token)
        echo "✓ Loaded chanoyu-adventure secrets" >&2
        ;;
    chanoyu-sb)
        export SUPABASE_SERVICE_ROLE_KEY=$(get_chanoyu_sb_service_role_key)
        export SUPABASE_ACCESS_TOKEN=$(get_chanoyu_sb_access_token)
        export SUPABASE_DB_PASSWORD=$(get_chanoyu_sb_db_password)
        echo "✓ Loaded chanoyu-sb secrets" >&2
        ;;
    health-tracker)
        export SUPABASE_SERVICE_ROLE_KEY=$(get_health_tracker_service_role_key)
        export SUPABASE_ACCESS_TOKEN=$(get_health_tracker_access_token)
        export SUPABASE_DB_PASSWORD=$(get_health_tracker_db_password)
        export WITHINGS_CLIENT_ID=$(get_withings_client_id)
        export WITHINGS_CLIENT_SECRET=$(get_withings_client_secret)
        export WHOOP_CLIENT_ID=$(get_whoop_client_id)
        export WHOOP_CLIENT_SECRET=$(get_whoop_client_secret)
        echo "✓ Loaded health-tracker secrets" >&2
        ;;
    notion)
        export NOTION_TOKEN=$(get_notion_token)
        echo "✓ Loaded notion secrets" >&2
        ;;
    all)
        export OPENAI_API_KEY=$(get_openai_api_key)
        export GEMINI_API_KEY=$(get_gemini_api_key)
        export DEEPL_API_KEY=$(get_deepl_api_key)
        export NOTION_TOKEN=$(get_notion_token)
        export SLACK_BOT_TOKEN=$(get_slack_bot_token)
        export SLACK_SIGNING_SECRET=$(get_slack_signing_secret)
        export SLACK_APP_TOKEN=$(get_slack_app_token)
        export SLACK_SENSEI_BOT_TOKEN=$(get_slack_sensei_bot_token)
        export SLACK_SENSEI_APP_TOKEN=$(get_slack_sensei_app_token)
        echo "✓ Loaded all secrets" >&2
        ;;
    *)
        echo "Unknown profile: $PROFILE" >&2
        echo "Available: chanoyu-adventure, chanoyu-sb, health-tracker, notion, all" >&2
        exit 1
        ;;
esac

# Run the command
exec "$@"
