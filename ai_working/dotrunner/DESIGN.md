# DotRunner: Technical Design

This document provides technical architecture details for implementing DotRunner.

## Architecture Overview

DotRunner follows the **"Code for Structure, AI for Intelligence"** principle:

- **Code** manages workflow orchestration, state persistence, routing logic
- **AI** handles content generation, condition evaluation, agent tasks

### Core Components

```
┌─────────────────────────────────────────────────────┐
│                   CLI Layer                         │
│  (Click commands: run, resume, validate)            │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Workflow Engine                        │
│  - Load workflows                                   │
│  - Manage execution state                           │
│  - Route between nodes                              │
│  - Handle errors/retries                            │
└──────────────┬────────────────┬─────────────────────┘
               │                │
       ┌───────▼─────┐  ┌──────▼─────────┐
       │   Node      │  │   Condition    │
       │  Executor   │  │  Evaluator     │
       │             │  │                │
       │ Delegates   │  │ AI evaluates   │
       │ to agents   │  │ routing logic  │
       └──────┬──────┘  └────────────────┘
              │
       ┌──────▼──────┐
       │   State     │
       │  Manager    │
       │             │
       │ Persists    │
       │ after each  │
       │ node        │
       └─────────────┘
```

## Module Structure

```
ai_working/dotrunner/
├── __init__.py              # Package exports
├── README.md                # User documentation
├── DESIGN.md                # This file
│
├── cli.py                   # Click CLI commands
├── workflow.py              # Workflow & Node data models
├── engine.py                # WorkflowEngine orchestration
├── executor.py              # NodeExecutor for agent delegation
├── evaluator.py             # ConditionEvaluator for routing
├── state.py                 # StateManager for persistence
├── parser.py                # YAML parsing and validation
│
├── examples/                # Example workflow files
│   ├── simple_linear.yaml
│   ├── conditional_flow.yaml
│   └── pr_review.yaml
│
└── tests/                   # Test suite
    ├── test_workflow.py
    ├── test_engine.py
    ├── test_executor.py
    ├── test_evaluator.py
    └── test_state.py
```

## Data Models

### Workflow Definition

```python
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union

@dataclass
class Node:
    """Single workflow node"""
    id: str                              # Unique node identifier
    name: str                            # Human-readable name
    prompt: str                          # Prompt template with {var} interpolation
    agent: str = "auto"                  # Agent to use (default: auto-select)
    outputs: List[str] = field(default_factory=list)  # Named outputs to capture
    next: Optional[Union[str, List[Dict]]] = None     # Next node or conditions
    retry_on_failure: int = 1            # Retry attempts on failure
    type: Optional[str] = None           # "terminal" for end nodes

@dataclass
class Workflow:
    """Complete workflow definition"""
    name: str                            # Workflow identifier
    description: str                     # What this workflow does
    nodes: List[Node]                    # Ordered list of nodes
    context: Dict[str, Any] = field(default_factory=dict)  # Global context

    @classmethod
    def from_yaml(cls, path: Path) -> 'Workflow':
        """Load and validate workflow from YAML"""
        # Parse YAML, validate schema, return Workflow

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID"""
        return next((n for n in self.nodes if n.id == node_id), None)
```

### Execution State

```python
@dataclass
class NodeResult:
    """Result from node execution"""
    node_id: str
    success: bool
    outputs: Dict[str, Any]
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class WorkflowState:
    """Execution state for a workflow run"""
    workflow_name: str
    current_node: Optional[str] = None
    completed_nodes: Set[str] = field(default_factory=set)
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_context(self) -> Dict[str, Any]:
        """Get merged context with all node results"""
        merged = dict(self.context)
        for node_id, result in self.node_results.items():
            merged.update(result.outputs)
        return merged
```

## Component Specifications

### 1. WorkflowEngine (engine.py)

**Purpose**: Orchestrate workflow execution from start to completion.

```python
class WorkflowEngine:
    """Executes workflows node by node with state management"""

    def __init__(self, workflow: Workflow, state_dir: Path):
        self.workflow = workflow
        self.state_mgr = StateManager(state_dir)
        self.executor = NodeExecutor()
        self.evaluator = ConditionEvaluator()

    async def run(self, initial_context: Dict = None, resume: bool = False):
        """Execute workflow from start or resume from saved state"""

        # Load or initialize state
        if resume:
            state = self.state_mgr.load(self.workflow.name)
        else:
            state = WorkflowState(
                workflow_name=self.workflow.name,
                context=initial_context or {}
            )

        # Merge global workflow context
        state.context.update(self.workflow.context)

        # Execute nodes until terminal
        while True:
            # Get next node to execute
            node = self._get_next_node(state)
            if not node:
                break

            # Execute node
            try:
                result = await self._execute_node(node, state)
                state.node_results[node.id] = result
                state.completed_nodes.add(node.id)

            except Exception as e:
                logger.error(f"Node {node.id} failed: {e}")
                if node.retry_on_failure > 1:
                    # TODO: Implement retry logic
                    pass
                raise

            finally:
                # ALWAYS save state after node attempt
                self.state_mgr.save(state)

            # Determine next node
            state.current_node = await self._evaluate_next(node, state)
            self.state_mgr.save(state)

        return state

    def _get_next_node(self, state: WorkflowState) -> Optional[Node]:
        """Get the next node to execute"""
        if state.current_node:
            return self.workflow.get_node(state.current_node)

        # Start from first node
        if self.workflow.nodes:
            return self.workflow.nodes[0]

        return None

    async def _execute_node(self, node: Node, state: WorkflowState) -> NodeResult:
        """Execute a single node"""
        logger.info(f"Executing node: {node.name} ({node.id})")

        # Get merged context
        context = state.get_context()

        # Execute via NodeExecutor
        outputs = await self.executor.execute(node, context)

        return NodeResult(
            node_id=node.id,
            success=True,
            outputs=outputs
        )

    async def _evaluate_next(self, node: Node, state: WorkflowState) -> Optional[str]:
        """Determine next node based on routing logic"""

        # Check if terminal node
        if node.type == "terminal":
            return None

        # Simple next (string)
        if isinstance(node.next, str):
            return node.next

        # Conditional next (list of conditions)
        if isinstance(node.next, list):
            context = state.get_context()
            return await self.evaluator.evaluate(node.next, context)

        # No explicit next - use sequential
        current_idx = self.workflow.nodes.index(node)
        if current_idx + 1 < len(self.workflow.nodes):
            return self.workflow.nodes[current_idx + 1].id

        return None
```

### 2. NodeExecutor (executor.py)

**Purpose**: Execute individual nodes by delegating to agents.

```python
class NodeExecutor:
    """Executes nodes via agent delegation"""

    async def execute(self, node: Node, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute node and return outputs"""

        # Interpolate prompt with context
        prompt = self._interpolate_prompt(node.prompt, context)

        # Delegate to agent
        if node.agent == "auto":
            result = await self._execute_generic(prompt)
        else:
            result = await self._delegate_to_agent(node.agent, prompt)

        # Extract named outputs
        outputs = self._extract_outputs(result, node.outputs)

        return outputs

    def _interpolate_prompt(self, template: str, context: Dict) -> str:
        """Replace {var} with context values"""
        try:
            return template.format(**context)
        except KeyError as e:
            raise ValueError(f"Missing context variable: {e}")

    async def _execute_generic(self, prompt: str) -> str:
        """Execute with generic Claude session"""
        from amplifier.ccsdk_toolkit import ClaudeSession, SessionOptions

        async with ClaudeSession(SessionOptions()) as session:
            response = await session.generate(prompt)
            return response

    async def _delegate_to_agent(self, agent: str, task: str) -> str:
        """Delegate to specific agent via Task tool"""
        # Note: Task tool is synchronous in Claude Code
        # This would need to be adapted for actual usage

        # For now, placeholder showing the pattern
        logger.info(f"Delegating to agent: {agent}")

        # In real implementation, this would use:
        # result = task_tool(subagent_type=agent, prompt=task)

        raise NotImplementedError("Task tool delegation needs integration")

    def _extract_outputs(self, result: str, output_names: List[str]) -> Dict[str, Any]:
        """Extract named outputs from result"""
        if not output_names:
            return {"result": result}

        # Try to parse as JSON first
        from amplifier.ccsdk_toolkit.defensive import parse_llm_json

        try:
            parsed = parse_llm_json(result)
            if isinstance(parsed, dict):
                return {k: v for k, v in parsed.items() if k in output_names}
        except:
            pass

        # Fallback: return full result for each named output
        return {name: result for name in output_names}
```

### 3. ConditionEvaluator (evaluator.py)

**Purpose**: Evaluate routing conditions using AI.

```python
class ConditionEvaluator:
    """Evaluates routing conditions"""

    async def evaluate(self, conditions: List[Dict], context: Dict[str, Any]) -> str:
        """Evaluate conditions and return next node ID"""

        for condition in conditions:
            if "default" in condition:
                # Default case - always matches
                return condition["default"]

            # Evaluate condition
            when_clause = condition.get("when")
            goto_node = condition.get("goto")

            if when_clause and goto_node:
                matches = await self._evaluate_condition(when_clause, context)
                if matches:
                    return goto_node

        # No match and no default - error
        raise ValueError("No matching condition and no default route")

    async def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate a single condition using AI"""

        # Simple evaluation: interpolate and check
        try:
            interpolated = condition.format(**context)
            # This is a simplification - would need proper expression eval
            # For MVP, can use AI to evaluate the condition

            prompt = f"""Evaluate this condition as true or false:

Condition: {interpolated}

Context: {json.dumps(context, indent=2)}

Return ONLY 'true' or 'false'."""

            from amplifier.ccsdk_toolkit import ClaudeSession, SessionOptions

            async with ClaudeSession(SessionOptions()) as session:
                response = await session.generate(prompt)
                return response.strip().lower() == "true"

        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            return False
```

### 4. StateManager (state.py)

**Purpose**: Persist and restore workflow execution state.

```python
class StateManager:
    """Manages workflow execution state persistence"""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)

    def save(self, state: WorkflowState):
        """Save state to disk (atomic write)"""
        from amplifier.utils.file_io import write_json

        run_dir = self.state_dir / state.workflow_name
        run_dir.mkdir(parents=True, exist_ok=True)

        state_file = run_dir / "state.json"

        # Update timestamp
        state.updated_at = datetime.now().isoformat()

        # Save state
        write_json(asdict(state), state_file)

        logger.info(f"State saved: {state_file}")

    def load(self, workflow_name: str) -> WorkflowState:
        """Load state from disk"""
        state_file = self.state_dir / workflow_name / "state.json"

        if not state_file.exists():
            raise FileNotFoundError(f"No saved state for workflow: {workflow_name}")

        with open(state_file) as f:
            data = json.load(f)

        # Reconstruct state object
        return WorkflowState(**data)

    def exists(self, workflow_name: str) -> bool:
        """Check if saved state exists"""
        return (self.state_dir / workflow_name / "state.json").exists()
```

## Implementation Phases

### Phase 1: MVP (Linear Workflows)

**Goal**: Basic working system with linear workflows

**Features**:
- YAML parsing and validation
- Linear workflow execution (no branching)
- State persistence and resume
- Basic agent delegation
- Context interpolation
- CLI commands (run, resume)

**Tests**:
- test_workflow_parsing.py
- test_linear_execution.py
- test_state_persistence.py
- test_context_interpolation.py
- test_cli_commands.py

### Phase 2: Conditional Routing

**Goal**: Add branching and loops

**Features**:
- Conditional next nodes
- AI-driven condition evaluation
- Loop support (with max iterations)
- Retry logic for failures

**Tests**:
- test_conditional_routing.py
- test_condition_evaluation.py
- test_loop_execution.py
- test_retry_logic.py

### Phase 3: Advanced Features

**Goal**: Production-ready enhancements

**Features**:
- Parallel node execution
- Sub-workflows
- Dynamic node generation
- Progress visualization
- Workflow templates
- Comprehensive error recovery

## Integration Points

### With Claude Code SDK (ccsdk_toolkit)

```python
# Session management for AI operations
from amplifier.ccsdk_toolkit import SessionManager, ClaudeSession, SessionOptions

# Defensive LLM response parsing
from amplifier.ccsdk_toolkit.defensive import parse_llm_json, retry_with_feedback

# File I/O with retry logic
from amplifier.utils.file_io import write_json, read_json
```

### With Amplifier Agent Ecosystem

Delegation to agents via Claude Code's Task tool:
- zen-architect
- bug-hunter
- test-coverage
- security-guardian
- modular-builder
- etc.

## Testing Strategy

### Unit Tests (60%)

- Workflow parsing and validation
- Node execution logic
- Condition evaluation
- State persistence
- Context interpolation

### Integration Tests (30%)

- End-to-end workflow execution
- Agent delegation
- State recovery after interruption
- Error handling and retries

### End-to-End Tests (10%)

- Real workflows with multiple agents
- Complex conditional routing
- Long-running workflows with resume
- Error scenarios and recovery

## Error Handling

### Node Execution Failures

1. Log error details
2. Save state with error info
3. Retry if configured (retry_on_failure)
4. If all retries exhausted, halt and report

### Workflow Validation Errors

1. Validate YAML syntax
2. Check required fields
3. Validate node references
4. Check for circular dependencies
5. Report clear error messages

### Recovery Patterns

1. **Interruption**: State saved after every node → resume from exact point
2. **API Failure**: Retry with exponential backoff
3. **Agent Unavailable**: Clear error message, suggest alternatives
4. **Invalid Context**: Report missing variables before execution

## Performance Considerations

### State Persistence

- Write after EVERY successful node (not batched)
- Use atomic writes (write temp file, then rename)
- Fixed filenames (not timestamps) for resume

### Memory Management

- Stream large results to disk (don't hold in memory)
- Clear completed node data after saving
- Limit context size to prevent bloat

### Parallel Execution (Phase 3)

- Identify independent nodes (no data dependencies)
- Execute in parallel with asyncio
- Merge results back to main state

## Security Considerations

### YAML Parsing

- Use safe YAML loader (no code execution)
- Validate all fields and types
- Limit file size (prevent DOS)

### Context Variables

- Sanitize environment variable expansion
- Don't log sensitive data
- Validate variable names (no code injection)

### Agent Delegation

- Trust amplifier's agent security model
- Don't expose internal state to agents
- Validate agent names against whitelist

## Future Enhancements

### Workflow Templates

```yaml
# Define reusable workflow components
templates:
  code-review:
    nodes:
      - id: analyze
        agent: zen-architect
        prompt: "Analyze {file}"
      - id: summarize
        prompt: "Summarize {analysis}"

# Use in workflows
workflow:
  name: "my-review"
  uses: code-review
  with:
    file: "app.py"
```

### Sub-Workflows

```yaml
nodes:
  - id: "run-sub-workflow"
    type: "workflow"
    workflow: "another_workflow.yaml"
    inputs:
      context: "{previous_results}"
```

### Dynamic Node Generation

```yaml
nodes:
  - id: "generate-nodes"
    prompt: "Generate 5 analysis tasks for {topic}"
    outputs:
      - generated_nodes
    dynamic: true  # Creates nodes at runtime
```

## References

- [Blog Writer](../blog_writer/) - Similar multi-stage pipeline pattern
- [CCSDK Toolkit](../../amplifier/ccsdk_toolkit/) - Session management and defensive utilities
- [Amplifier Philosophy](../../ai_context/IMPLEMENTATION_PHILOSOPHY.md) - Design principles
- [Modular Design](../../ai_context/MODULAR_DESIGN_PHILOSOPHY.md) - Modularity approach
