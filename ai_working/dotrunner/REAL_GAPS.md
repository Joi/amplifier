# DotRunner: Real Implementation Gaps

**Date**: 2025-01-20
**Purpose**: Honest assessment of spec vs implementation

---

## Critical Gaps Found

### 1. Node Structure Mismatch ❌

**API Contract Says:**
```python
class Node:
    def __init__(
        self,
        id: str,
        node_type: NodeType,  # ← MISSING
        inputs: Dict[str, Any],  # ← MISSING
        outputs: List[str],
        # ...
        workflow: Optional[str]  # ← MISSING (Phase 2)
    )
```

**Current Implementation:**
```python
@dataclass
class Node:
    id: str
    name: str  # ← Has this (not in spec)
    prompt: str
    agent: str | None = None
    # NO inputs field
    # NO node_type field
    # NO workflow field
```

**Gap**: API contract and implementation have different Node structures

### 2. Workflow.nodes Structure Mismatch ❌

**API Contract Says:**
```python
self.nodes = {node.id: node for node in nodes}  # Dict by ID
```

**Current Implementation:**
```python
nodes: list[Node]  # List, not dict
```

**Gap**: Workflow stores nodes as list, spec says dict

### 3. Missing Version Field ❌

**API Contract Says:**
```yaml
version: string  # Semantic version (e.g., "1.0.0")
```

**Current Implementation:**
- No `version` field in Workflow
- No version parsing in from_yaml()
- No version in to_dict()

**Gap**: Version field completely missing

### 4. Missing inputs Field ❌

**API Contract Says:**
```yaml
inputs:
  feature_description: "{user_request}"
```

**Current Implementation:**
- No `inputs` field in Node
- No input mapping/resolution

**Gap**: Cannot map parent context to node inputs as shown in spec examples

### 5. Expression-Based Routing Not Implemented ❌

**API Contract Shows:**
```yaml
next:
  - when: "evidence_score >= 0.8"
    goto: "deploy"
```

**Current Implementation:**
- Dict-based routing works
- List-based routing partially supported in validation
- No ExpressionEvaluator class
- No ast.literal_eval evaluation

**Gap**: Complex routing documented but not implemented

### 6. Sub-Workflow Support Not Implemented ❌

**API Contract Shows:**
```yaml
- id: "verify-evidence"
  workflow: "quality_checks.yaml"
  inputs:
    code: "{implementation}"
```

**Current Implementation:**
- No `workflow` field in Node
- No sub-workflow execution in engine
- No WorkflowComposer class

**Gap**: Sub-workflows documented but not implemented

### 7. CLI Command Arguments Mismatch ❌

**API Contract Says:**
```bash
dotrunner run workflow.yaml --input feature="user authentication"
dotrunner run workflow.yaml --agent-backend subprocess
```

**Current CLI (cli.py):**
```bash
python -m ai_working.dotrunner run workflow.yaml --context key=value
# No --input option
# No --agent-backend option
```

**Gap**: CLI arguments don't match spec

### 8. State Directory Structure Incomplete ❌

**API Contract Says:**
```
.dotrunner/sessions/<session-id>/
├── state.json
├── context.json  # ← MISSING
├── trace.jsonl
└── nodes/<node-id>/
    ├── input.json  # ← MISSING
    ├── output.json  # ← MISSING
    └── agent_response.json  # ← MISSING
```

**Current Implementation:**
- Has state.json
- Has metadata.json (not in spec)
- Has trace.jsonl
- NO context.json
- NO nodes/ subdirectory structure

**Gap**: State persistence structure doesn't match spec

### 9. Missing description Field in Node ❌

**API Contract Says:**
```yaml
description: string  # Node purpose description (optional)
```

**Current Implementation:**
- Has `name` field
- NO `description` field

**Gap**: Node has name but spec shows description

---

## Phase 2 Features (Documented, Not Implemented)

These are EXPECTED to be missing:

1. ✅ Expression-based routing - Documented as Phase 2
2. ✅ Sub-workflow support - Documented as Phase 2
3. ✅ Parallel execution - Documented as Phase 2
4. ✅ ExpressionEvaluator class - Documented as Phase 2

---

## Test Coverage Reality Check

**Claim**: 95% coverage, 171 tests passing

**Reality**: Tests pass for CURRENT implementation, not for SPEC

The tests validate what's built, not what the spec describes. This means:
- Tests don't cover `inputs` field (doesn't exist)
- Tests don't cover `workflow` field (doesn't exist)
- Tests don't cover `version` field (doesn't exist)
- Tests don't cover expression routing (not implemented)
- Tests don't cover sub-workflows (not implemented)

**Conclusion**: High test coverage of incomplete implementation

---

## Summary of Real Status

### What Works ✅
- Dict-based routing
- Agent execution via subprocess
- State persistence (basic)
- Context interpolation
- CLI commands (partially)
- Test coverage of what exists

### What's Missing ❌
1. Node `inputs` field
2. Node `workflow` field
3. Node `description` vs `name` discrepancy
4. Workflow `version` field
5. Workflow.nodes as dict (currently list)
6. Expression-based routing
7. Sub-workflow execution
8. Complete state directory structure
9. CLI argument matching

### MVP Status

**Honest Assessment**: Implementation is a working subset of the spec, not a complete implementation.

**What This Means**:
- Current code WORKS for basic workflows
- Current code DOESN'T match the full API contract
- Tests validate current behavior, not spec compliance
- Phase 2 is documented but not built

---

## Recommendation

**Option 1**: Update specs to match implementation
- Simpler Node structure
- List-based nodes storage
- Current CLI arguments
- Current state structure

**Option 2**: Update implementation to match specs
- Add missing fields
- Implement Phase 2 features
- Update tests to validate spec compliance
- Complete state directory structure

**Option 3**: Clearly separate MVP vs Full Spec
- Document "MVP Profile" = what's built
- Document "Full Profile" = complete spec
- Mark fields/features by profile

---

**Real gaps identified. Awaiting direction on how to proceed.**
