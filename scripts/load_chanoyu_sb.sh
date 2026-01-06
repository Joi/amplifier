#!/bin/bash
# Load Chanoyu Supabase credentials into environment variables
#
# Usage:
#   source scripts/load_chanoyu_sb.sh
#   # or
#   eval "$(scripts/load_chanoyu_sb.sh)"
#
# This exports (standard Supabase env vars for CLI compatibility):
#   SUPABASE_SERVICE_ROLE_KEY - Server-side admin access
#   SUPABASE_ACCESS_TOKEN     - CLI operations, migrations
#   SUPABASE_DB_PASSWORD      - Direct PostgreSQL connections

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "$SCRIPT_DIR/lib/secrets.sh"

# Load secrets using chanoyu-specific functions
SERVICE_ROLE_KEY=$(get_chanoyu_sb_service_role_key)
ACCESS_TOKEN=$(get_chanoyu_sb_access_token)
DB_PASSWORD=$(get_chanoyu_sb_db_password)

# Check if all loaded successfully
if [ -z "$SERVICE_ROLE_KEY" ] || [ -z "$ACCESS_TOKEN" ] || [ -z "$DB_PASSWORD" ]; then
    echo "Error: Failed to load one or more Chanoyu Supabase secrets" >&2
    exit 1
fi

# Export for current shell (when sourced)
# Keep standard SUPABASE_* names for Supabase CLI compatibility
export SUPABASE_SERVICE_ROLE_KEY="$SERVICE_ROLE_KEY"
export SUPABASE_ACCESS_TOKEN="$ACCESS_TOKEN"
export SUPABASE_DB_PASSWORD="$DB_PASSWORD"

# Also output for eval usage
echo "export SUPABASE_SERVICE_ROLE_KEY='$SERVICE_ROLE_KEY'"
echo "export SUPABASE_ACCESS_TOKEN='$ACCESS_TOKEN'"
echo "export SUPABASE_DB_PASSWORD='$DB_PASSWORD'"

# Status message to stderr (doesn't affect eval)
echo "✓ Loaded Chanoyu Supabase credentials (cached for 4 hours)" >&2
