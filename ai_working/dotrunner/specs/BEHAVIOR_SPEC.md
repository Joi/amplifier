# DotRunner Behavior Specification

**Status**: AUTHORITATIVE - Implementation must match this specification
**Version**: 1.0
**Last Updated**: 2025-01-20

See `/workspaces/amplifier/ai_working/dotrunner/ARCHITECTURE_DECISIONS.md` for design rationale.

## Overview

This document specifies the behavioral guarantees and execution semantics of DotRunner, including state management, composition patterns, and error handling.

**Key Behaviors**:
- Deterministic DAG execution
- State checkpointing after every node
- Agent-based state evaluation (EVALUATE mode)
- Hybrid routing (simple dict + complex expressions)
- Sub-workflow composition with isolation (Phase 2)
- Parallel execution within nodes (Phase 2)

## Core Execution Guarantees

### Deterministic DAG Execution

DotRunner guarantees deterministic execution through a directed acyclic graph (DAG) model:

1. **Sequential node execution** - Nodes execute one at a time in determined order
2. **State checkpointing** - State saved after every node execution
3. **Resumable sessions** - Can resume from any saved checkpoint
4. **Context accumulation** - All outputs available to subsequent nodes
5. **Atomic state updates** - State changes are atomic and crash-safe

### Workflow Composition

Workflows can compose hierarchically:

```yaml
# Parent workflow
- id: "quality-check"
  workflow: "sub_workflows/quality_gates.yaml"
  inputs:
    code: "{implementation}"
  outputs:
    - quality_score
    - issues_found
```

**Composition guarantees:**
- Sub-workflows execute in isolated context
- Parent provides explicit inputs
- Child returns explicit outputs
- State tracked hierarchically
- Errors bubble up with context

## State Evaluation Patterns

### Agent-Based Quality Assessment

Agents can evaluate state and make quality determinations:

```yaml
- id: "test-evaluation"
  agent: "test-coverage"
  agent_mode: "Analyze test completeness and coverage"
  prompt: "Evaluate tests in {test_dir}"
  outputs:
    - tests_complete  # yes/no
    - coverage_percent  # numeric
    - missing_areas    # list
  next:
    - when: "tests_complete == 'yes' and coverage_percent > 80"
      goto: "deploy"
    - default: "improve-tests"
```

**Evaluation patterns:**
- Natural language mode instructions
- Agents assess quality/completeness/readiness
- Output structured evaluations
- Route based on quality thresholds

### Evidence-Based Reliability

The core use case - ensuring reliable AI work through evidence:

```yaml
# Evidence collection node
- id: "gather-evidence"
  agent: "evidence-collector"
  agent_mode: "Collect all supporting evidence for implementation"
  prompt: "Find evidence that {implementation} is correct"
  outputs:
    - test_evidence
    - documentation_evidence
    - type_check_evidence

# Evidence evaluation node
- id: "evaluate-evidence"
  agent: "evidence-evaluator"
  agent_mode: "Score evidence completeness from 0-100"
  prompt: |
    Score the evidence:
    Tests: {test_evidence}
    Docs: {documentation_evidence}
    Types: {type_check_evidence}
  outputs:
    - evidence_score
    - missing_evidence
```

## Routing Behavior

### Simple Routing (Dict-Based)

For 80% of cases - straightforward value matching:

```yaml
next:
  pass: "success-path"
  fail: "failure-path"
  retry: "retry-path"
  default: "unknown-path"
```

**Behavior:**
- First output value determines route
- Case-insensitive matching
- Default fallback required
- O(1) routing decision

### Complex Routing (Expression-Based)

For 20% of cases - sophisticated conditions:

```yaml
next:
  - when: "all_tests_passed and coverage > 0.9"
    goto: "fast-deploy"
  - when: "all_tests_passed and coverage > 0.8"
    goto: "standard-deploy"
  - when: "some_tests_failed"
    goto: "fix-tests"
  - default: "manual-review"
```

**Expression capabilities:**
- Comparisons: `>`, `>=`, `<`, `<=`, `==`, `!=`
- Logical: `and`, `or`
- Functions: `len(list)`
- Safe evaluation via ast.literal_eval

## Error Handling

### Node-Level Retry

Each node can specify retry behavior:

```yaml
- id: "flaky-operation"
  agent: "deployment-agent"
  retry_on_failure: 3  # Retry up to 3 times
  retry_delay: 5       # Wait 5 seconds between retries
```

**Retry behavior:**
- Exponential backoff by default
- State preserved between retries
- Different error types can have different retry strategies

### Workflow-Level Recovery

Workflows handle failures gracefully:

```python
class WorkflowRecovery:
    def handle_node_failure(self, node, error):
        if node.critical:
            # Critical node - fail entire workflow
            raise WorkflowCriticalError(f"Critical node {node.id} failed")
        elif node.optional:
            # Optional node - log and continue
            log.warning(f"Optional node {node.id} failed: {error}")
            return self.get_next_node(node.on_optional_failure)
        else:
            # Standard node - use error routing
            return self.route_on_error(node, error)
```

### Error Propagation

Errors propagate with full context:

```python
@dataclass
class NodeError:
    node_id: str
    error_type: str
    message: str
    context: dict
    stack_trace: str
    recovery_suggestions: list[str]
```

## Resume Behavior

### Session Persistence

Sessions persist with complete state:

```
.dotrunner/sessions/<session-id>/
├── state.json       # Current execution state
├── context.json     # Accumulated context
├── trace.jsonl      # Execution history
└── nodes/
    └── <node-id>/
        ├── input.json
        ├── output.json
        └── agent_response.json
```

### Resume Semantics

When resuming a session:

1. **State restoration** - Full state loaded from disk
2. **Context preservation** - All previous outputs available
3. **Position recovery** - Continues from exact interruption point
4. **Trace continuation** - Appends to existing execution trace
5. **Idempotent resume** - Safe to resume multiple times

### Partial Completion Handling

```python
def resume_workflow(session_id: str):
    state = load_state(session_id)

    if state.status == "completed":
        return state.final_context  # Already done

    if state.current_node:
        # Resume from interruption point
        next_node = determine_next_node(state.current_node, state.context)
        continue_execution(next_node, state)
    else:
        # Start from beginning with existing context
        start_execution(workflow.entry_node, state)
```

## Phase 2: Internal Node Parallelism

### Parallel Execution Within Nodes

While the graph remains sequential, nodes can parallelize internally:

```yaml
- id: "parallel-validation"
  agent: "multi-validator"
  agent_mode: "Run all validations in parallel"
  parallel_tasks:
    - lint_check
    - type_check
    - security_scan
    - performance_test
  outputs:
    - all_passed
    - failed_checks
    - validation_report
```

**Parallel execution contract:**
- Node blocks until all parallel tasks complete
- Results aggregated before proceeding
- Failures collected for routing decision
- Graph determinism maintained

### Example: Parallel Test Runner

```python
class ParallelTestRunner:
    async def execute(self, node: Node, context: dict) -> dict:
        # Spawn parallel test executions
        test_tasks = []
        for test_suite in context["test_suites"]:
            task = asyncio.create_task(self.run_test_suite(test_suite))
            test_tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*test_tasks, return_exceptions=True)

        # Aggregate results
        all_passed = all(r.passed for r in results if not isinstance(r, Exception))
        total_tests = sum(r.count for r in results if not isinstance(r, Exception))

        return {
            "all_passed": all_passed,
            "total_tests": total_tests,
            "results": results
        }
```

## Composition Patterns

### Quality Gate Pattern

Ensure quality before proceeding:

```yaml
name: "quality-gate"
nodes:
  - id: "run-checks"
    workflow: "quality/all_checks.yaml"
    outputs:
      - quality_score
      - blocking_issues

  - id: "evaluate"
    agent: "quality-evaluator"
    agent_mode: "Determine if quality is sufficient"
    prompt: "Score: {quality_score}, Issues: {blocking_issues}"
    outputs:
      - proceed
    next:
      yes: "continue"
      no: "remediate"
```

### Evidence Collection Pattern

Gather evidence for decision-making:

```yaml
name: "evidence-based-decision"
nodes:
  - id: "collect"
    agent: "evidence-collector"
    parallel_tasks:
      - check_tests
      - check_docs
      - check_types
      - check_security

  - id: "synthesize"
    agent: "evidence-synthesizer"
    agent_mode: "Synthesize all evidence into decision"
```

### Retry with Remediation Pattern

Attempt fix and retry:

```yaml
name: "self-healing"
nodes:
  - id: "attempt"
    agent: "executor"
    next:
      success: "done"
      failure: "diagnose"

  - id: "diagnose"
    agent: "diagnostician"
    agent_mode: "Identify root cause of failure"

  - id: "remediate"
    agent: "fixer"
    agent_mode: "Fix the identified issue"
    next: "attempt"  # Retry after fix
```

## Performance Characteristics

### Execution Overhead

- **Node transition**: ~10ms (state save + routing)
- **Context interpolation**: O(n) where n = template length
- **State persistence**: O(s) where s = state size
- **Agent invocation**: Dominated by agent response time

### Resource Usage

- **Memory**: O(n × m) where n = nodes, m = average output size
- **Disk**: O(n × m) for state persistence
- **Network**: Minimal (only for agent calls)

### Optimization Strategies

1. **Minimize context size** - Only pass necessary data
2. **Use sub-workflows** - Isolate context domains
3. **Leverage caching** - Reuse expensive computations
4. **Parallel node internals** - Maximize throughput

## Security Considerations

### Input Validation

- YAML parsing uses safe_load (no code execution)
- Expression evaluation restricted to ast.literal_eval
- No arbitrary code execution in templates

### State Protection

- Atomic writes prevent corruption
- Session isolation prevents cross-contamination
- No automatic cleanup preserves audit trail

### Agent Isolation

- Subprocess backend available for untrusted agents
- Timeout protection (configurable)
- Resource limits can be applied at OS level