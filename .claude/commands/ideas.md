## Usage

`/ideas [COMMAND] [ARGS...]`

## Available Commands

- `/ideas list` - List all current ideas and projects
- `/ideas new PROJECT_NAME` - Create a new project
- `/ideas add PROJECT_NAME "idea description"` - Add an idea to a project
- `/ideas show PROJECT_NAME` - Show details for a project
- `/ideas context` - Show current branch/project context
- `/ideas sync` - Sync with ideas data repository

## Process

This command delegates to the ideas_tracker amplifier CLI tool with branch context detection.

**Auto-Setup**: If the ideas data repository doesn't exist locally, it will be automatically cloned from `ramparte/amplifier-ideas-data` to `~/amplifier-ideas-data/`.

**Branch Context**: The tool automatically detects which amplifier branch you're working in and can associate ideas with specific projects or branches.

**Data Storage**: All ideas and projects are stored in your private `ramparte/amplifier-ideas-data` repository, ensuring they're accessible across all your codespaces and branches.

**Implementation**: The command runs:
```bash
make ideas-run ARGS="$ARGUMENTS"
```

If no arguments provided, defaults to `list` command.

## Arguments

$ARGUMENTS