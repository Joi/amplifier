#!/bin/bash
# Load Health Tracker credentials from 1Password into environment variables
#
# Usage:
#   source scripts/load_health_tracker.sh
#   # or
#   eval "$(bash scripts/load_health_tracker.sh 2>/dev/null)"
#
# This exports:
#   SUPABASE_SERVICE_ROLE_KEY - Server-side admin access for health-tracker
#   WITHINGS_CLIENT_ID - Withings OAuth client ID
#   WITHINGS_CLIENT_SECRET - Withings OAuth client secret

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "$SCRIPT_DIR/lib/secrets.sh"

# Load Supabase secret
SERVICE_ROLE_KEY=$(get_health_tracker_service_role_key)

if [ -z "$SERVICE_ROLE_KEY" ]; then
    echo "Error: Failed to load Health Tracker Supabase secret" >&2
    exit 1
fi

# Load Withings secrets
WITHINGS_CLIENT_ID=$(get_withings_client_id)
WITHINGS_CLIENT_SECRET=$(get_withings_client_secret)

if [ -z "$WITHINGS_CLIENT_ID" ] || [ -z "$WITHINGS_CLIENT_SECRET" ]; then
    echo "Error: Failed to load Withings API credentials" >&2
    exit 1
fi

# Export for current shell (when sourced)
export SUPABASE_SERVICE_ROLE_KEY="$SERVICE_ROLE_KEY"
export WITHINGS_CLIENT_ID="$WITHINGS_CLIENT_ID"
export WITHINGS_CLIENT_SECRET="$WITHINGS_CLIENT_SECRET"

# Also output for eval usage
echo "export SUPABASE_SERVICE_ROLE_KEY='$SERVICE_ROLE_KEY'"
echo "export WITHINGS_CLIENT_ID='$WITHINGS_CLIENT_ID'"
echo "export WITHINGS_CLIENT_SECRET='$WITHINGS_CLIENT_SECRET'"

# Status message to stderr (doesn't affect eval)
echo "✓ Loaded Health Tracker credentials (Supabase + Withings, cached for 4 hours)" >&2
