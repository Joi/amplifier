#!/usr/bin/env bash
set -euo pipefail

# Log file for debugging post-create issues
LOG_FILE="/tmp/devcontainer-post-create.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "========================================="
echo "Post-create script starting at $(date)"
echo "========================================="

echo ""
echo "🔧  Configuring Git to auto-create upstream on first push..."
git config --global push.autoSetupRemote true
echo "    ✅ Git configured"

echo ""
echo "🔧  Setting up pnpm global bin directory..."
# Ensure SHELL is set for pnpm setup
export SHELL="${SHELL:-/bin/bash}"
# Configure pnpm to use a global bin directory
pnpm setup 2>&1 | grep -v "^$" || true
# Export for current session (will also be in ~/.bashrc for future sessions)
export PNPM_HOME="/home/vscode/.local/share/pnpm"
export PATH="$PNPM_HOME:$PATH"
echo "    ✅ pnpm configured"

echo ""
echo "📦  Installing Claude Code CLI…"
if command -v claude >/dev/null 2>&1; then
  echo "    claude already installed; skipping."
else
  pnpm install -g @anthropics/claude-code
  echo "    claude installed successfully!"
fi

echo ""
echo "🔧  Ensuring pnpm path in ~/.bashrc…"
if ! grep -q "PNPM_HOME" ~/.bashrc; then
  cat >> ~/.bashrc << 'EOF'

# pnpm
export PNPM_HOME="/home/vscode/.local/share/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac
# pnpm end
EOF
fi

# Ensure .bash_profile sources .bashrc (for VS Code terminals)
if [ ! -f ~/.bash_profile ] || ! grep -q "source.*bashrc" ~/.bash_profile; then
  cat >> ~/.bash_profile << 'EOF'
# Source .bashrc if it exists
if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi
EOF
fi

echo ""
echo "========================================="
echo "✅  Post-create tasks complete at $(date)"
echo "========================================="
echo ""
echo "📋 Development Environment Ready:"
echo "  • Python: $(python3 --version 2>&1 | cut -d' ' -f2)"
echo "  • uv: $(uv --version 2>&1)"
echo "  • Node.js: $(node --version)"
echo "  • npm: $(npm --version)"
echo "  • pnpm: $(pnpm --version)"
echo "  • Git: $(git --version | cut -d' ' -f3)"
echo "  • Make: $(make --version 2>&1 | head -n 1 | cut -d' ' -f3)"
echo "  • Claude CLI: $(claude --version 2>&1 || echo 'NOT INSTALLED')"
echo ""
echo "💡 Logs saved to: $LOG_FILE"
echo ""
