# Amplifier: Bring AI Superpowers to Your Projects

> "I have more ideas than time to try them out" — The problem we're solving

> [!CAUTION]
> This project is a research demonstrator. It is in early development and may change significantly. Using permissive AI tools in your repository requires careful attention to security considerations and careful human supervision, and even then things can still go wrong. Use it with caution, and at your own risk.

## What Is Amplifier?

**Amplifier brings a complete AI development environment directly to YOUR projects — supercharging AI coding assistants with discovered patterns, specialized expertise, and powerful automation. Install it anywhere, configure it once, and watch your AI assistant become a force multiplier.**

Unlike traditional AI tools that work in isolation, Amplifier integrates seamlessly into your existing projects. It provides immediate access to proven patterns, specialized agents for different tasks, and workflows that actually work — all without leaving your codebase.

**Amplifier provides powerful tools and systems:**

- **20+ Specialized Agents**: Each expert in specific tasks (architecture, debugging, security, etc.)
- **Mode System**: Switch between different configurations optimized for your work style
- **Pre-loaded Context**: Proven patterns and philosophies built into the environment
- **Parallel Worktree System**: Build and test multiple solutions simultaneously
- **Knowledge Extraction System**: Transform your documentation into queryable, connected knowledge
- **Conversation Transcripts**: Never lose context - automatic export before compaction, instant restoration
- **Automation Tools**: Quality checks and patterns enforced automatically

## 🚀 Quick Start

### Prerequisites

Before starting, you'll need:

- **Python 3.11+** with **uv** - [Install uv](https://docs.astral.sh/uv/)
- **Node.js** - [Download Node.js](https://nodejs.org/)
- **Claude Code CLI** - [Install Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- **Git** - [Download Git](https://git-scm.com/)

> **Platform Note**: Development and testing has primarily been done in Windows WSL2. macOS and Linux should work but have received less testing. Your mileage may vary.

### Installation


_These are temporary instructions for working with amplifier until we get it buttoned up a bit more and deployed as a package._

Install Amplifier directly in your project:

```bash
# Navigate to your project directory
cd /path/to/your/project

# Initialize Python environment (if not already done)
uv init && uv sync && source .venv/bin/activate

# Add Amplifier package
uv add amplifier

# Initialize Amplifier in your project
amplifier init

# Set your preferred mode (e.g., python-coder, typescript-dev, etc.)
amplifier mode set python-coder

# Start Claude with Amplifier enhancements
claude
```

That's it! Amplifier is now integrated into your project with all its capabilities available.

## 🎯 Core Concepts

### Modes: Tailored Development Environments

Modes are pre-configured sets of agents, hooks, commands, and context files optimized for different development styles:

```bash
# List available modes
amplifier mode list

# Set a mode for your project
amplifier mode set python-coder    # Python development with testing focus
amplifier mode set typescript-dev  # TypeScript/Node.js development
amplifier mode set data-scientist  # Data analysis and ML workflows

# Unset the current mode
amplifier mode unset

# Create custom modes
# Note: Mode cloning/freezing commands are under development
# For now, manually copy and edit mode directories

# Currently, create modes by copying existing ones:
# cp -r .amplifier/directory/modes/python-coder .amplifier/directory/modes/my-mode
```

Each mode provides:
- Specialized agent configurations
- Language-specific tools and commands
- Tailored context files and patterns
- Custom hooks and automations

### Configuration: Simple and Flexible

Amplifier uses `.amplifier/config.yaml` for all configuration:

```yaml
# Mode configuration
mode: python-coder  # Your active mode

# Directory configuration
directory: git+microsoft/amplifier/directory  # Official directory source

# Path configuration
paths:
  # Centralized knowledge base - shared across all projects
  # Using cloud storage enables automatic backup!
  data_dir: ~/OneDrive/amplifier/data

  # Your source materials (documentation, specs, design docs)
  content_dirs:
    - .data/content
    - ~/OneDrive/amplifier/content
    - ~/Documents/project-specs

# Model configuration (optional - uses sensible defaults)
models:
  default: claude-sonnet-4-20250514
  fast: claude-3-5-haiku-20241022
```

**Why centralize data?**
- **Shared knowledge across projects** - Learn once, apply everywhere
- **Cross-device synchronization** - Work from any machine
- **Automatic cloud backup** - Never lose insights
- **Reusable patterns** - Apply to new codebases instantly

### Directory System: Modular and Extensible

The `.amplifier/directory/` contains all Amplifier resources:
- **agents/** - Specialized AI agents
- **hooks/** - Automation triggers
- **commands/** - Custom Claude commands
- **tools/** - Python utilities
- **context/** - AI context files

This modular structure allows easy customization and sharing of configurations.

## 📖 Key Features

### Specialized Agents

Instead of one generalist AI, you get 20+ specialists:

**Core Development**:
- `zen-architect` - Designs with ruthless simplicity
- `modular-builder` - Builds following modular principles
- `bug-hunter` - Systematic debugging
- `test-coverage` - Comprehensive testing
- `api-contract-designer` - Clean API design

**Analysis & Optimization**:
- `security-guardian` - Security analysis
- `performance-optimizer` - Performance profiling
- `database-architect` - Database design and optimization
- `integration-specialist` - External service integration

**Knowledge & Insights**:
- `insight-synthesizer` - Finds hidden connections
- `knowledge-archaeologist` - Traces idea evolution
- `concept-extractor` - Extracts knowledge from documents
- `ambiguity-guardian` - Preserves productive contradictions

**Meta & Support**:
- `subagent-architect` - Creates new specialized agents
- `post-task-cleanup` - Maintains codebase hygiene
- `content-researcher` - Researches from content collection

See available agents in `.amplifier/directory/agents/` directory after initialization

### Knowledge Base

**Why use this?** Stop losing insights. Every document, specification, design decision, and lesson learned becomes part of your permanent knowledge that Claude can instantly access.

> [!NOTE]
> Knowledge extraction is an evolving feature that continues to improve with each update.

1. **Add your content** (any text-based files: documentation, specs, notes, decisions)

2. **Build your knowledge base**:
   ```bash
   uv run python .amplifier/directory/tools/knowledge_update.py
   ```

3. **Query your accumulated wisdom**:
   ```bash
   uv run python .amplifier/directory/tools/knowledge_query.py "authentication patterns"
   uv run python .amplifier/directory/tools/knowledge_graph_viz.py  # See connections
   ```

### Conversation Transcripts

**Never lose context again.** Amplifier automatically exports your entire conversation before compaction, preserving all details. When Claude Code compacts to stay within limits, instantly restore the full history.

**Automatic Export**: PreCompact hook captures conversations before compaction:
- Saves complete transcript with all content types
- Timestamps and organizes in `.data/transcripts/`
- Works for both manual (`/compact`) and auto-compact events

**Easy Restoration**: Use `/transcripts` command in Claude Code:
```
/transcripts  # Restores entire conversation history
```

**CLI Commands**:
```bash
amplifier transcript list              # List available transcripts
amplifier transcript search "auth"     # Search past conversations
amplifier transcript restore           # Restore full lineage
```

### Parallel Worktree Development

**Why use this?** Stop wondering "what if" — build multiple solutions simultaneously and pick the winner.

```bash
# Try different approaches in parallel
make worktree feature-jwt     # JWT authentication approach
make worktree feature-oauth   # OAuth approach in parallel

# Compare and choose
amplifier worktree list                   # See all experiments
amplifier worktree remove feature-jwt     # Remove the one you don't want
```

Each worktree is completely isolated with its own branch, environment, and context.

See the [Worktree Guide](docs/WORKTREE_GUIDE.md) for advanced features.

### Modular Builder (Lite)

A one-command workflow to go from idea to module (**Contract & Spec → Plan → Generate → Review**):

**Run inside a Claude Code session:**
```
/modular-build Build a module that reads markdown summaries, synthesizes net-new ideas with provenance, and expands them into plans. mode: auto level: moderate
```

**Features:**
- **Docs:** See `docs/MODULAR_BUILDER_LITE.md` for detailed flow
- **Artifacts:** Planning in `ai_working/<module>/`, code in `amplifier/<module>/`
- **Isolation:** Workers read only module contracts/specs
- **Modes:** `auto` (autonomous), `assist` (interactive), `dry-run` (plan only)
- **Resume:** Re-run `/modular-build` to continue from saved session

### Enhanced Status Line

See costs, model, and session info at a glance:

**Example**: `~/repos/myproject (main → origin) Opus 4.1 💰$4.67 ⏱18m`

Enable with:
```
/statusline use the script at .amplifier/directory/tools/statusline-example.sh
```

## 🔄 Advanced Usage

### Mode Customization

Currently, modes are managed by modifying files in `.amplifier/directory/modes/` directly:

```bash
# Edit mode configuration
# Modify files in .amplifier/directory/modes/python-coder/

# Share with team via git
git add .amplifier/directory/modes/
git commit -m "Customize mode configurations"
```

### Multi-Project Setup

Use Amplifier across multiple projects with shared knowledge:

```bash
# Project 1: Web API
cd ~/projects/api
uv add amplifier && amplifier init
amplifier mode set python-coder

# Project 2: Frontend
cd ~/projects/frontend
uv add amplifier && amplifier init
amplifier mode set typescript-dev

# Both projects share the same knowledge base!
```

### Development Commands

```bash
# Reinitialize Amplifier configuration
amplifier init

# Fetch latest directory updates
amplifier directory fetch
```

## 📦 Migration from v0.1.0

### What's Changed

**Model Shift**: From "work in Amplifier" to "bring Amplifier to your projects"
- Install Amplifier directly in your projects
- No need to copy projects into Amplifier directory
- Work stays in your natural project structure

**Key Changes**:
1. **CLI-based installation**: `uv add amplifier` replaces `make install`
2. **Mode system**: Switch between different configurations
3. **Configuration**: `.amplifier/config.yaml` replaces `.env` files
4. **Tool relocations**: CLI commands replace Makefile targets

### Step-by-Step Migration

1. **Back up your customizations**:
   ```bash
   cd amplifier
   mv .claude .claude.bak
   mv CLAUDE.md CLAUDE.md.bak
   mv AGENTS.md AGENTS.md.bak
   ```

2. **Pull latest Amplifier**:
   ```bash
   git pull origin main
   ```

3. **Install Amplifier package**:
   ```bash
   source .venv/bin/activate
   uv pip install -e .
   ```

4. **Initialize v0.2.0**:
   ```bash
   amplifier init
   ```

5. **Migrate configuration**:
   - Copy custom settings from `.env` to `.amplifier/config.yaml`
   - Environment variables still work as `AMPLIFIER__NESTED__KEY` format

6. **Set your mode**:
   ```bash
   amplifier mode set python-coder
   ```

### Command Migration Reference

| v0.1.0 (Makefile)          | v0.2.0 (CLI)                    |
|----------------------------|----------------------------------|
| `make install`             | `uv add amplifier && amplifier init` |
| `make worktree-create`     | `amplifier worktree create`     |
| `make worktree-list`       | `amplifier worktree list`       |
| `make transcript-list`     | `amplifier transcript list`     |
| `make transcript-search`   | `amplifier transcript search`   |
| `make knowledge-update`    | `uv run python .amplifier/directory/tools/knowledge_update.py` |
| `make knowledge-query`     | `uv run python .amplifier/directory/tools/knowledge_query.py` |

## 💡 Example Workflows

### Starting a New Feature

```bash
# In your project directory
amplifier worktree create feature-notifications

# In Claude Code
"Use zen-architect to design the notification system architecture"
"Have modular-builder implement the core notification module"
"Deploy test-coverage to ensure comprehensive testing"
```

### Debugging Production Issues

```bash
# In Claude Code with your project
"Use bug-hunter to investigate the API timeout issues"
"Have performance-optimizer analyze the bottlenecks"
"Apply security-guardian to check for vulnerabilities"
```

### Knowledge-Driven Development

```bash
# Extract knowledge from your docs
uv run python .amplifier/directory/tools/knowledge_update.py

# Query patterns
uv run python .amplifier/directory/tools/knowledge_query.py "error handling"

# In Claude Code
"Implement error handling using patterns from our knowledge base"
```

### Building with Parallel Experiments

```bash
# Try three different caching strategies
amplifier worktree create cache-redis
amplifier worktree create cache-memory
amplifier worktree create cache-hybrid

# In each worktree with Claude
"Implement the caching layer using [strategy]"

# Compare results and pick the best
amplifier worktree list
amplifier worktree remove cache-memory cache-hybrid  # Keep redis
```

## 🔮 Vision

We're building toward a future where:

1. **You describe, AI builds** - Natural language to working systems
2. **Parallel exploration** - Test 10 approaches simultaneously
3. **Knowledge compounds** - Every project makes you more effective
4. **AI handles the tedious** - You focus on creative decisions

The patterns, knowledge base, and workflows in Amplifier are designed to be portable and tool-agnostic, ready to evolve with the best available AI technologies.

See [AMPLIFIER_VISION.md](AMPLIFIER_VISION.md) for details.

## Current Limitations

- Knowledge extraction works best in Claude environment
- Processing time: ~10-30 seconds per document
- Memory system still in development
- Mode system is in early development with limited presets

> [!IMPORTANT]
> **This is an experimental system. _We break things frequently_.**
>
> - Not accepting contributions yet (but we plan to!)
> - No stability guarantees
> - Pin commits if you need consistency
> - This is a learning resource, not production software
> - **No support provided** - See [SUPPORT.md](SUPPORT.md)

---

_"The best AI system isn't the smartest - it's the one that makes YOU most effective."_

---

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.