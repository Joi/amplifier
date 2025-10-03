### The Amplifier CLI Tool

Amplifier provides a powerful command-line interface (`amplifier`) for managing projects, modes, transcripts, worktrees, and directories. Amplifier integrates with and uses claude code. This CLI is the primary interface for configuring and controlling Amplifier's features.

Amplifier "modes" can be thought of as full configurations of claude code and amplifier that allow you switch configurations easily. Modes contain all the built-up knowledge and tooling to be able to use claude code in a particular scenario. Our default mode is "vanilla" which supports coding and interacting with amplifier. However, additional modes can be developed to configure claude code and amplifier. A "data-science" mode, or a "content-creation" mode would be good modes to create in the future.

This document explains how modes and other amplifier features can be used via the `amplifier` client.

When in claude code, modes should be interacted with interactively using the claude code command: `/mode <your instructions>`.

** IMPORTANT: these commands assume you have an active uv environment that has the `amplifier` library installed along with the `amplifier` cli. This usually entails having `uv` installed and running `uv sync` in your project directory that has amplifier in your `pyproject.yaml` and running `source .venv/bin/activate`. Alternatively, all these commands can be run with `uv run <command>`.

If you help the user create or modify an existing mode, let the user know they will have to restart claude code for the changes to be available. After exiting claude, they can use `claude -c` to continue the previous claude session.

## Amplifier Modes Directory Structure

**CRITICAL**: When creating or customizing modes, agents, commands, or contexts:
- **ALWAYS use `.amplifier.local/directory/`** for custom/experimental work
- **NEVER modify `.amplifier/directory/`** (cached official directory)
- **NEVER use `directory/`** alone (not the right path)

The overlay system:
1. `.amplifier.local/directory/` - Your customizations (gitignored, safe to experiment)
2. `.amplifier/directory/` - Official cached directory (updated via `amplifier directory fetch`)

Example: Custom mode goes in `.amplifier.local/directory/modes/my-mode/`

** IMPORTANT: If the user asks you to customize or create a custom mode, be sure to refer to the customization section below. However, in general, it is important to do all customization in the `.amplifier.local/directory/` directory which shadows the `.amplifier/directory/` which itself is a cached copy of the official amplifier directory.

#### Core Commands

**`amplifier init`** - Initialize Amplifier in a project
```bash
amplifier init              # Initialize in current directory
amplifier init -t /path     # Initialize in target directory
amplifier init --force      # Overwrite existing configuration
```

Creates `.amplifier/config.yaml`, fetches the official directory, and sets up the project structure.

**`amplifier mode`** - Manage development modes
```bash
amplifier mode              # Show current mode
amplifier mode list         # List available modes
amplifier mode set <mode>   # Activate a mode (e.g., amplifier-dev, typescript-dev)
amplifier mode unset        # Deactivate current mode
```

Modes configure agents, commands, contexts, and hooks optimized for different development styles. Setting a mode creates symlinks from `.amplifier/directory/modes/<mode>/` to project root and `.claude/` directory.

**`amplifier directory`** - Manage the Amplifier directory
```bash
amplifier directory fetch         # Fetch latest official directory
amplifier directory fetch --force # Overwrite existing directory
amplifier directory freeze        # Copy official files to custom overlay
amplifier directory freeze -v     # Verbose output showing skipped files
```

The directory contains all Amplifier resources (agents, commands, contexts, tools, modes). `freeze` copies official files to `.amplifier.local/directory/` for customization without modifying official files.

#### Transcript Management

**`amplifier transcript`** - Manage conversation transcripts
```bash
amplifier transcript list                    # List all transcripts
amplifier transcript list --last 5           # Show last 5 transcripts
amplifier transcript list --json             # Output as JSON
amplifier transcript load <session-id>       # Load specific transcript
amplifier transcript search "term"           # Search transcripts
amplifier transcript search "term" --max 20  # Limit results
amplifier transcript restore                 # Restore current/latest session
amplifier transcript restore --session-id ID # Restore specific session
amplifier transcript export                  # Export current session
amplifier transcript export --format markdown # Export as markdown
```

Transcripts are automatically captured before compaction (via PreCompact hook), preserving full conversation history. The `restore` command reconstructs the entire conversation lineage.

#### Worktree Management

**`amplifier worktree`** - Manage parallel development branches
```bash
amplifier worktree create <branch>           # Create new worktree
amplifier worktree create <branch> --adopt-remote  # From remote branch
amplifier worktree create <branch> --eval    # Output for shell eval
amplifier worktree list                      # List all worktrees
amplifier worktree remove <branch>           # Remove worktree
amplifier worktree remove <branch> --force   # Force removal
amplifier worktree stash <branch>            # Hide from git tracking
amplifier worktree unstash <branch>          # Restore to git tracking
amplifier worktree list-stashed              # List stashed worktrees
amplifier worktree adopt <remote-branch>     # Create from remote
```

Worktrees enable parallel exploration of different approaches in isolated branches. Each worktree has its own branch, environment, and context. The CLI automatically copies `.data/` and sets up virtual environments.

#### Configuration Structure

`.amplifier/config.yaml` controls all Amplifier settings:

```yaml
# Active mode
mode: amplifier-dev

# Directory source (git+owner/repo/path or file://path)
directory: git+microsoft/amplifier/directory

# Paths configuration
paths:
  data_dir: ~/OneDrive/amplifier/data        # Shared knowledge base
  content_dirs:                               # Source materials
    - .data/content
    - ~/OneDrive/amplifier/content

# Model configuration
models:
  default: claude-sonnet-4-20250514
  fast: claude-3-5-haiku-20241022

# Custom directory overlay
custom_directory:
  enabled: true
  path: ".amplifier.local/directory"
```

#### CLI Integration Patterns

The CLI enables powerful workflow patterns:

**Project Initialization Flow**:
```bash
cd /path/to/project
uv add amplifier              # Install package
amplifier init                # Initialize configuration
amplifier mode set amplifier-dev  # Activate mode
claude                        # Start Claude with Amplifier
```

**Multi-Project Knowledge Sharing**:
```bash
# Configure shared knowledge base in config.yaml:
# data_dir: ~/OneDrive/amplifier/data

# All projects now share:
# - Knowledge extraction results
# - Transcripts (optionally)
# - Content libraries
```

**Experimentation Workflow**:
```bash
# Try multiple approaches in parallel
amplifier worktree create approach-a
amplifier worktree create approach-b
amplifier worktree create approach-c

# Work in each worktree with Claude
cd ../approach-a && claude

# Compare and clean up
amplifier worktree list
amplifier worktree remove approach-b approach-c
```

**Customization Workflow**:
```bash
# Freeze official directory for customization
amplifier directory freeze

# Edit files in .amplifier.local/directory/
# - modes/amplifier-dev/CLAUDE.md
# - agents/zen-architect.md
# - commands/ultrathink-task.md

# Your customizations override official versions
amplifier mode set amplifier-dev
```

### Directory Overlay System: Safe Experimentation

The directory overlay system enables risk-free customization and experimentation with Amplifier resources.

#### How Directory Overlay Works

Amplifier uses a two-layer resolution system:

```
Resolution Order:
1. Check .amplifier.local/directory/<path>  (Custom overlay)
2. Fallback to .amplifier/directory/<path>  (Official directory)
```

When you set a mode or load resources, Amplifier:
1. First looks in `.amplifier.local/directory/` for the file
2. If not found, uses `.amplifier/directory/` (official version)
3. Creates symlinks pointing to the resolved file

**Benefits**:
- **Non-destructive**: Official files remain unchanged
- **Selective override**: Only customize what you need
- **Version control friendly**: `.amplifier.local/` is gitignored by default
- **Easy updates**: Fetch latest official directory without losing customizations
- **Graduation path**: Helpful overlays can be optionally made in to modes and the can be added to the official directory for use by everyone.

#### Freezing for Experimentation

The `amplifier directory freeze` command copies official files to the custom overlay:

```bash
# Copy all official files to custom overlay (skips existing)
amplifier directory freeze

# See what gets copied vs skipped
amplifier directory freeze --verbose
```

**Freeze behavior**:
- Only copies files that don't exist in custom overlay
- Preserves your existing customizations
- Provides starting point for further modifications
- Enables safe experimentation without risking official files

#### Experimentation Workflow

**Experiment with Agent Behavior**:
```bash
# Freeze the agent you want to modify
amplifier directory freeze
# This creates: .amplifier.local/directory/agents/zen-architect.md

# Edit the custom copy
vim .amplifier.local/directory/agents/zen-architect.md
# Modify prompts, add examples, change behavior

# Reload mode to use customized agent
amplifier mode unset
amplifier mode set amplifier-dev

# Test in Claude - your custom agent is now active
claude
```

**Try Different Command Variations**:
```bash
# Create custom version of a command
mkdir -p .amplifier.local/directory/commands
cp .amplifier/directory/commands/ultrathink-task.md \
   .amplifier.local/directory/commands/ultrathink-task.md

# Modify the command behavior
vim .amplifier.local/directory/commands/ultrathink-task.md

# Use the custom command immediately
amplifier mode unset && amplifier mode set amplifier-dev
```

**Develop Context Variations**:
```bash
# Freeze specific context files
amplifier directory freeze

# Create variations for different projects
cp .amplifier.local/directory/contexts/IMPLEMENTATION_PHILOSOPHY.md \
   .amplifier.local/directory/contexts/TEAM_SPECIFIC_PHILOSOPHY.md

# Update mode manifest to use custom context
vim .amplifier.local/directory/modes/amplifier-dev/CLAUDE.md
# Change @import to reference custom context
```

#### Pointing to Custom Directories

You can configure Amplifier to use completely custom directory sources:

**Local Custom Directory**:
```yaml
# .amplifier/config.yaml
directory: file:///path/to/my/custom/directory

# Or relative path
directory: file://./my-custom-directory
```

**Private Git Repository**:
```yaml
# .amplifier/config.yaml
directory: git+myorg/private-amplifier-directory/directory
```

**Fork of Official Directory**:
```yaml
# .amplifier/config.yaml
directory: git+myusername/amplifier-fork/directory
```

After changing the directory source:
```bash
amplifier directory fetch --force  # Fetch from new source
amplifier mode set amplifier-dev   # Activate mode from new directory
```

**Use Cases**:
- **Team customization**: Fork official directory for company-specific agents
- **Private agents**: Keep proprietary agent logic in private repos
- **Version pinning**: Point to specific commit/tag for stability
- **Experimental features**: Develop new features in separate repo

#### Sharing Custom Directories

**As Separate Package**:
```bash
# Create separate repo for custom directory
mkdir my-amplifier-directory
cd my-amplifier-directory
# Copy structure from official directory
cp -r ~/.amplifier/directory/* .
# Customize and version control
git init && git add . && git commit -m "Initial custom directory"

# Configure projects to use it
# In each project's .amplifier/config.yaml:
directory: git+myorg/my-amplifier-directory
```

### Developing Custom Modes

Modes package together agents, commands, contexts, hooks, and settings for specific development workflows.

#### Mode Structure

A mode directory contains:

```
.amplifier/directory/modes/my-mode/
├── amplifier.yaml      # Mode manifest
├── CLAUDE.md          # Claude Code instructions (auto-loaded)
└── AGENT.md           # Shared agent guidelines (optional)
```

#### Mode Manifest Format

`amplifier.yaml` defines what resources the mode includes:

```yaml
# Mode metadata
name: my-mode
description: Custom mode for my workflow

# Resources to symlink when mode is activated
agents:
  - zen-architect.md
  - modular-builder.md
  - bug-hunter.md

commands:
  - ultrathink-task.md
  - modular-build.md
  - prime.md

contexts:
  - IMPLEMENTATION_PHILOSOPHY.md
  - MODULAR_DESIGN_PHILOSOPHY.md

tools:
  - hook_session_start.py
  - hook_stop.py
  - subagent-logger.py

# Claude settings to apply
allow:
  - "Bash"
  - "WebFetch"

deny: []

defaultClaudeMode: "code"

# Hooks configuration
hooks:
  SessionStart:
    - command: "uv run python .claude/tools/hook_session_start.py"
      matcher: "*"

  PreToolUse:
    - command: "uv run python .claude/tools/subagent-logger.py"
      matcher: "Task"

# MCP servers to enable
mcp:
  - "filesystem"
  - "github"
```

#### Creating a Custom Mode

**Option 1: Copy Existing Mode**:

Run `amplifier mode create <name>`, which does the following manually:

```bash
# Copy an existing mode as starting point
cp -r .amplifier/directory/modes/vanilla \
      .amplifier.local/directory/modes/my-mode

# Customize the mode
cd .amplifier.local/directory/modes/my-mode
vim amplifier.yaml    # Adjust manifest
vim CLAUDE.md         # Customize instructions
vim AGENT.md          # Adjust agent guidelines

# Activate your custom mode
amplifier mode set my-mode
```

**Option 2: Build from Scratch**:
```bash
# Create mode directory
mkdir -p .amplifier.local/directory/modes/my-mode

# Create minimal manifest
cat > .amplifier.local/directory/modes/my-mode/amplifier.yaml << 'EOF'
name: my-mode
description: My custom development mode

agents:
  - zen-architect.md

commands:
  - ultrathink-task.md

contexts:
  - IMPLEMENTATION_PHILOSOPHY.md

tools: []

allow: ["Bash", "WebFetch"]
deny: []
EOF

# Create CLAUDE.md instructions
cat > .amplifier.local/directory/modes/my-mode/CLAUDE.md << 'EOF'
# My Custom Mode

You are operating in my custom development mode.

## Import contexts
- @amplifier-context/IMPLEMENTATION_PHILOSOPHY.md

## Mode-specific guidelines
- Follow TDD practices strictly
- Prefer functional programming patterns
- Write detailed commit messages
EOF

# Activate the mode
amplifier mode set my-mode
```

#### Mode Development Workflow

**Iterative Mode Refinement**:
```bash
# 1. Start with minimal mode
amplifier mode set my-mode

# 2. Test in Claude
claude
# Notice what's missing or could be improved

# 3. Add resources incrementally
vim .amplifier.local/directory/modes/my-mode/amplifier.yaml
# Add agents: ["new-agent.md"]

# 4. Reload mode
exit claude
amplifier mode unset
amplifier mode set my-mode
claude -c

# 5. Test again and iterate
```
