# /bplan Architecture

This document describes the internal architecture of the /bplan interactive project planning system.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     /bplan Command                          │
│                  (Orchestrator)                             │
└──────────────┬──────────────────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌──────▼──────┐
│   Agents    │  │ Components  │
│             │  │             │
│ • planner   │  │ • state     │
│ • executor  │  │ • enforce   │
│ • reviewer  │  │ • beads     │
└─────────────┘  └─────────────┘
       │                │
       └───────┬────────┘
               │
       ┌───────▼────────┐
       │  Beads Issues  │
       │  (Truth Store) │
       └────────────────┘
```

## Core Components

### 1. Workflow Orchestrator

**Location**: `.claude/commands/bplan.md`

**Responsibility**: Main state machine that coordinates the five-stage workflow.

**Key Functions**:
- Parse user's initial request
- Manage workflow state transitions
- Spawn agents at appropriate stages
- Handle user interactions and approvals
- Coordinate beads updates

**State Transitions**:
```
INTAKE → PLANNING → EXECUTION → REVIEW → RECONCILIATION
   ↓         ↓          ↓           ↓            ↓
 brief    epic +    phase work   approve/    complete/
          phases                  reject      adjust
```

### 2. Workflow State Management

**Location**: `amplifier/bplan/workflow_state.py`

**Responsibility**: Persist and restore workflow state across sessions.

**Data Model**:
```python
@dataclass
class WorkflowState:
    epic_id: str              # Beads epic ID
    current_stage: str        # intake|planning|execution|review|reconciliation
    current_phase: str        # Current phase being worked on
    phases: list[dict]        # All phase IDs and statuses
    project_brief: str        # Original project description
    plan_summary: str         # High-level plan overview
```

**Storage**:
- File: `.beads/bplan_state.json`
- Format: JSON
- Operations: save_state(), load_state(), clear_state()

**Design Decisions**:
- **File-based over database**: Simplicity, no dependencies
- **JSON over pickle**: Human-readable, debuggable
- **Defensive I/O**: Retry logic for cloud sync (OneDrive, Dropbox)
- **Graceful degradation**: Returns None on missing/corrupted files

### 3. Test-First Enforcement

**Location**: `amplifier/bplan/test_enforcement.py`

**Responsibility**: Ensure tests exist before implementation through subprocess isolation.

**Key Functions**:
```python
get_test_path(module_path) -> Path
    # Calculate test file path for module
    # amplifier/auth.py → tests/test_auth.py

check_test_exists(module_path) -> bool
    # Check if test file exists
    # Uses file system, no imports

generate_test_stub(module_path, spec) -> Path
    # Create pytest-compatible test stub
    # Includes: imports, test class, placeholder tests

validate_test_first(module_path) -> bool
    # Validate in subprocess (no namespace pollution)
    # Returns: True if tests exist, False otherwise
```

**Subprocess Isolation**:
```
Parent Process              Subprocess
     │                           │
     ├─ validate_test_first()   │
     │   ├─ Build validation    │
     │   │  code string         │
     │   │                       │
     │   └─ subprocess.run() ────┼──> Execute validation
     │                           │    (clean namespace)
     │                           │
     │   ◄────── returncode ─────┤
     │                           │
     └─ Return True/False        │
```

**Why Subprocess**:
- **No namespace pollution**: Module being validated never imported into parent
- **Clean validation**: Each check runs in fresh Python process
- **Side effect isolation**: Module with global state doesn't affect parent
- **Test integrity**: Validates test existence without running implementation

### 4. Beads Integration

**Location**: `amplifier/bplan/beads_integration.py`

**Responsibility**: Python wrapper for bd CLI with type-safe interfaces.

**Key Classes**:
```python
class BeadsClient:
    # Main client for bd operations
    create_issue() -> str                    # Returns issue ID
    update_status(id, status) -> None
    close_issue(id) -> None
    add_comment(id, comment) -> None
    list_issues(status?) -> list[BeadsIssue]
    get_issue(id) -> BeadsIssue

class BeadsIssue:
    # Type-safe issue representation
    id: str
    title: str
    type: IssueType
    status: IssueStatus
    priority: int
    description: str
    labels: list[str]
    dependencies: list[str]

enum IssueType: EPIC | TASK | BUG | FEATURE | CHORE
enum IssueStatus: OPEN | IN_PROGRESS | CLOSED
```

**Command Execution**:
```
BeadsClient
     │
     ├─ _run_command(["bd", "create", ...])
     │       │
     │       └─ subprocess.run()
     │              │
     │              └─ bd CLI (Go binary)
     │                     │
     │                     └─ .beads/amplifier.db (SQLite)
     │                     └─ .beads/issues.jsonl (export)
     │
     └─ Parse output → Return result
```

**Error Handling**:
- Command failures raise `BeadsError` with details
- Missing bd binary detected and reported
- JSON parsing errors handled gracefully

## Specialized Agents

### Project-Planner Agent

**Location**: `.claude/agents/project-planner.md`

**Invoked At**: Stages 2 (planning) and 5 (reconciliation)

**Inputs**:
- Project brief (from intake)
- Codebase context (@files)
- Philosophy docs (@ai_context/*)

**Outputs**:
- Phase breakdown with dependencies
- Test strategies per phase
- Acceptance criteria (testable)
- Risk analysis
- Beads issue structure

**Key Capabilities**:
- Codebase analysis (Glob/Grep)
- Pattern recognition (existing architecture)
- Philosophy compliance checking
- Dependency graph construction

### Phase-Executor Agent

**Location**: `.claude/agents/phase-executor.md`

**Invoked At**: Stage 3 (per phase, fresh session)

**Inputs**:
- Phase specification (from planner)
- Beads issue ID for tracking
- Test strategy requirements

**Outputs**:
- Comprehensive test suite (written FIRST)
- Implementation code (minimal to pass tests)
- Test execution results
- Acceptance criteria checklist

**Test-First Flow**:
```
1. RED Phase
   ├─ Write ALL tests first
   ├─ Run tests (expect failures)
   └─ Verify tests fail for RIGHT reasons

2. GREEN Phase
   ├─ Implement minimal code
   ├─ Run tests repeatedly
   └─ Fix until all pass

3. REFACTOR Phase
   ├─ Improve code structure
   ├─ Keep tests passing
   └─ No new functionality
```

**Retry Strategy**:
- Max 5 attempts per phase
- Each failure logged to beads
- Root cause analysis on 5th failure
- User intervention requested after 5 failures

### Phase-Reviewer Agent

**Location**: `.claude/agents/phase-reviewer.md`

**Invoked At**: Stage 3 (after each phase execution)

**Inputs**:
- Phase specification (original)
- Completed work (code + tests)
- Acceptance criteria

**Outputs**:
- APPROVED or REJECTED decision
- Test quality analysis
- Acceptance criteria checklist
- Detailed feedback if rejected

**Quality Checks**:
```
1. Test Execution
   └─ All tests must pass

2. Test Quality
   ├─ No weak assertions (assert result)
   ├─ No mock abuse (real implementations)
   ├─ Antagonistic tests (catch cheating)
   └─ Proper coverage (>80%)

3. Acceptance Criteria
   └─ All criteria met (binary check)

4. Code Quality
   ├─ Philosophy compliance
   ├─ No stubs/placeholders
   ├─ Proper error handling
   └─ Type hints complete

5. Integration
   └─ Existing tests still pass
```

## Data Flow

### Complete Workflow Data Flow

```
1. INTAKE STAGE
   User Input → Questions → Project Brief
        ↓
   save_state(brief)
        ↓
   User Approval

2. PLANNING STAGE
   Project Brief → project-planner → Phase Plan
        ↓
   create_issue(epic) → epic_id
        ↓
   For each phase:
      create_issue(phase, deps) → phase_id
        ↓
   save_state(epic_id, phases)
        ↓
   User Approval

3. EXECUTION STAGE (per phase)
   load_state() → current_phase
        ↓
   update_status(phase_id, IN_PROGRESS)
        ↓
   Phase Spec → phase-executor → Implementation
        ↓
   save_state(progress)
        ↓
   Implementation → phase-reviewer → Decision
        ↓
   if APPROVED:
      close_issue(phase_id)
      save_state(next_phase)
   else:
      add_comment(phase_id, feedback)
      retry (max 5)

4. VALIDATION STAGE
   Run all tests → Check regressions
        ↓
   if issues:
      spawn bug-hunter → fixes

5. RECONCILIATION STAGE
   All Phases → project-planner → Validation
        ↓
   close_issue(epic_id)
        ↓
   clear_state()
```

### State Persistence Flow

```
Session 1                Session 2 (after restart)
   │                            │
   ├─ save_state()             │
   │  └─ .beads/state.json ────┼──> load_state()
   │                            │    └─ Resume from saved position
   │                            │
   ├─ Work interrupted          │
   │  (compaction, crash)       │
   │                            │
   └─ ✗ Session ends           └─ ✓ Work continues
```

## Design Decisions

### Why File-Based State?

**Alternatives Considered**:
- SQLite database
- In-memory only (no persistence)
- Beads-only (no separate state file)

**Why JSON File Won**:
- ✅ Simple: No DB setup, no schema migrations
- ✅ Debuggable: Human-readable, can edit manually
- ✅ Portable: Copy/paste between machines
- ✅ No dependencies: Standard library only
- ✅ Git-friendly: Text format, easy diffs

**Trade-offs Accepted**:
- ❌ No ACID transactions (but single-writer, so okay)
- ❌ No complex queries (but don't need them)

### Why Subprocess Isolation?

**Problem**: Validating test existence shouldn't import the module being validated.

**Alternatives Considered**:
- Import module and check (❌ namespace pollution)
- Parse AST (❌ complex, fragile)
- File existence only (✅ simple but already done in check_test_exists)

**Why Subprocess Won**:
- ✅ Complete isolation
- ✅ No side effects
- ✅ Validates test existence without running code
- ✅ Detects test files reliably

**Trade-offs Accepted**:
- ❌ Slightly slower (~100ms per validation)
- ❌ More complex testing (need to mock subprocess)

### Why Separate Agents?

**Alternative**: Single "do everything" agent

**Why Separation Won**:
- ✅ Single responsibility per agent
- ✅ Fresh context per phase (no pollution)
- ✅ Specialized prompts for each role
- ✅ Parallel execution possible
- ✅ Easier to debug and improve

**Trade-offs Accepted**:
- ❌ More files to maintain
- ❌ Coordination overhead in orchestrator

## Performance Characteristics

### Time Complexity

**Intake Stage**: O(1) - Fixed number of questions

**Planning Stage**: O(n) - Linear in number of files analyzed
- Glob operations: O(files)
- Grep operations: O(files × lines)

**Execution Stage**: O(phases × attempts)
- Each phase: 1-5 attempts
- Each attempt: O(tests) to run

**Review Stage**: O(tests) per phase
- Test execution: O(tests)
- Quality checks: O(lines of code)

### Space Complexity

**State File**: O(phases)
- ~1KB per phase
- Typical project: 5-10 phases = 5-10KB

**Beads Database**: O(issues)
- ~1KB per issue
- Typical project: 1 epic + 5-10 phases = ~10KB

**Agent Context**: O(1) per agent
- Fresh session per phase
- No context accumulation

## Error Handling

### State Corruption

**Symptom**: `load_state()` returns None

**Causes**:
- Malformed JSON
- Missing required fields
- File permissions issue

**Recovery**:
1. Try to parse JSON (catch JSONDecodeError)
2. Validate required fields present
3. If corrupted: log warning, return None
4. User can clear state and restart

### Beads Command Failures

**Symptom**: `BeadsError` raised

**Causes**:
- bd CLI not in PATH
- Invalid command arguments
- Database locked
- Permission issues

**Recovery**:
1. Catch subprocess errors
2. Parse stderr for error message
3. Raise BeadsError with context
4. User sees clear error, can fix

### Agent Failures

**Symptom**: Phase fails multiple times

**Causes**:
- Unclear requirements
- Missing dependencies
- Complex implementation
- Test-first discipline not followed

**Recovery**:
1. Track attempt count in beads
2. After 5 attempts: generate root cause analysis
3. Ask user for help
4. Options: debug together, skip phase, abort

## Testing Strategy

### Component Tests

**workflow_state.py**: 21 tests
- Dataclass serialization (4 tests)
- File I/O operations (14 tests)
- Workflow resumption (3 tests)

**test_enforcement.py**: 22 tests
- Path calculation (4 tests)
- Test existence checking (3 tests)
- Stub generation (6 tests)
- Validation logic (3 tests)
- Subprocess isolation (3 tests)
- Edge cases (3 tests)

**beads_integration.py**: 18 tests
- Issue CRUD operations (8 tests)
- Command execution (3 tests)
- Error handling (3 tests)
- Dataclass operations (4 tests)

### Integration Tests

See Phase 4 (amplifier-12) for end-to-end workflow testing.

## Extension Points

### Adding New Agents

1. Create agent spec in `.claude/agents/`
2. Use `/agents` command to register
3. Update orchestrator to spawn at appropriate stage

### Adding New State Fields

1. Update `WorkflowState` dataclass
2. Update tests for serialization
3. Update orchestrator to populate new fields

### Adding New Beads Operations

1. Add method to `BeadsClient`
2. Add tests for new operation
3. Update orchestrator to use new operation

## Related Documentation

- [README](README.md) - User guide and examples
- [EXTENDING](EXTENDING.md) - Customization guide
- [Implementation Philosophy](../../ai_context/IMPLEMENTATION_PHILOSOPHY.md)
- [Modular Design Philosophy](../../ai_context/MODULAR_DESIGN_PHILOSOPHY.md)
