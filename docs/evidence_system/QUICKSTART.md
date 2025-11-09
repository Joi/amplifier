# Evidence System - Quick Start Guide

Get started with the Evidence-Based Validation System in 5 minutes.

## Installation

The evidence system is part of the Amplifier project. No separate installation needed.

```bash
# Ensure dependencies are installed
make install
```

## Basic Usage

### 1. Using the Python API

```python
from amplifier.bplan.agent_interface import AgentAPI

# Initialize API
api = AgentAPI()

# Validate a todo with evidence
result = api.validate_todo_completion(
    content="Implement authentication feature",
    evidence_ids=["evidence_abc123"],
    requires_evidence=True
)

if result["can_complete"]:
    print("✅ Task can be completed")
else:
    print(f"❌ Blocked: {result['reason']}")
```

### 2. Using the CLI

```bash
# Check if evidence exists
uv run python -m amplifier.bplan.agent_interface check-evidence evidence_abc123

# Validate a todo
uv run python -m amplifier.bplan.agent_interface validate-todo \
    "Complete feature X" \
    --evidence-ids evidence_001 \
    --evidence-ids evidence_002

# List all evidence
uv run python -m amplifier.bplan.agent_interface list-evidence
```

### 3. Create Evidence

```python
from amplifier.bplan.evidence_system import EvidenceStore
from pathlib import Path

# Initialize store
store = EvidenceStore(base_dir=Path(".beads/evidence"))

# Add evidence from test run
evidence = store.add_evidence(
    type="test_output",
    content={
        "text": "All 10 tests passed successfully",
        "tests_passed": 10,
        "tests_failed": 0,
        "timestamp": "2025-10-16T12:00:00"
    },
    validator_id="pytest"
)

print(f"Evidence created: {evidence.id}")
```

## Common Workflows

### Workflow 1: Task Completion with Evidence

```python
from amplifier.bplan.agent_interface import AgentAPI
from amplifier.bplan.evidence_system import EvidenceStore
from pathlib import Path

# Setup
api = AgentAPI()
store = EvidenceStore(base_dir=Path(".beads/evidence"))

# Step 1: Do your work (run tests, build, etc.)
# ... your implementation code ...

# Step 2: Create evidence of completion
evidence = store.add_evidence(
    type="test_output",
    content={"text": "Feature X: All validations passed"},
    validator_id="my_validator"
)

# Step 3: Validate you can complete the task
result = api.validate_todo_completion(
    content="Implement Feature X",
    evidence_ids=[evidence.id],
    requires_evidence=True
)

# Step 4: Check result
if result["can_complete"]:
    print("✅ Task complete with evidence")
    # Mark task as done in your system
else:
    print(f"❌ Cannot complete: {result['reason']}")
```

### Workflow 2: Three-Agent Code Validation

```python
from amplifier.bplan.agent_interface import AgentAPI

api = AgentAPI()

# Run 3-agent workflow
result = api.validate_code(
    task="Create a function that calculates factorial"
)

if result["passed"]:
    print(f"✅ Code validated! Evidence: {result['evidence_id']}")
else:
    print(f"❌ Validation failed: {result['message']}")
```

### Workflow 3: Check Evidence Quality

```python
from amplifier.bplan.agent_interface import AgentAPI

api = AgentAPI()

# Check if evidence exists and is valid
result = api.check_evidence("evidence_abc123")

if result["exists"]:
    print(f"✅ Evidence found")
    print(f"   Type: {result['type']}")
    print(f"   Created: {result['timestamp']}")
else:
    print("❌ Evidence not found")
```

## Evidence Quality Requirements

For evidence to be accepted, it must:

### ✅ GOOD Evidence

```python
# Detailed, specific, with context
evidence = store.add_evidence(
    type="test_output",
    content={
        "text": "Authentication module: 15 tests passed, 0 failed. "
               "Tested login, logout, session management, and token refresh.",
        "tests_passed": 15,
        "coverage": 0.95,
        "timestamp": datetime.now().isoformat()
    },
    validator_id="pytest"
)
```

### ❌ BAD Evidence (Will Be Rejected)

```python
# Too generic, no details
bad_evidence = store.add_evidence(
    type="test_output",
    content={"text": "done"},  # ❌ Too vague
    validator_id="me"
)

# Placeholder content
bad_evidence = store.add_evidence(
    type="test_output",
    content={"text": "TODO: Run tests later"},  # ❌ Placeholder
    validator_id="me"
)

# No details
bad_evidence = store.add_evidence(
    type="test_output",
    content={"text": "ok"},  # ❌ No specifics
    validator_id="me"
)
```

## Error Handling

```python
from amplifier.bplan.agent_interface import AgentAPI
from amplifier.bplan.todowrite_integration import EvidenceValidationError

api = AgentAPI()

try:
    result = api.validate_todo_completion(
        content="Complete task",
        evidence_ids=["some_evidence_id"],
        requires_evidence=True
    )

    if not result["can_complete"]:
        # Handle specific failure reasons
        reason = result["reason"]

        if "not found" in reason:
            print("Evidence doesn't exist")
        elif "weak" in reason or "placeholder" in reason:
            print("Evidence quality too low")
        elif "stale" in reason:
            print("Evidence is too old (>24 hours)")
        else:
            print(f"Other validation issue: {reason}")

except Exception as e:
    print(f"Unexpected error: {e}")
```

## Configuration

### Evidence Directory

By default, evidence is stored in `.beads/evidence/`. To use a custom location:

```python
from pathlib import Path
from amplifier.bplan.agent_interface import AgentAPI

# Custom evidence directory
api = AgentAPI(evidence_dir=Path("/custom/path/evidence"))
```

### Evidence Expiration

Evidence older than 24 hours is considered stale:

```python
# This is enforced automatically
# To use older evidence, create fresh evidence or adjust the time check
```

## Troubleshooting

### "Evidence not found" error

**Problem**: Evidence ID doesn't exist in store

**Solution**:
```python
# Check if evidence exists first
result = api.check_evidence(evidence_id)
if not result["exists"]:
    # Create the evidence or use a different ID
    pass
```

### "Weak or placeholder evidence detected"

**Problem**: Evidence content is too generic or contains placeholders

**Solution**: Provide detailed, specific evidence
```python
# Bad
content = {"text": "done"}

# Good
content = {
    "text": "Implemented login feature with 12 unit tests. "
           "All authentication flows validated.",
    "tests_passed": 12,
    "timestamp": datetime.now().isoformat()
}
```

### "Evidence mismatch - content doesn't match todo task"

**Problem**: Evidence is about a different feature/task

**Solution**: Ensure evidence content relates to the todo
```python
# Todo about authentication
todo_content = "Implement authentication"

# Evidence should mention authentication
evidence_content = {
    "text": "Authentication feature: All security checks passed"
}
```

## Next Steps

- Read [PROOF_OF_FUNCTION.md](PROOF_OF_FUNCTION.md) to see verification tests
- See [README.md](README.md) for full system documentation
- Check [code_workflow_example.md](code_workflow_example.md) for 3-agent workflow details
- Review [agent_integration.md](agent_integration.md) for agent-specific usage

## Running Tests

```bash
# Run all evidence system tests
uv run pytest tests/bplan/ -v

# Run proof tests
uv run pytest tests/test_evidence_proof_real.py -v

# Run specific test
uv run pytest tests/bplan/test_evidence_store.py -v
```

## Getting Help

If you encounter issues:

1. Check [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for common problems
2. Run the proof tests to verify system integrity
3. Check logs for detailed error messages
4. Review evidence quality requirements above

---

**Remember**: The evidence system enforces quality. If evidence is rejected, it's because the quality standards weren't met. This is by design to prevent shortcuts.
