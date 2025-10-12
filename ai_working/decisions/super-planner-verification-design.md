# Super-Planner Verification Loop Design

**Date**: 2025-01-21
**Status**: Proposed
**Context**: Vi editor project revealed that super-planner completes tasks without verifying tests pass

## Problem Statement

Current super-planner marks tasks as COMPLETED when agents report "done" without running tests to verify the code actually works. This led to:
- 83% test failure rate (3/18 tests passing) in vi editor project
- Tasks marked "completed" despite broken functionality
- No automatic retry mechanism when tests fail
- Human discovers failures after project reports "success"

## Proposed Solution: Enhanced Verification Loop

### New Task States

Extend `TaskState` enum in `models.py`:

```python
class TaskState(Enum):
    """Task states for workflow management with verification."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"           # NEW: Running tests after implementation
    TEST_FAILED = "test_failed"   # NEW: Tests failed, needs bug-hunter
    COMPLETED = "completed"
    BLOCKED = "blocked"
```

### State Transition Flow

```
PENDING
  ↓
IN_PROGRESS (agent implementing)
  ↓
TESTING (auto-run tests)
  ↓
  ├─→ COMPLETED (tests pass)
  └─→ TEST_FAILED (tests fail)
        ↓
      bug-hunter spawned with failure details
        ↓
      IN_PROGRESS (retry implementation)
        ↓
      TESTING (retry tests)
        ↓
      [repeat up to max_retries times]
```

### Orchestrator Changes

#### 1. After Agent Completes Implementation

```python
async def execute_task(task: Task) -> TaskResult:
    # Agent does implementation
    task.state = TaskState.IN_PROGRESS
    impl_output = await _execute_with_agent(task)

    # NEW: Transition to TESTING instead of COMPLETED
    task.state = TaskState.TESTING

    # NEW: Auto-run tests
    test_result = await _run_task_tests(task)

    if test_result.passed:
        task.state = TaskState.COMPLETED
        return TaskResult(success=True, output=impl_output)
    else:
        task.state = TaskState.TEST_FAILED
        return TaskResult(success=False, error=test_result.failure_details)
```

#### 2. Test Execution Logic

```python
async def _run_task_tests(task: Task) -> TestResult:
    """
    Run tests associated with a task.

    For tasks with test dependencies (e.g., buffer-impl depends on buffer-tests),
    look for test files in the project directory and execute them.

    Returns TestResult with:
    - passed: bool
    - output: str (test runner output)
    - failure_details: str (parsed failures for bug-hunter)
    """
    # Identify test command from task metadata or conventions
    # Examples:
    # - pytest tests/test_buffer.py -v
    # - make test-buffer
    # - python -m unittest tests.test_buffer

    test_command = _determine_test_command(task)

    # Execute test command
    result = await _execute_command(test_command, cwd=task.project_dir)

    # Parse output to determine pass/fail
    passed = _parse_test_success(result)

    # Extract failure details if tests failed
    failure_details = _extract_failure_details(result) if not passed else None

    return TestResult(
        passed=passed,
        output=result.stdout,
        failure_details=failure_details
    )
```

#### 3. Bug-Hunter Retry Loop

```python
async def _handle_test_failure(task: Task, test_result: TestResult, retry_count: int = 0, max_retries: int = 3) -> TaskResult:
    """
    Handle test failures with bug-hunter retry loop.

    1. Spawn bug-hunter with failure details
    2. Bug-hunter analyzes and fixes code
    3. Re-run tests
    4. Repeat up to max_retries times
    """
    if retry_count >= max_retries:
        return TaskResult(
            success=False,
            error=f"Tests failed after {max_retries} bug-hunter attempts:\n{test_result.failure_details}"
        )

    # Spawn bug-hunter with context
    bug_hunter_prompt = f"""
Task: {task.description}

Tests have failed with the following errors:
{test_result.failure_details}

Please analyze the failures, fix the bugs, and ensure all tests pass.

Test command: {_determine_test_command(task)}
"""

    task.state = TaskState.IN_PROGRESS
    fix_output = await _execute_bug_hunter(bug_hunter_prompt, task)

    # Re-run tests
    task.state = TaskState.TESTING
    retest_result = await _run_task_tests(task)

    if retest_result.passed:
        task.state = TaskState.COMPLETED
        return TaskResult(success=True, output=f"Fixed after {retry_count + 1} attempts:\n{fix_output}")
    else:
        task.state = TaskState.TEST_FAILED
        return await _handle_test_failure(task, retest_result, retry_count + 1, max_retries)
```

### Task Metadata Requirements

Tasks need test identification info. Extend `Task` model:

```python
@dataclass
class Task:
    id: str
    description: str
    state: TaskState
    dependencies: List[str]

    # NEW: Test specification
    test_command: Optional[str] = None  # Explicit test command
    test_file: Optional[str] = None     # Test file path for conventions
    requires_testing: bool = True       # Some tasks (planning, docs) skip tests
```

### Test Discovery Conventions

If `test_command` not specified, use conventions:

1. **Pytest convention**: `pytest tests/test_{task_id}.py -v`
2. **Make convention**: `make test-{task_id}`
3. **File-based convention**: Look for `{task_id}_test.py` or `test_{task_id}.py`

### Orchestrator Integration Points

```python
async def orchestrate_execution(project: Project) -> Dict[str, TaskResult]:
    """Enhanced orchestration with verification loop."""
    results = {}

    for task_id in _get_executable_tasks(project):
        task = project.tasks[task_id]

        # Execute implementation
        task.state = TaskState.IN_PROGRESS
        impl_result = await _execute_with_agent(task)

        # Skip testing for non-code tasks
        if not task.requires_testing:
            task.state = TaskState.COMPLETED
            results[task_id] = TaskResult(success=True, output=impl_result)
            continue

        # Run verification loop
        task.state = TaskState.TESTING
        test_result = await _run_task_tests(task)

        if test_result.passed:
            task.state = TaskState.COMPLETED
            results[task_id] = TaskResult(success=True, output=impl_result)
        else:
            # Enter bug-hunter retry loop
            task.state = TaskState.TEST_FAILED
            retry_result = await _handle_test_failure(task, test_result)
            results[task_id] = retry_result

    return results
```

## Key Design Decisions

### 1. Automatic Test Execution
**Decision**: Orchestrator automatically runs tests after implementation.
**Rationale**: Manual verification is unreliable and easy to skip.
**Alternative considered**: Require explicit test tasks - rejected as too manual.

### 2. Test Failure = Not Complete
**Decision**: Tasks remain in TEST_FAILED state, not COMPLETED, until tests pass.
**Rationale**: COMPLETED must mean "working code", not just "agent stopped".
**Alternative considered**: Mark complete but flag failures - rejected as misleading.

### 3. Bug-Hunter Auto-Retry
**Decision**: Automatically spawn bug-hunter on test failure with up to 3 retries.
**Rationale**: Most test failures are fixable bugs that don't require human intervention.
**Alternative considered**: Stop and ask human - rejected as breaking autonomous execution.

### 4. Test Command Discovery
**Decision**: Support both explicit test commands and convention-based discovery.
**Rationale**: Balance flexibility (explicit) with ease of use (conventions).
**Alternative considered**: Require all test commands - rejected as too rigid.

### 5. Non-Code Task Handling
**Decision**: Add `requires_testing` flag to skip verification for planning/docs tasks.
**Rationale**: Not all tasks produce testable code.
**Alternative considered**: Try to test everything - rejected as impractical.

## Implementation Plan

1. **Update models.py**:
   - Add TESTING and TEST_FAILED to TaskState enum
   - Add test_command, test_file, requires_testing to Task dataclass
   - Add TestResult dataclass

2. **Update orchestrator.py**:
   - Implement `_run_task_tests()` function
   - Implement `_handle_test_failure()` with retry loop
   - Modify `orchestrate_execution()` to use verification loop
   - Add `_determine_test_command()` for convention discovery
   - Add `_parse_test_success()` and `_extract_failure_details()` helpers

3. **Add bug-hunter integration**:
   - Create bug-hunter prompt template with failure details
   - Use existing Task tool to spawn bug-hunter agent
   - Pass task context and test failures

4. **Testing**:
   - Create simple test project with intentional bugs
   - Verify TESTING → TEST_FAILED → bug-hunter → TESTING → COMPLETED flow
   - Verify retry limits work
   - Verify non-code tasks skip testing

## Success Metrics

After implementation, measure:
- **Process success**: Tasks transition through states correctly
- **Product success**: Final test pass rate = 100% (not 16.7%)
- **Autonomous recovery**: Bug-hunter fixes >80% of test failures without human intervention
- **Reliability**: No tasks marked COMPLETED with failing tests

## Hierarchical/Recursive Planning and Execution

**User insight**: "it might be the case that super planner needs to be recursive - both in the planning and execution phases"

### The Problem

The vi editor project had 29 tasks at one level. This creates challenges:

1. **Planning complexity**: LLM struggles to reason about 29 interdependent tasks simultaneously
2. **Execution coordination**: Managing dependencies and parallelization across 29 tasks is error-prone
3. **Cognitive overload**: Human can't easily track progress across flat 29-task list
4. **Context limits**: Full context for 29 tasks may exceed LLM context window

### Proposed Solution: Hierarchical Task Structure

Support nested sub-projects within tasks:

```python
@dataclass
class Task:
    id: str
    description: str
    state: TaskState
    dependencies: List[str]

    # NEW: Hierarchical support
    is_parent: bool = False                    # True if this task has sub-tasks
    sub_project_id: Optional[str] = None       # Reference to nested Project

    # Existing fields
    test_command: Optional[str] = None
    test_file: Optional[str] = None
    requires_testing: bool = True
```

### Hierarchical Planning Phase

When creating project plan, LLM can:

1. **Top-level decomposition**: Break project into 5-10 major phases
2. **Recursive decomposition**: Each phase becomes a parent task with its own sub-project
3. **Leaf tasks**: Eventually decompose to atomic implementation tasks

Example for vi editor:

```
Project: Vi Editor
├─ Phase 1: Foundation (parent task)
│  └─ Sub-project: Foundation
│     ├─ design-architecture (leaf task)
│     ├─ create-test-framework (leaf task)
│     └─ setup-project-structure (leaf task)
├─ Phase 2: Buffer Management (parent task)
│  └─ Sub-project: Buffer Management
│     ├─ buffer-tests (leaf task)
│     ├─ buffer-impl (leaf task)
│     └─ buffer-integration (leaf task)
├─ Phase 3: Navigation (parent task)
│  └─ Sub-project: Navigation
│     ├─ navigation-tests (leaf task)
│     ├─ navigation-impl (leaf task)
│     └─ navigation-integration (leaf task)
...
```

### Hierarchical Execution Phase

Orchestrator handles parent tasks by:

1. **Detect parent task**: Check `is_parent` flag
2. **Load sub-project**: Load nested project by `sub_project_id`
3. **Recursive orchestration**: Call `orchestrate_execution(sub_project)` recursively
4. **Aggregate results**: Parent task state depends on sub-project completion
5. **Bubble up failures**: If sub-project has TEST_FAILED tasks, parent remains IN_PROGRESS

```python
async def orchestrate_execution(project: Project, depth: int = 0, max_depth: int = 3) -> Dict[str, TaskResult]:
    """Hierarchical orchestration with recursion."""
    if depth > max_depth:
        raise RecursionError(f"Project nesting exceeds max depth {max_depth}")

    results = {}

    for task_id in _get_executable_tasks(project):
        task = project.tasks[task_id]

        if task.is_parent:
            # Recursive case: orchestrate sub-project
            task.state = TaskState.IN_PROGRESS
            sub_project = _load_project(task.sub_project_id)

            # Recursive call with increased depth
            sub_results = await orchestrate_execution(sub_project, depth + 1, max_depth)

            # Check if all sub-tasks completed successfully
            if all(r.success for r in sub_results.values()):
                task.state = TaskState.COMPLETED
                results[task_id] = TaskResult(success=True, output="All sub-tasks completed")
            else:
                # Parent stays in progress if any sub-task failed
                failed = [tid for tid, r in sub_results.items() if not r.success]
                results[task_id] = TaskResult(
                    success=False,
                    error=f"Sub-tasks failed: {failed}"
                )
        else:
            # Base case: execute leaf task with verification loop
            result = await _execute_leaf_task(task)
            results[task_id] = result

    return results
```

### Planning UI/UX Improvements

Support hierarchical planning in interactive mode:

```
Human: "Build a vi editor"

Agent: "This is a large project. I'll break it into phases:
1. Foundation (architecture, tests, project setup)
2. Buffer Management (data structure for text)
3. Navigation (cursor movement)
4. Editing (insert, delete, yank/paste, visual)
5. Advanced Features (undo/redo, search, replace)
6. File I/O
7. Display & CLI
8. Integration & Documentation

Should I create detailed sub-tasks for each phase? (yes/no/customize)"

### Benefits of Hierarchical Approach

1. **Bounded context per level**: Each sub-project fits comfortably in LLM context
2. **Clear progress tracking**: Human sees "Phase 2: Buffer Management (3/3 tasks complete)"
3. **Natural parallelization**: Sub-projects within same phase can run in parallel
4. **Incremental planning**: Can plan Phase 1 fully, then plan Phase 2 based on Phase 1 results
5. **Easier debugging**: Failures isolated to specific sub-project, not entire 29-task list

### Implementation Requirements for Hierarchy

1. **Update models.py**:
   - Add `is_parent` and `sub_project_id` fields to Task
   - Ensure Project can reference parent project for navigation

2. **Update orchestrator.py**:
   - Add recursive `orchestrate_execution()` with depth tracking
   - Implement `_load_project()` to fetch sub-projects
   - Add parent task state aggregation logic

3. **Update CLI**:
   - Add commands to navigate hierarchies: `/superplanner show --depth 2`
   - Display hierarchical status: tree view vs. flat list
   - Support drilling down: `/superplanner status phase-2`

4. **Planning agent integration**:
   - Agent asks if project should be hierarchical (>10 tasks)
   - Agent proposes phase breakdown before detailed planning
   - Agent creates sub-projects with proper linkage

### Design Decision: When to Use Hierarchy

**Heuristics**:
- Projects with >15 estimated tasks → suggest hierarchy
- Projects with clear phases → suggest hierarchy
- Projects that span multiple domains → suggest hierarchy
- Simple CRUD apps or single features → keep flat

**User control**:
- Always ask before hierarchical decomposition
- Allow forcing flat structure: `--flat` flag
- Allow specifying depth: `--max-depth 2`

## Combined Implementation Plan

### Phase 1: Verification Loop (Priority 1)
1. Update TaskState enum with TESTING/TEST_FAILED
2. Add test metadata fields to Task
3. Implement test execution in orchestrator
4. Add bug-hunter retry loop
5. Test with simple project (single level)

### Phase 2: Hierarchical Support (Priority 2)
1. Add hierarchical fields to Task model
2. Implement recursive orchestrator
3. Update CLI for hierarchy navigation
4. Add planning heuristics for hierarchy detection
5. Test with vi editor project structure

### Phase 3: Integration (Priority 3)
1. Combine verification with hierarchy
2. Ensure sub-project tests bubble up correctly
3. Add parent task aggregation logic
4. Test complete system with complex project

## Review Triggers

Revisit this design if:
- Bug-hunter retry success rate < 50%
- Test execution adds >30% to project time
- Humans frequently override test failures
- Test discovery conventions miss >20% of tests
- Hierarchical projects exceed 3 levels depth regularly
- Context limits still hit even with hierarchy
- Users find hierarchy navigation confusing

## Success Criteria

**Verification loop success**:
- ✅ No tasks marked COMPLETED with failing tests
- ✅ Bug-hunter fixes >80% of failures autonomously
- ✅ Test pass rate = 100% at project completion

**Hierarchical planning success**:
- ✅ Complex projects (>20 tasks) decompose into manageable sub-projects
- ✅ Each sub-project has <10 tasks
- ✅ Human can track progress at any level
- ✅ Failures isolate to specific sub-projects

**Overall success**:
- ✅ Vi editor project completes with 100% test pass rate
- ✅ Human only intervenes for architectural decisions, not bug fixes
- ✅ System scales to projects of any size through hierarchy
