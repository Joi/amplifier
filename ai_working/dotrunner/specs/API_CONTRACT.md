# DotRunner API Contract Specification

**Status**: AUTHORITATIVE - Implementation must match this specification
**Version**: 1.0
**Last Updated**: 2025-01-20

See `/workspaces/amplifier/ai_working/dotrunner/ARCHITECTURE_DECISIONS.md` for design rationale.

## Overview

DotRunner is a declarative workflow orchestration system for AI agents. It enables:
- Composable workflows (agents and sub-workflows as nodes)
- Conditional routing with state evaluation
- Parallel execution patterns (Phase 2)
- Dynamic workflow generation
- Evidence-based coding with isolated steps

## YAML Workflow Schema

### Workflow Definition

```yaml
name: string                    # Workflow name
description: string             # Human-readable description
version: string                 # Semantic version (e.g., "1.0.0")
nodes: [Node]                   # List of workflow nodes
```

### Node Definition

A node can be either an **Agent Node** or a **Workflow Node** (sub-workflow invocation).

#### Common Node Properties

```yaml
id: string                      # Unique node identifier
description: string             # Node purpose description (optional)
inputs: dict[str, any]          # Input parameters (can reference context)
outputs: [string]               # List of output variable names
next: RouteConfig               # Routing configuration (see below)
```

#### Agent Node (additional properties)

```yaml
agent: string                   # Agent name (e.g., "zen-architect", "bug-hunter")
agent_mode: string | enum       # Flexible mode: enum ("ANALYZE") or natural language
prompt: string                  # The prompt/task for the agent
```

#### Workflow Node (additional properties)

```yaml
workflow: string                # Path to sub-workflow YAML file
```

### Routing Configuration

DotRunner supports two routing formats:

#### Simple String Routing

Direct reference to next node:

```yaml
next: "node-id"
```

#### Conditional Dict-based Routing

Routes based on the node's first output value:

```yaml
next:
  pass: "deploy"                # If first output value == "pass", goto "deploy"
  fail: "fix-tests"             # If first output value == "fail", goto "fix-tests"
  default: "investigate"        # Fallback if no match (optional)
```

**How it works:**
1. Engine gets the first output name from node's `outputs` list
2. Looks up that output's value in the context (e.g., "pass", "fail")
3. Matches value (case-insensitive) against routing keys
4. Routes to corresponding node, or uses `default` if no match

### Complete Example

```yaml
name: "evidence-based-development"
description: "Reliable coding with evidence verification"
version: "1.0.0"

nodes:
  - id: "implement"
    agent: "modular-builder"
    agent_mode: "BUILD"
    prompt: "Implement feature: {feature_description}"
    inputs:
      feature_description: "{user_request}"
    outputs:
      - implementation
      - files_changed
    next:
      success: "verify-evidence"
      error: "debug"

  - id: "verify-evidence"
    workflow: "quality_checks.yaml"
    inputs:
      code: "{implementation}"
      changed_files: "{files_changed}"
    outputs:
      - quality_status  # Returns "excellent", "good", or "needs-work"
    next:
      excellent: "deploy"
      good: "improve"
      default: "refactor"

  - id: "deploy"
    agent: "deployment-specialist"
    agent_mode: "Execute deployment with verification"
    prompt: "Deploy {implementation} to staging"
    inputs:
      implementation: "{implementation}"
    outputs:
      - deployment_status
```

## Python API

### Core Classes

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union
from enum import Enum

class AgentMode(str, Enum):
    """Standard agent execution modes."""
    ANALYZE = "ANALYZE"
    EVALUATE = "EVALUATE"
    EXECUTE = "EXECUTE"
    REVIEW = "REVIEW"
    GENERATE = "GENERATE"

@dataclass
class Node:
    """Represents a workflow node (agent or sub-workflow)."""

    # Required fields
    id: str                              # Unique node identifier
    name: str                            # Human-readable name
    prompt: str = ""                     # Prompt template (or empty for workflow nodes)

    # Optional fields with defaults
    description: str | None = None       # Node purpose description
    inputs: dict[str, Any] = field(default_factory=dict)  # Input parameter mapping
    agent: str | None = None             # Agent to use (e.g., "zen-architect")
    agent_mode: str | None = None        # Mode: AgentMode enum or natural language string
    workflow: str | None = None          # Path to sub-workflow YAML (for workflow nodes)
    outputs: list[str] = field(default_factory=list)  # Named outputs to capture
    next: Union[str, dict[str, str], list[dict[str, str]]] | None = None  # Routing config
    retry_on_failure: int = 1            # Number of retry attempts
    type: str | None = None              # "terminal" to mark end nodes

@dataclass
class Workflow:
    """Represents a complete workflow."""

    name: str                            # Workflow identifier
    description: str                     # What this workflow does
    nodes: list[Node]                    # Ordered list of nodes
    version: str = "1.0.0"               # Semantic version
    context: dict[str, Any] = field(default_factory=dict)  # Global context

    def get_node(self, node_id: str) -> Node | None:
        """Get node by ID, returns None if not found."""
        return next((n for n in self.nodes if n.id == node_id), None)

    def validate(self) -> list[str]:
        """Validate workflow structure, return list of errors (empty if valid)."""
        # Validates: at least one node, unique IDs, valid references, no cycles
        ...

    @classmethod
    def from_yaml(cls, path: Path) -> "Workflow":
        """Load workflow from YAML file."""
        ...

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        ...

class WorkflowEngine:
    """Executes workflows with state management."""

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        save_checkpoints: bool = True
    ):
        """
        Initialize engine.

        Args:
            session_manager: Optional session manager for Claude Code integration
            save_checkpoints: Whether to save state after each node (default: True)
        """
        self.session_mgr = session_manager or SessionManager()
        self.executor = NodeExecutor(session_manager)
        self.save_checkpoints = save_checkpoints
        self.session_id = None

    async def run(
        self,
        workflow: Workflow,
        session_id: str | None = None
    ) -> WorkflowResult:
        """
        Execute workflow with optional resume from session_id.

        Returns:
            WorkflowResult with status, timing, node results, final context
        """
        ...

@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    workflow_id: str
    status: str                          # "completed", "failed", or "running"
    total_time: float                    # Execution time in seconds
    node_results: list[NodeResult]       # Results from each node
    final_context: dict[str, Any]        # Final context state
    error: str | None                    # Error message if failed
    execution_path: list[str]            # Ordered list of executed node IDs

@dataclass
class NodeResult:
    """Result of single node execution."""
    node_id: str
    status: str                          # "success" or "failed"
    outputs: dict[str, Any]              # Captured outputs
    raw_response: str                    # Full agent/AI response
    error: str | None = None             # Error message if failed
    execution_time: float = 0.0          # Node execution time

class SafeExpressionEvaluator:
    """Safe expression evaluation for routing conditions."""

    def evaluate(self, expression: str, context: dict[str, Any]) -> bool:
        """
        Safely evaluate routing expressions using ast.literal_eval.
        Supports: comparisons (>, <, ==, !=), and/or, len() function.
        """
        ...
```

### Helper Functions

```python
from ai_working.dotrunner.persistence import (
    save_state, load_state,
    list_sessions, delete_session,
    save_workflow, load_workflow
)

# State management
session_id = save_state(state, session_id=None)  # Returns generated or provided ID
state = load_state(session_id)                    # Raises FileNotFoundError if missing
sessions = list_sessions()                        # Returns list[SessionInfo]
delete_session(session_id)                        # Removes session directory

# Workflow persistence
save_workflow(workflow, session_id)               # Save workflow definition with session
workflow = load_workflow(session_id)              # Load workflow from session
```

## CLI Commands

### Run Workflow

```bash
# Basic execution
dotrunner run workflow.yaml

# With context override (JSON string)
dotrunner run workflow.yaml --context '{"feature": "user authentication"}'

# Without saving checkpoints
dotrunner run workflow.yaml --no-save
```

### Resume Session

```bash
# Resume interrupted workflow
dotrunner resume <session-id>

# Example
dotrunner resume my_workflow_20250119_143022_a3f2
```

### List Sessions

```bash
# List active sessions (non-completed)
dotrunner list

# List all sessions including completed
dotrunner list --all
```

### Get Session Status

```bash
# Show session details
dotrunner status <session-id>

# Output as JSON
dotrunner status <session-id> --json
```

## File System Structure

```
.dotrunner/
└── sessions/               # Workflow execution state
    └── <session-id>/
        ├── state.json      # Current execution state (WorkflowState dataclass)
        ├── metadata.json   # Session metadata (status, timestamps, progress)
        └── workflow.yaml   # Saved workflow definition (for resumption)
```

### Session Directory Naming

Session IDs follow the pattern: `{workflow_name}_{timestamp}_{uuid}`

Example: `evidence_based_dev_20250119_143022_a3f2b1c7`

### state.json Format

```json
{
  "workflow_id": "evidence-based-development",
  "current_node": "verify-evidence",
  "status": "running",
  "context": {
    "user_request": "implement auth",
    "implementation": "...",
    "files_changed": ["auth.py"]
  },
  "results": [
    {
      "node_id": "implement",
      "status": "success",
      "execution_time": 12.5,
      "outputs": {"implementation": "...", "files_changed": ["auth.py"]},
      "error": null
    }
  ]
}
```

### metadata.json Format

```json
{
  "session_id": "evidence_based_dev_20250119_143022_a3f2b1c7",
  "workflow_name": "evidence-based-development",
  "status": "running",
  "started_at": "2025-01-19T14:30:22.123456Z",
  "updated_at": "2025-01-19T14:30:45.789012Z",
  "nodes_completed": 1,
  "nodes_total": 3
}
```

## Context Variable Reference

Variables in prompts and inputs are referenced using `{variable_name}` syntax.

### Basic Variable Interpolation

```python
# Template with variables
prompt = "Implement feature: {feature_description}"

# Context provides values
context = {"feature_description": "user authentication"}

# Result after interpolation
# "Implement feature: user authentication"
```

### Variable Sources

Variables can come from:

1. **Workflow context** - Global variables defined in workflow YAML
2. **Node outputs** - Values captured from previous node executions
3. **User input** - Context overrides passed via `--context` flag

### Variable Resolution

The context interpolation system:

- Extracts all `{variable}` patterns from templates
- Validates all required variables are present in context
- Performs string substitution to replace patterns with values
- Raises `ContextError` if variables are missing

### Examples

```yaml
workflow:
  name: "feature-implementation"
  description: "Build new features"
  context:
    project: "myapp"

nodes:
  - id: "design"
    agent: "zen-architect"
    prompt: "Design {feature} for {project}"
    inputs:
      feature: "{user_request}"  # From initial context
      project: "{project}"        # From workflow context
    outputs:
      - design_doc

  - id: "implement"
    agent: "modular-builder"
    prompt: "Implement: {design_doc}"  # From previous node output
    outputs:
      - implementation
```

## Agent Integration

DotRunner integrates with specialized AI agents for workflow execution. Nodes can execute using:

1. **Generic AI execution** - Direct Claude interaction via ClaudeSession
2. **Specialized agent execution** - Subprocess invocation of `amplifier agent` CLI

### Generic Execution (No Agent Specified)

When a node doesn't specify an agent, DotRunner uses ClaudeSession directly:

```python
async def _execute_generic(self, prompt: str, output_names: list[str]) -> str:
    """Execute prompt using ClaudeSession with retry"""
    system_prompt = "You are executing a workflow step..."

    # Add output format guidance if outputs are expected
    if output_names:
        system_prompt += "\n\nIMPORTANT: Your response MUST include these outputs..."

    options = SessionOptions(
        system_prompt=system_prompt,
        timeout_seconds=60,
    )

    async with ClaudeSession(options) as session:
        response = await retry_with_feedback(
            func=session.query,
            prompt=prompt,
            max_retries=3
        )

    return response.content
```

### Agent Execution (Agent Specified)

When a node specifies an agent, DotRunner invokes it via subprocess:

```python
async def _execute_with_agent(self, node: Node, prompt: str) -> str:
    """Execute using specified agent via subprocess"""

    # Write prompt to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(prompt)
        prompt_file = f.name

    # Build command
    cmd = ["amplifier", "agent", node.agent]
    if node.agent_mode:
        cmd.extend(["--mode", node.agent_mode])
    cmd.extend(["--prompt-file", prompt_file])
    cmd.append("--json")

    # Execute agent with timeout
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300  # 5 minutes
    )

    if result.returncode != 0:
        raise RuntimeError(f"Agent {node.agent} failed: {result.stderr}")

    return result.stdout.strip()
```

### Agent Modes

Agents can be invoked with optional modes (enum or natural language):

```yaml
# Standard enum mode
- id: "analyze"
  agent: "zen-architect"
  agent_mode: "ANALYZE"
  prompt: "Analyze this architecture"

# Natural language mode
- id: "review"
  agent: "zen-architect"
  agent_mode: "Review for complexity issues"
  prompt: "Check this code"
```

Available standard modes (AgentMode enum):
- `ANALYZE` - Examine and break down information
- `EVALUATE` - Assess quality, completeness, or correctness
- `EXECUTE` - Perform actions or implement changes
- `REVIEW` - Check work for issues or improvements
- `GENERATE` - Create new content or artifacts

### Output Extraction

DotRunner extracts outputs from agent responses using multiple strategies:

1. **JSON parsing** - If response contains JSON, extract named fields
2. **Pattern matching** - Parse "output_name: value" patterns
3. **Fallback** - Map entire response to first output if no patterns match

```python
def _extract_outputs(self, response: str, output_names: list[str]) -> dict[str, Any]:
    """Extract named outputs from AI response"""

    # Try JSON parsing first
    if any(keyword in response for keyword in ["{", "json"]):
        try:
            parsed = parse_llm_json(response)
            if isinstance(parsed, dict):
                return {name: parsed.get(name, "") for name in output_names}
        except Exception:
            pass  # Fall back to pattern matching

    # Pattern-based extraction: "name: value"
    outputs = {}
    for line in response.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            if key.strip() in output_names:
                outputs[key.strip()] = value.strip()

    # Fallback: map entire response to first output
    if not outputs and output_names:
        outputs[output_names[0]] = response.strip()

    return outputs
```

## Error Handling

DotRunner uses Python's built-in exception system with one custom exception for context errors:

### Custom Exceptions

```python
class ContextError(Exception):
    """Raised when context interpolation fails due to missing variables.

    Attributes:
        message: Human-readable error message
        missing_vars: List of variable names that were missing from context
        template: The template string that failed to interpolate
    """

    def __init__(self, message: str, missing_vars: list[str], template: str):
        super().__init__(message)
        self.missing_vars = missing_vars
        self.template = template
```

### Built-in Exceptions

DotRunner uses standard Python exceptions for common errors:

- **ValueError** - Workflow validation failures, invalid YAML, missing required fields
- **FileNotFoundError** - Missing workflow files, session not found
- **RuntimeError** - Agent execution failures, node execution errors
- **subprocess.TimeoutExpired** - Agent timeout (300 seconds)

### Error Handling Patterns

#### Node Execution Errors

Node execution uses try/catch with retry logic:

```python
async def execute(self, node: Node, context: dict[str, Any]) -> NodeResult:
    """Execute a single node with retry support."""
    max_attempts = max(1, node.retry_on_failure)
    last_error = None

    for attempt in range(max_attempts):
        try:
            # Execute node...
            return NodeResult(status="success", ...)

        except ContextError as e:
            # Don't retry context errors - return failure immediately
            return NodeResult(
                status="failed",
                error=f"Missing required variables: {e.missing_vars}",
                ...
            )

        except Exception as e:
            # Retry other errors with exponential backoff
            last_error = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(2**attempt)

    # All retries failed
    return NodeResult(status="failed", error=str(last_error), ...)
```

#### Workflow Validation Errors

```python
def validate(self) -> list[str]:
    """Validate workflow structure, return list of errors (empty if valid)."""
    errors = []

    if not self.nodes:
        errors.append("Workflow must have at least one node")

    # Check for duplicate node IDs
    node_ids = [n.id for n in self.nodes]
    duplicates = [nid for nid in node_ids if node_ids.count(nid) > 1]
    if duplicates:
        errors.append(f"Duplicate node ID found: {duplicates[0]}")

    # Check all node references are valid
    for node in self.nodes:
        if isinstance(node.next, str):
            if not self.get_node(node.next):
                errors.append(f"Node '{node.id}' references nonexistent node '{node.next}'")

    return errors

# Usage
errors = workflow.validate()
if errors:
    raise ValueError(f"Workflow validation failed: {'; '.join(errors)}")
```

### NodeResult Status

Every node execution returns a NodeResult with:

```python
@dataclass
class NodeResult:
    node_id: str
    status: str                    # "success" or "failed"
    outputs: dict[str, Any]        # Captured outputs
    raw_response: str              # Full agent/AI response
    error: str | None = None       # Error message if failed
    execution_time: float = 0.0    # Node execution time
```

## Version Compatibility

- DotRunner version: 1.0.0
- Python requirement: >=3.11
- YAML version: 1.2
- Dependencies: See pyproject.toml