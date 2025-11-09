# DotRunner: Skeptical Review - Real Implementation Gaps

**Date**: 2025-01-20
**Purpose**: Honest, comprehensive comparison of API Contract spec vs actual implementation

---

## Executive Summary

**Status**: Implementation has MAJOR gaps compared to API Contract specification

**Critical Findings**:
1. ❌ **Python API completely different** - Spec shows class-based API, implementation uses dataclasses
2. ❌ **Workflow.nodes structure wrong** - Spec says dict, implementation is list
3. ❌ **CLI arguments missing** - No `--input`, no `--agent-backend`, no session management flags
4. ❌ **File system structure incomplete** - Missing context.json, nodes/ subdirectories
5. ❌ **Missing classes** - No NodeType enum, no RouteType enum, no WorkflowEngine.__init__ params
6. ❌ **Node has `name` field** - Spec doesn't show this field at all

---

## Category 1: Python API Structure Mismatches

### 1.1 Node Class Structure ❌ CRITICAL

**API Contract Says** (lines 115-143):
```python
class Node:
    def __init__(
        self,
        id: str,
        node_type: NodeType,  # ← ENUM TYPE
        inputs: Dict[str, Any] = None,
        outputs: List[str] = None,
        next: Union[Dict[str, str], List[Dict[str, str]]] = None,
        agent: Optional[str] = None,
        agent_mode: Optional[Union[str, Enum]] = None,
        prompt: Optional[str] = None,
        workflow: Optional[str] = None,
        description: Optional[str] = None
    ):
```

**Actual Implementation** (workflow.py:40-68):
```python
@dataclass
class Node:
    id: str
    name: str  # ← NOT IN SPEC
    prompt: str = ""
    description: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    agent: str | None = None
    agent_mode: str | None = None
    workflow: str | None = None
    outputs: list[str] = field(default_factory=list)
    next: Union[str, dict[str, str], list[dict[str, str]]] | None = None
    retry_on_failure: int = 1  # ← NOT IN SPEC
    type: str | None = None  # ← NOT IN SPEC
```

**Gaps**:
- ❌ No `node_type: NodeType` field
- ❌ Has `name: str` field (not in spec)
- ❌ Has `retry_on_failure: int` field (not in spec)
- ❌ Has `type: str` field (not in spec)
- ❌ Uses dataclass instead of __init__ method

### 1.2 Workflow Class Structure ❌ CRITICAL

**API Contract Says** (lines 153-180):
```python
class Workflow:
    def __init__(
        self,
        name: str,
        nodes: List[Node],  # ← Takes LIST in constructor
        description: Optional[str] = None,
        version: str = "1.0.0"
    ):
        self.name = name
        self.nodes = {node.id: node for node in nodes}  # ← STORES AS DICT
        self.description = description
        self.version = version

    def get_entry_node(self) -> Node:  # ← MISSING IN IMPLEMENTATION
        """Get the first node in execution order."""
```

**Actual Implementation** (workflow.py:70-90):
```python
@dataclass
class Workflow:
    name: str
    description: str
    nodes: list[Node]  # ← STORES AS LIST, NOT DICT
    version: str = "1.0.0"
    context: dict[str, Any] = field(default_factory=dict)  # ← NOT IN SPEC

    def get_node(self, node_id: str) -> Node | None:  # ← Different method
        return next((n for n in self.nodes if n.id == node_id), None)

    # ← NO get_entry_node() method
```

**Gaps**:
- ❌ `nodes` stored as list, spec says dict
- ❌ Has `context` field (not in spec constructor)
- ❌ Missing `get_entry_node()` method
- ❌ Has `get_node()` method (different from spec)

### 1.3 WorkflowEngine Class ❌ CRITICAL

**API Contract Says** (lines 181-210):
```python
class WorkflowEngine:
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
        initial_context: Dict[str, Any] = None,  # ← DIFFERENT PARAM NAME
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:  # ← RETURNS DICT
```

**Actual Implementation** (engine.py:22-33):
```python
class WorkflowEngine:
    def __init__(self, session_manager: SessionManager | None = None, save_checkpoints: bool = True):
        self.session_mgr = session_manager or SessionManager()
        self.executor = NodeExecutor(session_manager)
        self.logger = logging.getLogger(__name__)
        self.save_checkpoints = save_checkpoints
        self.session_id = None

    async def run(self, workflow: Workflow, session_id: str | None = None) -> WorkflowResult:
        # ← NO initial_context parameter
        # ← Returns WorkflowResult, not Dict
```

**Gaps**:
- ❌ No `state_dir` parameter
- ❌ No `agent_backend` parameter
- ❌ Has `session_manager` parameter (not in spec)
- ❌ Has `save_checkpoints` parameter (not in spec)
- ❌ `run()` missing `initial_context` parameter
- ❌ `run()` returns `WorkflowResult`, spec says `Dict[str, Any]`

### 1.4 Missing Enums ❌ CRITICAL

**API Contract Requires** (lines 107-113):
```python
class NodeType(Enum):
    AGENT = "agent"
    WORKFLOW = "workflow"

class RouteType(Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"
```

**Actual Implementation**:
- ❌ No `NodeType` enum exists
- ❌ No `RouteType` enum exists
- ✅ Has `AgentMode` enum (this one is good)

### 1.5 Missing Methods ❌

**API Contract Requires**:
- `Node.get_route_type() -> RouteType` - ❌ Missing
- `Workflow.get_entry_node() -> Node` - ❌ Missing
- `WorkflowEngine.list_sessions() -> List[Dict[str, Any]]` - ❌ Missing (exists in persistence.py, not engine)

---

## Category 2: CLI Arguments Mismatches

### 2.1 `run` Command ❌ CRITICAL

**API Contract Says** (lines 232-243):
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

**Actual Implementation** (cli.py:35-39):
```python
@cli.command()
@click.argument("workflow_file", type=click.Path(exists=True))
@click.option("--context", "-c", help="Override context as JSON string")
@click.option("--no-save", is_flag=True, help="Don't save checkpoints")
def run(workflow_file: str, context: str | None, no_save: bool):
```

**Gaps**:
- ❌ Has `--context` but spec shows `--input`
- ❌ Missing `--session` option
- ❌ Missing `--agent-backend` option
- ❌ Has `--no-save` (not in spec)

### 2.2 `resume` Command ❌

**API Contract Says** (lines 246-253):
```bash
# Resume interrupted workflow
dotrunner resume <session-id>

# Resume with additional context
dotrunner resume <session-id> --input retry_count=3
```

**Actual Implementation** (cli.py:155-157):
```python
@cli.command()
@click.argument("session_id")
def resume(session_id: str):
```

**Gaps**:
- ❌ Missing `--input` option for resume

### 2.3 `list` Command ❌

**API Contract Says** (lines 255-268):
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

**Actual Implementation** (cli.py:68-70):
```python
@cli.command()
@click.option("--all", "show_all", is_flag=True, help="Show all sessions including completed")
def list(show_all: bool):
```

**Gaps**:
- ❌ Has `--all` but spec shows `--detailed`
- ❌ Missing `--status` filter option

### 2.4 `status` Command ⚠️ Partial

**API Contract Says** (lines 270-281):
```bash
# Show session details
dotrunner status <session-id>

# Show with full context
dotrunner status <session-id> --show-context

# Show execution trace
dotrunner status <session-id> --trace
```

**Actual Implementation** (cli.py:110-113):
```python
@cli.command()
@click.argument("session_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def status(session_id: str, output_json: bool):
```

**Gaps**:
- ❌ Missing `--show-context` option
- ❌ Missing `--trace` option
- ⚠️ Has `--json` (not in spec, but reasonable)

---

## Category 3: File System Structure

### 3.1 Session Directory Structure ❌ CRITICAL

**API Contract Says** (lines 284-301):
```
.dotrunner/
├── sessions/
│   ├── <session-id>/
│   │   ├── state.json      # Current execution state
│   │   ├── context.json    # Current context/variables  ← MISSING
│   │   ├── trace.jsonl     # Execution history
│   │   └── nodes/          # Node-specific data  ← MISSING
│   │       ├── <node-id>/
│   │       │   ├── input.json
│   │       │   ├── output.json
│   │       │   └── agent_response.json
├── workflows/              # Workflow definitions (optional)  ← MISSING
│   ├── library/            # Reusable workflows
│   └── custom/             # User workflows
└── config.yaml             # DotRunner configuration  ← MISSING
```

**Actual Implementation** (persistence.py creates):
```
.dotrunner/
└── sessions/
    └── <session-id>/
        ├── state.json
        ├── metadata.json  # ← NOT IN SPEC
        ├── trace.jsonl
        └── workflow.yaml  # ← NOT IN SPEC
        # ← NO context.json
        # ← NO nodes/ subdirectory
```

**Gaps**:
- ❌ Missing `context.json` file
- ❌ Missing `nodes/<node-id>/` subdirectories
- ❌ Missing `nodes/<node-id>/input.json`
- ❌ Missing `nodes/<node-id>/output.json`
- ❌ Missing `nodes/<node-id>/agent_response.json`
- ❌ Missing `workflows/` directory structure
- ❌ Missing `config.yaml` file
- ⚠️ Has `metadata.json` (not in spec)
- ⚠️ Has `workflow.yaml` (not in spec, but useful)

---

## Category 4: Context Variable References

### 4.1 Special Context Variables ❌

**API Contract Says** (lines 303-313):
```python
# Variables can be referenced using {variable_name} syntax:
- {user_request} - Initial input variable
- {node_id.output_name} - Specific node output  ← QUALIFIED REFS
- {output_name} - Most recent value with this name
- {_session_id} - Current session ID  ← SYSTEM VARS
- {_timestamp} - Current timestamp
- {_node_id} - Current node ID
```

**Actual Implementation** (context.py):
- ✅ Supports `{variable_name}` basic syntax
- ⚠️ Has `{node_id.output}` qualified references (partially implemented)
- ❌ No `{_session_id}` system variable
- ❌ No `{_timestamp}` system variable
- ❌ No `{_node_id}` system variable

---

## Category 5: Error Handling

### 5.1 Exception Classes ❌

**API Contract Says** (lines 344-363):
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

**Actual Implementation**:
- ❌ No `DotRunnerError` base class
- ❌ No `WorkflowSyntaxError` class
- ❌ No `NodeExecutionError` class
- ❌ No `RoutingError` class
- ⚠️ Uses built-in exceptions (ValueError, RuntimeError)

---

## Category 6: Phase 2 Features (Documented, Not Implemented)

These are EXPECTED gaps (Phase 2):
- ✅ Expression-based routing - Documented as Phase 2, evaluator.py exists
- ✅ Sub-workflow execution - Fields added, execution not implemented
- ✅ Parallel execution - Not in current spec
- ✅ ExpressionEvaluator integration - Created but not integrated into engine

---

## Summary Matrix

| Feature | Spec | Implementation | Status |
|---------|------|----------------|--------|
| **Python API Structure** |
| Node as class with __init__ | ✅ | ❌ Dataclass | WRONG |
| Node.node_type field | ✅ | ❌ | MISSING |
| Node.name field | ❌ | ✅ | EXTRA |
| Workflow.nodes as dict | ✅ | ❌ List | WRONG |
| WorkflowEngine.__init__ params | ✅ | ❌ Different | WRONG |
| NodeType enum | ✅ | ❌ | MISSING |
| RouteType enum | ✅ | ❌ | MISSING |
| **CLI Commands** |
| run --input | ✅ | ❌ --context | WRONG |
| run --session | ✅ | ❌ | MISSING |
| run --agent-backend | ✅ | ❌ | MISSING |
| list --detailed | ✅ | ❌ --all | WRONG |
| list --status | ✅ | ❌ | MISSING |
| status --show-context | ✅ | ❌ | MISSING |
| status --trace | ✅ | ❌ | MISSING |
| **File System** |
| context.json | ✅ | ❌ | MISSING |
| nodes/<id>/ subdirs | ✅ | ❌ | MISSING |
| workflows/ directory | ✅ | ❌ | MISSING |
| config.yaml | ✅ | ❌ | MISSING |
| **Context Variables** |
| {_session_id} | ✅ | ❌ | MISSING |
| {_timestamp} | ✅ | ❌ | MISSING |
| {_node_id} | ✅ | ❌ | MISSING |
| **Error Classes** |
| DotRunnerError | ✅ | ❌ | MISSING |
| WorkflowSyntaxError | ✅ | ❌ | MISSING |
| NodeExecutionError | ✅ | ❌ | MISSING |
| RoutingError | ✅ | ❌ | MISSING |

---

## Critical Misalignments

### 1. Fundamental Design Mismatch
**API Contract** shows a class-based OOP design with specific constructor signatures.
**Implementation** uses dataclasses with different fields and structure.

This is NOT a minor gap - it's a fundamental architectural difference.

### 2. CLI Interface Incompatible
**API Contract** defines specific flags (`--input`, `--agent-backend`, `--detailed`, `--status`).
**Implementation** uses different flags (`--context`, `--all`).

Users following the spec will get errors.

### 3. File System Contract Broken
**API Contract** specifies exact directory structure with `context.json` and `nodes/` subdirectories.
**Implementation** creates different structure.

Tools expecting spec structure will break.

---

## Recommendations

### Option 1: Update Spec to Match Implementation ⚠️
**Effort**: Medium
**Impact**: Spec becomes accurate
**Risk**: Lose the cleaner design shown in spec

### Option 2: Update Implementation to Match Spec ❌
**Effort**: VERY HIGH
**Impact**: Complete rewrite of core classes
**Risk**: Break all 171 passing tests

### Option 3: Create "MVP Profile" vs "Full Profile" ✅ RECOMMENDED
**Effort**: Low
**Impact**: Honest documentation
**Risk**: None

Document two profiles:
- **MVP Profile**: What's actually built (current implementation)
- **Full Profile**: The ideal API from spec (future goal)

Mark each feature with `[MVP]` or `[Full]` tags.

---

## Conclusion

**The implementation works well** (171 tests passing, 95% coverage) **BUT does not match the API Contract specification.**

This is NOT a testing problem - tests validate what's built, not what spec describes.

The gap is between **specification** and **implementation**, not between **code** and **tests**.

**Immediate Action Required**: Decide which is authoritative - spec or code?

Then either:
1. Rewrite spec to match code (realistic)
2. Rewrite code to match spec (massive effort)
3. Document as two separate profiles (honest approach)
