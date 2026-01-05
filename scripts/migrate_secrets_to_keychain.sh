#!/bin/bash
# migrate_secrets_to_keychain.sh - Migrate secrets from 1Password to Apple Keychain
#
# This script reads secrets from 1Password and stores them in Apple Keychain
# for SSH-accessible usage without biometric prompts.
#
# Usage: ./scripts/migrate_secrets_to_keychain.sh
#
# Requirements:
# - 1Password CLI (op) installed and configured
# - macOS with Keychain Access
# - User must be logged into 1Password (will prompt for biometric)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "  1Password → Apple Keychain Migration"
echo "======================================"
echo ""

# Track success/failure
SUCCESS_COUNT=0
FAIL_COUNT=0

migrate_secret() {
    local op_path="$1"
    local keychain_service="$2"

    printf "  %-45s " "$keychain_service"

    # Read from 1Password
    local secret
    if ! secret=$(op read "$op_path" 2>/dev/null); then
        echo -e "${RED}FAILED${NC} (could not read from 1Password)"
        ((FAIL_COUNT++))
        return 1
    fi

    # Check if secret is empty
    if [[ -z "$secret" ]]; then
        echo -e "${RED}FAILED${NC} (empty secret)"
        ((FAIL_COUNT++))
        return 1
    fi

    # Delete existing entry if present (to allow update)
    security delete-generic-password -s "$keychain_service" 2>/dev/null || true

    # Store in Keychain
    if ! security add-generic-password \
        -s "$keychain_service" \
        -a "$USER" \
        -w "$secret" 2>/dev/null; then
        echo -e "${RED}FAILED${NC} (could not store in Keychain)"
        ((FAIL_COUNT++))
        unset secret
        return 1
    fi

    # Verify storage
    local verify
    if ! verify=$(security find-generic-password -s "$keychain_service" -w 2>/dev/null); then
        echo -e "${RED}FAILED${NC} (verification failed)"
        ((FAIL_COUNT++))
        unset secret verify
        return 1
    fi

    if [[ "$verify" == "$secret" ]]; then
        echo -e "${GREEN}✓${NC}"
        ((SUCCESS_COUNT++))
    else
        echo -e "${RED}FAILED${NC} (content mismatch)"
        ((FAIL_COUNT++))
    fi

    # Clear sensitive data from memory
    unset secret verify
}

echo "Step 1: Checking prerequisites..."
echo ""

# Check for 1Password CLI
if ! command -v op &> /dev/null; then
    echo -e "${RED}Error: 1Password CLI (op) not found${NC}"
    echo "Install from: https://1password.com/downloads/command-line/"
    exit 1
fi
echo "  ✓ 1Password CLI found"

# Check for macOS security command
if ! command -v security &> /dev/null; then
    echo -e "${RED}Error: macOS security command not found${NC}"
    echo "This script requires macOS"
    exit 1
fi
echo "  ✓ macOS Keychain available"

# Check 1Password session
echo ""
echo "Step 2: Authenticating with 1Password..."
echo "  (You may be prompted for biometric authentication)"
echo ""

if ! op account get &> /dev/null; then
    echo -e "${YELLOW}Please sign in to 1Password...${NC}"
    if ! op signin; then
        echo -e "${RED}Error: Could not authenticate with 1Password${NC}"
        exit 1
    fi
fi
echo "  ✓ 1Password authenticated"

echo ""
echo "Step 3: Migrating secrets..."
echo ""

# API Keys (single credential items)
echo "  API Keys:"
migrate_secret "op://Employee/Amplifier Gemini Key/credential" "Amplifier Gemini API Key"
migrate_secret "op://Employee/2025-12-10 OpenAI Key/credential" "Amplifier OpenAI API Key"
migrate_secret "op://Employee/2025-12-10 Anthropic Key/credential" "Amplifier Anthropic API Key"
migrate_secret "op://Employee/DeepL API Key/credential" "Amplifier DeepL API Key"

echo ""
echo "  Supabase Chanoyu:"
migrate_secret "op://Employee/Supabase Chanoyu/service_role_key" "Amplifier Supabase Chanoyu Service Role Key"
migrate_secret "op://Employee/Supabase Chanoyu/access_token" "Amplifier Supabase Chanoyu Access Token"
migrate_secret "op://Employee/Supabase Chanoyu/db_password" "Amplifier Supabase Chanoyu DB Password"

echo ""
echo "  Supabase Health Tracker:"
migrate_secret "op://Employee/Supabase Health Tracker/service_role_key" "Amplifier Health Tracker Service Role Key"
migrate_secret "op://Employee/Supabase Health Tracker/access_token" "Amplifier Health Tracker Access Token"
migrate_secret "op://Employee/Supabase Health Tracker/db_password" "Amplifier Health Tracker DB Password"

echo ""
echo "  Withings API:"
migrate_secret "op://Employee/Withings API/client_id" "Amplifier Withings Client ID"
migrate_secret "op://Employee/Withings API/secret" "Amplifier Withings Client Secret"

echo ""
echo "======================================"
echo "  Migration Complete"
echo "======================================"
echo ""
echo -e "  ${GREEN}Successful:${NC} $SUCCESS_COUNT"
echo -e "  ${RED}Failed:${NC}     $FAIL_COUNT"
echo ""

if [[ $FAIL_COUNT -eq 0 ]]; then
    echo -e "${GREEN}All secrets migrated successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Clear the old cache: rm -rf ~/.cache/amplifier/secrets/*"
    echo "  2. Test with: security find-generic-password -s 'Amplifier Gemini API Key' -w"
    echo "  3. The updated secrets.py will use Keychain automatically"
else
    echo -e "${YELLOW}Some secrets failed to migrate. Please check the errors above.${NC}"
    exit 1
fi
