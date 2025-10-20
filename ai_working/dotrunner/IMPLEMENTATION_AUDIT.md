# DotRunner Implementation Audit

**Date**: 2025-01-20
**Purpose**: Compare current implementation against authoritative specifications

---

## Audit Summary

| Component | Spec Status | Implementation Status | Gap |
|-----------|-------------|----------------------|-----|
| Dict-based routing | ✅ Specified | ✅ Implemented | None |
| Agent execution | ✅ Task tool (spec) | ❌ Subprocess (code) | **CRITICAL** |
| Agent modes | ✅ Standardized | ⚠️ Flexible strings | Needs standardization |
| State directory | ✅ `.dotrunner/sessions/` | ✅ Implemented | None |
| Expression routing | ✅ Specified (Phase 2) | ❌ Not implemented | Phase 2 |
| Sub-workflows | ✅ Specified (Phase 2) | ❌ Not implemented | Phase 2 |
| Parallel execution | ✅ Specified (Phase 2) | ❌ Not implemented | Phase 2 |
| Context interpolation | ✅ Specified | ✅ Implemented | None |
| State persistence | ✅ Atomic writes | ✅ Implemented | None |
| Test coverage | ✅ 85%+ required | ❓ Unknown | Needs measurement |

---

## Critical Gaps (MVP - Must Fix)

### 1. Agent Execution Backend ❌ CRITICAL

**Spec says**: Use Task tool for agent execution (default)
**Code does**: Uses subprocess calls to `amplifier agent`

**Files affected**:
- `executor.py:204-238` - `_execute_with_agent()` method

**Fix required**:
```python
# Current (subprocess):
cmd = ["amplifier", "agent", node.agent]
result = subprocess.run(cmd, ...)

# Should be (Task tool):
from amplifier.ccsdk_toolkit import task_tool
response = await task_tool.execute(
    agent_name=node.agent,
    mode=node.agent_mode,
    prompt=prompt
)
```

**Priority**: P0 - Core architectural decision

---

### 2. Agent Mode Standardization ⚠️ IMPORTANT

**Spec says**: Standard modes: ANALYZE, EVALUATE, EXECUTE, REVIEW, GENERATE
**Code does**: Accepts any string in `agent_mode`

**Files affected**:
- `workflow.py:36` - Node dataclass accepts `agent_mode: str | None`
- No validation of agent_mode values

**Fix required**:
- Add AgentMode enum
- Validate agent_mode values
- Update documentation to use standard modes

**Priority**: P1 - Important for consistency

---

### 3. Expression-Based Routing ❌ PHASE 2

**Spec says**: Support both dict and expression-based routing
**Code does**: Only dict-based routing

**Files affected**:
- `engine.py:154-179` - `_resolve_conditional_next()` only handles dict

**Fix required**:
- Add `SafeExpressionEvaluator` class
- Support list-based routing with `when`/`goto`
- Use `ast.literal_eval` for safe evaluation

**Priority**: P2 - Phase 2 feature, document but defer

---

### 4. Workflow Node Type ❌ PHASE 2

**Spec says**: Nodes can be agents OR workflows
**Code does**: Only agent nodes

**Files affected**:
- `workflow.py` - No `workflow` field in Node
- `executor.py` - No workflow execution path

**Fix required**:
- Add `workflow: str` field to Node
- Implement sub-workflow execution
- Handle input/output mapping

**Priority**: P2 - Phase 2 feature

---

### 5. Parallel Node Type ❌ PHASE 2

**Spec says**: Support `type: "parallel"` with `for_each`
**Code does**: No parallel execution

**Fix required**:
- Add `type` field validation
- Implement `for_each` iteration
- Add `wait_for` logic (all, any, majority)

**Priority**: P2 - Phase 2 feature

---

## Working Correctly ✅

### 1. Dict-Based Routing ✅

**Location**: `engine.py:154-179`

Correctly implements:
- Case-insensitive matching
- Default fallback
- Uses first output value

### 2. State Directory ✅

**Location**: `persistence.py:37-53`

Correctly uses `.dotrunner/sessions/`

### 3. Context Interpolation ✅

**Location**: `context.py:87-129`

Correctly implements:
- `{variable}` pattern matching
- Missing variable detection
- Template interpolation

### 4. Atomic State Persistence ✅

**Location**: `persistence.py:56-111`

Correctly implements:
- Temp file + rename pattern
- Metadata saving
- Session ID generation

### 5. CLI Commands ✅

**Location**: `cli.py`

All commands implemented:
- run (line 35-104)
- list (line 107-146)
- status (line 149-191)
- resume (line 194-253)

---

## Test Coverage Analysis

**Test files found**: 9 test files in `/tests/` directory

**Test categories**:
1. `test_workflow_model.py` - Workflow/Node models
2. `test_context.py` - Context interpolation
3. `test_executor.py` - Node execution
4. `test_engine.py` - Workflow engine
5. `test_persistence.py` - State persistence
6. `test_state.py` - State models
7. `test_conditional_routing.py` - Routing logic
8. `test_agent_integration.py` - Agent execution
9. `test_cli.py` - CLI commands

**Coverage measurement needed**: Run `pytest --cov` to determine actual coverage

**Missing tests** (from spec):
- Integration stress test with real agents
- E2E evidence-based workflow test
- Sub-workflow tests (Phase 2)
- Parallel execution tests (Phase 2)

---

## Implementation Priority

### Immediate (MVP - Phase 1)

1. **P0**: Switch executor from subprocess to Task tool
2. **P1**: Standardize agent_mode with enum
3. **P0**: Run tests and measure coverage
4. **P1**: Create integration stress test
5. **P1**: Update user-facing docs (README.md, DESIGN.md)

### Later (Phase 2)

6. **P2**: Add expression-based routing
7. **P2**: Add sub-workflow support
8. **P2**: Add parallel execution
9. **P2**: Add configurable timeouts

---

## Files Requiring Changes

### Critical Changes (MVP)

- `executor.py` - Switch to Task tool
- `workflow.py` - Add AgentMode enum
- `tests/test_agent_integration.py` - Update for Task tool
- `README.md` - Update to match specs
- `DESIGN.md` - Update to match specs

### Phase 2 Changes

- `engine.py` - Add expression evaluator
- `workflow.py` - Add workflow/parallel node support
- `executor.py` - Add workflow/parallel execution
- New: `evaluator.py` - SafeExpressionEvaluator class

---

## Next Steps

1. Create detailed task breakdown for each gap
2. Start with P0 items (Task tool, tests)
3. Validate with real workflow execution
4. Measure and improve test coverage to 85%+
5. Update documentation

---

**Audit complete. Ready for implementation.**
