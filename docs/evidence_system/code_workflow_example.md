# Code Workflow Example - 3-Agent Blind Validation

This document walks through the complete 3-agent code validation workflow with a concrete example.

## Overview

The 3-agent workflow validates code implementations using blind testing to prevent cheating:

1. **Spec Writer** - Creates test + golden files (trusted teacher)
2. **Coder** - Implements code without golden file access (restricted student)
3. **Blind Tester** - Validates output matches golden (independent grader)

## Example Task: Implement `calculate_sum` Function

Let's validate an implementation of a simple sum calculator.

### Step 1: Spec Writer Creates Test + Golden Files

The Spec Writer is trusted to create correct tests and expected outputs.

**Test File Created** (`test_calculator.py`):
```python
def test_calculate_sum():
    """Test the calculate_sum function"""
    from calculator import calculate_sum

    # Test cases
    assert calculate_sum([1, 2, 3]) == 6
    assert calculate_sum([0]) == 0
    assert calculate_sum([-1, 1]) == 0
    assert calculate_sum([]) == 0

    print("All tests passed!")
```

**Golden File Created** (`.beads/evidence/golden/calculator_output.golden`):
```
All tests passed!
```

The golden file is stored in a restricted directory that the Coder cannot access.

### Step 2: Coder Implements Without Golden File Access

The Coder sees ONLY the test file, not the golden output.

**Coder Environment**:
- Can read: `test_calculator.py`
- Cannot read: `.beads/evidence/golden/` directory
- Must implement correct logic from test descriptions

**Implementation Created** (`calculator.py`):
```python
def calculate_sum(numbers):
    """Calculate sum of a list of numbers"""
    return sum(numbers)
```

**Key Constraint**: The Coder subprocess has filesystem restrictions preventing access to golden files.

### Step 3: Blind Tester Validates Output

The Blind Tester runs the implementation in a clean subprocess and compares output.

**Validation Process**:
```python
# Run implementation
result = subprocess.run(
    ["python", "test_calculator.py"],
    capture_output=True,
    text=True
)

# Load golden file
with open(golden_path) as f:
    expected = f.read()

# Byte-for-byte comparison
if result.stdout == expected:
    validation_passed = True
```

**Validation Result**:
```
✅ Validation PASSED
Actual output: "All tests passed!\n"
Expected output: "All tests passed!\n"
Match: True
Cheating detected: False
```

### Step 4: Evidence Stored

The validation result is stored as evidence:

```json
{
  "id": "evidence_calc_001",
  "type": "code_validation",
  "timestamp": "2025-10-15T12:34:56Z",
  "validator_id": "blind_tester",
  "content": {
    "task": "Implement calculate_sum function",
    "passed": true,
    "golden_file": "calculator_output.golden",
    "actual_output": "All tests passed!\n",
    "cheating_detected": false
  }
}
```

## Using the Workflow via API

### Python API

```python
from amplifier.bplan.agent_interface import AgentAPI

api = AgentAPI()

# Run complete 3-agent workflow
result = api.validate_code("Implement calculate_sum function")

if result["passed"]:
    print(f"✅ Validation passed!")
    print(f"Evidence ID: {result['evidence_id']}")
    print(f"Details: {result['message']}")
else:
    print(f"❌ Validation failed: {result['message']}")
    if result["cheating_detected"]:
        print("⚠️  CHEATING DETECTED")
```

### CLI

```bash
uv run python -m amplifier.bplan.agent_interface validate-code \
    "Implement calculate_sum function"

# Output:
# ✅ Code validation PASSED
# Evidence ID: evidence_calc_001
# Details: Implementation validated successfully
```

## Anti-Cheat Protection

### What Prevents Cheating?

1. **Filesystem Restrictions**
   ```python
   # Coder subprocess cannot access golden directory
   coder_env = create_restricted_env(
       exclude_paths=[Path(".beads/evidence/golden")]
   )
   ```

2. **Process Isolation**
   - Each agent runs in separate subprocess
   - No shared memory between agents
   - Fresh environment for each execution

3. **Access Logging**
   ```python
   # Verify no golden file access occurred
   if accessed_restricted_paths(coder_env):
       raise CheatingDetectedError("Unauthorized file access")
   ```

### Example: Catching Cheating Attempt

**Bad Implementation** (tries to read golden file):
```python
def calculate_sum(numbers):
    # Cheating attempt - try to read golden file
    try:
        with open(".beads/evidence/golden/calculator_output.golden") as f:
            # This will fail due to filesystem restrictions
            pass
    except:
        pass
    return sum(numbers)
```

**Result**:
```
❌ Validation FAILED
Reason: Unauthorized file access detected
Cheating: True
File: .beads/evidence/golden/calculator_output.golden
```

## Complex Example: String Formatter

### Task: Implement String Formatter

**Test File**:
```python
def test_format_name():
    from formatter import format_name

    result = format_name("john", "doe")
    print(result)

    result = format_name("alice", "wonderland")
    print(result)
```

**Golden File**:
```
John Doe
Alice Wonderland
```

**Correct Implementation**:
```python
def format_name(first, last):
    return f"{first.capitalize()} {last.capitalize()}"
```

**Validation**:
- Output must match golden file exactly
- Byte-for-byte comparison
- No partial credit for "close enough"

## Workflow States

### Success Path

```
Task Created
    ↓
Spec Writer Creates Test + Golden
    ↓
Coder Implements (Restricted)
    ↓
Blind Tester Validates
    ↓
✅ Evidence Stored
```

### Failure Path - Invalid Implementation

```
Task Created
    ↓
Spec Writer Creates Test + Golden
    ↓
Coder Implements (Restricted)
    ↓
Blind Tester Validates
    ↓
❌ Output Mismatch
    ↓
No Evidence Stored
    ↓
Task Cannot Complete
```

### Failure Path - Cheating Detected

```
Task Created
    ↓
Spec Writer Creates Test + Golden
    ↓
Coder Attempts to Access Golden File
    ↓
❌ Filesystem Restriction Blocks Access
    ↓
Cheating Logged
    ↓
Task Cannot Complete
```

## Integration with TodoWrite

```python
from amplifier.bplan.agent_interface import AgentAPI
from amplifier.bplan.todowrite_integration import EvidenceRequiredTodo

api = AgentAPI()

# Create todo requiring evidence
todo = EvidenceRequiredTodo(
    content="Implement calculate_sum function",
    status="in_progress",
    activeForm="Implementing calculate_sum",
    evidence_ids=[],
    requires_evidence=True
)

# Validate code
result = api.validate_code(todo.content)

if result["passed"]:
    # Add evidence to todo
    todo.evidence_ids.append(result["evidence_id"])

    # Now can complete
    validate_result = api.validate_todo_completion(
        content=todo.content,
        evidence_ids=todo.evidence_ids,
        requires_evidence=True
    )

    if validate_result["can_complete"]:
        print("✅ Todo can be marked complete")
```

## Best Practices

1. **Clear Test Descriptions** - Make expected behavior obvious from test code
2. **Comprehensive Golden Files** - Include all expected outputs
3. **Deterministic Output** - Avoid timestamps or random values
4. **Error Cases** - Test both success and failure paths
5. **Edge Cases** - Include boundary conditions

## Troubleshooting

### Validation Always Fails

**Problem**: Output doesn't match golden file

**Solutions**:
- Check for extra whitespace or newlines
- Verify output encoding (UTF-8)
- Ensure deterministic output (no timestamps)

### Filesystem Restriction Errors

**Problem**: Coder cannot read necessary files

**Solutions**:
- Verify allowed paths are configured correctly
- Check file permissions
- Ensure paths are absolute, not relative

### Timeout Issues

**Problem**: Validation takes too long

**Solutions**:
- Check for infinite loops in implementation
- Optimize test execution
- Increase timeout if legitimately needed

## Summary

The 3-agent code workflow provides:

- **Blind validation** - Coder never sees expected output
- **Anti-cheat protection** - Filesystem restrictions prevent cheating
- **Reproducible evidence** - Byte-for-byte output comparison
- **Integration ready** - Works with TodoWrite and beads

This ensures implementations are correct and verified, not just claimed to work.
