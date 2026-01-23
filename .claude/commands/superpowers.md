---
description: Run superpowers workflows - TDD, code review, debugging, and more
category: development
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
---

# /superpowers - Development Workflows

Run superpowers workflows via amplifier CLI. Superpowers provides disciplined development practices including TDD, code review, systematic debugging, and subagent-driven development.

## Usage

```
/superpowers                      # List available skills
/superpowers tdd <task>           # Test-driven development
/superpowers debug <issue>        # Systematic debugging
/superpowers review <changes>     # Code review workflow
/superpowers plan <feature>       # Write implementation plan
/superpowers verify               # Verification before completion
```

## Available Skills

| Skill | Description |
|-------|-------------|
| `test-driven-development` | TDD workflow: write tests first, then implement |
| `systematic-debugging` | Methodical debugging with hypothesis testing |
| `writing-plans` | Create detailed implementation plans |
| `executing-plans` | Execute plans step by step |
| `requesting-code-review` | Prepare changes for review |
| `receiving-code-review` | Process review feedback |
| `verification-before-completion` | Validate work before marking done |
| `subagent-driven-development` | Delegate to specialized subagents |
| `dispatching-parallel-agents` | Run multiple agents in parallel |
| `brainstorming` | Structured ideation |
| `finishing-a-development-branch` | Clean up and merge branch |
| `using-git-worktrees` | Parallel development with worktrees |

## Instructions

### List Available Skills

If no arguments or just `/superpowers`:

```bash
ls ~/amplifier-bundle-superpowers/superpowers/skills/
```

Show the available skills as a formatted list.

### Run a Skill via Amplifier

For any skill request, use amplifier with the superpowers bundle:

```bash
amplifier run --bundle ~/amplifier-bundle-superpowers/bundle-dev.md "<task description>"
```

### Common Workflows

#### Test-Driven Development (TDD)

```bash
amplifier run --bundle ~/amplifier-bundle-superpowers/bundle-tdd-only.md "Implement <feature> using TDD"
```

The TDD workflow:
1. Write failing test first
2. Implement minimum code to pass
3. Refactor while keeping tests green
4. Repeat

#### Systematic Debugging

```bash
amplifier run --bundle ~/amplifier-bundle-superpowers/bundle-dev.md "Debug: <description of issue>"
```

Debugging workflow:
1. Reproduce the issue
2. Form hypothesis about cause
3. Design experiment to test hypothesis
4. Execute and observe
5. Iterate until root cause found
6. Fix and verify

#### Code Review

**Requesting review:**
```bash
amplifier run --bundle ~/amplifier-bundle-superpowers/bundle-dev.md "Prepare code review for <changes>"
```

**Receiving review:**
```bash
amplifier run --bundle ~/amplifier-bundle-superpowers/bundle-dev.md "Process code review feedback: <feedback>"
```

#### Writing Plans

```bash
amplifier run --bundle ~/amplifier-bundle-superpowers/bundle-dev.md "Write plan for: <feature description>"
```

### Bundle Options

| Bundle | Use Case |
|--------|----------|
| `bundle-dev.md` | Full workflow (all skills) |
| `bundle-minimal.md` | TDD + code review only |
| `bundle-tdd-only.md` | Just TDD workflow |

### Reading Skill Documentation

To understand a skill in detail:

```bash
cat ~/amplifier-bundle-superpowers/superpowers/skills/<skill-name>/skill.md
```

## Examples

**Run TDD for a feature:**
```
/superpowers tdd Implement caching layer for API responses
```

**Debug an issue:**
```
/superpowers debug Users getting 500 error on login
```

**Plan a feature:**
```
/superpowers plan Add OAuth2 authentication support
```

**Verify before shipping:**
```
/superpowers verify
```

## Notes

- Superpowers enforces disciplined practices (TDD, proper debugging, etc.)
- Each skill has detailed documentation in `~/amplifier-bundle-superpowers/superpowers/skills/`
- The bundle adapts superpowers skills for amplifier's tool system
- Works best with clear, specific task descriptions

## Additional Guidance

$ARGUMENTS
