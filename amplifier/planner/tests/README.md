# Super-Planner Tests

## Overview

This directory contains tests for the super-planner hierarchical task orchestration system.

## Test Categories

### Unit Tests

- `test_models.py` - Task and Project data models
- `test_orchestrator_basic.py` - Basic orchestration logic (mocked agents)

### Integration Tests

- `test_hierarchical_orchestration.py` - Hierarchical/recursive project execution
- `test_simple_project.py` - End-to-end with real Claude SDK agents (manual testing)

## Running Tests

### Run All Tests (Automated)

```bash
make test
# or
uv run pytest amplifier/planner/tests/ -v
```

### Run Specific Test Files

```bash
uv run pytest amplifier/planner/tests/test_hierarchical_orchestration.py -v
```

### Skip Manual/Integration Tests

By default, tests marked with `@pytest.mark.skip` are skipped. These include:
- `test_simple_project.py::test_simple_3_task_project` - Requires Claude Code CLI and API key

### Run Manual Tests (End-to-End with Real Agents)

**Prerequisites:**
1. Install Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
2. Set up API key: `export ANTHROPIC_API_KEY=your_key_here`
3. Install Claude Code SDK: `uv add claude-code-sdk` (in amplifier directory)

**Execute:**

```bash
# Run directly with Python
cd /workspaces/amplifier
uv run python amplifier/planner/tests/test_simple_project.py

# Or remove skip marker and run with pytest
uv run pytest amplifier/planner/tests/test_simple_project.py -v -s
```

**What the test does:**
- Creates a temporary project directory
- Defines 3 simple tasks with dependencies:
  1. Create `add()` function in `math_utils.py`
  2. Create `multiply()` function (depends on task 1)
  3. Create tests for both functions (depends on task 2)
- Spawns real Claude Code agents via SDK to implement each task
- Verifies:
  - All tasks complete successfully
  - Dependencies execute in order
  - Files are created by agents
  - Tests pass after implementation

**Expected output:**
```
============================================================
Starting simple 3-task project orchestration
Project directory: /tmp/tmp_xyz123
============================================================

[Agent execution logs...]

============================================================
Orchestration Results:
Status: completed
Completed: 3/3
Failed: 0
Skipped: 0
============================================================

✓ All assertions passed!

This test verified:
  - Real agent execution via Claude SDK
  - Dependency ordering (task1 → task2 → task3)
  - File creation by agents
  - Test verification loop
  - Successful orchestration completion
```

## Test Philosophy

### Unit Tests
- Fast, deterministic, no external dependencies
- Mock agent execution to test orchestration logic
- Focus on state transitions, dependency resolution, error handling

### Integration Tests
- Test real hierarchical project loading and execution
- Use temp directories and fixture data
- Mock or stub agent execution to avoid API calls

### Manual/End-to-End Tests
- Marked with `@pytest.mark.skip` by default
- Require API keys and external services
- Test complete system with real Claude SDK agents
- Run manually before major releases or when debugging agent integration

## Coverage

Run with coverage report:

```bash
uv run pytest amplifier/planner/tests/ --cov=amplifier.planner --cov-report=term-missing
```

Target: 80%+ coverage for core orchestration logic

## Debugging

### Enable Verbose Logging

```bash
uv run pytest amplifier/planner/tests/ -v -s --log-cli-level=DEBUG
```

### Debug Single Test

```python
# Add breakpoint in test code
import pdb; pdb.set_trace()

# Run with pdb
uv run pytest amplifier/planner/tests/test_file.py::test_name -v -s
```

### Inspect Orchestration State

The orchestrator logs detailed state transitions. Enable INFO level logging to see:
- Task state changes (PENDING → IN_PROGRESS → TESTING → COMPLETED)
- Dependency resolution
- Agent execution progress
- Test execution results
- Bug-hunter retry attempts

## Future Tests

Planned test additions:
- Breadth limit validation (max 15 tasks per level)
- Hierarchical auto-decomposition with LLM
- CLI command integration
- Error recovery and retry scenarios
- Performance benchmarks for large projects
