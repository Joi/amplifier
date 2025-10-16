# Agent Integration Guide - Evidence System

This guide shows how agents and tools can integrate with the evidence-based validation system.

## Overview

The evidence system provides two access methods:
1. **Python API** - For programmatic access within agents
2. **CLI Commands** - For shell-based operations and debugging

Both methods provide the same functionality: validating code, checking evidence, and validating todo completion.

## Python API Integration

### Basic Usage

```python
from amplifier.bplan.agent_interface import AgentAPI

# Initialize the API
api = AgentAPI()  # Uses default .beads/evidence directory

# Or specify custom evidence directory
api = AgentAPI(evidence_dir=Path("/custom/path"))
```

### Validating Code (3-Agent Workflow)

```python
# Validate code implementation with blind testing
result = api.validate_code("Implement calculate_sum function")

if result["passed"]:
    print(f"✅ Validation passed!")
    print(f"Evidence ID: {result['evidence_id']}")
    print(f"Details: {result['message']}")
else:
    print(f"❌ Validation failed: {result['message']}")
    if result["cheating_detected"]:
        print("⚠️  Cheating attempt detected!")
```

### Checking Evidence

```python
# Check if evidence exists and is valid
result = api.check_evidence("evidence_12345")

if result["exists"]:
    print(f"✅ Evidence found")
    print(f"Type: {result['type']}")
    print(f"Created: {result['timestamp']}")
else:
    print(f"❌ Evidence not found: {result['details']}")
```

### Validating Todo Completion

```python
# Validate a todo can be completed with provided evidence
result = api.validate_todo_completion(
    content="Implement user authentication",
    evidence_ids=["evidence_001", "evidence_002"],
    requires_evidence=True
)

if result["can_complete"]:
    print(f"✅ Todo can be completed: {result['reason']}")
else:
    print(f"❌ Cannot complete: {result['reason']}")
```

## CLI Integration

### Available Commands

The evidence system CLI provides four commands:

```bash
# List all commands
uv run python -m amplifier.bplan.agent_interface --help

# Commands:
#   validate-code   - Run 3-agent workflow validation
#   check-evidence  - Check if evidence exists
#   validate-todo   - Validate todo completion
#   list-evidence   - List all evidence
```

### Validate Code

```bash
# Basic validation
uv run python -m amplifier.bplan.agent_interface validate-code "Implement feature X"

# With custom evidence directory
uv run python -m amplifier.bplan.agent_interface validate-code \
    "Implement feature X" \
    --evidence-dir /custom/path

# Exit codes:
#   0 = Validation passed
#   1 = Validation failed
```

### Check Evidence

```bash
# Check specific evidence
uv run python -m amplifier.bplan.agent_interface check-evidence evidence_12345

# With custom directory
uv run python -m amplifier.bplan.agent_interface check-evidence \
    evidence_12345 \
    --evidence-dir /custom/path
```

### Validate Todo

```bash
# Validate with evidence IDs
uv run python -m amplifier.bplan.agent_interface validate-todo \
    "Complete feature implementation" \
    --evidence-ids evidence_001 \
    --evidence-ids evidence_002

# Validate todo that doesn't require evidence
uv run python -m amplifier.bplan.agent_interface validate-todo \
    "Update documentation" \
    --no-evidence-required
```

### List Evidence

```bash
# List all evidence
uv run python -m amplifier.bplan.agent_interface list-evidence

# Output format:
# ID: evidence_001
#   Type: test_output
#   Created: 2025-10-15T12:34:56
#   Validator: pytest
```

## Integration Patterns

### Pattern 1: Pre-Completion Validation

Before marking a todo as complete, validate evidence:

```python
def complete_todo(todo_content: str, evidence_ids: list[str]):
    """Complete todo with evidence validation"""
    api = AgentAPI()

    # Validate before completing
    result = api.validate_todo_completion(
        content=todo_content,
        evidence_ids=evidence_ids,
        requires_evidence=True
    )

    if result["can_complete"]:
        # Mark todo as complete
        mark_complete(todo_content)
        return True
    else:
        # Block completion
        raise ValueError(f"Cannot complete: {result['reason']}")
```

### Pattern 2: Automated Code Validation

Integrate into code generation workflows:

```python
def generate_and_validate_code(task: str):
    """Generate code and validate with blind testing"""
    api = AgentAPI()

    # Generate code (implementation omitted)
    generate_code(task)

    # Validate with 3-agent workflow
    result = api.validate_code(task)

    if not result["passed"]:
        # Handle validation failure
        raise CodeValidationError(result["message"])

    # Store evidence ID for later use
    return result["evidence_id"]
```

### Pattern 3: Evidence Collection

Collect evidence from test runs:

```python
from amplifier.bplan.evidence_system import EvidenceStore

def run_tests_and_collect_evidence(test_suite: str):
    """Run tests and store evidence"""
    store = EvidenceStore()

    # Run tests
    test_output = run_pytest(test_suite)

    # Store as evidence
    evidence = store.add_evidence(
        type="test_output",
        content={
            "text": test_output,
            "metadata": {"suite": test_suite}
        },
        validator_id="pytest"
    )

    return evidence.id
```

## Agent-Specific Examples

### For Code Generation Agents

```python
class CodeGeneratorAgent:
    def __init__(self):
        self.api = AgentAPI()

    def generate_with_validation(self, spec: str):
        """Generate code with automatic validation"""
        # Generate implementation
        code = self.generate_code(spec)

        # Validate with blind testing
        result = self.api.validate_code(spec)

        if result["passed"]:
            return {
                "code": code,
                "evidence_id": result["evidence_id"],
                "status": "validated"
            }
        else:
            return {
                "code": code,
                "evidence_id": None,
                "status": "failed",
                "reason": result["message"]
            }
```

### For Testing Agents

```python
class TestRunnerAgent:
    def __init__(self):
        self.store = EvidenceStore()

    def run_and_record(self, test_suite: str):
        """Run tests and record evidence"""
        # Execute tests
        results = self.execute_tests(test_suite)

        # Store evidence
        evidence = self.store.add_evidence(
            type="test_output",
            content={
                "text": results.summary,
                "metadata": {
                    "passed": results.passed,
                    "failed": results.failed,
                    "total": results.total
                }
            },
            validator_id="test_runner_agent"
        )

        return evidence
```

### For Design Review Agents

```python
class DesignReviewAgent:
    def __init__(self):
        self.api = AgentAPI()
        self.store = EvidenceStore()

    def review_design(self, requirements: str, design: str):
        """Review design and create evidence"""
        # Perform review
        review_result = self.perform_review(requirements, design)

        # Store review as evidence
        evidence = self.store.add_evidence(
            type="design_review",
            content={
                "text": review_result.summary,
                "metadata": {
                    "approved": review_result.approved,
                    "issues": review_result.issues
                }
            },
            validator_id="design_review_agent"
        }

        return evidence
```

## Error Handling

### Common Errors and Solutions

**Import Error: Module not found**
```python
# Problem: Cannot import AgentAPI
# Solution: Ensure you're in the project root and using uv run
uv run python your_script.py
```

**Evidence Not Found**
```python
# Problem: check_evidence returns exists=False
# Solution: Verify evidence_id and evidence_dir path
result = api.check_evidence("evidence_id")
if not result["exists"]:
    print(f"Evidence not found: {result['details']}")
    # Check evidence directory exists
    print(f"Evidence dir: {api.evidence_dir}")
```

**Validation Timeout**
```python
# Problem: validate_code times out
# Solution: The 3-agent workflow can take time; ensure:
# - Code/test paths are accessible
# - No infinite loops in implementation
# - Filesystem restrictions are properly configured
```

## Testing Your Integration

### Unit Test Example

```python
import tempfile
from pathlib import Path
from amplifier.bplan.agent_interface import AgentAPI

def test_agent_integration():
    """Test agent integration with evidence system"""
    # Use temp directory for testing
    temp_dir = tempfile.mkdtemp()
    api = AgentAPI(evidence_dir=Path(temp_dir))

    # Test evidence creation
    evidence = api.evidence_store.add_evidence(
        type="test_output",
        content={"text": "Tests passed"},
        validator_id="test_agent"
    )

    # Test evidence check
    result = api.check_evidence(evidence.id)
    assert result["exists"] is True

    # Test todo validation
    result = api.validate_todo_completion(
        content="Test task",
        evidence_ids=[evidence.id],
        requires_evidence=True
    )
    assert result["can_complete"] is True
```

## Best Practices

1. **Always validate before completion** - Don't mark todos complete without checking evidence
2. **Store evidence immediately** - Record evidence as soon as it's generated
3. **Use descriptive evidence types** - Use clear types like "test_output", "design_review", "code_validation"
4. **Include metadata** - Add relevant context to evidence content
5. **Handle errors gracefully** - Always check validation results and handle failures
6. **Use appropriate validator IDs** - Identify which agent/tool created the evidence

## See Also

- [README.md](README.md) - System overview
- [Code Workflow Example](code_workflow_example.md) - 3-agent workflow walkthrough
- [Design Workflow Example](design_workflow_example.md) - Design review walkthrough
- [Evidence System Source](../../amplifier/bplan/agent_interface.py) - Implementation details
