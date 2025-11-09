# Evidence-Based Validation System

A comprehensive system for enforcing evidence-based task completion through automated validation workflows and independent review processes.

## Overview

This system prevents "lazy coder" shortcuts by requiring hard evidence (test output, golden files, independent reviews) for task completion. It implements a trust-but-verify philosophy where claims must be backed by reproducible evidence.

## Core Principles

1. **Evidence Over Trust** - No task marked complete without proof
2. **Blind Validation** - Validators have no context from implementation
3. **Antagonistic Testing** - Tests designed to catch cheating attempts
4. **Independent Review** - Context-free evaluation of designs
5. **Meta-Validation** - System validates its own completion

## System Components

### 1. Evidence System (Phase 1)
Core data models and storage for evidence tracking.

**Key Classes:**
- `EvidenceStore` - File-based evidence storage in `.beads/evidence/`
- `Evidence` - Dataclass for evidence records
- `GoldenFileHandler` - Manages golden file generation and comparison

**Files:**
- `amplifier/bplan/evidence_system.py`
- `amplifier/bplan/golden_file_handler.py`

### 2. Three-Agent Code Workflow (Phase 2)
Blind validation workflow with filesystem restrictions to prevent cheating.

**Workflow:**
1. **Spec Writer** - Creates test code + golden files (trusted)
2. **Coder** - Implements code without seeing golden files (restricted)
3. **Blind Tester** - Validates output matches golden files (independent)

**Anti-Cheat Mechanisms:**
- Filesystem access control (Coder cannot read golden directory)
- Process isolation (separate subprocesses)
- Path restrictions (golden paths hidden)
- Access logging and validation

**Files:**
- `amplifier/bplan/three_agent_workflow.py`

### 3. Design Review Workflow (Phase 3)
Context-free validation for design documents.

**Features:**
- Zero context from original TODO creation
- Compares requirements vs design output
- Both code-based and LLM-based validators
- Context pollution detection

**Files:**
- `amplifier/bplan/design_review.py`

### 4. TodoWrite Integration (Phase 4)
Integration with Claude Code's TodoWrite tool.

**Features:**
- Evidence field in todo data structure
- Completion validation before marking complete
- Strict blocking without valid evidence
- Weak evidence detection

**Files:**
- `amplifier/bplan/todowrite_integration.py`

### 5. Beads Integration (Phase 5)
Integration with the beads issue tracking system.

**Features:**
- Evidence tracking in issue metadata
- Block issue closure without evidence
- Evidence retrieval from beads
- Seamless workflow integration

**Files:**
- `amplifier/bplan/beads_integration.py`

### 6. Agent Interface (Phase 6)
Universal access for all agents via CLI and Python API.

**Features:**
- Python AgentAPI for programmatic access
- CLI commands for shell operations
- Evidence checking and validation
- Todo completion validation

**Files:**
- `amplifier/bplan/agent_interface.py`
- `docs/evidence_system/agent_integration.md`

## Quick Start

### Python API

```python
from amplifier.bplan.agent_interface import AgentAPI

# Initialize
api = AgentAPI()

# Validate code with 3-agent workflow
result = api.validate_code("Implement calculate_sum function")
if result["passed"]:
    print(f"✅ Validation passed! Evidence: {result['evidence_id']}")

# Check if evidence exists
result = api.check_evidence("evidence_12345")
if result["exists"]:
    print(f"✅ Evidence found: {result['type']}")

# Validate todo completion
result = api.validate_todo_completion(
    content="Implement feature X",
    evidence_ids=["evidence_001"],
    requires_evidence=True
)
if result["can_complete"]:
    print("✅ Todo can be completed")
```

### CLI Commands

```bash
# Validate code
uv run python -m amplifier.bplan.agent_interface validate-code "Implement feature X"

# Check evidence
uv run python -m amplifier.bplan.agent_interface check-evidence evidence_12345

# Validate todo
uv run python -m amplifier.bplan.agent_interface validate-todo \
    "Complete feature" \
    --evidence-ids evidence_001

# List all evidence
uv run python -m amplifier.bplan.agent_interface list-evidence
```

## Workflows

### Code Validation Workflow

See [code_workflow_example.md](code_workflow_example.md) for detailed walkthrough.

**Summary:**
1. Spec Writer creates test + golden files
2. Coder implements without seeing golden files
3. Blind Tester validates output matches golden
4. Evidence stored for task completion

### Design Review Workflow

See [design_workflow_example.md](design_workflow_example.md) for detailed walkthrough.

**Summary:**
1. Requirements + design submitted for review
2. Independent reviewer validates (zero context)
3. Review result stored as evidence
4. Evidence required for task completion

## Architecture

### Data Flow

```
User Request
    ↓
Agent/Tool
    ↓
AgentAPI / CLI
    ↓
Workflow Orchestrator
    ↓
Evidence Store
    ↓
Task Completion
```

### Evidence Storage

```
.beads/evidence/
├── golden/              # Golden files (restricted access)
│   └── *.golden
├── validations/         # Validation evidence
│   └── *.json
└── evidence_store.json  # Evidence metadata
```

### Validation Flow

```
Task → Spec Writer → Test + Golden Files
                        ↓
Task → Coder (restricted) → Implementation
                        ↓
Task → Blind Tester → Validation Result → Evidence
```

## Testing

The system includes comprehensive test coverage:

```bash
# Run all evidence system tests
uv run pytest tests/bplan/ -v

# Run integration tests
uv run pytest tests/test_*evidence*.py -v

# Run agent interface tests
uv run pytest tests/test_agent_interface.py -v
```

### Test Categories

1. **Unit Tests** - Individual component testing
2. **Integration Tests** - Multi-component workflows
3. **Antagonistic Tests** - Cheat detection and blocking
4. **Edge Case Tests** - Error handling and boundary conditions

## Key Features

### Filesystem Restrictions

The Coder agent runs in a subprocess with restricted filesystem access:

```python
# Golden files hidden from Coder
coder_env = create_restricted_env(exclude_paths=[golden_dir])

# Coder implements without seeing golden files
result = coder.implement_in_subprocess(env=coder_env)

# Verify no golden file access occurred
assert not accessed_golden_files(coder_env)
```

### Evidence Validation

Evidence must meet quality standards:

```python
# Strong evidence: actual test results
evidence = store.add_evidence(
    type="test_output",
    content={"text": "Tests passed: 100/100", "metadata": {...}},
    validator_id="pytest"
)

# Weak evidence rejected
if is_placeholder(evidence.content):
    raise ValueError("Placeholder evidence not accepted")
```

### Context-Free Review

Design reviews happen without context pollution:

```python
# Fresh LLM context for review
reviewer = DesignReviewer()
result = reviewer.review(
    requirements=user_requirements,
    design=design_output,
    # No context from original TODO creation
)
```

## Best Practices

1. **Always require evidence** - Never mark tasks complete without proof
2. **Use appropriate evidence types** - Match evidence to task type
3. **Store evidence immediately** - Don't wait until completion
4. **Include metadata** - Add context to evidence content
5. **Handle errors gracefully** - Check validation results
6. **Test with antagonistic cases** - Try to break the system

## Troubleshooting

### Evidence Not Found

```python
result = api.check_evidence("evidence_id")
if not result["exists"]:
    # Check evidence directory path
    print(f"Evidence dir: {api.evidence_dir}")
    # List all evidence
    all_evidence = api.evidence_store.list_evidence()
```

### Validation Timeout

- Ensure code/test paths are accessible
- Check for infinite loops in implementation
- Verify filesystem restrictions are configured

### Weak Evidence Rejected

- Avoid placeholder text like "TODO" or "TBD"
- Include actual results, not promises
- Add meaningful metadata

## Documentation

- [Agent Integration Guide](agent_integration.md) - How agents use the system
- [Code Workflow Example](code_workflow_example.md) - 3-agent workflow walkthrough
- [Design Workflow Example](design_workflow_example.md) - Design review walkthrough

## Philosophy

This system embodies:

- **Ruthless Simplicity** - Minimal abstractions, direct implementations
- **Trust in Emergence** - Complex validation emerges from simple components
- **Evidence Over Trust** - Proof required, no exceptions
- **Bricks & Studs** - Modular design with clear interfaces

## Meta-Validation

The system validates its own completion using the same evidence requirements it enforces on others. See Phase 7 implementation for details on how the system proves all 7 success criteria are met.

## Contributing

When extending the system:

1. Follow test-first development (RED-GREEN-REFACTOR)
2. Include antagonistic tests for new features
3. Maintain simplicity - avoid unnecessary abstractions
4. Document integration patterns
5. Validate changes with evidence

## License

Part of the Amplifier project. See project root for license details.
