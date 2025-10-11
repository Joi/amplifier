# Super-Planner Stress Test: Vi Editor Rewrite

## Overview

This stress test validates the super-planner system with a realistic, large-scale project: **rewriting the vi text editor in Python**.

The test simulates:
- **44 tasks** across 11 phases
- **Complex dependencies** (architecture → implementation → testing → release)
- **Multiple amplifier sessions** with interruption and resume
- **Project discovery** (find by name, resume most recent)
- **Real-world task breakdown** with proper agent assignments

## What It Tests

### Core Functionality
- ✅ Project persistence across sessions
- ✅ Task dependency resolution
- ✅ Multi-session interruption/resume workflow
- ✅ Project discovery by name
- ✅ "Resume most recent" functionality
- ✅ Task state management (PENDING → IN_PROGRESS → COMPLETED)
- ✅ Agent assignment

### Realistic Scenarios
- ✅ Long-running project (15 sessions to complete)
- ✅ Complex dependency chains (11 phases)
- ✅ Multiple domains (architecture, implementation, testing, documentation)
- ✅ Parallel work paths (buffer system, display system, I/O run independently)

## Project Structure

The vi rewrite plan includes:

### Phase 1: Architecture & Design
- Overall architecture design
- Core data structures
- API contracts

### Phase 2: Core Buffer System
- Buffer data structure
- Buffer operations (insert, delete, replace)
- Undo/redo system
- Tests

### Phase 3: Display System
- Terminal interface (curses)
- Viewport (scrolling, wrapping)
- Syntax highlighting
- Tests

### Phase 4: Command Parser
- Mode system (normal, insert, visual, command)
- Normal mode commands
- Insert mode
- Visual mode
- Ex commands
- Tests

### Phase 5: File I/O
- File loading
- File saving
- Autosave/recovery
- Tests

### Phase 6: Advanced Features
- Search and replace
- Macro system
- Marks and jumps
- Multiple buffers
- Tests

### Phase 7: Configuration
- .virc configuration
- Key remapping
- Tests

### Phase 8: Performance & Polish
- Buffer optimization
- Display optimization
- Lazy loading
- Error messages
- Status line

### Phase 9: Integration Testing
- End-to-end workflows
- Compatibility testing
- Stress testing

### Phase 10: Documentation
- User manual
- Developer documentation
- Tutorial

### Phase 11: Packaging & Release
- PyPI packaging
- Release scripts
- Beta testing
- v1.0 release

## Running the Stress Test

### Quick Test (Pytest)

```bash
uv run pytest amplifier/planner/tests/stress_test_vi_rewrite.py -v -s
```

This runs the full simulation with 15 sessions, completing 3 tasks per session.

### Custom Test Parameters

```python
from amplifier.planner.tests.stress_test_vi_rewrite import run_stress_test

# Run with different parameters
results = run_stress_test(
    sessions=20,          # Max sessions to simulate
    tasks_per_session=5   # Tasks per session
)

print(f"Completed {results['total_completed']}/{results['total_tasks']} tasks")
print(f"Status: {results['final_status']}")
```

### Manual Inspection

```python
from amplifier.planner.tests.stress_test_vi_rewrite import create_vi_rewrite_project
from amplifier.planner.storage import save_project, load_project

# Create and save the project
project = create_vi_rewrite_project()
save_project(project)

# Manually inspect structure
print(f"Total tasks: {len(project.tasks)}")
for task_id, task in list(project.tasks.items())[:5]:
    print(f"  {task_id}: {task.title}")
    print(f"    Depends on: {task.depends_on}")
    print(f"    Assigned to: {task.assigned_to}")
```

## Expected Results

When run successfully:

```
Stress Test Results:
  Total tasks: 44
  Sessions used: 15
  Total completed: 44
  Final status: completed

Session breakdown:
  Session 1: completed 3, total so far: 3, pending: 41
  Session 2: completed 3, total so far: 6, pending: 38
  ...
  Session 15: completed 2, total so far: 44, pending: 0
```

### Key Observations

1. **Progressive completion**: Each session completes ~3 tasks
2. **Dependency resolution**: Only tasks with completed dependencies are picked
3. **State persistence**: Each session resumes from where the last left off
4. **Project discovery**: First session finds by name, rest use "resume"

## Test Mechanics

### Simulated Session Flow

Each `simulate_amplifier_session()` call mimics:

1. **Project Discovery**:
   - First session: `find_project_by_name("Vi Editor Rewrite")`
   - Later sessions: `get_most_recent_project()` (simulating "resume")

2. **Load State**:
   - `load_project(project_id)` restores all task states

3. **Find Ready Tasks**:
   - `get_next_ready_task()` finds PENDING tasks with completed dependencies

4. **Execute Tasks**:
   - Mark IN_PROGRESS
   - Save state (simulates interruption safety)
   - `simulate_task_completion()` (fake work)
   - Mark COMPLETED
   - Save state

5. **Repeat**: Continue until max_tasks reached or no ready tasks

### Fake Task Completion

```python
def simulate_task_completion(task: Task) -> None:
    """Simulate completion of a task (fake for testing)."""
    task.state = TaskState.COMPLETED
```

This is intentionally simple - we're testing the **orchestration**, not actual task execution.

## Integration with Real Super-Planner

This stress test demonstrates the expected workflow for actual super-planner use:

```python
# Real usage would look like:
from amplifier.planner import (
    Project, save_project, load_project,
    find_project_by_name, get_most_recent_project,
    orchestrate_execution
)

# Session 1: Create project
project = decompose_goal("Rewrite vi editor in Python")
save_project(project)

# Session 2: Resume and execute
project = load_project(get_most_recent_project())
await orchestrate_execution(project, max_parallel=3)
save_project(project)

# Session 3: Resume again
project = load_project(get_most_recent_project())
await orchestrate_execution(project, max_parallel=3)
# ... continue until done
```

The stress test validates this pattern works correctly.

## Debugging Test Failures

If the test fails, check:

1. **Project file corruption**: `data/planner/projects/*.json`
2. **Dependency cycles**: Should be caught by validation
3. **State transitions**: Tasks should go PENDING → IN_PROGRESS → COMPLETED
4. **Resume logic**: Most recent project should be found correctly

Run with verbose output:

```bash
uv run pytest amplifier/planner/tests/stress_test_vi_rewrite.py -v -s --tb=long
```

## Future Enhancements

Potential additions to make this test even more realistic:

1. **Actual agent invocation**: Call real agents instead of fake completion
2. **Random failures**: Simulate some tasks failing and being retried
3. **Parallel sessions**: Multiple "amplifiers" working simultaneously
4. **Time simulation**: Track estimated vs actual time
5. **Resource constraints**: Limit concurrent tasks per agent type

## Why This Test Matters

This stress test proves the super-planner can handle:
- **Real complexity**: 44-task project with 11 phases
- **Long duration**: 15+ sessions to complete
- **Interruption tolerance**: Can stop/resume at any point
- **State integrity**: No lost work across sessions
- **Usability**: Simple "resume" workflow

If this test passes, the super-planner is ready for actual large-scale projects.
