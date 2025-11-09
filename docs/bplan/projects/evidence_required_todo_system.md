# Evidence-Required Todo System Enhancement - Project Plan

**Epic**: bd-3
**Status**: In Progress
**Priority**: P0
**Created**: 2025-10-14

## Executive Summary

Build an independent validation system that enforces strict evidence requirements for task completion, preventing "lazy coder" shortcuts through blind testing and independent review with golden file validation.

## Project Goals

Create a system that:
1. Requires hard evidence (golden files, metrics, test output) for code TODO completion
2. Implements 3-agent workflow (Spec Writer, Coder, Blind Tester) with subprocess isolation
3. Provides independent review for design TODOs with context-free validation
4. Integrates seamlessly with TodoWrite and beads
5. Is universally accessible to all agents in the system
6. Validates itself using its own evidence requirements (meta-validation)

## Core Requirements

### System Independence
- Compatible with TodoWrite and beads but not dependent on either
- Universal visibility to all coding agents and tools
- Accessible via CLI and Python API
- Works in transient codespaces (commit frequently)

### Two Validation Tracks

#### 1. Code TODO Workflow (3-Agent with Blind Testing)
1. **Agent 1 (Spec Writer)**: Creates test/spec + golden files
   - Writes test code defining expected behavior
   - Creates golden output files (expected results)
   - Stores golden files in restricted `.beads/evidence/golden/` directory
   - Agent 1 is TRUSTED to create correct golden files
2. **Agent 2 (Coder)**: Implements code to pass spec
   - Sees only test code, NOT golden files
   - Runs in subprocess with filesystem restrictions
   - Cannot access `.beads/evidence/golden/` directory
   - Must implement correct logic from test descriptions alone
3. **Agent 3 (Blind Tester)**: Validates with zero context pollution
   - Runs implementation in isolated subprocess
   - Has access to golden files for validation
   - Performs byte-for-byte comparison: actual vs golden output
   - Zero context from Agent 1 or Agent 2's process
4. **Evidence**: Golden files must be reproduced by executing code
5. **Validation**: Strict blocking - cannot mark complete without passing

#### 2. Design TODO Workflow (Independent Review)
1. **Input**: User requirement + Design TODO output
2. **Validator**: Neutral observer (context-free LLM or non-LLM code)
3. **Evidence**: Independent review confirming design meets requirements
4. **Validation**: Strict blocking without approval

### Anti-Cheat Protocol

Critical enforcement mechanisms:
- **Filesystem access control**: Agent 2 subprocess cannot read golden directory
- **Process isolation**: Each agent runs in separate subprocess (no shared memory)
- **Path restrictions**: Golden file paths hidden in environment variables
- **Access validation**: Agent 3 verifies golden files weren't accessed by Agent 2
- **Antagonistic testing**: Tests designed to catch all cheating attempts

## Success Criteria (ALL must be met)

1. ✅ Code TODO completes 3-agent workflow with blind validation
2. ✅ Design TODO requires independent review before completion
3. ✅ System integrates with TodoWrite seamlessly
4. ✅ System integrates with beads seamlessly
5. ✅ Documentation and examples exist showing both workflows
6. ✅ All existing agents can invoke this system
7. ✅ **Meta-validation**: Success criteria themselves validated with same proof-based approach

## Implementation Phases

### Phase 1: Core Evidence System - Data Models and Validation Logic (bd-6)

**Purpose**: Build foundational evidence storage and validation interfaces

**Tests FIRST (RED)**:
- `test_evidence_store.py`: Test evidence creation, retrieval, validation
- `test_golden_file_handler.py`: Test golden file generation and reproduction
- `test_validation_interfaces.py`: Test code and design validation contracts
- Antagonistic tests: Invalid evidence formats, missing fields, tampered files

**Implementation (GREEN)**:
- `amplifier/bplan/evidence_system.py`:
  - `EvidenceStore` class (file-based `.beads/evidence/`)
  - `Evidence` dataclass (type, content, timestamp, validator_id)
  - `GoldenFileHandler` class (generate, compare, reproduce)
  - `ValidationInterface` protocol (validate_code, validate_design)

**Acceptance Criteria**:
- ✅ All tests pass with real file I/O
- ✅ Evidence stored and retrieved correctly
- ✅ Golden files generate/compare byte-for-byte
- ✅ Validation interface contracts defined
- ✅ No mocks (real filesystem operations)

**Dependencies**: None (foundational phase)

---

### Phase 2: 3-Agent Code Workflow - Spec Writer, Coder, Blind Tester (bd-7)

**Purpose**: Implement 3-agent workflow with golden file anti-cheat protocol

**CRITICAL: Golden File Anti-Cheat Protocol**

**Golden File Workflow**:
1. Agent 1 (Spec Writer) creates BOTH:
   - `test_module.py` (test code that calls implementation)
   - `golden_output.txt` (expected correct output)
   - Stores golden files in `.beads/evidence/golden/` (restricted directory)
2. Agent 2 (Coder) sees ONLY:
   - `test_module.py` (test logic and function calls)
   - Test descriptions explaining expected behavior
   - CANNOT access `.beads/evidence/golden/` directory
3. Agent 3 (Blind Tester) validates:
   - Runs Agent 2's implementation in isolated subprocess
   - Loads golden files from `.beads/evidence/golden/`
   - Byte-for-byte comparison of actual vs golden output

**Tests FIRST (RED)**:
- `test_spec_writer_creates_golden_files.py`: Verify Agent 1 creates both test + golden
- `test_coder_cannot_access_golden.py`: ANTAGONISTIC - Agent 2 tries to read golden, fails
- `test_filesystem_isolation.py`: Verify subprocess cannot access restricted paths
- `test_blind_validation.py`: Verify Agent 3 validates in clean subprocess
- `test_cheat_detection.py`: ANTAGONISTIC - Detect all cheating attempts

**Implementation (GREEN)**:
- `amplifier/bplan/three_agent_workflow.py`:
  - `SpecWriterAgent` class: Creates both test + golden files
  - `CoderAgent` class: Implements in restricted subprocess
  - `BlindTesterAgent` class: Validates in isolated subprocess
  - `FilesystemRestrictor`: Enforces access controls
  - `WorkflowOrchestrator`: Coordinates agents with isolation

**Anti-Cheat Enforcement**:
- ✅ Filesystem access control
- ✅ Process isolation
- ✅ Path restrictions
- ✅ Access logging and validation

**Acceptance Criteria**:
- ✅ Spec writer creates both test + golden files
- ✅ Golden files stored in restricted directory
- ✅ Coder subprocess CANNOT access golden directory (verified by tests)
- ✅ All attempts to access golden files detected and blocked
- ✅ Blind tester validates in isolated subprocess
- ✅ Byte-for-byte reproduction required
- ✅ Antagonistic tests catch all cheating attempts

**Dependencies**: Phase 1 (evidence system, golden file handler)

---

### Phase 3: Design TODO Independent Review Workflow (bd-8)

**Purpose**: Context-free validation for design TODOs

**Tests FIRST (RED)**:
- `test_design_reviewer.py`: Test context-free validation
- `test_requirement_matcher.py`: Test user req vs design output comparison
- Antagonistic tests: Context pollution detection, biased reviews

**Implementation (GREEN)**:
- `amplifier/bplan/design_review.py`:
  - `DesignReviewer` class (context-free LLM or code-based)
  - `RequirementMatcher`: Compares user req vs design output
  - `IndependentValidator`: Ensures no context pollution

**Validation Options**:
1. Code-based: Template matching, checklist validation
2. LLM-based: Fresh context, no prior conversation history

**Acceptance Criteria**:
- ✅ Reviewer has zero context from original TODO creation
- ✅ Validation compares user req vs design output accurately
- ✅ Context pollution detection works
- ✅ Both code-based and LLM-based validators implemented
- ✅ Integration tests pass

**Dependencies**: Phase 1 (evidence system)

---

### Phase 4: TodoWrite Integration (bd-9)

**Purpose**: Integrate evidence requirements into TodoWrite completion flow

**Tests FIRST (RED)**:
- `test_todowrite_evidence.py`: Test evidence requirement on completion
- `test_evidence_blocking.py`: Test strict blocking without evidence
- Antagonistic tests: Completing without evidence, weak evidence, fake evidence

**Implementation (GREEN)**:
- `amplifier/bplan/todowrite_integration.py`:
  - `EvidenceRequiredTodo` class: Extends todo with evidence field
  - `CompletionValidator`: Checks evidence before marking complete
  - `BlockingEnforcer`: Prevents completion without evidence

**Integration Points**:
- Hook into TodoWrite completion flow
- Add evidence field to todo data structure
- Validate evidence before allowing completion

**Acceptance Criteria**:
- ✅ Cannot mark todo complete without evidence
- ✅ Evidence validated before completion
- ✅ TodoWrite tool works seamlessly with evidence system
- ✅ All blocking attempts work correctly
- ✅ Integration tests pass with real TodoWrite

**Dependencies**: Phases 1,2,3 (all validation types)

---

### Phase 5: Beads Integration (bd-10)

**Purpose**: Enable evidence tracking in beads issue tracker

**Tests FIRST (RED)**:
- `test_beads_evidence.py`: Test evidence tracking in beads issues
- `test_beads_blocking.py`: Test blocking issue closure without evidence
- Antagonistic tests: Closing without evidence, tampering with evidence

**Implementation (GREEN)**:
- Extensions to `amplifier/bplan/beads_integration.py`:
  - `add_evidence()` method to BeadsClient
  - `validate_evidence()` before `close_issue()`
  - Evidence field in `BeadsIssue` dataclass

**Integration Points**:
- Store evidence in beads issue metadata
- Block issue closure without evidence
- Link to evidence files in `.beads/evidence/`

**Acceptance Criteria**:
- ✅ Evidence tracked in beads issues
- ✅ Cannot close issue without evidence
- ✅ Evidence retrievable from beads
- ✅ Integration with existing beads workflow seamless
- ✅ Integration tests pass with real beads

**Dependencies**: Phases 1,2,3 (all validation types)

---

### Phase 6: Agent Visibility and Invocation (bd-11)

**Purpose**: Make system accessible to all agents via CLI and API

**Tests FIRST (RED)**:
- `test_agent_interface.py`: Test CLI and API access
- `test_agent_discovery.py`: Test agents can find and invoke system
- Antagonistic tests: Unauthorized access, malformed requests

**Implementation (GREEN)**:
- `amplifier/bplan/agent_interface.py`:
  - CLI commands: `validate-code`, `validate-design`, `check-evidence`
  - Agent API: Simple function calls from any agent
  - Documentation for agent integration

**Visibility Mechanisms**:
- CLI commands in Makefile
- Python API importable from any agent
- Clear examples in agent documentation

**Acceptance Criteria**:
- ✅ CLI commands work from terminal
- ✅ Agents can import and call validation functions
- ✅ All existing agents updated with examples
- ✅ Documentation includes invocation patterns
- ✅ Integration tests pass with multiple agents

**Dependencies**: Phases 1-5 (complete system)

---

### Phase 7: Documentation, Examples, and Meta-Validation (bd-12)

**Purpose**: Complete documentation and validate system using its own evidence requirements

**Tests FIRST (RED)**:
- `test_meta_validation.py`: System validates itself using own evidence
- `test_documentation_completeness.py`: Verify all docs exist
- `test_examples_work.py`: Run all examples and verify they work
- Antagonistic tests: Incomplete docs, broken examples, circular validation

**Implementation (GREEN)**:
- `docs/evidence_system/README.md`: Complete system documentation
- `docs/evidence_system/code_workflow_example.md`: 3-agent workflow walkthrough
- `docs/evidence_system/design_workflow_example.md`: Design review walkthrough
- `docs/evidence_system/agent_integration.md`: How agents use the system
- Meta-validation implementation: System validates own success criteria

**Meta-Validation Requirements**:

Use the evidence system to prove all 7 success criteria met:
1. Code workflow → Evidence from test runs
2. Design workflow → Evidence from reviews
3. TodoWrite integration → Evidence from integration tests
4. Beads integration → Evidence from beads operations
5. Documentation → Evidence that docs exist and are complete
6. Agent visibility → Evidence agents can invoke system
7. Meta-validation → This evidence itself

**Acceptance Criteria**:
- ✅ Complete documentation for both workflows
- ✅ Working examples for code and design validation
- ✅ All agents have integration examples
- ✅ Meta-validation proves all criteria met using own evidence
- ✅ System can validate its own completion

**Dependencies**: Phases 1-6 (everything)

---

## Technical Architecture

### File Structure

```
/workspaces/amplifier/
├── amplifier/bplan/
│   ├── evidence_system.py          # Phase 1: Core evidence storage
│   ├── three_agent_workflow.py     # Phase 2: 3-agent code workflow
│   ├── design_review.py            # Phase 3: Design validation
│   ├── todowrite_integration.py    # Phase 4: TodoWrite hooks
│   ├── beads_integration.py        # Phase 5: Beads extensions (already exists)
│   └── agent_interface.py          # Phase 6: CLI and API
├── tests/bplan/
│   ├── test_evidence_system.py
│   ├── test_three_agent_workflow.py
│   ├── test_design_review.py
│   ├── test_todowrite_integration.py
│   ├── test_beads_evidence.py
│   ├── test_agent_interface.py
│   ├── test_meta_validation.py
│   └── test_complete_integration.py
├── docs/evidence_system/
│   ├── README.md
│   ├── code_workflow_example.md
│   ├── design_workflow_example.md
│   └── agent_integration.md
└── .beads/evidence/
    ├── golden/                      # Golden files (restricted access)
    └── validations/                 # Validation evidence

```

### Data Models

```python
@dataclass
class Evidence:
    """Evidence of task completion"""
    type: str  # "code_validation", "design_review", "test_output"
    content: str  # Evidence content or path to evidence file
    timestamp: datetime
    validator_id: str  # Agent or process that created evidence
    golden_file_path: Optional[str] = None

@dataclass
class ValidationResult:
    """Result of validation process"""
    passed: bool
    evidence: Evidence
    details: str
    cheating_detected: bool = False
```

### Key Interfaces

```python
class ValidationInterface(Protocol):
    """Contract for all validators"""
    def validate_code(self, code: str, spec: str) -> ValidationResult: ...
    def validate_design(self, design: str, requirements: str) -> ValidationResult: ...

class FilesystemRestrictor:
    """Enforces filesystem access restrictions"""
    def create_restricted_env(self, exclude_paths: list[str]) -> dict: ...
    def validate_no_access(self, log_file: str, restricted_paths: list[str]) -> bool: ...
```

## Philosophy Alignment

### Ruthless Simplicity
- File-based evidence storage (no complex database)
- Direct subprocess calls (no elaborate frameworks)
- Minimal abstractions throughout
- Simple dataclasses over complex OOP hierarchies

### Trust in Emergence
- Simple components doing one thing well
- Complex validation emerges from simple isolation
- Good architecture emerges from good practices
- No elaborate state machines

### Evidence Over Trust
- Golden files must be reproduced by executing code
- No exceptions, no shortcuts, no "trust me it works"
- System validates itself (meta-validation)
- Antagonistic tests catch all cheating attempts

### "Bricks & Studs" Modular Design
- Each phase is self-contained ("brick")
- Clear interfaces between phases ("studs")
- Phases can be regenerated independently
- Simple contracts, isolated implementation

## Development Approach

### Test-First Discipline (RED-GREEN-REFACTOR)

Every phase follows strict TDD:
1. **RED**: Write antagonistic tests first, verify they fail
2. **GREEN**: Implement minimal code to pass tests
3. **REFACTOR**: Simplify while keeping tests green
4. **EVIDENCE**: Save evidence at each stage

### Antagonistic Testing Philosophy

Tests designed to catch shortcuts:
- Try to access golden files from restricted context
- Attempt to complete without evidence
- Submit weak or fake evidence
- Detect context pollution in validators
- Verify filesystem restrictions work

### Integration > Mocks

- Real subprocess execution (not mocked)
- Real file I/O (not mocked)
- Real filesystem restrictions (not mocked)
- Real agent execution (not mocked)
- Mocks only where necessary for speed/isolation

## Constraints and Considerations

### Transient Codespaces
- Commit frequently to preserve progress
- Store evidence in git-tracked `.beads/evidence/`
- Document state in beads issues
- Enable resumption after interruption

### Performance
- Thoroughness > speed
- Validation may take time (that's OK)
- Real subprocess execution (not optimized)
- Focus on correctness first

### No Budget Constraints
- Use multiple LLM calls if needed
- Don't optimize prematurely
- Build correctly first, optimize later

## Risk Mitigation

### Risk: Context Pollution in Validators
**Mitigation**: Subprocess isolation, fresh LLM contexts, access logging

### Risk: Filesystem Restrictions Bypassed
**Mitigation**: Antagonistic tests that try to cheat, access validation logs

### Risk: Weak Golden Files (Agent 1 Errors)
**Mitigation**: Agent 1 review process, golden file validation tests

### Risk: Circular Meta-Validation
**Mitigation**: Bootstrap validation with external evidence, document bootstrapping process

## Success Metrics

1. **Code Validation Rate**: 100% of code TODOs require evidence
2. **Cheat Detection Rate**: 100% of cheating attempts caught
3. **Design Review Rate**: 100% of design TODOs require independent review
4. **Integration Success**: All agents can invoke system
5. **Meta-Validation**: System proves its own completion

## Timeline and Milestones

- **Phase 1**: Foundation (Core Evidence System)
- **Phase 2**: Critical (3-Agent Workflow with Anti-Cheat)
- **Phase 3**: Essential (Design Review)
- **Phases 4-5**: Integration (TodoWrite & Beads)
- **Phase 6**: Accessibility (Agent Visibility)
- **Phase 7**: Validation (Documentation & Meta-Validation)

Each phase must be 100% complete before moving to next phase.

## References

- Epic: bd-3 (Evidence-Required Todo System Enhancement)
- Phase Tasks: bd-6 through bd-12
- Philosophy: `@ai_context/IMPLEMENTATION_PHILOSOPHY.md`
- Design: `@ai_context/MODULAR_DESIGN_PHILOSOPHY.md`
- Inspiration: claude_template "Five Truths" (Trust But Verify)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-14
**Status**: Planning Complete, Ready for Execution
