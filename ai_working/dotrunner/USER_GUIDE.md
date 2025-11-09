# DotRunner User Guide

**Version**: Phase 4 (CLI + State Persistence)
**Status**: Production Ready
**Last Updated**: 2025-10-19

---

## Table of Contents

1. [Introduction](#introduction)
2. [What is DotRunner?](#what-is-dotrunner)
3. [Quick Start](#quick-start)
4. [Architecture Overview](#architecture-overview)
5. [Writing Workflows](#writing-workflows)
6. [Using DotRunner](#using-dotrunner)
7. [Advanced Topics](#advanced-topics)
8. [API Reference](#api-reference)
9. [Troubleshooting](#troubleshooting)
10. [Design Documentation](#design-documentation)

---

## Introduction

DotRunner is a declarative agentic workflow orchestration system that allows you to define multi-step AI workflows in YAML files. It handles the orchestration, context management, and AI integration while you focus on defining what you want accomplished.

### Key Features

- 📝 **Declarative YAML workflows** - Define complex processes in simple configuration files
- 🤖 **AI-powered execution** - Nodes execute using Claude AI via ClaudeSession
- 🔄 **Context flow** - Automatic context accumulation between nodes
- 💾 **State persistence** - Automatic checkpointing after each node
- 🎯 **CLI interface** - Run workflows from command line with rich output
- 🛡️ **Robust error handling** - Clear error messages and graceful degradation
- ✅ **Well-tested** - 91 comprehensive tests ensuring reliability
- 🧱 **Modular design** - Clean architecture following "bricks and studs" philosophy

---

## What is DotRunner?

DotRunner transforms workflow definitions like this:

```yaml
workflow:
  name: "code-review"
  description: "Automated code review process"
  context:
    file_path: "src/auth.py"

nodes:
  - id: "analyze"
    name: "Analyze Code Structure"
    prompt: "Analyze the Python file at {file_path} and describe its structure"
    outputs: ["code_structure"]
    next: "find-bugs"

  - id: "find-bugs"
    name: "Find Potential Bugs"
    prompt: "Given this code structure: {code_structure}, identify potential bugs"
    outputs: ["bugs_found"]
    next: "summarize"

  - id: "summarize"
    name: "Create Summary"
    prompt: "Summarize the analysis. Structure: {code_structure}. Bugs: {bugs_found}"
    outputs: ["final_summary"]
    type: "terminal"
```

Into automated execution that:
1. Analyzes code structure
2. Finds potential bugs using the structure analysis
3. Creates a comprehensive summary
4. Returns all results with timing and status

---

## Quick Start

### Prerequisites

- Python 3.11+
- Claude API access (via ccsdk_toolkit)
- Project dependencies installed (`make install`)

### Your First Workflow

1. **Create a workflow file** (`my_workflow.yaml`):

```yaml
workflow:
  name: "hello-workflow"
  description: "Simple greeting workflow"
  context:
    user_name: "Alice"

nodes:
  - id: "greet"
    name: "Generate Greeting"
    prompt: "Create a friendly greeting for {user_name}"
    outputs: ["greeting"]
    type: "terminal"
```

2. **Run the workflow** (via CLI):

```bash
python -m ai_working.dotrunner run my_workflow.yaml
```

3. **View results**:

```
Loading workflow: hello-workflow
Starting workflow: hello-workflow

✓ Workflow completed successfully

Summary:
  • Total time: 5.23s
  • Nodes completed: 1/1
  • Session ID: hello-workflow_20251019_143022_a3f2

Node Results:
  ✓ greet (5.23s)
```

**Or run programmatically**:

```python
from ai_working.dotrunner.workflow import Workflow
from ai_working.dotrunner.engine import WorkflowEngine
from pathlib import Path
import asyncio

async def run_workflow():
    workflow = Workflow.from_yaml(Path("my_workflow.yaml"))
    engine = WorkflowEngine()
    result = await engine.run(workflow)
    print(f"Greeting: {result.final_context['greeting']}")

asyncio.run(run_workflow())
```

---

## Architecture Overview

DotRunner follows a layered architecture with clear separation of concerns:

```
┌────────────────────────────────────────────────────────────┐
│                    WorkflowEngine                          │
│  • Orchestrates workflow execution                         │
│  • Manages sequential node processing                      │
│  • Accumulates context between nodes                       │
│  • Handles failures and logging                            │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────┐
│                    NodeExecutor                            │
│  • Executes individual workflow nodes                      │
│  • Integrates with ClaudeSession for AI                    │
│  • Extracts named outputs from responses                   │
│  • Provides error handling and timing                      │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────┐
│              Context Utilities                             │
│  • Variable interpolation ({variable} → value)             │
│  • Variable extraction and validation                      │
│  • Context error reporting                                 │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│              State Management                              │
│  • NodeResult: Single node execution result                │
│  • WorkflowState: Current execution state                  │
│  • WorkflowResult: Final workflow outcome                  │
└────────────────────────────────────────────────────────────┘
```

### Core Modules

| Module | Purpose | Lines | Tests |
|--------|---------|-------|-------|
| **workflow.py** | YAML parsing, validation | 233 | 20 |
| **state.py** | State management dataclasses | 76 | 10 |
| **context.py** | Variable interpolation | 124 | 27 |
| **executor.py** | Node execution with AI | 156 | 16 |
| **engine.py** | Workflow orchestration | 147 | 18 |
| **persistence.py** | State persistence (Phase 3) | 156 | - |
| **cli.py** | CLI interface (Phase 4) | 237 | - |

**Total**: ~1100 lines of code, 91 comprehensive tests

---

## Writing Workflows

### Workflow Structure

Every workflow YAML file has two main sections:

```yaml
workflow:
  name: "workflow-id"
  description: "What this workflow does"
  context:
    # Initial context variables
    variable1: "value1"
    variable2: "value2"

nodes:
  # List of nodes to execute
  - id: "node-1"
    # ... node configuration
  - id: "node-2"
    # ... node configuration
```

### Node Configuration

Each node has these fields:

```yaml
- id: "unique-node-id"           # Required: Unique identifier
  name: "Human Readable Name"    # Required: Display name
  prompt: "Instruction with {var}"  # Required: AI prompt template
  outputs: ["output1", "output2"]   # Optional: Named outputs to extract
  next: "next-node-id"           # Optional: Next node (omit for terminal)
  type: "terminal"               # Optional: Mark as terminal node
```

### Context Variables

Variables defined in workflow context or node outputs can be used in any subsequent node prompt:

```yaml
workflow:
  context:
    topic: "AI Safety"  # Available in all nodes

nodes:
  - id: "research"
    prompt: "Research {topic}"
    outputs: ["findings"]  # Creates {findings} variable
    next: "analyze"

  - id: "analyze"
    prompt: "Analyze these {findings} about {topic}"
    # Can use both {topic} and {findings}
```

### Output Extraction

DotRunner supports two output formats:

#### 1. Pattern-Based (Simple)

The AI response should include outputs in this format:

```
output_name: The extracted value
another_output: Another value
```

Example:

```yaml
- id: "analyze"
  prompt: "Analyze the code and provide: code_structure, complexity"
  outputs: ["code_structure", "complexity"]
```

AI Response:
```
code_structure: Well-organized with clear modules
complexity: Moderate, around 150 lines
```

#### 2. JSON-Based (Structured)

For structured data, request JSON output:

```yaml
- id: "evaluate"
  prompt: "Evaluate and return JSON with: score, feedback, recommendations"
  outputs: ["score", "feedback", "recommendations"]
```

AI Response:
```json
{
  "score": 8.5,
  "feedback": "Good code quality",
  "recommendations": ["Add more tests", "Improve docs"]
}
```

### Node Execution Flow

1. **Interpolate** - Replace {variables} in prompt with context values
2. **Execute** - Send prompt to Claude AI via ClaudeSession
3. **Extract** - Parse named outputs from response
4. **Accumulate** - Add outputs to context for next node
5. **Continue** - Move to next node or complete

---

## Using DotRunner

### Command Line Interface

DotRunner provides a rich CLI for running and managing workflows.

#### Run a Workflow

```bash
python -m ai_working.dotrunner run workflow.yaml
```

**With context override**:
```bash
python -m ai_working.dotrunner run workflow.yaml --context '{"file": "main.py", "mode": "strict"}'
```

**Without checkpoint saving** (for testing):
```bash
python -m ai_working.dotrunner run workflow.yaml --no-save
```

#### List Workflow Sessions

View recent workflow executions:

```bash
python -m ai_working.dotrunner list
```

Show all sessions including completed:

```bash
python -m ai_working.dotrunner list --all
```

Output example:
```
Workflow Sessions
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Session ID           ┃ Workflow         ┃ Status    ┃ Progress ┃ Updated         ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ code-review_20...    │ code-review-flow │ completed │ 3/3      │ 2025-10-19T...  │
│ analysis_202...      │ analysis         │ failed    │ 2/5      │ 2025-10-19T...  │
└──────────────────────┴──────────────────┴───────────┴──────────┴─────────────────┘
```

#### Check Session Status

Get detailed information about a specific session:

```bash
python -m ai_working.dotrunner status code-review_20251019_143022_a3f2
```

**As JSON** (for scripting):
```bash
python -m ai_working.dotrunner status code-review_20251019_143022_a3f2 --json
```

#### Resume Interrupted Workflow

Resume a workflow from its last checkpoint:

```bash
python -m ai_working.dotrunner resume code-review_20251019_143022_a3f2
```

*(Note: Full resume implementation coming soon)*

### Python API

#### Basic Usage

```python
from ai_working.dotrunner.workflow import Workflow
from ai_working.dotrunner.engine import WorkflowEngine
from pathlib import Path
import asyncio

async def main():
    # Load workflow from YAML
    workflow = Workflow.from_yaml(Path("workflow.yaml"))

    # Create engine and run
    engine = WorkflowEngine()
    result = await engine.run(workflow)

    # Check results
    if result.status == "completed":
        print("✅ Workflow completed successfully!")
        print(f"Total time: {result.total_time:.2f}s")
        print(f"Final context: {result.final_context}")
    else:
        print(f"❌ Workflow failed: {result.error}")

asyncio.run(main())
```

#### Access Individual Node Results

```python
result = await engine.run(workflow)

for node_result in result.node_results:
    print(f"Node: {node_result.node_id}")
    print(f"Status: {node_result.status}")
    print(f"Time: {node_result.execution_time:.2f}s")
    print(f"Outputs: {node_result.outputs}")
    if node_result.error:
        print(f"Error: {node_result.error}")
```

#### Custom Context

Override initial context:

```python
workflow = Workflow.from_yaml(Path("workflow.yaml"))

# Override context
workflow.context = {
    "file_path": "custom/path.py",
    "mode": "strict"
}

result = await engine.run(workflow)
```

### Workflow Validation

Validate workflows before execution:

```python
from ai_working.dotrunner.workflow import Workflow

# Load and validate
workflow = Workflow.from_yaml(Path("workflow.yaml"))

# Check for issues
errors = workflow.validate()
if errors:
    print("Workflow has issues:")
    for error in errors:
        print(f"  - {error}")
else:
    print("✅ Workflow is valid")
```

Validation checks:
- No empty workflows
- No duplicate node IDs
- Valid node references in `next`
- No circular dependencies

---

## Advanced Topics

### Error Handling

#### Missing Context Variables

If a node references a variable that doesn't exist:

```yaml
- id: "broken"
  prompt: "Process {nonexistent_var}"  # ❌ Error!
```

Result:
```python
NodeResult(
    status="failed",
    error="Missing context variables: nonexistent_var"
)
```

#### Node Execution Failures

If AI execution fails (timeout, API error):

```python
NodeResult(
    status="failed",
    error="ClaudeSession timeout after 60s",
    execution_time=60.0
)
```

The workflow stops at the failed node and returns:

```python
WorkflowResult(
    status="failed",
    error="Workflow failed",
    node_results=[...],  # Results up to failure
    final_context={...}  # Context accumulated so far
)
```

### Context Interpolation Details

Variables are replaced using Python's `str.format()`:

```python
template = "Process {file} with {config}"
context = {"file": "data.csv", "config": "strict"}
# Result: "Process data.csv with strict"
```

Supported types:
- **Strings**: Direct substitution
- **Numbers**: Converted to string
- **Booleans**: "True" or "False"
- **Lists/Dicts**: String representation (use JSON for structured data)

### Output Extraction Priority

1. **JSON extraction** - If response contains `{` or mentions "json"
2. **Pattern extraction** - Fall back to `name: value` pattern matching
3. **Partial success** - Extract what's available, don't fail

Example with partial extraction:

```yaml
outputs: ["analysis", "score", "recommendations"]
```

AI returns:
```
analysis: Good code
score: 8
```

Result:
```python
outputs = {
    "analysis": "Good code",
    "score": "8"
    # recommendations missing but node succeeds
}
```

### Logging

DotRunner logs execution progress:

```python
import logging

logging.basicConfig(level=logging.INFO)

# Logs will show:
# INFO:ai_working.dotrunner.engine:Starting workflow: code-review
# INFO:ai_working.dotrunner.engine:Executing node: analyze (Analyze Code)
# INFO:ai_working.dotrunner.engine:Executing node: find-bugs (Find Bugs)
# INFO:ai_working.dotrunner.engine:Workflow code-review completed
```

For errors:

```python
logging.basicConfig(level=logging.ERROR)

# Shows only failures:
# ERROR:ai_working.dotrunner.engine:Node analyze failed: Missing variable
```

---

## API Reference

### Workflow Class

```python
from ai_working.dotrunner.workflow import Workflow

@dataclass
class Workflow:
    name: str
    description: str
    context: Dict[str, Any]
    nodes: List[Node]

    @classmethod
    def from_yaml(cls, path: Path) -> Workflow:
        """Load workflow from YAML file"""

    def validate(self) -> List[str]:
        """Validate workflow structure, returns error list"""

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID"""
```

### Node Class

```python
@dataclass
class Node:
    id: str
    name: str
    prompt: str
    outputs: List[str] = field(default_factory=list)
    next: Union[str, Dict[str, str], None] = None
    type: Optional[str] = None  # "terminal" for last node
```

### WorkflowEngine Class

```python
from ai_working.dotrunner.engine import WorkflowEngine

class WorkflowEngine:
    def __init__(self, session_manager: Optional[SessionManager] = None):
        """Initialize engine"""

    async def run(self, workflow: Workflow) -> WorkflowResult:
        """Execute workflow and return results"""
```

### WorkflowResult Class

```python
from ai_working.dotrunner.state import WorkflowResult, NodeResult

@dataclass
class WorkflowResult:
    workflow_id: str
    status: str  # "completed" or "failed"
    total_time: float
    node_results: List[NodeResult]
    final_context: Dict[str, Any]
    error: Optional[str] = None

@dataclass
class NodeResult:
    node_id: str
    status: str  # "success", "failed", "skipped"
    outputs: Dict[str, Any]
    raw_response: str
    error: Optional[str] = None
    execution_time: float = 0.0
```

### Context Utilities

```python
from ai_working.dotrunner.context import interpolate, extract_variables, validate_context

def interpolate(template: str, context: Dict[str, Any]) -> str:
    """Replace {variables} with context values"""

def extract_variables(template: str) -> Set[str]:
    """Find all {variable} names in template"""

def validate_context(template: str, context: Dict[str, Any]) -> List[str]:
    """Return list of missing variables"""
```

---

## Troubleshooting

### Common Issues

#### 1. Missing Context Variable Error

**Problem**:
```
ContextError: Missing context variables: file_path
```

**Solution**: Ensure the variable is either:
- Defined in workflow context
- Produced by a previous node's outputs

```yaml
workflow:
  context:
    file_path: "src/main.py"  # ✅ Define it

# OR

nodes:
  - id: "setup"
    outputs: ["file_path"]  # ✅ Produce it
    next: "process"
```

#### 2. Node Timeout

**Problem**:
```
NodeResult(status="failed", error="ClaudeSession timeout after 60s")
```

**Solution**:
- Simplify the prompt
- Break complex tasks into multiple nodes
- Check API connectivity

#### 3. Output Not Extracted

**Problem**: Node succeeds but output not in final context

**Solution**: Ensure AI response includes the output name:

```yaml
outputs: ["analysis"]
```

AI must respond with:
```
analysis: Your analysis here
```

Or JSON:
```json
{"analysis": "Your analysis here"}
```

#### 4. Workflow Validation Fails

**Problem**:
```
['Duplicate node ID: analyze', 'Invalid node reference: nonexistent']
```

**Solution**: Fix the YAML:
- Use unique node IDs
- Reference only existing nodes in `next`
- Don't create circular dependencies

### Debug Mode

Enable detailed logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Testing Workflows

Test workflows with custom context:

```python
# Create test workflow
workflow = Workflow(
    name="test",
    description="Test workflow",
    context={"test_var": "test_value"},
    nodes=[...]
)

# Run with controlled context
result = await engine.run(workflow)

# Assert results
assert result.status == "completed"
assert "expected_output" in result.final_context
```

---

## Design Documentation

For deeper technical understanding, see these documents:

### Architecture & Design

1. **[DESIGN.md](DESIGN.md)** - Complete system architecture and design philosophy
2. **[PHASE_2_DESIGN.md](PHASE_2_DESIGN.md)** - Phase 2 detailed technical specifications
3. **[PHASE_2_INTEGRATION_TESTS.md](PHASE_2_INTEGRATION_TESTS.md)** - Integration test scenarios

### Implementation Details

4. **[PHASE_2_COMPLETE.md](PHASE_2_COMPLETE.md)** - Phase 2 completion summary
5. **[PROGRESS_NOTES.md](PROGRESS_NOTES.md)** - Development progress tracking
6. **[README.md](README.md)** - Project overview and development guide

### Source Code

All implementation code is in `ai_working/dotrunner/`:
- `workflow.py` - YAML parsing and validation (Phase 1)
- `state.py` - State management dataclasses (Phase 2)
- `context.py` - Context interpolation utilities (Phase 2)
- `executor.py` - Node execution with AI (Phase 2)
- `engine.py` - Workflow orchestration (Phase 2)

### Test Suite

Comprehensive test coverage in `ai_working/dotrunner/tests/`:
- `test_workflow_model.py` - Workflow parsing and validation (20 tests)
- `test_state.py` - State management (10 tests)
- `test_context.py` - Context interpolation (27 tests)
- `test_executor.py` - Node execution (16 tests)
- `test_engine.py` - Workflow orchestration (18 tests)

**Total**: 91 tests ensuring reliability

---

## Future Phases

### Phase 3: State Persistence ✅ Complete
- ✅ Save workflow state after each node
- ✅ Session management with unique IDs
- ✅ List and inspect sessions
- ⏳ Resume from checkpoint (framework ready)

### Phase 4: CLI Interface ✅ Complete
- ✅ `python -m ai_working.dotrunner run workflow.yaml`
- ✅ Rich terminal output with colors
- ✅ Session tracking and management
- ✅ Status inspection with JSON export

### Phase 5: Agent Integration (Planned)
- Support for specialized agents
- Agent capability discovery
- Agent configuration in YAML

### Phase 6: Conditional Routing (Planned)
- Branch based on node outputs
- Conditional next nodes
- Decision logic

---

## Getting Help

- **Issues**: File issues in the project repository
- **Questions**: Refer to design documentation
- **Examples**: See `examples/` directory for sample workflows

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| Phase 1 | 2025-10-18 | YAML parsing and validation |
| Phase 2 | 2025-10-19 | Linear execution engine |
| Phase 3 | 2025-10-19 | State persistence and session management |
| Phase 4 | 2025-10-19 | CLI interface with rich output |

---

**Built with**:
- Python 3.11+
- Claude AI (via ccsdk_toolkit)
- Ruthless simplicity philosophy
- Test-first development

**Architecture Review**: ✅ Approved by zen-architect (10/10 philosophy compliance)
