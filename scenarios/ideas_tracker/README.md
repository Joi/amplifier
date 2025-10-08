# Ideas Tracker: Cross-Branch Project and Ideas Management

**Track your ideas and projects across all amplifier branches and codespaces.**

## The Problem

Working on multiple projects and branches creates scattered ideas:
- **Ideas get lost** - Great thoughts disappear when you switch branches
- **Context switching pain** - Hard to remember what you were thinking in each project
- **No central repository** - Ideas live in random files across different branches
- **Codespaces isolation** - Each environment has its own isolated state

## The Solution

Ideas Tracker is a cross-branch system that:

1. **Central storage** - All ideas stored in your private `ramparte/amplifier-ideas-data` repository
2. **Branch awareness** - Knows which amplifier project/branch you're working in
3. **Universal access** - `/ideas` command available in every branch and codespace
4. **Auto-sync** - Automatically clones and syncs your ideas data repository
5. **Simple CLI** - Easy commands to capture, organize, and recall ideas

## Quick Start

**Prerequisites**: Complete the [Amplifier setup instructions](../../README.md#-step-by-step-setup) first.

### Basic Usage

The `/ideas` slash command is available in any amplifier branch:

```bash
/ideas list                           # Show all projects and ideas
/ideas new "api-refactor"            # Create a new project
/ideas add "api-refactor" "Use FastAPI instead of Flask"  # Add idea to project
/ideas show "api-refactor"           # Show project details
/ideas context                      # Show current branch context
/ideas sync                         # Sync with data repository
```

### Your First Project

1. **Create a project** for your current work:
```bash
/ideas new "authentication-system"
```

2. **Add ideas** as they come to you:
```bash
/ideas add "authentication-system" "Implement OAuth 2.0 with GitHub provider"
/ideas add "authentication-system" "Add rate limiting to login endpoint"
/ideas add "authentication-system" "Consider using JWT for sessions"
```

3. **Review your ideas**:
```bash
/ideas show "authentication-system"
```

4. **Switch branches** and still access your ideas:
```bash
git checkout feature/other-work
/ideas list  # Same ideas, different branch context
```

## Usage Examples

### Basic: Capture Quick Ideas

```bash
/ideas new "mobile-app"
/ideas add "mobile-app" "React Native vs Flutter comparison needed"
/ideas add "mobile-app" "Push notifications architecture"
/ideas show "mobile-app"
```

### Advanced: Branch Context Awareness

The tool automatically detects your current amplifier branch and can associate context:

```bash
# In feature/auth-refactor branch
/ideas context  # Shows: "Current branch: feature/auth-refactor"
/ideas add "authentication-system" "This branch implements the OAuth flow"
```

### Cross-Environment: Same Data Everywhere

Your ideas are stored in `ramparte/amplifier-ideas-data` and accessible from:
- Local WSL environment
- GitHub Codespaces
- Any amplifier branch you create
- Multiple machines with the same GitHub access

## How It Works

### Auto-Setup
1. First time you run `/ideas`, it automatically clones `ramparte/amplifier-ideas-data` to `~/amplifier-ideas-data/`
2. All subsequent commands read/write to this shared location
3. Changes are automatically saved and can be synced back to GitHub

### Data Structure
```
~/amplifier-ideas-data/
├── projects/
│   ├── authentication-system.json
│   ├── mobile-app.json
│   └── api-refactor.json
├── config.json
└── README.md
```

### Branch Context Detection
- Automatically detects current git branch
- Shows amplifier project context when available
- Associates ideas with specific branches when relevant

## Configuration

### Command Reference

```bash
/ideas list                     # List all projects and recent ideas
/ideas new PROJECT_NAME         # Create a new project
/ideas add PROJECT "idea text"  # Add idea to project
/ideas show PROJECT             # Show project details and all ideas
/ideas context                  # Show current branch and project context
/ideas sync                     # Sync changes with GitHub repository
```

### Data Storage

All data is stored in your private `ramparte/amplifier-ideas-data` repository:
- **Projects**: Individual JSON files with metadata and ideas
- **Config**: Settings and preferences
- **Templates**: Optional templates for different project types

## Troubleshooting

### "Repository not found"
**Problem**: Can't access `ramparte/amplifier-ideas-data`
**Solution**: Ensure the repository exists and you have access. Create it on GitHub if needed.

### "Git authentication failed"
**Problem**: Can't clone or push to the ideas repository
**Solution**: Ensure your SSH key or GitHub token is configured properly.

### "Ideas command not found"
**Problem**: `/ideas` slash command not available
**Solution**: The command is only available in amplifier repositories. Ensure you're in an amplifier directory.

## Learn More

- **[Amplifier](https://github.com/microsoft/amplifier)** - The framework that powers this tool
- **[Scenario Tools](../)** - More tools like this one

## What's Next?

1. **Use it** - Start capturing ideas across your projects
2. **Sync across environments** - Access the same ideas in codespaces and local environments
3. **Build your workflow** - Develop patterns for idea capture and project organization
4. **Extend it** - Add your own features or integrate with other tools

---

**Built with Amplifier CLI Tools** - Simple, focused, and designed to work across all your development environments.