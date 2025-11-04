# Probabilistic Git History Analysis

**Goal**: Extract patterns from git history using LLMs, then build GenJax probabilistic models that learn from those patterns to guide AI coding agents.

## The Architecture

```
GitHub Commits/PRs (unstructured text)
    ↓
LLM Analysis (extracts structured events)
    ↓
Event Database (bug patterns, refactoring outcomes, etc.)
    ↓
GenJax Models (learns probabilistic patterns)
    ↓
Agent Tools (provides guidance during coding)
```

## What We Extract

1. **Bug Patterns** - What caused bugs, what fixed them
2. **Refactoring Outcomes** - What works, what fails
3. **Code Review Insights** - Which concerns predict bugs
4. **Test Effectiveness** - What tests catch what bugs
5. **Breaking Change Patterns** - What changes break things

## What GenJax Learns

- P(bug | code features, historical patterns)
- P(refactoring success | approach, code size, test coverage)
- P(production bug | review concerns not addressed)
- P(breaking change | change type, despite semver)

## Agent Integration

Agents can call these models before:
- Making code changes
- Merging PRs
- Refactoring
- Updating dependencies

Getting probabilistic risk scores based on repo-specific learned patterns.

## Components

- `git_analyzer.py` - Extract commits, diffs, PR data
- `llm_extractor.py` - LLM analysis of commits/PRs
- `event_store.py` - Store extracted events
- `bug_models.py` - GenJax models for bug prediction
- `agent_api.py` - Agent-callable API for predictions
