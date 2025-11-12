#!/bin/bash
# Claude Code status line with cost tracking
# Reads JSON from stdin and displays cost, model, and directory

# Read JSON input from stdin
input=$(cat)

# Extract values using jq (install with: brew install jq)
MODEL=$(echo "$input" | jq -r '.model.display_name' 2>/dev/null || echo "Claude")
CURRENT_DIR=$(echo "$input" | jq -r '.workspace.current_dir' 2>/dev/null || pwd)
COST=$(echo "$input" | jq -r '.cost.total_cost_usd' 2>/dev/null || echo "0")
LINES_ADDED=$(echo "$input" | jq -r '.cost.total_lines_added' 2>/dev/null || echo "0")
LINES_REMOVED=$(echo "$input" | jq -r '.cost.total_lines_removed' 2>/dev/null || echo "0")

# Format cost
if [ "$COST" != "null" ] && [ "$COST" != "0" ]; then
    COST_DISPLAY=$(printf "\$%.4f" "$COST")
else
    COST_DISPLAY="\$0.0000"
fi

# Format lines changed
if [ "$LINES_ADDED" != "null" ] && [ "$LINES_ADDED" != "0" ]; then
    LINES_DISPLAY=" | +$LINES_ADDED/-$LINES_REMOVED"
else
    LINES_DISPLAY=""
fi

# Get directory name
DIR_NAME=$(basename "$CURRENT_DIR")

# Check for git branch
GIT_BRANCH=""
cd "$CURRENT_DIR" 2>/dev/null
if git rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null)
    if [ -n "$BRANCH" ]; then
        GIT_BRANCH=" | 🌿 $BRANCH"
    fi
fi

# Output status line
echo "[$MODEL] 💰 $COST_DISPLAY | 📁 $DIR_NAME$GIT_BRANCH$LINES_DISPLAY"
