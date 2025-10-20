# DotRunner: Architecture Decisions

**Status**: AUTHORITATIVE - This document defines what DotRunner SHOULD be
**Created**: 2025-01-20
**Purpose**: Document-Driven Development - Specifications before implementation

---

## Decision Record

These decisions define the authoritative specification for DotRunner. Code should be updated to match these specifications, not the other way around.

---

## ✅ CONFIRMED DECISIONS

### 1. Conditional Routing Format

**Decision**: Dictionary-based routing
**Rationale**: Simpler for common cases

```yaml
next:
  pass: "deploy"
  fail: "fix-tests"
  default: "manual-review"
```

**Status**: Current implementation matches ✓

### 2. Agent Integration Strategy

**Decision**: Dual approach
- **Default**: Task tool for standard execution
- **Parallel**: Subprocess for parallel workflow scenarios

**Rationale**: Need control AND the ability to run multiple agents in parallel

**Implementation needed**:
- [ ] Switch default execution to Task tool
- [ ] Keep subprocess option for parallel blocks
- [ ] Document when to use each approach

### 3. State Directory Location

**Decision**: `.dotrunner/sessions/` (my choice as requested)
**Rationale**:
- Standard dotfile convention
- Clear naming (sessions not runs)
- Matches current implementation

**Status**: Current implementation matches ✓

### 4. Condition Evaluation

**Decision**: Use Python's `ast.literal_eval()` for safe expression evaluation
**Rationale**: Allows boolean logic without code execution risk

**Examples**:
```python
# Safe evaluations:
count > 10
status == "ready"
count > 10 and files < 5
result in ["pass", "approved"]
```

**Implementation needed**:
- [ ] Create ConditionEvaluator using ast.literal_eval()
- [ ] Support both dict routing (simple) and expression evaluation (complex)
- [ ] Document expression syntax limits

### 5. Module Structure

**Decision**: Inline implementation (no separate parser.py, evaluator.py)
**Rationale**: Ruthless simplicity - don't need extra modules yet

**Status**: Current implementation matches ✓

### 6. Agent Mode Parameter

**Decision**: CRITICAL FEATURE - agents must be able to evaluate state

**Use case**: Agents need to make decisions (tests pass/fail, quality checks, etc.)

```yaml
- id: "check-tests"
  agent: "test-coverage"
  agent_mode: "EVALUATE"
  prompt: "Run tests and evaluate if all pass"
  outputs:
    - test_status
  next:
    pass: "deploy"
    fail: "fix-tests"
```

**Status**: Partially implemented (agent_mode exists but not fully specified) ⚠️

**Implementation needed**:
- [ ] Document agent_mode parameter in spec
- [ ] Define standard modes (ANALYZE, EVALUATE, EXECUTE, etc.)
- [ ] Specify how agents should structure evaluation outputs

### 7. Core Feature Set

**Decision**: Sub-workflows are MVP feature
**Rationale**: Composition is key - need to invoke workflows OR agents as nodes

```yaml
# Agent node
- id: "analyze"
  agent: "zen-architect"
  prompt: "Review code"

# Workflow node
- id: "full-review"
  workflow: "code_review_workflow.yaml"
  inputs:
    file_path: "{current_file}"
  outputs:
    - review_result
```

**Implementation needed**:
- [ ] Add workflow node type
- [ ] Define input/output mapping for sub-workflows
- [ ] Handle sub-workflow state isolation

### 8. Testing Requirements

**Decision**:
- Complete unit test coverage on all units
- Integration test that stresses the whole system

**Requirements**:
- Unit tests for every module/class
- Integration test with real agents and complex workflows
- Test coverage > 85%

**Status**: ~65% coverage currently - needs work ❌

---

## ✅ FINAL DECISIONS (2025-01-20)

### A. Agent State Evaluation Pattern

**Decision**: Either pattern is acceptable - optimize for LLM generation reliability

**Rationale**: Users will express workflows in natural language, and models will generate the YAML. Choose whichever pattern LLMs generate more reliably.

**Recommended**: Option 1 (agent produces output, routing uses it) - simpler structure

```yaml
- id: "check-tests"
  agent: "test-coverage"
  agent_mode: "EVALUATE"
  prompt: "Run tests and return 'pass' or 'fail'"
  outputs:
    - test_status
  next:
    pass: "deploy"
    fail: "fix-tests"
```

### B. Sub-workflow Composition

**Decision**: Nodes can be agents OR workflows - full composability

**Key principles**:
- Each node can invoke an agent or a workflow
- Agents/workflows may do their own sub-invocations internally
- Inputs map to sub-workflow context
- Outputs become available to parent workflow
- Sub-workflows run isolated

```yaml
# Agent node
- id: "analyze"
  agent: "zen-architect"
  prompt: "Review code"

# Workflow node
- id: "full-review"
  workflow: "code_review.yaml"
  inputs:
    file_path: "{current_file}"
  outputs:
    - review_result
```

**Status**: Phase 2 implementation, document in spec NOW

### C. Parallel Execution

**Decision**: Support explicit parallel execution pattern

**Pattern**: Workflow can specify "run this agent/workflow across all items in a list, in parallel"

```yaml
- id: "parallel-tests"
  type: "parallel"
  agent: "test-runner"
  for_each: "{test_files}"
  prompt: "Run tests for {item}"
  wait_for: "all"
  outputs:
    - test_results  # Array of results
  next: "aggregate-results"
```

**Status**: Phase 2 implementation, document in spec NOW

### D. Condition Evaluation - Hybrid Support

**Decision**: Support BOTH simple dict AND complex expressions

**Rationale**:
- Simple dict for 80% of cases (fast, clear)
- Complex expressions for conditional logic needs

```yaml
# Simple dict matching
next:
  pass: "deploy"
  fail: "fix"

# Complex Python expressions
next:
  - when: "count > 10 and status == 'ready'"
    goto: "proceed"
  - default: "wait"
```

**Implementation**: Use ast.literal_eval() for expression evaluation

### E. Primary Use Cases

**Decision**: ALL workflow types - DotRunner is general-purpose

**Use cases**:
- Multi-agent code review pipelines
- Test-fix-deploy automation
- Content generation with review loops
- Document processing workflows
- **Dynamic workflow generation** - models create workflows on-the-fly
- **Evidence-based coding** - explicit steps with isolation that can't be cheated

**Key requirement**: Repeatable, reliable workflows with agent/sub-agent composition

---

## IMPLEMENTATION GAPS

Based on decisions above, here's what needs to be built:

### High Priority

1. **Switch to Task tool** for default agent execution
2. **Add ConditionEvaluator** with ast.literal_eval()
3. **Document agent_mode** parameter and standard modes
4. **Add sub-workflow support** (workflow node type)
5. **Increase test coverage** to 85%+

### Medium Priority

6. **Support expression-based routing** (in addition to dict)
7. **Add integration tests** with real agents
8. **Implement session cleanup** mechanism
9. **Add configurable timeouts** (not just 300s)

### Low Priority / Future

10. **Parallel node execution** (depends on C decision)
11. **Progress callbacks** for long workflows
12. **Workflow templates** for reusability

---

## NEXT STEPS

1. Get answers to clarification questions (A-E)
2. Update specifications to reflect SHOULD BE state
3. Mark implementation gaps clearly
4. Prioritize implementation work
5. Build test suite to validate new features

---

*This document is the AUTHORITATIVE source for DotRunner architecture. When in doubt, refer here.*
