#!/bin/bash
# Run a command with secrets from 1Password injected
#
# Usage: ./scripts/run-with-secrets.sh python scripts/extract_raku_book.py
#
# This script resolves op:// references in .env.local and exports them
# before running the specified command.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env.local"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: .env.local not found at $ENV_FILE"
    exit 1
fi

# Check if op CLI is available
if ! command -v op &> /dev/null; then
    echo "Error: 1Password CLI (op) not found. Install with: brew install 1password-cli"
    exit 1
fi

# Use op run to inject secrets and run the command
cd "$PROJECT_ROOT"
source .venv/bin/activate

exec op run --env-file="$ENV_FILE" -- "$@"
