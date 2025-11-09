# Phase 2: Linear Execution Engine - Detailed Design

## Overview

Phase 2 implements a linear workflow execution engine that processes nodes sequentially, managing context flow and AI execution through a clean, modular architecture.

**Status**: In Development
**Dependencies**: Phase 1 (Complete)
**Test Strategy**: Test-First with Golden File Validation

## Architecture

### Design Philosophy

Following our ruthless simplicity principle and modular "bricks and studs" philosophy:

- **Code for structure, AI for intelligence**
  - Code: Workflow orchestration, node sequencing, context passing
  - AI: Understanding prompts, generating outputs, extracting information

- **Layered Architecture**
  - Clear separation of concerns
  - Testable units with well-defined interfaces
  - Clean "bricks" that can be regenerated independently

- **ccsdk_toolkit Integration**
  - Use ClaudeSession for AI execution
  - Leverage defensive utilities (parse_llm_json, retry_with_feedback)
  - SessionManager for workflow state persistence

### Module Structure

```
ai_working/dotrunner/
├── workflow.py          # Phase 1 - Data models (existing)
├── state.py             # Phase 2 - State management dataclasses
├── context.py           # Phase 2 - Context interpolation utilities
├── executor.py          # Phase 2 - Node execution with AI
├── engine.py            # Phase 2 - Workflow orchestration
├── examples/
│   ├── simple_linear.yaml                    # Basic 3-node workflow
│   ├── conditional_flow.yaml                 # 6-node with conditionals (Phase 6)
│   └── integration_tests/
│       ├── research_analysis.yaml            # Multi-stage analysis
│       ├── data_pipeline.yaml                # Data transformation
│       ├── content_synthesis.yaml            # Multi-source aggregation
│       └── error_scenarios.yaml              # Error handling validation
└── tests/
    ├── test_state.py                         # State dataclasses
    ├── test_context.py                       # Context interpolation
    ├── test_executor.py                      # Node execution (mocked AI)
    ├── test_engine.py                        # Workflow orchestration
    ├── integration_test_workflows.py         # End-to-end with real/mocked AI
    └── golden/
        ├── simple_linear_result.json
        ├── research_analysis_result.json
        ├── data_pipeline_result.json
        └── content_synthesis_result.json
```

## Module Specifications

### Module: `state.py`

**Purpose**: Define state management data structures

**Location**: `ai_working/dotrunner/state.py`

**Contract**:
- Pure data classes, no behavior
- Immutable where possible
- Type-safe with dataclasses

**Dependencies**: `workflow.py`

**Classes**:

```python
@dataclass
class NodeResult:
    """Result of executing a single node"""
    node_id: str
    status: str  # "success", "failed", "skipped"
    outputs: Dict[str, Any]  # Named outputs extracted
    raw_response: str  # Full AI response
    error: Optional[str] = None
    execution_time: float = 0.0

@dataclass
class WorkflowState:
    """Current state of workflow execution"""
    workflow_id: str
    current_node: Optional[str]
    context: Dict[str, Any]  # Accumulated context
    results: List[NodeResult]  # History of node results
    status: str  # "running", "completed", "failed"

@dataclass
class WorkflowResult:
    """Final result of workflow execution"""
    workflow_id: str
    status: str  # "completed", "failed"
    total_time: float
    node_results: List[NodeResult]
    final_context: Dict[str, Any]
    error: Optional[str] = None
```

---

### Module: `context.py`

**Purpose**: Handle context interpolation and variable resolution

**Location**: `ai_working/dotrunner/context.py`

**Contract**:
- Inputs: Template strings with {variables}, context dict
- Outputs: Interpolated strings
- Errors: `ContextError` for missing variables (custom exception)

**Dependencies**: None (pure functions)

**Functions**:

```python
def interpolate(template: str, context: Dict[str, Any]) -> str:
    """
    Replace {variable} placeholders with context values.

    Args:
        template: String with {var} placeholders
        context: Dict mapping variable names to values

    Returns:
        Interpolated string

    Raises:
        ContextError: If required variable missing

    Examples:
        >>> interpolate("Analyze {file}", {"file": "main.py"})
        "Analyze main.py"

        >>> interpolate("Process {count} items", {"count": 42})
        "Process 42 items"
    """

def extract_variables(template: str) -> Set[str]:
    """
    Extract all {variable} names from template.

    Args:
        template: String with {var} placeholders

    Returns:
        Set of variable names

    Examples:
        >>> extract_variables("Analyze {file} for {pattern}")
        {"file", "pattern"}
    """

def validate_context(template: str, context: Dict[str, Any]) -> List[str]:
    """
    Check if context has all required variables.

    Args:
        template: String with {var} placeholders
        context: Dict with available values

    Returns:
        List of missing variable names (empty if all present)

    Examples:
        >>> validate_context("Use {a} and {b}", {"a": 1})
        ["b"]
    """
```

**Error Handling**:
```python
class ContextError(Exception):
    """Raised when context interpolation fails"""
    def __init__(self, message: str, missing_vars: List[str], template: str):
        super().__init__(message)
        self.missing_vars = missing_vars
        self.template = template
```

---

### Module: `executor.py`

**Purpose**: Execute individual nodes using AI and manage output extraction

**Location**: `ai_working/dotrunner/executor.py`

**Contract**:
- Inputs: Node object, execution context dict
- Outputs: NodeResult with outputs and raw response
- Side Effects: Makes ClaudeSession API calls
- Errors: `NodeExecutionError` for execution failures

**Dependencies**:
- `workflow.py` (Node dataclass)
- `state.py` (NodeResult)
- `context.py` (interpolation)
- `amplifier.ccsdk_toolkit` (ClaudeSession, defensive utilities)

**Class**:

```python
class NodeExecutor:
    """Executes workflow nodes using AI"""

    def __init__(self, session_manager: Optional[SessionManager] = None):
        """
        Initialize executor.

        Args:
            session_manager: Optional SessionManager for persistence
        """
        self.session_mgr = session_manager or SessionManager()

    async def execute(self, node: Node, context: Dict[str, Any]) -> NodeResult:
        """
        Execute a single node.

        Args:
            node: Node to execute
            context: Current workflow context

        Returns:
            NodeResult with outputs and execution details

        Raises:
            NodeExecutionError: If execution fails
        """
        start_time = time.time()

        try:
            # 1. Interpolate prompt
            prompt = self._interpolate_prompt(node.prompt, context)

            # 2. Execute with AI
            response = await self._execute_generic(prompt)

            # 3. Extract outputs
            outputs = self._extract_outputs(response, node.outputs)

            # 4. Create result
            return NodeResult(
                node_id=node.id,
                status="success",
                outputs=outputs,
                raw_response=response,
                execution_time=time.time() - start_time
            )

        except Exception as e:
            return NodeResult(
                node_id=node.id,
                status="failed",
                outputs={},
                raw_response="",
                error=str(e),
                execution_time=time.time() - start_time
            )

    def _interpolate_prompt(self, template: str, context: Dict[str, Any]) -> str:
        """Interpolate context variables into prompt template"""
        from ai_working.dotrunner.context import interpolate
        return interpolate(template, context)

    async def _execute_generic(self, prompt: str) -> str:
        """Execute prompt using ClaudeSession"""
        from amplifier.ccsdk_toolkit import ClaudeSession, SessionOptions
        from amplifier.ccsdk_toolkit.defensive import retry_with_feedback

        options = SessionOptions(
            system_prompt="You are executing a workflow step. Provide clear, structured outputs as requested.",
            timeout_seconds=60
        )

        async with ClaudeSession(options) as session:
            # Use retry_with_feedback for robustness
            response = await retry_with_feedback(
                async_func=session.query,
                prompt=prompt,
                max_retries=3
            )

        return response

    def _extract_outputs(self, response: str, output_names: List[str]) -> Dict[str, Any]:
        """Extract named outputs from AI response"""
        from amplifier.ccsdk_toolkit.defensive import parse_llm_json

        outputs = {}

        # If expecting structured data, try JSON parsing
        if any(keyword in response.lower() for keyword in ["json", "{", "}"]):
            try:
                parsed = parse_llm_json(response)
                if isinstance(parsed, dict):
                    # Extract requested outputs from parsed JSON
                    for name in output_names:
                        if name in parsed:
                            outputs[name] = parsed[name]
                    return outputs
            except Exception:
                pass  # Fall back to pattern matching

        # Pattern-based extraction: look for "name: value" patterns
        import re
        for name in output_names:
            pattern = rf"{name}:\s*(.+?)(?:\n|$)"
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                outputs[name] = match.group(1).strip()

        return outputs
```

---

### Module: `engine.py`

**Purpose**: Orchestrate workflow execution from start to finish

**Location**: `ai_working/dotrunner/engine.py`

**Contract**:
- Inputs: Workflow object from Phase 1
- Outputs: WorkflowResult with complete execution history
- Side Effects: Logs execution progress, makes AI API calls
- Errors: `WorkflowExecutionError` for runtime failures

**Dependencies**:
- `workflow.py` (Workflow, Node)
- `state.py` (WorkflowState, WorkflowResult, NodeResult)
- `executor.py` (NodeExecutor)

**Class**:

```python
class WorkflowEngine:
    """Orchestrates linear workflow execution"""

    def __init__(self, session_manager: Optional[SessionManager] = None):
        """
        Initialize engine.

        Args:
            session_manager: Optional SessionManager for persistence
        """
        self.session_mgr = session_manager or SessionManager()
        self.executor = NodeExecutor(session_manager)
        self.logger = logging.getLogger(__name__)

    async def run(self, workflow: Workflow) -> WorkflowResult:
        """
        Execute workflow from start to finish.

        Args:
            workflow: Workflow to execute

        Returns:
            WorkflowResult with execution details

        Raises:
            WorkflowExecutionError: If execution fails critically
        """
        start_time = time.time()

        # Initialize state
        state = WorkflowState(
            workflow_id=workflow.name,
            current_node=None,
            context=workflow.context.copy(),  # Start with global context
            results=[],
            status="running"
        )

        self.logger.info(f"Starting workflow: {workflow.name}")

        try:
            # Execute nodes sequentially
            while True:
                # Get next node
                next_node = self._get_next_node(workflow, state)
                if not next_node:
                    break  # No more nodes

                self.logger.info(f"Executing node: {next_node.id} ({next_node.name})")

                # Execute node
                result = await self._execute_node(next_node, state)

                # Update state
                state.results.append(result)
                state.current_node = next_node.id

                # Merge outputs into context
                state.context.update(result.outputs)

                # Check for failure
                if result.status == "failed":
                    self.logger.error(f"Node {next_node.id} failed: {result.error}")
                    state.status = "failed"
                    break

            # Mark as completed if we got through all nodes
            if state.status == "running":
                state.status = "completed"

            self.logger.info(f"Workflow {workflow.name} {state.status}")

            return WorkflowResult(
                workflow_id=workflow.name,
                status=state.status,
                total_time=time.time() - start_time,
                node_results=state.results,
                final_context=state.context,
                error=None if state.status == "completed" else "Workflow failed"
            )

        except Exception as e:
            self.logger.exception(f"Workflow execution failed: {e}")
            return WorkflowResult(
                workflow_id=workflow.name,
                status="failed",
                total_time=time.time() - start_time,
                node_results=state.results,
                final_context=state.context,
                error=str(e)
            )

    def _get_next_node(self, workflow: Workflow, state: WorkflowState) -> Optional[Node]:
        """
        Get next node to execute (linear for Phase 2).

        Args:
            workflow: Workflow definition
            state: Current execution state

        Returns:
            Next node or None if done
        """
        # If no current node, return first node
        if not state.current_node:
            return workflow.nodes[0] if workflow.nodes else None

        # Get current node
        current = workflow.get_node(state.current_node)
        if not current:
            return None

        # Linear execution: follow 'next' if it's a string
        if isinstance(current.next, str):
            return workflow.get_node(current.next)

        # No next node or conditional (Phase 6)
        return None

    async def _execute_node(self, node: Node, state: WorkflowState) -> NodeResult:
        """
        Execute a single node.

        Args:
            node: Node to execute
            state: Current workflow state

        Returns:
            NodeResult from execution
        """
        return await self.executor.execute(node, state.context)
```

## Data Flow

```
1. User creates workflow YAML (Phase 1 parsing)
   ↓
2. WorkflowEngine.run(workflow)
   ↓
3. Initialize WorkflowState:
   - workflow_id = workflow.name
   - context = workflow.context (global context)
   - results = []
   - status = "running"
   ↓
4. Loop: For each node in sequence
   a. _get_next_node(workflow, state)
      - First iteration: returns workflow.nodes[0]
      - Subsequent: follows current_node.next
   ↓
   b. NodeExecutor.execute(node, state.context)
      - Interpolate prompt: "Analyze {file}" → "Analyze main.py"
      - Execute via ClaudeSession
      - Extract outputs from response
      - Return NodeResult
   ↓
   c. Update state:
      - Add NodeResult to state.results
      - Merge outputs into state.context
      - Update state.current_node
   ↓
   d. Check status:
      - If node failed: break loop
      - Else: continue to next node
   ↓
5. Return WorkflowResult:
   - status: "completed" or "failed"
   - node_results: all NodeResults
   - final_context: accumulated context
   - total_time: execution duration
```

## Context Flow Example

```python
# Initial state
workflow.context = {"topic": "AI Safety"}

# After Node 1 (extract-thesis)
state.context = {
    "topic": "AI Safety",
    "thesis": "AI systems require robust alignment mechanisms",
    "methodology": "Empirical analysis of failure modes"
}

# After Node 2 (evaluate-evidence)
state.context = {
    "topic": "AI Safety",
    "thesis": "...",
    "methodology": "...",
    "evidence_quality": "Strong empirical support",
    "strengths": "Well-documented failure cases",
    "weaknesses": "Limited long-term data"
}

# After Node 3 (synthesize-critique)
state.context = {
    ... (all previous context) ...,
    "overall_assessment": "Compelling but needs more research",
    "recommendations": "Focus on long-term alignment"
}
```

## Error Handling Strategy

### 1. Context Errors (ContextError)
**When**: Missing variables during interpolation

**Example**:
```python
# Node prompt: "Analyze {file_path}"
# Context: {"topic": "AI"}  # Missing file_path

# Raises ContextError with:
# - message: "Missing context variable: file_path"
# - missing_vars: ["file_path"]
# - template: original prompt
```

**Response**: Fail immediately with clear error message

### 2. Node Execution Errors
**When**: AI call fails, timeout, parsing error

**Example**:
```python
# AI service unavailable
NodeResult(
    node_id="analyze",
    status="failed",
    outputs={},
    error="ClaudeSession timeout after 60s",
    raw_response=""
)
```

**Response**: Mark node as failed, halt workflow, preserve state

### 3. Output Extraction Failures
**When**: Expected outputs not found in response

**Example**:
```python
# Node expects outputs=["analysis", "recommendations"]
# AI response: "Here's my analysis: ..."
# Only "analysis" found

# Result:
outputs = {"analysis": "..."}  # partial extraction
# Log warning but continue
```

**Response**: Extract what's available, log warning, continue

## Testing Strategy

### Unit Tests

#### test_state.py
- Create NodeResult with all fields
- Create WorkflowState with context
- Create WorkflowResult
- Verify dataclass serialization

#### test_context.py
```python
def test_interpolate_single_var():
    result = interpolate("Hello {name}", {"name": "World"})
    assert result == "Hello World"

def test_interpolate_multiple_vars():
    result = interpolate("{a} + {b} = {c}", {"a": 1, "b": 2, "c": 3})
    assert result == "1 + 2 = 3"

def test_interpolate_missing_var_raises():
    with pytest.raises(ContextError) as exc:
        interpolate("Missing {x}", {})
    assert "x" in exc.value.missing_vars

def test_extract_variables():
    vars = extract_variables("Use {a} and {b} for {c}")
    assert vars == {"a", "b", "c"}

def test_validate_context_all_present():
    missing = validate_context("Use {a}", {"a": 1, "b": 2})
    assert missing == []

def test_validate_context_some_missing():
    missing = validate_context("Use {a} and {b}", {"a": 1})
    assert missing == ["b"]
```

#### test_executor.py (Mocked AI)
```python
@pytest.fixture
def mock_session(monkeypatch):
    """Mock ClaudeSession to return controlled responses"""
    async def mock_query(prompt):
        if "analyze" in prompt:
            return "analysis: The code is well-structured"
        return "result: Success"

    # Patch ClaudeSession
    # ... monkeypatch implementation

def test_execute_node_success(mock_session):
    executor = NodeExecutor()
    node = Node(id="test", name="Test", prompt="Analyze {file}", outputs=["analysis"])
    context = {"file": "main.py"}

    result = await executor.execute(node, context)

    assert result.status == "success"
    assert "analysis" in result.outputs
    assert result.execution_time > 0

def test_execute_node_missing_context_fails():
    executor = NodeExecutor()
    node = Node(id="test", name="Test", prompt="Analyze {missing}", outputs=[])
    context = {}

    result = await executor.execute(node, context)

    assert result.status == "failed"
    assert "missing" in result.error.lower()
```

#### test_engine.py
```python
def test_get_next_node_first():
    workflow = Workflow(name="test", description="test", nodes=[
        Node(id="n1", name="First", prompt="test", next="n2"),
        Node(id="n2", name="Second", prompt="test")
    ])
    state = WorkflowState(workflow_id="test", current_node=None, context={}, results=[], status="running")
    engine = WorkflowEngine()

    next_node = engine._get_next_node(workflow, state)
    assert next_node.id == "n1"

def test_get_next_node_follows_chain():
    workflow = Workflow(name="test", description="test", nodes=[
        Node(id="n1", name="First", prompt="test", next="n2"),
        Node(id="n2", name="Second", prompt="test")
    ])
    state = WorkflowState(workflow_id="test", current_node="n1", context={}, results=[], status="running")
    engine = WorkflowEngine()

    next_node = engine._get_next_node(workflow, state)
    assert next_node.id == "n2"
```

### Integration Tests

#### test_integration_workflows.py
```python
@pytest.mark.integration
@pytest.mark.mock_ai
async def test_simple_linear_workflow_mock():
    """Test simple workflow with mocked AI responses"""
    # Load workflow
    workflow = Workflow.from_yaml(Path("examples/simple_linear.yaml"))

    # Mock AI responses
    mock_responses = {
        "analyze": "code_structure: Well organized with clear modules",
        "find-bugs": "bugs_found: No critical bugs detected",
        "summarize": "final_summary: Code is production-ready"
    }

    # Execute with mocked AI
    engine = WorkflowEngine()
    result = await engine.run(workflow)

    # Verify
    assert result.status == "completed"
    assert len(result.node_results) == 3
    assert all(nr.status == "success" for nr in result.node_results)
    assert "final_summary" in result.final_context

@pytest.mark.integration
@pytest.mark.real_ai
@pytest.mark.slow
async def test_simple_linear_workflow_real():
    """Test simple workflow with real AI calls"""
    workflow = Workflow.from_yaml(Path("examples/simple_linear.yaml"))

    # Execute with real AI
    engine = WorkflowEngine()
    result = await engine.run(workflow)

    # Verify basic execution
    assert result.status in ["completed", "failed"]
    assert len(result.node_results) > 0

    # Save as golden file if successful
    if result.status == "completed":
        save_golden("simple_linear_result.json", result)

@pytest.mark.integration
async def test_context_flow_through_nodes():
    """Verify context accumulates correctly"""
    workflow = create_test_workflow([
        Node(id="n1", name="First", prompt="Start", outputs=["a"], next="n2"),
        Node(id="n2", name="Second", prompt="Use {a}", outputs=["b"], next="n3"),
        Node(id="n3", name="Third", prompt="Use {a} and {b}", outputs=["c"])
    ])

    engine = WorkflowEngine()
    result = await engine.run(workflow)

    # Check context accumulation
    assert "a" in result.final_context
    assert "b" in result.final_context
    assert "c" in result.final_context
```

### Golden File Validation

```python
def save_golden(filename: str, result: WorkflowResult):
    """Save result as golden file"""
    golden_path = Path("tests/golden") / filename
    golden_path.parent.mkdir(exist_ok=True)

    with open(golden_path, "w") as f:
        json.dump(asdict(result), f, indent=2)

def assert_golden_match(result: WorkflowResult, golden_file: str):
    """Compare result against golden file"""
    golden_path = Path("tests/golden") / golden_file

    with open(golden_path) as f:
        expected = json.load(f)

    actual = asdict(result)

    # Compare (excluding timing and raw responses)
    assert actual["status"] == expected["status"]
    assert len(actual["node_results"]) == len(expected["node_results"])
    # ... more assertions
```

## Implementation Plan

### Step 1: Create State Data Classes
- Implement state.py with all dataclasses
- Write unit tests for state structures
- Verify serialization works

### Step 2: Implement Context Utilities
- Implement context.py functions
- Write comprehensive unit tests
- Test edge cases (missing vars, empty context)

### Step 3: Implement NodeExecutor (Mocked AI)
- Create executor.py with mocked ClaudeSession
- Test interpolation, execution, output extraction
- Verify error handling

### Step 4: Implement WorkflowEngine
- Create engine.py orchestration logic
- Test with mocked executor
- Verify sequential execution

### Step 5: Integration with ccsdk_toolkit
- Replace mocked AI with real ClaudeSession
- Add retry_with_feedback
- Add parse_llm_json for output extraction
- Test with real API calls

### Step 6: Integration Tests
- Run full workflows end-to-end
- Generate golden files
- Validate context flow

### Step 7: Evidence Collection
- Save test results
- Copy golden files to evidence directory
- Create Phase 2 completion summary

## Success Criteria

- ✅ All unit tests pass (context, executor, engine)
- ✅ Integration tests pass with mocked AI
- ✅ At least 2 integration tests pass with real AI
- ✅ Golden files generated and validated
- ✅ Context flows correctly between nodes
- ✅ Error scenarios handled gracefully
- ✅ Clear, actionable error messages
- ✅ Execution progress visible in logs

## Next Phases

**Phase 3**: Add state persistence and resume capability
**Phase 4**: CLI interface for running workflows
**Phase 5**: Agent integration (specialized agents vs generic)
**Phase 6**: Conditional routing and branching logic
