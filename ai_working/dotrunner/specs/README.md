# DotRunner Complete Specifications

**Created**: 2025-01-19
**Purpose**: Document-Driven Development (DDD) compliant specifications based on ACTUAL implementation
**Status**: COMPLETE

---

## Overview

These specifications document what DotRunner ACTUALLY is, not what the documentation claims it to be. They were created by reverse-engineering the working implementation to provide accurate, complete specifications suitable for:

1. **Understanding** the real system behavior
2. **Testing** against actual functionality
3. **Re-implementing** from scratch if needed
4. **Fixing** discrepancies between docs and code

---

## Specification Documents

### 1. [API_CONTRACT.md](./API_CONTRACT.md)
**Purpose**: Defines all public interfaces

- Python API (classes, functions, data structures)
- CLI commands and options
- YAML schema and format
- File system structure
- Error handling contracts

### 2. [IMPLEMENTATION_SPEC.md](./IMPLEMENTATION_SPEC.md)
**Purpose**: Documents internal implementation

- Module organization
- Execution flow details
- Key algorithms and patterns
- Performance characteristics
- Technical debt and limitations

### 3. [BEHAVIOR_SPEC.md](./BEHAVIOR_SPEC.md)
**Purpose**: Specifies system behavior

- System guarantees
- Routing behavior
- Error handling behavior
- Edge cases and limitations
- Common issues and solutions

### 4. [TEST_SPEC.md](./TEST_SPEC.md)
**Purpose**: Documents testing requirements

- Current test coverage
- Missing critical tests
- Test patterns to implement
- Test data requirements
- Coverage goals

---

## Key Findings: Documentation vs Reality

### Critical Discrepancies

| Feature | Documentation Claims | Actual Implementation |
|---------|---------------------|----------------------|
| **Conditional Routing** | List format with `when`/`goto` | Dictionary with simple value matching |
| **Agent Integration** | Uses Task tool | Subprocess to `amplifier agent` CLI |
| **State Directory** | `.data/dotrunner/runs/` | `.dotrunner/sessions/` |
| **Condition Evaluation** | AI evaluates complex conditions | Simple case-insensitive string match |
| **Missing Components** | ConditionEvaluator, parser.py, evaluator.py | Don't exist |

### Undocumented Behaviors

1. **Routing uses ONLY first output** - Additional outputs ignored for routing
2. **300-second hard timeout** - For all agent subprocess calls
3. **Case-insensitive routing** - All condition matching ignores case
4. **No cleanup mechanism** - Sessions persist forever
5. **Atomic writes** - Uses temp file + rename pattern

---

## System Architecture (Actual)

```
┌─────────────────────────────────────────┐
│                CLI (cli.py)              │
│         Click-based commands             │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│         WorkflowEngine (engine.py)       │
│   - Orchestrates execution               │
│   - Manages state persistence            │
│   - Implements routing logic inline      │
└────────┬──────────────────┬──────────────┘
         │                  │
    ┌────▼─────┐     ┌─────▼──────┐
    │  Node    │     │   State    │
    │ Executor │     │ Persistence│
    │          │     │            │
    └────┬─────┘     └────────────┘
         │
    ┌────▼─────────────────┐
    │  Agent Integration   │
    │  (subprocess calls)  │
    └──────────────────────┘
```

---

## How to Use These Specifications

### For Developers

1. **Understanding the system**: Start with [BEHAVIOR_SPEC.md](./BEHAVIOR_SPEC.md)
2. **Using the API**: Reference [API_CONTRACT.md](./API_CONTRACT.md)
3. **Debugging issues**: Check [IMPLEMENTATION_SPEC.md](./IMPLEMENTATION_SPEC.md)
4. **Writing tests**: Follow [TEST_SPEC.md](./TEST_SPEC.md)

### For Re-implementation

Follow this order:
1. Implement data models from API_CONTRACT.md
2. Build core logic from IMPLEMENTATION_SPEC.md
3. Ensure behaviors match BEHAVIOR_SPEC.md
4. Validate with tests from TEST_SPEC.md

### For Bug Fixes

1. Identify discrepancy in specifications
2. Decide: Fix code or update specs?
3. Ensure consistency across all specs
4. Add tests for the fix

---

## Implementation Status

### What Works

✅ **Core Functionality**
- Linear workflow execution
- State persistence and resume
- Basic conditional routing
- Context interpolation
- Agent integration (via subprocess)

✅ **CLI Commands**
- run - Execute workflows
- list - Show sessions
- status - Check session state
- resume - Continue from checkpoint

### What Doesn't Match Docs

❌ **Documented but not implemented**
- Complex condition evaluation
- Task tool integration
- ConditionEvaluator class
- Parser module
- Original state directory location

❌ **Implemented but not documented**
- Dictionary-based routing
- Case-insensitive matching
- Subprocess agent execution
- Session ID format
- Atomic write pattern

---

## Recommendations

### Immediate Actions

1. **Update user documentation** to match actual behavior
2. **Add missing tests** identified in TEST_SPEC.md
3. **Fix critical gaps**:
   - Add agent timeout configuration
   - Implement session cleanup
   - Add resource limits

### Architecture Improvements

1. **Replace subprocess with native integration** for agents
2. **Add streaming support** for large outputs
3. **Implement parallel node execution** where possible
4. **Add progress callbacks** for long-running workflows

### Quality Improvements

1. **Increase test coverage** to 85%+
2. **Add integration tests** with real agents
3. **Implement performance benchmarks**
4. **Add error recovery tests**

---

## Validation Checklist

Use this to verify the specifications are complete:

### API Contract
- [x] All public classes documented
- [x] All CLI commands specified
- [x] YAML schema complete
- [x] Error types listed
- [x] File formats documented

### Implementation
- [x] Module structure mapped
- [x] Execution flow documented
- [x] Key algorithms explained
- [x] Performance noted
- [x] Limitations identified

### Behavior
- [x] Guarantees stated
- [x] Edge cases documented
- [x] Error handling specified
- [x] Common issues listed
- [x] Limitations clear

### Testing
- [x] Current coverage analyzed
- [x] Missing tests identified
- [x] Test patterns provided
- [x] Data requirements listed
- [x] Execution matrix defined

---

## Conclusion

These specifications represent the TRUTH about DotRunner as implemented. They expose significant discrepancies between documentation and reality, but also show that the core system works and provides value.

The specifications are complete enough to:
- Understand exactly how DotRunner works
- Fix the discrepancies between docs and code
- Re-implement the entire system if needed
- Build comprehensive tests
- Make informed architectural decisions

**Next Steps**:
1. Decide whether to fix code to match original docs OR update docs to match code
2. Prioritize and implement the missing tests
3. Address the critical gaps identified
4. Consider architectural improvements for v2

---

*These specifications follow Document-Driven Development (DDD) principles and were created through systematic code analysis and reverse engineering of the actual implementation.*