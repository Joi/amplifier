# Evidence System Architecture

## Overview

The Evidence-Based Validation System enforces "trust but verify" principles by requiring hard evidence (test output, validation results, reviews) before allowing task completion.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User / Agent                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
         ┌──────▼──────┐          ┌──────▼──────┐
         │   AgentAPI   │          │     CLI     │
         │  (Python)    │          │  (Click)    │
         └──────┬───────┘          └──────┬──────┘
                │                         │
                └────────────┬────────────┘
                             │
         ┌───────────────────▼───────────────────┐
         │      Core Validation Layer            │
         │  ┌─────────────────────────────────┐  │
         │  │   CompletionValidator           │  │
         │  │   - Evidence quality checks      │  │
         │  │   - Content matching            │  │
         │  │   - Staleness detection         │  │
         │  └────────────┬────────────────────┘  │
         │               │                        │
         │  ┌────────────▼────────────────────┐  │
         │  │   BlockingEnforcer              │  │
         │  │   - Completion blocking          │  │
         │  │   - Timing validation           │  │
         │  └─────────────────────────────────┘  │
         └───────────────────┬───────────────────┘
                             │
         ┌───────────────────▼───────────────────┐
         │       Evidence Storage Layer          │
         │  ┌─────────────────────────────────┐  │
         │  │   EvidenceStore                 │  │
         │  │   - File-based storage          │  │
         │  │   - UUID-based IDs              │  │
         │  │   - JSON persistence            │  │
         │  └────────────┬────────────────────┘  │
         └───────────────┼───────────────────────┘
                         │
         ┌───────────────▼───────────────────────┐
         │    Filesystem (.beads/evidence/)      │
         │    - evidence/*.json files            │
         │    - golden/*.golden files            │
         └───────────────────────────────────────┘
```

## Component Breakdown

### 1. Agent Interface Layer

#### AgentAPI (amplifier/bplan/agent_interface.py)

**Purpose**: Python API for agents to interact with evidence system

**Key Methods**:
- `validate_todo_completion(content, evidence_ids, requires_evidence)` → dict
- `check_evidence(evidence_id)` → dict
- `validate_code(task)` → dict

**Responsibilities**:
- Input validation
- Error handling
- Result formatting
- Evidence status aggregation

#### CLI (Click-based)

**Purpose**: Command-line interface for shell/terminal operations

**Commands**:
- `validate-code <task>` - Run 3-agent workflow
- `check-evidence <id>` - Check evidence existence
- `validate-todo <content>` - Validate completion
- `list-evidence` - List all evidence

### 2. Core Validation Layer

#### CompletionValidator (amplifier/bplan/todowrite_integration.py)

**Purpose**: Validates evidence quality and relevance

**Validation Checks**:
1. **Existence**: Evidence IDs must exist in store
2. **Quality**: Rejects weak/placeholder content
3. **Freshness**: Evidence must be <24 hours old
4. **Relevance**: Content must match todo description
5. **Pattern Detection**: Blocks suspicious patterns
6. **Injection Prevention**: Detects injection attempts

**Quality Patterns Detected**:
```python
PLACEHOLDER_PATTERNS = [r"\bTODO\b", r"\bFIXME\b", r"\bTBD\b", ...]
GENERIC_MESSAGES = ["done", "ok", "complete", ...]
SUSPICIOUS_PATTERNS = [r"^(.)\1{5,}$", r"lorem ipsum", ...]
INJECTION_PATTERNS = [r"DROP TABLE", r"<script", ...]
```

#### BlockingEnforcer (amplifier/bplan/todowrite_integration.py)

**Purpose**: Enforces evidence requirements and blocks invalid completions

**Enforcement Actions**:
- Block completion without evidence
- Validate evidence before allowing status change
- Detect tampering attempts
- Check timing validity (prevents suspiciously fast completion)

### 3. Evidence Storage Layer

#### EvidenceStore (amplifier/bplan/evidence_system.py)

**Purpose**: Persistent storage and retrieval of evidence

**Storage Format**:
```json
{
  "id": "857dd53f-8f0e-4e60-b51f-7380f1aeb211",
  "type": "test_output",
  "content": {
    "text": "Detailed evidence text...",
    "metadata": {"tests_passed": 10}
  },
  "timestamp": "2025-10-16T12:00:00.000000",
  "validator_id": "pytest",
  "checksum": "sha256:..."
}
```

**Key Operations**:
- `add_evidence(type, content, validator_id)` → Evidence
- `get_evidence(evidence_id)` → Evidence | None
- `list_evidence(type=None)` → list[Evidence]
- `verify_integrity(evidence_id)` → bool

**Storage Location**: `.beads/evidence/*.json`

### 4. Workflow Orchestration

#### WorkflowOrchestrator (amplifier/bplan/three_agent_workflow.py)

**Purpose**: Coordinates 3-agent validation workflow

**Workflow Steps**:
1. **SpecWriterAgent**: Creates test + golden files
2. **CoderAgent**: Implements (filesystem restricted)
3. **BlindTesterAgent**: Validates against golden

**Anti-Cheat Mechanisms**:
- Subprocess isolation
- Environment variable filtering
- Golden file path hiding
- Access attempt logging

**Evidence Generated**:
- Artifact evidence (test files, golden files)
- Validation evidence (test results, comparisons)
- Workflow execution evidence

#### FilesystemRestrictor (amplifier/bplan/three_agent_workflow.py)

**Purpose**: Prevents CoderAgent from accessing golden files

**Restrictions**:
- Blocks golden directory access
- Removes GOLDEN env vars
- Logs access attempts
- Creates restricted subprocess environment

### 5. Meta-Validation

#### MetaValidator (amplifier/bplan/meta_validation.py)

**Purpose**: System validates its own completion

**Success Criteria** (7 total):
1. Code validation workflow exists
2. Design review workflow exists
3. TodoWrite integration works
4. Beads integration works
5. Documentation complete
6. Agent interface accessible
7. Meta-validation functional (self-referential)

**Validation Method**:
```python
validator = MetaValidator()
report = validator.generate_completion_report()

# Check completion
assert report["summary"]["completion_percentage"] == 100.0
assert report["summary"]["all_criteria_met"] is True
```

## Data Flow

### Evidence Creation Flow

```
1. Work Completed
   ↓
2. Evidence Created
   ├─ Type (test_output, validation, design_review, etc.)
   ├─ Content (detailed description + metadata)
   ├─ Validator ID (who/what created it)
   └─ Timestamp (when created)
   ↓
3. Stored to Filesystem
   └─ .beads/evidence/{uuid}.json
   ↓
4. Evidence ID Returned
   └─ Used for validation later
```

### Todo Completion Validation Flow

```
1. Attempt Completion
   ├─ Todo content
   ├─ Evidence IDs list
   └─ Requires evidence flag
   ↓
2. Check Evidence Exists
   ├─ Query EvidenceStore
   └─ Mark invalid IDs
   ↓
3. Validate Evidence Quality
   ├─ Check for placeholders
   ├─ Check for generic content
   ├─ Check freshness (<24h)
   ├─ Check relevance to todo
   └─ Detect suspicious patterns
   ↓
4. Return Result
   ├─ can_complete: bool
   ├─ reason: str
   └─ evidence_status: dict
```

### Three-Agent Workflow

```
1. SpecWriterAgent
   ├─ Generate test specification
   ├─ Create golden reference
   └─ Store in golden/ directory (RESTRICTED)
   ↓
2. CoderAgent (ISOLATED SUBPROCESS)
   ├─ Read test specification
   ├─ Generate implementation
   ├─ CANNOT access golden/ (enforced)
   └─ Run with filesystem restrictions
   ↓
3. BlindTesterAgent (FRESH SUBPROCESS)
   ├─ Run tests against implementation
   ├─ Load golden files (HAS ACCESS)
   ├─ Compare results byte-for-byte
   └─ Generate validation evidence
   ↓
4. Evidence Stored
   └─ Workflow result + validation proof
```

## Security Model

### Trust Boundaries

```
TRUSTED:
- SpecWriterAgent (creates golden files)
- BlindTesterAgent (validates results)
- EvidenceStore (storage layer)
- MetaValidator (self-validation)

UNTRUSTED:
- CoderAgent (filesystem restricted)
- User-provided evidence
- Todo content/descriptions

RESTRICTED:
- Golden directory (coder cannot access)
- Evidence files (write-only for most operations)
```

### Anti-Cheat Mechanisms

1. **Filesystem Isolation**
   - Subprocess with restricted paths
   - Environment variable filtering
   - Golden directory hidden

2. **Evidence Quality Checks**
   - Pattern detection for weak evidence
   - Content validation
   - Timestamp verification
   - Reuse detection

3. **Blind Validation**
   - Tester has no context from coder
   - Fresh subprocess for each validation
   - Byte-for-byte golden comparison

## Extension Points

### Adding New Evidence Types

```python
# Define new type
NEW_TYPE = "code_review"

# Create evidence
evidence = store.add_evidence(
    type=NEW_TYPE,
    content={"reviewer": "human", "approved": True},
    validator_id="code_review_bot"
)

# Validation automatically works
result = api.validate_todo_completion(
    content="Get code reviewed",
    evidence_ids=[evidence.id],
    requires_evidence=True
)
```

### Custom Validators

```python
from amplifier.bplan.todowrite_integration import CompletionValidator

class CustomValidator(CompletionValidator):
    def _validate_evidence(self, evidence_id, todo):
        # Add custom validation logic
        evidence = self.evidence_store.retrieve_evidence(evidence_id)

        # Custom checks
        if evidence.type == "custom_type":
            # Custom validation
            pass

        # Call parent for standard checks
        super()._validate_evidence(evidence_id, todo)
```

### Integrating with Other Tools

```python
# Beads Integration Example
from amplifier.bplan.beads_integration import BeadsClient

beads = BeadsClient()
issue_id = beads.create_task("Complete feature X")

# Attach evidence to issue
beads.attach_evidence(issue_id, evidence_id)

# Close issue (requires evidence)
beads.close_issue(issue_id)  # Validates evidence first
```

## Performance Considerations

### Evidence Storage

- **Storage**: File-based (JSON)
- **Lookup**: O(1) by ID (direct file access)
- **List**: O(n) (scans directory)
- **Scalability**: Good for <10k evidence items

**Optimization Ideas**:
- Index by type/validator for faster filtering
- Use SQLite for large-scale deployments
- Implement evidence cleanup/archival

### Validation Performance

- **Quality Checks**: O(content_length) per evidence
- **Pattern Matching**: O(patterns × content_length)
- **Typical Time**: <1ms per evidence validation

**Bottlenecks**:
- Three-agent workflow (subprocess overhead)
- Large evidence content (pattern matching)

## Testing Strategy

### Test Pyramid

```
        ┌────────────┐
        │    E2E     │  9 tests (proof tests)
        │  (Manual)  │
        ├────────────┤
        │Integration │  50 tests (workflow tests)
        ├────────────┤
        │    Unit    │  142 tests (component tests)
        └────────────┘
```

### Test Categories

1. **Unit Tests** (tests/bplan/)
   - EvidenceStore operations
   - Validator logic
   - Pattern detection
   - Error handling

2. **Integration Tests** (tests/bplan/test_integration.py)
   - Multi-component workflows
   - State persistence
   - Beads integration
   - Workflow orchestration

3. **Antagonistic Tests** (tests/bplan/test_cheat_detection.py)
   - Cheat attempt detection
   - Weak evidence rejection
   - Filesystem restriction bypass attempts
   - Injection attempts

4. **Proof Tests** (tests/test_evidence_proof_real.py)
   - End-to-end system validation
   - Real API usage (no mocks)
   - Adversarial testing
   - Meta-validation

## Design Principles

Following the "Bricks & Studs" philosophy:

1. **Simple Components** - Each module does one thing well
2. **Clear Interfaces** - Public API is minimal and obvious
3. **Direct Implementation** - No unnecessary abstractions
4. **Evidence Over Trust** - Proof required, no exceptions
5. **Fail Fast** - Errors are loud and immediate
6. **Regeneratable** - Modules can be rebuilt from specs

## Future Enhancements

Potential improvements (not currently prioritized):

1. **Database Backend** - SQLite for better scalability
2. **Evidence Compression** - Reduce storage for large evidence
3. **Distributed Evidence** - Support for remote evidence stores
4. **Webhook Integration** - Notify on evidence creation
5. **Evidence Expiration** - Auto-cleanup old evidence
6. **Evidence Chains** - Link related evidence together

---

**Philosophy**: This architecture prioritizes simplicity and directness over perfect isolation. It's designed for AI agent validation, not nuclear launch codes.
