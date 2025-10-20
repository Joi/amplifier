# DotRunner Implementation Specification

**Status**: AUTHORITATIVE - Implementation must match this specification
**Version**: 1.0
**Last Updated**: 2025-01-20

See `/workspaces/amplifier/ai_working/dotrunner/ARCHITECTURE_DECISIONS.md` for design rationale.

## Overview

This document specifies the internal implementation details of DotRunner, focusing on how components interact to execute workflows reliably.

**Key Decisions**:
- Task tool backend is default (subprocess for parallel Phase 2)
- State directory: `.dotrunner/sessions/`
- Expression evaluation via `ast.literal_eval`
- Atomic writes for crash safety
- Sub-workflows run in isolated context (Phase 2)

## Core Components

### 1. Agent Invocation System

#### Task Tool Backend (Default)

The primary agent invocation method uses the Claude Code SDK Task tool for seamless integration:

```python
async def invoke_agent_task(node: Node, context: dict) -> dict:
    """Invoke agent using Task tool backend."""

    # Resolve prompt with context variables
    prompt = interpolate_template(node.prompt, context)

    # Execute via Task tool
    response = await task_tool.execute(
        agent_name=node.agent,
        mode=node.agent_mode,  # Can be enum or natural language
        prompt=prompt
    )

    # Parse response and extract outputs
    return parse_agent_response(response, node.outputs)
```

#### Subprocess Backend (Isolation Option)

For cases requiring process isolation:

```python
def invoke_agent_subprocess(node: Node, context: dict) -> dict:
    """Invoke agent in isolated subprocess."""

    prompt = interpolate_template(node.prompt, context)

    # Prepare command
    cmd = ["amplifier", "agent", node.agent]
    if node.agent_mode:
        cmd.extend(["--mode", node.agent_mode])

    # Execute subprocess
    input_data = json.dumps({
        "prompt": prompt,
        "mode": node.agent_mode
    })

    result = subprocess.run(
        cmd,
        input=input_data,
        capture_output=True,
        text=True,
        timeout=300  # 5-minute timeout
    )

    if result.returncode != 0:
        raise NodeExecutionError(f"Agent {node.agent} failed")

    return parse_agent_response(result.stdout, node.outputs)
```

### 2. Sub-Workflow Execution

Sub-workflows are first-class citizens, executed recursively:

```python
class WorkflowExecutor:
    """Handles both primary and sub-workflow execution."""

    async def execute_workflow_node(self, node: Node, context: dict) -> dict:
        """Execute a sub-workflow node."""

        # Load sub-workflow
        sub_workflow = Workflow.from_yaml(Path(node.workflow))

        # Map inputs from parent context
        sub_context = {}
        for key, value in node.inputs.items():
            sub_context[key] = interpolate_template(value, context)

        # Execute sub-workflow with isolated context
        sub_engine = WorkflowEngine(
            state_dir=self.state_dir / "sub_workflows" / node.id,
            agent_backend=self.agent_backend
        )

        result = await sub_engine.run(
            workflow=sub_workflow,
            initial_context=sub_context
        )

        # Extract specified outputs back to parent
        outputs = {}
        for output_name in node.outputs:
            if output_name in result:
                outputs[output_name] = result[output_name]

        return outputs
```

### 3. Expression Evaluator

Safe expression evaluation using `ast.literal_eval` with custom visitor:

```python
import ast
import operator

class SafeExpressionEvaluator:
    """Safely evaluate routing expressions."""

    # Allowed operators
    OPERATORS = {
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.And: operator.and_,
        ast.Or: operator.or_,
    }

    def evaluate(self, expression: str, context: dict) -> bool:
        """
        Evaluate expression safely with context.

        Supports:
        - Comparisons: >, >=, <, <=, ==, !=
        - Logical: and, or
        - Variables from context
        - Literals: numbers, strings, booleans

        Examples:
            "count > 10"
            "status == 'ready' and count > 5"
            "test_passed or coverage >= 0.8"
        """
        try:
            # Parse expression into AST
            tree = ast.parse(expression, mode='eval')

            # Evaluate with context
            return self._eval_node(tree.body, context)

        except Exception as e:
            raise ValueError(f"Invalid expression: {expression}") from e

    def _eval_node(self, node, context):
        """Recursively evaluate AST node."""

        if isinstance(node, ast.Compare):
            # Handle comparisons
            left = self._eval_node(node.left, context)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context)
                if not self.OPERATORS[type(op)](left, right):
                    return False
                left = right
            return True

        elif isinstance(node, ast.BoolOp):
            # Handle and/or
            op = self.OPERATORS[type(node.op)]
            values = [self._eval_node(n, context) for n in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            else:  # Or
                return any(values)

        elif isinstance(node, ast.Name):
            # Variable lookup
            return context.get(node.id)

        elif isinstance(node, ast.Constant):
            # Literal value
            return node.value

        elif isinstance(node, ast.Call):
            # Handle len() function
            if node.func.id == "len":
                arg = self._eval_node(node.args[0], context)
                return len(arg) if arg else 0

        else:
            raise ValueError(f"Unsupported expression type: {type(node)}")
```

### 4. State Persistence

Atomic state saving with crash recovery:

```python
class StatePersistence:
    """Manages workflow state persistence."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, session_id: str, state: WorkflowState):
        """
        Save state atomically to prevent corruption.

        Process:
        1. Write to temp file
        2. Sync to disk
        3. Atomic rename to final location
        """
        session_dir = self.state_dir / session_id
        session_dir.mkdir(exist_ok=True)

        # State file
        state_file = session_dir / "state.json"
        temp_file = session_dir / f"state.{uuid4()}.tmp"

        # Write to temp file
        with open(temp_file, 'w') as f:
            json.dump(asdict(state), f, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Atomic rename
        temp_file.replace(state_file)

        # Save metadata
        self._save_metadata(session_id, state)

        # Save trace entry
        self._append_trace(session_id, state)

    def load_state(self, session_id: str) -> WorkflowState:
        """Load state from disk."""
        state_file = self.state_dir / session_id / "state.json"

        if not state_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        with open(state_file) as f:
            data = json.load(f)

        return WorkflowState(**data)

    def _save_metadata(self, session_id: str, state: WorkflowState):
        """Save session metadata for listing/status."""
        metadata = {
            "session_id": session_id,
            "workflow_name": state.workflow_id,
            "status": state.status,
            "started_at": state.started_at,
            "updated_at": datetime.now().isoformat(),
            "current_node": state.current_node,
            "nodes_completed": len([r for r in state.results if r.status == "success"]),
            "nodes_total": len(state.all_nodes)
        }

        metadata_file = self.state_dir / session_id / "metadata.json"
        temp_file = self.state_dir / session_id / f"metadata.{uuid4()}.tmp"

        with open(temp_file, 'w') as f:
            json.dump(metadata, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        temp_file.replace(metadata_file)

    def _append_trace(self, session_id: str, state: WorkflowState):
        """Append to execution trace (JSONL format)."""
        trace_file = self.state_dir / session_id / "trace.jsonl"

        trace_entry = {
            "timestamp": datetime.now().isoformat(),
            "node": state.current_node,
            "status": state.status,
            "context_size": len(state.context),
            "results_count": len(state.results)
        }

        with open(trace_file, 'a') as f:
            f.write(json.dumps(trace_entry) + "\n")
```

### 5. Context Management

Context accumulation and variable resolution:

```python
class ContextManager:
    """Manages workflow context and variable interpolation."""

    def __init__(self):
        self.context = {}
        self.node_outputs = {}  # Track outputs by node ID

    def update_context(self, node_id: str, outputs: dict):
        """Update context with node outputs."""

        # Store by node ID for qualified references
        self.node_outputs[node_id] = outputs

        # Also store in flat context for simple references
        self.context.update(outputs)

    def interpolate_template(self, template: str, additional_context: dict = None) -> str:
        """
        Replace {variable} patterns with values.

        Resolution order:
        1. Additional context (if provided)
        2. Node-qualified reference: {node_id.output_name}
        3. Most recent value: {output_name}
        4. System variables: {_session_id}, {_timestamp}
        """
        import re
        from datetime import datetime

        # Build resolution context
        resolution_context = {
            "_timestamp": datetime.now().isoformat(),
            "_session_id": self.session_id,
            **self.context
        }

        if additional_context:
            resolution_context.update(additional_context)

        # Find all {variable} patterns
        pattern = r'\{([^}]+)\}'

        def replace_var(match):
            var_name = match.group(1)

            # Check for node-qualified reference
            if '.' in var_name:
                node_id, output_name = var_name.split('.', 1)
                if node_id in self.node_outputs:
                    value = self.node_outputs[node_id].get(output_name, match.group(0))
                else:
                    value = match.group(0)  # Keep original if not found
            else:
                # Simple variable lookup
                value = resolution_context.get(var_name, match.group(0))

            return str(value)

        return re.sub(pattern, replace_var, template)

    def validate_requirements(self, template: str) -> list[str]:
        """Check if all required variables are available."""
        import re

        pattern = r'\{([^}]+)\}'
        required = set(re.findall(pattern, template))

        missing = []
        for var in required:
            if var.startswith('_'):
                continue  # System variables always available

            if '.' in var:
                node_id, output_name = var.split('.', 1)
                if node_id not in self.node_outputs:
                    missing.append(var)
            elif var not in self.context:
                missing.append(var)

        return missing
```

### 6. Routing Engine

Determines next node based on outputs and routing configuration:

```python
class RoutingEngine:
    """Handles node routing decisions."""

    def __init__(self, evaluator: SafeExpressionEvaluator):
        self.evaluator = evaluator

    def determine_next_node(self, node: Node, outputs: dict) -> str | None:
        """
        Determine next node based on routing configuration.

        Returns:
            Node ID to execute next, or None if terminal
        """

        # Terminal node
        if not node.next:
            return None

        # Simple string reference (linear flow)
        if isinstance(node.next, str):
            return node.next

        # Dict-based routing (simple)
        if isinstance(node.next, dict):
            return self._route_simple(node.next, outputs)

        # List-based routing (complex expressions)
        if isinstance(node.next, list):
            return self._route_complex(node.next, outputs)

        raise RoutingError(f"Invalid routing config for node {node.id}")

    def _route_simple(self, routes: dict, outputs: dict) -> str | None:
        """
        Simple dict-based routing.

        Match first output value to route keys.
        """
        # Get first output value (if any)
        if not outputs:
            return routes.get("default")

        first_key = next(iter(outputs))
        first_value = str(outputs[first_key]).lower()

        # Try to match value
        for route_key, node_id in routes.items():
            if route_key.lower() == first_value:
                return node_id

        # Fall back to default
        return routes.get("default")

    def _route_complex(self, routes: list, outputs: dict) -> str | None:
        """
        Complex expression-based routing.

        Evaluate conditions in order.
        """
        for route in routes:
            if "when" in route:
                # Evaluate condition
                if self.evaluator.evaluate(route["when"], outputs):
                    return route["goto"]
            elif "default" in route:
                # Default fallback
                return route

        # No match and no default
        raise RoutingError(f"No routing condition matched and no default provided")
```

### 7. Workflow Composition

How workflows invoke other workflows:

```python
class WorkflowComposer:
    """Manages workflow composition and sub-workflow calls."""

    def __init__(self, root_dir: Path = Path(".")):
        self.root_dir = root_dir
        self.workflow_cache = {}

    def load_workflow(self, path: str) -> Workflow:
        """Load workflow from file with caching."""

        # Resolve relative paths
        workflow_path = self.root_dir / path

        # Check cache
        if workflow_path in self.workflow_cache:
            return self.workflow_cache[workflow_path]

        # Load and cache
        workflow = Workflow.from_yaml(workflow_path)
        self.workflow_cache[workflow_path] = workflow

        return workflow

    def create_sub_context(self, parent_context: dict, input_mapping: dict) -> dict:
        """Create isolated context for sub-workflow."""

        sub_context = {}
        context_manager = ContextManager()
        context_manager.context = parent_context

        for key, template in input_mapping.items():
            # Resolve template from parent context
            value = context_manager.interpolate_template(template)
            sub_context[key] = value

        return sub_context

    def merge_outputs(self, parent_context: dict, sub_outputs: dict,
                     output_mapping: list[str]) -> dict:
        """Merge sub-workflow outputs back to parent."""

        merged = parent_context.copy()

        for output_name in output_mapping:
            if output_name in sub_outputs:
                merged[output_name] = sub_outputs[output_name]

        return merged
```

## Execution Flow

### Complete Workflow Execution

```python
async def execute_workflow(workflow: Workflow, initial_context: dict = None) -> dict:
    """
    Complete workflow execution flow.

    1. Initialize state and context
    2. Get entry node
    3. Execute nodes sequentially
    4. Handle routing decisions
    5. Save state after each node
    6. Return final context
    """

    # Initialize
    engine = WorkflowEngine()
    state = WorkflowState(
        workflow_id=workflow.name,
        context=initial_context or {},
        status="running"
    )

    # Generate session ID
    session_id = f"{workflow.name}_{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}"

    # Save initial state
    engine.persistence.save_state(session_id, state)

    # Execute nodes
    current_node_id = workflow.nodes[0].id  # Start with first node

    while current_node_id:
        # Load node
        node = workflow.get_node(current_node_id)
        if not node:
            raise ValueError(f"Node {current_node_id} not found")

        state.current_node = current_node_id

        try:
            # Execute based on node type
            if node.agent:
                # Agent node
                outputs = await engine.execute_agent_node(node, state.context)
            elif node.workflow:
                # Sub-workflow node
                outputs = await engine.execute_workflow_node(node, state.context)
            else:
                raise ValueError(f"Node {node.id} has no agent or workflow")

            # Update context
            state.context.update(outputs)

            # Record result
            result = NodeResult(
                node_id=node.id,
                status="success",
                outputs=outputs
            )
            state.results.append(result)

            # Determine next node
            current_node_id = engine.routing.determine_next_node(node, outputs)

        except Exception as e:
            # Handle failure
            result = NodeResult(
                node_id=node.id,
                status="failed",
                error=str(e)
            )
            state.results.append(result)
            state.status = "failed"

            # Save final state
            engine.persistence.save_state(session_id, state)

            raise

        # Save checkpoint
        engine.persistence.save_state(session_id, state)

    # Workflow complete
    state.status = "completed"
    engine.persistence.save_state(session_id, state)

    return state.context
```

## Phase 2 Features (Document Now, Implement Later)

### Parallel Node Execution

**Status**: Phase 2 - Document in spec now, implement later

Nodes can execute work in parallel using `type: "parallel"` and `for_each`:

```yaml
- id: "parallel-tests"
  name: "Run All Tests"
  type: "parallel"
  agent: "test-runner"
  for_each: "{test_files}"
  prompt: "Run tests for {item}"
  wait_for: "all"  # all, any, majority
  outputs:
    - test_results
```

### Sub-Workflow Composition

**Status**: Phase 2 - Document in spec now, implement later

Workflows can invoke other workflows as nodes:

```yaml
- id: "quality-gate"
  name: "Quality Checks"
  workflow: "quality_checks.yaml"
  inputs:
    code: "{implementation}"
  outputs:
    - quality_score
```

### Internal Node Parallelism

While the workflow graph remains deterministic (DAG), individual nodes can spawn parallel work internally:

```python
class ParallelNodeExecutor:
    """
    Executes parallel work within a single node.

    Note: This is internal to the node - the graph itself remains sequential.
    """

    async def execute_parallel_tests(self, test_files: list[Path]) -> dict:
        """
        Example: Run 100 tests in parallel, wait for all.

        This happens INSIDE a single node execution.
        """

        async def run_test(file: Path) -> dict:
            # Run individual test
            result = await subprocess_async(["pytest", str(file)])
            return {
                "file": str(file),
                "passed": result.returncode == 0,
                "output": result.stdout
            }

        # Spawn all tests in parallel
        tasks = [run_test(f) for f in test_files]
        results = await asyncio.gather(*tasks)

        # Aggregate results
        all_passed = all(r["passed"] for r in results)
        failed_tests = [r["file"] for r in results if not r["passed"]]

        return {
            "all_passed": all_passed,
            "test_count": len(results),
            "failed_tests": failed_tests,
            "results": results
        }
```

This maintains graph determinism while allowing efficient parallel execution within nodes.