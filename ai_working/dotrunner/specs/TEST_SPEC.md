# DotRunner Test Specification

**Status**: AUTHORITATIVE - Implementation must pass these tests
**Version**: 1.0
**Last Updated**: 2025-01-20

See `/workspaces/amplifier/ai_working/dotrunner/ARCHITECTURE_DECISIONS.md` for design rationale.

## Overview

This document specifies the comprehensive testing requirements for DotRunner, ensuring reliability of workflow execution, state management, and agent integration.

**Testing Goals**:
- 85%+ overall code coverage
- Unit tests for all components
- Integration test stressing complete system
- End-to-end tests for evidence-based workflows
- Phase 2 feature tests (sub-workflows, parallel)

## Test Categories

### 1. Unit Tests (60% of Coverage)

Unit tests verify individual components in isolation.

#### Workflow Model Tests

```python
# test_workflow.py

def test_workflow_creation():
    """Test basic workflow instantiation."""
    workflow = Workflow(
        name="test",
        nodes=[Node(id="n1", agent="test-agent", prompt="test")],
        version="1.0.0"
    )
    assert workflow.name == "test"
    assert len(workflow.nodes) == 1

def test_workflow_validation():
    """Test workflow validation rules."""
    # Test duplicate node IDs
    with pytest.raises(WorkflowSyntaxError, match="Duplicate node ID"):
        workflow = create_workflow_with_duplicate_ids()
        workflow.validate()

    # Test circular dependencies
    with pytest.raises(WorkflowSyntaxError, match="Circular dependency"):
        workflow = create_circular_workflow()
        workflow.validate()

    # Test missing node references
    with pytest.raises(WorkflowSyntaxError, match="Node not found"):
        workflow = create_workflow_with_missing_reference()
        workflow.validate()

def test_node_types():
    """Test both agent and workflow node types."""
    # Agent node
    agent_node = Node(
        id="agent",
        node_type=NodeType.AGENT,
        agent="zen-architect",
        agent_mode="ANALYZE",
        prompt="Analyze {code}"
    )
    assert agent_node.node_type == NodeType.AGENT

    # Workflow node
    workflow_node = Node(
        id="sub",
        node_type=NodeType.WORKFLOW,
        workflow="sub_workflow.yaml"
    )
    assert workflow_node.node_type == NodeType.WORKFLOW
```

#### Expression Evaluator Tests

```python
# test_evaluator.py

def test_simple_comparisons():
    """Test basic comparison operations."""
    evaluator = SafeExpressionEvaluator()

    assert evaluator.evaluate("5 > 3", {})
    assert evaluator.evaluate("count >= 10", {"count": 10})
    assert evaluator.evaluate("status == 'ready'", {"status": "ready"})
    assert not evaluator.evaluate("value < 0", {"value": 5})

def test_logical_operations():
    """Test and/or operations."""
    evaluator = SafeExpressionEvaluator()

    context = {"a": 5, "b": 10, "status": "ready"}
    assert evaluator.evaluate("a > 3 and b < 20", context)
    assert evaluator.evaluate("a < 3 or status == 'ready'", context)
    assert not evaluator.evaluate("a > 10 and b > 20", context)

def test_len_function():
    """Test len() function support."""
    evaluator = SafeExpressionEvaluator()

    context = {"items": [1, 2, 3], "text": "hello"}
    assert evaluator.evaluate("len(items) > 2", context)
    assert evaluator.evaluate("len(text) == 5", context)

def test_invalid_expressions():
    """Test that dangerous expressions are rejected."""
    evaluator = SafeExpressionEvaluator()

    with pytest.raises(ValueError):
        evaluator.evaluate("__import__('os').system('ls')", {})

    with pytest.raises(ValueError):
        evaluator.evaluate("exec('print(1)')", {})
```

#### Context Management Tests

```python
# test_context.py

def test_simple_interpolation():
    """Test basic variable interpolation."""
    manager = ContextManager()
    manager.context = {"name": "Alice", "age": 30}

    result = manager.interpolate_template("Hello {name}, age {age}")
    assert result == "Hello Alice, age 30"

def test_node_qualified_references():
    """Test node.output references."""
    manager = ContextManager()
    manager.node_outputs["node1"] = {"result": "success"}
    manager.node_outputs["node2"] = {"score": 95}

    result = manager.interpolate_template("{node1.result} with {node2.score}")
    assert result == "success with 95"

def test_missing_variables():
    """Test detection of missing variables."""
    manager = ContextManager()
    manager.context = {"present": "value"}

    missing = manager.validate_requirements("{present} and {missing}")
    assert missing == ["missing"]

def test_system_variables():
    """Test system variable interpolation."""
    manager = ContextManager()
    manager.session_id = "test-session"

    result = manager.interpolate_template("Session: {_session_id}")
    assert "test-session" in result
```

#### State Persistence Tests

```python
# test_persistence.py

def test_atomic_save():
    """Test atomic state saving."""
    persistence = StatePersistence(Path("/tmp/test"))
    state = WorkflowState(
        workflow_id="test",
        status="running",
        context={"key": "value"}
    )

    # Save should be atomic
    with mock.patch('os.fsync') as mock_fsync:
        persistence.save_state("session1", state)
        assert mock_fsync.called  # Ensures flush to disk

def test_state_recovery():
    """Test loading saved state."""
    persistence = StatePersistence(Path("/tmp/test"))

    # Save state
    original = WorkflowState(workflow_id="test", context={"data": "value"})
    persistence.save_state("session1", original)

    # Load state
    loaded = persistence.load_state("session1")
    assert loaded.workflow_id == original.workflow_id
    assert loaded.context == original.context

def test_trace_append():
    """Test execution trace is append-only."""
    persistence = StatePersistence(Path("/tmp/test"))
    session_id = "test-session"

    # Append multiple trace entries
    for i in range(3):
        state = WorkflowState(current_node=f"node{i}")
        persistence._append_trace(session_id, state)

    # Verify all entries preserved
    trace_file = persistence.state_dir / session_id / "trace.jsonl"
    lines = trace_file.read_text().strip().split("\n")
    assert len(lines) == 3
```

### 2. Integration Tests (30% of Coverage)

Integration tests verify component interactions.

#### Workflow Engine Tests

```python
# test_engine_integration.py

@pytest.mark.integration
async def test_complete_workflow_execution():
    """Test end-to-end workflow execution."""
    workflow = Workflow.from_yaml(Path("fixtures/simple_workflow.yaml"))
    engine = WorkflowEngine()

    result = await engine.run(workflow, initial_context={"input": "test"})

    assert result["status"] == "completed"
    assert len(result["node_results"]) == len(workflow.nodes)
    assert all(r.status == "success" for r in result["node_results"])

@pytest.mark.integration
async def test_workflow_with_routing():
    """Test workflow with conditional routing."""
    workflow = create_workflow_with_routing()
    engine = WorkflowEngine()

    # Test path A
    result_a = await engine.run(workflow, {"choice": "a"})
    assert "path_a" in result_a["execution_path"]

    # Test path B
    result_b = await engine.run(workflow, {"choice": "b"})
    assert "path_b" in result_b["execution_path"]

@pytest.mark.integration
async def test_workflow_resume():
    """Test resuming interrupted workflow."""
    workflow = create_interruptible_workflow()
    engine = WorkflowEngine()

    # Start execution
    session_id = "test-resume"
    with interrupt_after_node("node2"):
        await engine.run(workflow, session_id=session_id)

    # Resume execution
    result = await engine.resume(session_id)
    assert result["status"] == "completed"
    assert result["execution_path"][-1] == "final_node"
```

#### Sub-Workflow Tests

```python
# test_sub_workflows.py

@pytest.mark.integration
async def test_sub_workflow_execution():
    """Test sub-workflow invocation."""
    parent = Workflow.from_yaml(Path("fixtures/parent.yaml"))
    engine = WorkflowEngine()

    result = await engine.run(parent)

    # Verify sub-workflow was executed
    assert "sub_workflow_output" in result["context"]
    assert result["node_results"][1].node_type == NodeType.WORKFLOW

@pytest.mark.integration
async def test_sub_workflow_isolation():
    """Test context isolation in sub-workflows."""
    parent = create_parent_workflow()
    engine = WorkflowEngine()

    parent_context = {"parent_only": "value", "shared": "parent"}
    result = await engine.run(parent, parent_context)

    # Parent context should not be polluted
    assert result["context"]["parent_only"] == "value"
    # But sub-workflow outputs should be available
    assert "sub_output" in result["context"]

@pytest.mark.integration
async def test_nested_sub_workflows():
    """Test deeply nested workflow composition."""
    root = create_nested_workflow_tree(depth=3)
    engine = WorkflowEngine()

    result = await engine.run(root)
    assert result["status"] == "completed"
    assert result["nesting_depth"] == 3
```

#### Agent Integration Tests

```python
# test_agent_integration.py

@pytest.mark.integration
async def test_task_tool_backend():
    """Test agent execution via Task tool."""
    node = Node(
        id="test",
        agent="zen-architect",
        agent_mode="ANALYZE",
        prompt="Analyze this code"
    )

    executor = NodeExecutor(backend="task")
    result = await executor.execute(node, {})

    assert result.status == "success"
    assert result.outputs

@pytest.mark.integration
async def test_subprocess_backend():
    """Test agent execution via subprocess."""
    node = Node(
        id="test",
        agent="bug-hunter",
        agent_mode="Find issues",
        prompt="Check for bugs"
    )

    executor = NodeExecutor(backend="subprocess")
    result = await executor.execute(node, {})

    assert result.status == "success"
    verify_subprocess_called("amplifier", "agent", "bug-hunter")

@pytest.mark.integration
async def test_agent_timeout():
    """Test agent timeout handling."""
    node = Node(
        id="slow",
        agent="slow-agent",
        prompt="Take forever"
    )

    executor = NodeExecutor(timeout=1)  # 1 second timeout
    with pytest.raises(TimeoutError):
        await executor.execute(node, {})
```

### 3. End-to-End Tests (10% of Coverage)

E2E tests verify complete user scenarios.

#### Evidence-Based Workflow Test

```python
# test_evidence_workflow.py

@pytest.mark.e2e
async def test_evidence_based_development():
    """Test the core evidence-based development pattern."""
    workflow = Workflow.from_yaml(Path("examples/evidence_based.yaml"))
    engine = WorkflowEngine()

    context = {
        "feature_request": "Add user authentication",
        "requirements": "OAuth2 support required"
    }

    result = await engine.run(workflow, context)

    # Verify evidence was collected
    assert "test_evidence" in result["context"]
    assert "documentation_evidence" in result["context"]

    # Verify quality evaluation
    assert "evidence_score" in result["context"]
    assert result["context"]["evidence_score"] > 0

    # Verify routing based on evidence
    if result["context"]["evidence_score"] > 80:
        assert "deploy" in result["execution_path"]
    else:
        assert "improve" in result["execution_path"]
```

#### Stress Tests

```python
# test_stress.py

@pytest.mark.e2e
@pytest.mark.slow
async def test_large_workflow():
    """Test workflow with 100+ nodes."""
    workflow = create_large_workflow(node_count=100)
    engine = WorkflowEngine()

    start = time.time()
    result = await engine.run(workflow)
    duration = time.time() - start

    assert result["status"] == "completed"
    assert len(result["node_results"]) == 100
    assert duration < 300  # Should complete in 5 minutes

@pytest.mark.e2e
@pytest.mark.slow
async def test_concurrent_workflows():
    """Test multiple workflows running concurrently."""
    workflows = [create_workflow(f"workflow{i}") for i in range(10)]
    engine = WorkflowEngine()

    # Run all concurrently
    tasks = [engine.run(w) for w in workflows]
    results = await asyncio.gather(*tasks)

    # All should complete successfully
    assert all(r["status"] == "completed" for r in results)
    # All should have unique session IDs
    session_ids = [r["session_id"] for r in results]
    assert len(set(session_ids)) == 10

@pytest.mark.e2e
async def test_complex_routing_scenario():
    """Test complex multi-path routing."""
    workflow = create_complex_routing_workflow()
    engine = WorkflowEngine()

    # Test multiple paths
    test_cases = [
        ({"score": 95, "tests": "pass"}, "fast-track"),
        ({"score": 85, "tests": "pass"}, "standard"),
        ({"score": 75, "tests": "fail"}, "remediate"),
        ({"score": 50, "tests": "pass"}, "review"),
    ]

    for context, expected_path in test_cases:
        result = await engine.run(workflow, context)
        assert expected_path in result["execution_path"]
```

## Test Fixtures

### Workflow Fixtures

```python
# fixtures/workflows.py

def create_simple_workflow() -> Workflow:
    """Create minimal valid workflow."""
    return Workflow(
        name="simple",
        nodes=[
            Node(id="start", agent="test", prompt="Start"),
            Node(id="end", agent="test", prompt="End")
        ]
    )

def create_workflow_with_routing() -> Workflow:
    """Create workflow with conditional routing."""
    return Workflow(
        name="routing",
        nodes=[
            Node(
                id="decision",
                outputs=["choice"],
                next={
                    "a": "path_a",
                    "b": "path_b",
                    "default": "path_default"
                }
            ),
            Node(id="path_a", prompt="Path A"),
            Node(id="path_b", prompt="Path B"),
            Node(id="path_default", prompt="Default")
        ]
    )

def create_workflow_with_sub_workflow() -> Workflow:
    """Create workflow that invokes sub-workflow."""
    return Workflow(
        name="parent",
        nodes=[
            Node(id="prep", agent="test", prompt="Prepare"),
            Node(
                id="sub",
                node_type=NodeType.WORKFLOW,
                workflow="sub.yaml",
                inputs={"data": "{prep_output}"},
                outputs=["sub_result"]
            ),
            Node(id="final", prompt="Process {sub_result}")
        ]
    )
```

### Mock Agents

```python
# fixtures/mock_agents.py

class MockAgent:
    """Mock agent for testing."""

    def __init__(self, name: str, responses: dict):
        self.name = name
        self.responses = responses
        self.call_count = 0

    async def execute(self, prompt: str, mode: str = None) -> dict:
        """Simulate agent execution."""
        self.call_count += 1

        # Simulate processing time
        await asyncio.sleep(0.1)

        # Return predefined response
        if prompt in self.responses:
            return self.responses[prompt]
        return {"output": "default response"}

def create_mock_agent_registry():
    """Create registry of mock agents."""
    return {
        "test-agent": MockAgent("test", {"test": {"result": "success"}}),
        "slow-agent": MockAgent("slow", {}, delay=5.0),
        "failing-agent": MockAgent("fail", {}, should_fail=True),
    }
```

## Test Execution

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test category
pytest tests/ -m unit
pytest tests/ -m integration
pytest tests/ -m e2e

# Run with coverage
pytest tests/ --cov=dotrunner --cov-report=html

# Run in parallel
pytest tests/ -n auto

# Run with verbose output
pytest tests/ -v

# Stop on first failure
pytest tests/ -x
```

### Test Configuration

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (component interaction)
    e2e: End-to-end tests (full scenarios)
    slow: Long-running tests
    flaky: Tests that may fail intermittently
```

### Coverage Requirements

| Component | Required Coverage | Critical Paths |
|-----------|------------------|----------------|
| Workflow Model | 95% | Validation, YAML parsing |
| Expression Evaluator | 100% | All operators, safety |
| Context Manager | 90% | Interpolation, validation |
| State Persistence | 95% | Atomic saves, recovery |
| Workflow Engine | 85% | Execution, routing, resume |
| Node Executor | 90% | Agent calls, retries |
| Routing Engine | 95% | All routing types |
| Sub-Workflow Executor | 90% | Composition, isolation |

## Continuous Integration

### CI Pipeline

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run unit tests
        run: pytest tests/ -m unit --cov

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run integration tests
        run: pytest tests/ -m integration

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run E2E tests
        run: pytest tests/ -m e2e
```

### Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: Run tests
        entry: pytest tests/ -m "unit" --quiet
        language: system
        pass_filenames: false
```

## Test Quality Metrics

### Code Coverage

- Minimum 85% overall coverage
- 100% coverage for critical paths
- No untested error handlers

### Test Performance

- Unit tests: < 0.1s each
- Integration tests: < 1s each
- E2E tests: < 30s each
- Full suite: < 5 minutes

### Test Reliability

- Zero flaky tests in CI
- All tests deterministic
- Proper test isolation