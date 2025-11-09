# /bplan: Interactive Project Planning System

The `/bplan` command orchestrates Brian's multi-stage project planning and execution workflow, enabling test-first development at scale with beads integration for full state tracking.

## Quick Start

```bash
# Start a new project
/bplan Build user authentication with JWT tokens

# The system will:
# 1. Ask clarifying questions interactively
# 2. Create a detailed, phased plan
# 3. Execute each phase with test-first discipline
# 4. Review and validate each phase
# 5. Complete with all tests passing
```

## Core Philosophy

**Test-First Always**: Every phase starts with comprehensive, antagonistic tests written BEFORE any implementation.

**Interactive, Not Assumptive**: The system asks questions rather than making assumptions.

**Beads as Truth**: All project state tracked in beads issues, enabling resumption after interruptions.

**No Test Cheating**: Enforced through subprocess isolation and reviewer validation.

## The Five-Stage Workflow

### Stage 1: Interactive Intake

The system gathers project requirements through targeted questions:

1. **Project Description** - What needs to be built
2. **Existing Documentation** - Any planning docs or specs
3. **Key Requirements** - Must-have features
4. **Constraints** - Technical/time/resource limits
5. **Definition of Done** - Success criteria
6. **Context Files** - Relevant files/modules to review

**Output**: Project brief validated with user

### Stage 2: Discovery & Planning

Spawns **project-planner agent** to:

- Analyze codebase for existing patterns
- Review project philosophy docs
- Break project into test-first phases
- Define acceptance criteria per phase
- Create beads epic and phase issues
- Map dependencies

**Output**: Detailed implementation plan with beads structure

**User Approval**: "Does this approach look correct? (yes/no/adjust)"

### Stage 3: Phase Execution Loop

For each phase in sequence (or parallel if independent):

#### 3.1 Phase Execution

Spawns **phase-executor agent** in fresh session:

- Writes ALL tests BEFORE implementation (RED phase)
- Verifies tests fail initially
- Implements minimal code to pass (GREEN phase)
- Updates beads throughout
- Max 5 retry attempts on failures

#### 3.2 Phase Review

Spawns **phase-reviewer agent** to validate:

- All tests pass with real implementations
- No test cheating (mocks only where necessary)
- Acceptance criteria met
- Code quality and philosophy compliance
- Integration tests pass

**Outcomes**:
- **APPROVED**: Close phase, move to next
- **REJECTED**: Provide feedback, return to executor

**Optional**: Quick user sanity check (< 2 minutes)

### Stage 4: Inter-Phase Validation

After each phase:
- Run all previous tests (check for regressions)
- Verify integration between phases
- Spawn bug-hunter if issues found

### Stage 5: Final Reconciliation

Spawns **project-planner agent** again to:

- Review all phases against original ask
- Verify nothing missed or drifted
- Check philosophy alignment
- Run final integration tests
- Generate completion report

**User Approval**: "Project complete! Approve? (yes/adjust)"

## Key Components

### Workflow State Management

**Module**: `amplifier/bplan/workflow_state.py`

Persists workflow state to `.beads/bplan_state.json` for resumption after interruptions.

```python
from amplifier.bplan.workflow_state import WorkflowState, save_state, load_state

# Save current state
state = WorkflowState(
    epic_id="amplifier-42",
    current_stage="execution",
    current_phase="amplifier-43",
    phases=[{"id": "amplifier-43", "status": "in_progress"}],
    project_brief="Build authentication system",
    plan_summary="3 phases: core, JWT, tests"
)
save_state(state)

# Resume later
loaded_state = load_state()
if loaded_state:
    print(f"Resuming from {loaded_state.current_phase}")
```

**Features**:
- JSON-based persistence
- Graceful error handling (missing/corrupted files)
- Defensive file I/O for cloud sync compatibility

### Test-First Enforcement

**Module**: `amplifier/bplan/test_enforcement.py`

Ensures tests exist before implementation through subprocess isolation.

```python
from amplifier.bplan.test_enforcement import (
    get_test_path,
    check_test_exists,
    generate_test_stub,
    validate_test_first
)

# Check if tests exist for a module
module_path = Path("amplifier/auth/jwt.py")
if not check_test_exists(module_path):
    # Generate test stub
    test_file = generate_test_stub(
        module_path,
        spec="JWT token generation and validation"
    )
    print(f"Created test stub: {test_file}")

# Validate test-first (runs in subprocess)
if validate_test_first(module_path):
    print("Tests exist - safe to implement")
else:
    print("Write tests first!")
```

**Features**:
- Subprocess isolation (no namespace pollution)
- Automatic test stub generation
- Pytest-compatible test structure

### Beads Integration

**Module**: `amplifier/bplan/beads_integration.py`

Python wrapper for bd CLI with type-safe interfaces.

```python
from amplifier.bplan.beads_integration import (
    BeadsClient,
    IssueStatus,
    IssueType
)

client = BeadsClient()

# Create epic
epic_id = client.create_issue(
    title="Build Authentication System",
    description="JWT-based auth with session management",
    issue_type=IssueType.EPIC,
    priority=0
)

# Create phase
phase_id = client.create_issue(
    title="Phase 1: Core Auth Module",
    description="User registration and login",
    issue_type=IssueType.TASK,
    depends_on=[epic_id],
    labels=["phase", "test-first"],
    priority=0
)

# Update status
client.update_status(phase_id, IssueStatus.IN_PROGRESS)

# Close when done
client.close_issue(phase_id)
```

## Specialized Agents

### project-planner

**When Used**: Stages 2 and 5 (planning and reconciliation)

**Responsibilities**:
- Requirements analysis
- Codebase pattern analysis
- Phase breakdown with test strategies
- Dependency mapping
- Risk analysis

**Key Principle**: Plans so clear that executors never guess

### phase-executor

**When Used**: Stage 3 (phase execution)

**Responsibilities**:
- Write comprehensive tests FIRST (RED phase)
- Verify tests fail before implementation
- Implement minimal code to pass (GREEN phase)
- Refactor while keeping tests green
- Update beads throughout

**Key Principle**: Test-first is non-negotiable

### phase-reviewer

**When Used**: Stage 3 (phase validation)

**Responsibilities**:
- Validate all tests pass
- Check test quality (catch cheating)
- Verify acceptance criteria
- Check philosophy compliance
- Run integration tests

**Key Principle**: Quality gatekeeper, catches shortcuts

## Best Practices

### For Users

**Be Specific in Initial Ask**:
```
Good: "Build JWT authentication with refresh tokens, password hashing with bcrypt, and session management"
Bad: "Make auth stuff"
```

**Provide Context**:
```
Good: "We already use FastAPI for APIs, follow patterns in @api/auth.py"
Bad: [No context provided]
```

**Review Plans Carefully**:
- Check phase breakdown makes sense
- Verify test strategy is comprehensive
- Confirm dependencies are correct

### For Phase Executors

**Write Antagonistic Tests**:
```python
# Good - catches naive implementations
def test_password_hash_uses_salt():
    hash1 = hash_password("password")
    hash2 = hash_password("password")
    assert hash1 != hash2  # Verifies salt

# Bad - always passes
def test_password_hash():
    result = hash_password("password")
    assert result  # Weak assertion
```

**Use Real Implementations**:
```python
# Good - real database
def test_save_user():
    db = create_test_database()
    user_id = save_user(db, {"email": "test@example.com"})
    retrieved = db.get_user(user_id)
    assert retrieved.email == "test@example.com"

# Bad - mocked return
@mock.patch('db.save')
def test_save_user(mock_save):
    mock_save.return_value = True
    assert save_user({})  # Only tests mock
```

## Troubleshooting

### "Phase failed 5 times"

The phase-executor has retried 5 times and provided root cause analysis.

**Actions**:
1. Review the analysis in beads issue comments
2. Options: debug together, skip phase, abort project
3. Common causes: Missing dependencies, unclear requirements, complex implementation

### "Tests are cheating"

The phase-reviewer detected weak tests or mocking abuse.

**Actions**:
1. Review rejected feedback
2. Fix tests to verify real behavior
3. Remove unnecessary mocks
4. Add stronger assertions

### State Corruption

If `.beads/bplan_state.json` becomes corrupted:

```python
from amplifier.bplan.workflow_state import clear_state

# Remove corrupted state
clear_state()

# Restart /bplan
# It will create fresh state
```

## Examples

See `docs/bplan/examples/` for complete walkthroughs:

- `authentication_system.md` - Building JWT auth from scratch
- `api_endpoints.md` - Creating REST API with /bplan
- `data_pipeline.md` - Building ETL pipeline with phases

## Philosophy Alignment

The /bplan system embodies Amplifier's core principles:

**Ruthless Simplicity**:
- File-based state (not complex database)
- Direct subprocess calls (not elaborate frameworks)
- Minimal abstractions throughout

**Contract-First Design**:
- Clear interfaces between components
- Type-safe dataclasses
- Well-defined agent responsibilities

**Trust in Emergence**:
- Good architecture emerges from good practices
- Test-first discipline enforced
- Philosophy guides, doesn't dictate

**Modular "Bricks & Studs"**:
- Each phase is self-contained
- Clear connection points between phases
- Regeneratable components

## Related Documentation

- [Architecture](ARCHITECTURE.md) - System design and data flow
- [Extending](EXTENDING.md) - Adding features and customizing
- [Implementation Philosophy](../../ai_context/IMPLEMENTATION_PHILOSOPHY.md) - Core principles
- [Modular Design](../../ai_context/MODULAR_DESIGN_PHILOSOPHY.md) - "Bricks & studs" approach

## Getting Help

If you encounter issues:

1. Check beads issues for error details
2. Review phase-reviewer feedback
3. Consult examples in `docs/bplan/examples/`
4. Ask for human help if stuck after 5 retries

The /bplan system is designed to guide you through complex projects with confidence, catching mistakes early and enforcing quality throughout.
