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

#### Simple Routing (80% of cases) - Dict-based

```yaml
next:
  pass: "deploy"                # Key-value pairs: output_value -> node_id
  fail: "fix-tests"
  unknown: "investigate"
```

#### Complex Routing (20% of cases) - Expression-based

```yaml
next:
  - when: "test_count > 50 and coverage > 0.8"
    goto: "deploy"
  - when: "status == 'critical'"
    goto: "emergency-fix"
  - default: "needs-work"       # Required fallback
```

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
      - evidence_score
      - missing_evidence
    next:
      - when: "evidence_score >= 0.8"
        goto: "deploy"
      - when: "evidence_score >= 0.5"
        goto: "improve"
      - default: "refactor"

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
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum

class NodeType(Enum):
    AGENT = "agent"
    WORKFLOW = "workflow"

class RouteType(Enum):
    SIMPLE = "simple"      # Dict-based routing
    COMPLEX = "complex"    # Expression-based routing

class Node:
    """Represents a workflow node (agent or sub-workflow)."""

    def __init__(
        self,
        id: str,
        node_type: NodeType,
        inputs: Dict[str, Any] = None,
        outputs: List[str] = None,
        next: Union[Dict[str, str], List[Dict[str, str]]] = None,
        # Agent-specific
        agent: Optional[str] = None,
        agent_mode: Optional[Union[str, Enum]] = None,
        prompt: Optional[str] = None,
        # Workflow-specific
        workflow: Optional[str] = None,
        # Common
        description: Optional[str] = None
    ):
        self.id = id
        self.node_type = node_type
        self.inputs = inputs or {}
        self.outputs = outputs or []
        self.next = next
        self.agent = agent
        self.agent_mode = agent_mode
        self.prompt = prompt
        self.workflow = workflow
        self.description = description

    def get_route_type(self) -> RouteType:
        """Determine if routing is simple (dict) or complex (expressions)."""
        if isinstance(self.next, dict):
            return RouteType.SIMPLE
        elif isinstance(self.next, list):
            return RouteType.COMPLEX
        return None

class Workflow:
    """Represents a complete workflow."""

    def __init__(
        self,
        name: str,
        nodes: List[Node],
        description: Optional[str] = None,
        version: str = "1.0.0"
    ):
        self.name = name
        self.nodes = {node.id: node for node in nodes}
        self.description = description
        self.version = version

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "Workflow":
        """Load workflow from YAML file."""
        ...

    def validate(self) -> List[str]:
        """Validate workflow structure, return list of issues."""
        ...

    def get_entry_node(self) -> Node:
        """Get the first node in execution order."""
        ...

class WorkflowEngine:
    """Executes workflows with state management."""

    def __init__(
        self,
        state_dir: Path = Path(".dotrunner/sessions"),
        agent_backend: str = "task"  # "task" or "subprocess"
    ):
        self.state_dir = state_dir
        self.agent_backend = agent_backend

    async def run(
        self,
        workflow: Workflow,
        initial_context: Dict[str, Any] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute workflow, return final context."""
        ...

    async def resume(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """Resume interrupted workflow from saved state."""
        ...

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all workflow sessions with status."""
        ...

class ExpressionEvaluator:
    """Safe expression evaluation using ast.literal_eval."""

    def evaluate(
        self,
        expression: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Safely evaluate routing expressions.
        Supports: comparisons, and/or, basic operations.
        """
        ...
```

## CLI Commands

### Run Workflow

```bash
# Basic execution
dotrunner run workflow.yaml

# With initial context
dotrunner run workflow.yaml --input feature="user authentication"

# With custom session ID
dotrunner run workflow.yaml --session my-session-123

# With agent backend selection
dotrunner run workflow.yaml --agent-backend subprocess
```

### Resume Session

```bash
# Resume interrupted workflow
dotrunner resume <session-id>

# Resume with additional context
dotrunner resume <session-id> --input retry_count=3
```

### List Sessions

```bash
# List all sessions
dotrunner list

# List with details
dotrunner list --detailed

# Filter by status
dotrunner list --status running
dotrunner list --status completed
dotrunner list --status failed
```

### Get Session Status

```bash
# Show session details
dotrunner status <session-id>

# Show with full context
dotrunner status <session-id> --show-context

# Show execution trace
dotrunner status <session-id> --trace
```

## File System Structure

```
.dotrunner/
├── sessions/               # Workflow execution state
│   ├── <session-id>/
│   │   ├── state.json      # Current execution state
│   │   ├── context.json    # Current context/variables
│   │   ├── trace.jsonl     # Execution history
│   │   └── nodes/          # Node-specific data
│   │       ├── <node-id>/
│   │       │   ├── input.json
│   │       │   ├── output.json
│   │       │   └── agent_response.json
├── workflows/              # Workflow definitions (optional)
│   ├── library/            # Reusable workflows
│   └── custom/             # User workflows
└── config.yaml             # DotRunner configuration
```

## Context Variable Reference

Variables can be referenced using `{variable_name}` syntax:

- `{user_request}` - Initial input variable
- `{node_id.output_name}` - Specific node output
- `{output_name}` - Most recent value with this name
- `{_session_id}` - Current session ID
- `{_timestamp}` - Current timestamp
- `{_node_id}` - Current node ID

## Agent Integration

### Task Tool Backend (Default)

```python
# Invoked via Claude Code SDK Task tool
response = await task_tool.execute(
    agent_name=node.agent,
    mode=node.agent_mode,
    prompt=resolved_prompt
)
```

### Subprocess Backend (Isolation)

```python
# Invoked as subprocess for isolation
result = subprocess.run(
    ["amplifier", "agent", node.agent],
    input=json.dumps({
        "mode": node.agent_mode,
        "prompt": resolved_prompt
    }),
    capture_output=True
)
```

## Error Handling

All operations return structured errors:

```python
class DotRunnerError(Exception):
    """Base exception for DotRunner errors."""
    pass

class WorkflowSyntaxError(DotRunnerError):
    """Invalid workflow YAML syntax."""
    pass

class NodeExecutionError(DotRunnerError):
    """Node execution failed."""
    node_id: str
    cause: str

class RoutingError(DotRunnerError):
    """Cannot determine next node."""
    node_id: str
    context: dict
```

## Version Compatibility

- DotRunner version: 1.0.0
- Python requirement: >=3.11
- YAML version: 1.2
- Dependencies: See pyproject.toml