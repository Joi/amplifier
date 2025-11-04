# Quick Start Guide

## What This Does

Learns bug patterns from your git history, then predicts bug risk in new code using GenJax probabilistic models.

## Install

```bash
cd ~/amplifier
make install
```

## 3-Step Usage

### Step 1: Extract Patterns (One-time, ~5 min)

```bash
git-bug-analyzer extract . --limit 100
```

This analyzes your last 100 commits and extracts bug patterns.

**Cost**: ~$2-5 in Claude API calls (one-time)

**Output**:
```
✅ Extracted 32 bug events
📊 Bug Patterns:
   • null_pointer: 15 (87% preventable)
   • race_condition: 8 (75% preventable)
```

### Step 2: Check Code

```bash
git-bug-analyzer check src/auth.py --function login
```

**Output**:
```
📊 Analysis for login():
   Bug probability: 73%
   HIGH RISK: Add null checks, Add error handling
```

### Step 3: Agent Integration

```python
from amplifier.prob_tools.agent_api import AgentAPI

api = AgentAPI()
risk = api.check_code_before_commit("auth.py", "login")

if risk["prediction"]["bug_probability"] > 0.7:
    print(f"⚠️ {risk['prediction']['recommendation']}")
```

## What It Learns

From your git history:
- What patterns cause bugs? (missing null checks, no error handling, etc.)
- How often? (null pointer bugs: 247 times, 89% preventable)
- What prevents them? (type checking, linting, better tests)

Then predicts: "Code like this had bugs 73% of the time in YOUR repo"

## Files

- `git_analyzer.py` - Extract commits
- `llm_extractor.py` - LLM analysis
- `event_store.py` - Store patterns
- `bug_models.py` - GenJax models (THE KEY PART)
- `agent_api.py` - Agent integration
- `cli.py` - Command line

Total: 983 lines

## Read More

- `SUMMARY.md` - Complete overview
- `SYSTEM_OVERVIEW.md` - Detailed architecture
- `README.md` - Project intro
