# Flow Tools Implementation Plan (Ruthlessly Simple Edition)

**Version**: 2.0.0
**Status**: Draft
**Created**: 2025-01-20

## Core Philosophy: Ruthless Simplicity + Bricks & Studs

### What This Means

**Ruthless Simplicity**:
- Start with the absolute minimum that works
- Question EVERY abstraction - does it earn its keep?
- Prefer 20 lines of clear code over 100 lines of "flexible" code
- No speculative generality - solve today's problem, not tomorrow's
- If you can't explain why something is needed in one sentence, cut it

**Bricks & Studs**:
- Each module is a **brick** - self-contained, regeneratable, has ONE job
- Each module has **studs** - a clear contract (inputs, outputs, behavior)
- Studs are stable, bricks can be rebuilt from their contract
- If a brick needs changing, regenerate it entirely from its spec
- Test the studs (contract), not the brick's internals

**Quality Over Speed**:
- Assume each phase has bugs until proven otherwise
- MANDATORY skeptical review after each phase
- Don't move forward until impossible to find substantial issues
- Context and time are not constraints - correctness is
- User happiness comes from quality, not speed

---

## Project Overview

Two tools built as independent, regeneratable bricks:

1. **flow-builder** - CLI tool that creates DotRunner workflows
2. **/flow command** - Slash command that executes workflows

Each is a brick with clean studs connecting to DotRunner.

---

## Brick Architecture

### System as Bricks

```
┌─────────────────────┐
│   flow-builder      │ ← Brick: Creates workflows
│   ================  │
│   Studs:            │
│   - Input: User Q&A │
│   - Output: YAML    │
└─────────────────────┘
           ↓
    (writes to)
           ↓
┌─────────────────────┐
│   ai_flows/         │ ← Brick: Storage
│   ================  │
│   Studs:            │
│   - Format: YAML    │
└─────────────────────┘
           ↓
     (read by)
           ↓
┌─────────────────────┐
│   /flow command     │ ← Brick: Executes workflows
│   ================  │
│   Studs:            │
│   - Input: Name     │
│   - Output: Results │
└─────────────────────┘
           ↓
    (delegates to)
           ↓
┌─────────────────────┐
│   DotRunner         │ ← External brick (existing)
│   ================  │
│   Studs:            │
│   - Input: YAML     │
│   - Output: Results │
└─────────────────────┘
```

### Inside flow-builder Brick

```
┌───────────────────────────────────────┐
│         flow-builder (brick)          │
├───────────────────────────────────────┤
│                                       │
│  ┌──────────────┐  ┌──────────────┐ │
│  │  discovery   │  │ interrogation│ │
│  │  (sub-brick) │  │ (sub-brick)  │ │
│  └──────────────┘  └──────────────┘ │
│                                       │
│  ┌──────────────┐  ┌──────────────┐ │
│  │  validation  │  │  generator   │ │
│  │  (sub-brick) │  │ (sub-brick)  │ │
│  └──────────────┘  └──────────────┘ │
│                                       │
│  Studs (contract):                    │
│  - scan_agents() -> AgentCatalog      │
│  - interrogate() -> WorkflowSpec      │
│  - validate(spec) -> list[Error]      │
│  - generate(spec) -> YAML string      │
└───────────────────────────────────────┘
```

Each sub-brick:
- Has ONE responsibility
- Has a clear contract (studs)
- Can be regenerated independently
- Is testable through its contract

---

## Phase 1: Minimal Viable Flow Builder

**Goal**: Create the simplest possible tool that generates ONE valid workflow file

**Philosophy**: No AI, no fancy interrogation, no agent recommendations. Just prove the brick chain works.

### Phase 1 Studs (Contracts)

```python
# discovery.py - Sub-brick contract
def scan_agents(agents_dir: Path) -> list[Agent]:
    """
    Scan .claude/agents/ and return basic agent info.
    NO AI analysis, just parse TOML.

    Returns:
        [Agent(name="zen-architect", description="...", toml_path=...)]
    """

# interrogation.py - Sub-brick contract
def interrogate_minimal() -> WorkflowSpec:
    """
    Ask 3 questions only:
    1. Workflow name?
    2. What should it do? (one sentence)
    3. Which agent? (from list)

    Returns:
        WorkflowSpec with ONE node, no routing
    """

# validation.py - Sub-brick contract
def validate(spec: WorkflowSpec) -> list[str]:
    """
    Validate workflow spec using DotRunner's Workflow.validate().
    Add zero custom logic initially.

    Returns:
        [] if valid, [errors...] if invalid
    """

# generator.py - Sub-brick contract
def generate_yaml(spec: WorkflowSpec) -> str:
    """
    Convert WorkflowSpec to YAML string.
    Use PyYAML, no custom formatting logic.

    Returns:
        Valid DotRunner YAML
    """
```

### Phase 1 Tasks (Ruthlessly Minimal)

**1.1: Setup** (1 hour)
- [ ] Create `amplifier/flow_builder/` directory
- [ ] Create `ai_flows/` directory
- [ ] Add dependencies: `click`, `pyyaml`, `toml`
- [ ] Create test structure

**1.2: discovery.py Sub-Brick** (TEST-FIRST)

Tests define the stud:
```python
def test_scan_agents_returns_list():
    agents = scan_agents(Path(".claude/agents"))
    assert isinstance(agents, list)
    assert all(isinstance(a, Agent) for a in agents)

def test_scan_agents_extracts_name_and_description():
    # ... validates studs work
```

Implementation (AFTER tests):
- Read TOML files
- Extract name, description only
- Return list of Agent objects
- NO AI, NO caching, NO analysis

**Evidence**: Tests pass

**1.3: generator.py Sub-Brick** (TEST-FIRST)

Tests define the stud:
```python
def test_generate_creates_valid_yaml():
    spec = WorkflowSpec(name="test", ...)
    yaml_str = generate_yaml(spec)
    assert yaml_str.startswith("name:")
    # Verify DotRunner can load it
    workflow = Workflow.from_yaml_string(yaml_str)
    assert workflow.name == "test"
```

Implementation (AFTER tests):
- Use PyYAML dump
- Minimal formatting
- NO custom logic

**Evidence**: DotRunner loads generated YAML

**1.4: validation.py Sub-Brick** (TEST-FIRST)

Tests define the stud:
```python
def test_validate_uses_dotrunner():
    spec = WorkflowSpec(...)  # valid
    errors = validate(spec)
    assert errors == []

def test_validate_catches_errors():
    spec = WorkflowSpec(nodes=[])  # invalid
    errors = validate(spec)
    assert len(errors) > 0
```

Implementation (AFTER tests):
- Generate YAML from spec
- Create Workflow object
- Call workflow.validate()
- Return errors
- ZERO custom validation logic

**Evidence**: Catches same errors as DotRunner

**1.5: interrogation.py Sub-Brick** (TEST-FIRST)

Tests define the stud:
```python
def test_interrogate_collects_minimal_info(monkeypatch):
    # Mock input() calls
    inputs = ["my-workflow", "Do a thing", "1"]  # name, goal, agent choice
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))

    spec = interrogate_minimal()
    assert spec.name == "my-workflow"
    assert len(spec.nodes) == 1
```

Implementation (AFTER tests):
- Use `input()` for questions (no fancy UI yet)
- Ask 3 questions only
- Create WorkflowSpec with one node
- NO agent recommendation logic, just show list

**Evidence**: Creates valid WorkflowSpec

**1.6: CLI Entry Point** (TEST-FIRST)

Tests define the stud:
```python
def test_cli_creates_workflow_file(tmp_path, monkeypatch):
    # Mock interrogation inputs
    # Run CLI
    # Verify file exists in ai_flows/
    # Verify DotRunner can load it
```

Implementation (AFTER tests):
- Wire interrogate → validate → generate → save
- Use Click for CLI
- Save to `ai_flows/<name>.yaml`
- Print path to user

**Evidence**: Workflow file created and loadable

### Phase 1 Skeptical Review (MANDATORY)

**DO NOT PROCEED TO PHASE 2 UNTIL:**

1. **Run ALL tests** - 100% must pass
2. **Check test coverage** - Must be > 90%
3. **Manual workflow test**:
   - Run `amplifier flow-builder`
   - Create a workflow
   - Run `dotrunner run ai_flows/<name>.yaml`
   - Verify it executes without error
4. **Code review with skeptical eye**:
   - Any unnecessary complexity?
   - Any speculative features?
   - Any abstractions that don't earn their keep?
   - Can any code be deleted?
5. **Brick regeneration test**:
   - Pick one sub-brick
   - Delete implementation (keep tests)
   - Rewrite from contract
   - Tests should still pass
6. **Document gaps found** - Even if "no gaps", document that review happened

**Review Deliverable**: `PHASE_1_REVIEW.md` with:
- Test results (all passing)
- Coverage report (>90%)
- Manual test results (workflow executes)
- Code skepticism findings (list simplifications made)
- Brick regeneration test (which brick, did it work)
- Approval to proceed (YES/NO)

**Only proceed if approval is YES**

---

## Phase 2: Multi-Node Workflows (Still No AI)

**Goal**: Support workflows with 2-5 nodes and simple routing

**Philosophy**: Still no AI. Prove the brick architecture scales before adding intelligence.

### Phase 2 New Studs

```python
# interrogation.py - Extended contract
def interrogate_multi_node() -> WorkflowSpec:
    """
    Ask:
    1. Workflow name
    2. How many steps? (1-5)
    3. For each step:
       - What does this step do?
       - Which agent?
       - What outputs? (comma-separated names)
    4. How do steps connect? (linear or conditional)

    Returns:
        WorkflowSpec with 1-5 nodes
    """

# routing.py - New sub-brick
def parse_routing(routing_description: str, nodes: list[Node]) -> dict:
    """
    Parse simple routing:
    - "linear" → nodes connect A → B → C
    - "conditional on X" → parse output name for routing

    Returns:
        {node_id: next_config}
    """
```

### Phase 2 Tasks

**2.1: Multi-Node Interrogation** (TEST-FIRST)
- Tests define: collects 2-5 nodes
- Implementation: loop asking node questions
- NO agent recommendations yet, just show list

**2.2: Routing Logic** (TEST-FIRST)
- Tests define: linear and simple conditional routing
- Implementation: `routing.py` sub-brick
- Handle "linear" and "conditional on <output>" only

**2.3: Generator Updates** (TEST-FIRST)
- Tests define: multi-node YAML generation
- Implementation: extend generator for `next` field

### Phase 2 Skeptical Review (MANDATORY)

Same process as Phase 1:
1. All tests pass (100%)
2. Coverage > 90%
3. Manual test: Create 3-node workflow, execute in DotRunner
4. Code review: Any cruft? Any complexity?
5. Brick regeneration test
6. Document in `PHASE_2_REVIEW.md`
7. Only proceed if approval is YES

---

## Phase 3: AI Agent Recommendations (Add Intelligence)

**Goal**: Use AI to recommend agents, but keep interrogation simple

**Philosophy**: Add intelligence ONLY where it provides clear value. Don't over-engineer.

### Phase 3 New Studs

```python
# ai_analysis.py - New sub-brick
def analyze_agent(agent: Agent) -> AgentAnalysis:
    """
    Use Claude to analyze ONE agent's capabilities.

    Prompt: "Based on this agent's description, what is it good at?
             List 3-5 capabilities in one sentence each."

    Returns:
        AgentAnalysis(agent_name, capabilities=[...])
    """

def recommend_agent(task_description: str, agents: list[Agent]) -> Agent:
    """
    Use Claude to recommend best agent for a task.

    Prompt: "Given these agents and their capabilities, which is best for: {task}"

    Returns:
        Single Agent object (the recommendation)
    """
```

### Phase 3 Tasks

**3.1: AI Analysis Sub-Brick** (TEST-FIRST)
- Tests define: LLM returns structured capabilities
- Implementation: Simple Claude Code SDK call
- Cache results in memory (dict, not database)

**3.2: Agent Recommendation** (TEST-FIRST)
- Tests define: Returns reasonable agent for task
- Implementation: Call LLM with agent catalog
- Allow user to override ("no, use X")

### Phase 3 Skeptical Review (MANDATORY)

Same rigorous process:
1. Tests pass
2. Coverage > 90%
3. Manual test: AI recommends appropriate agents
4. Code review: Is AI integration simple? Any over-engineering?
5. Brick regeneration test on ai_analysis.py
6. Document in `PHASE_3_REVIEW.md`
7. Approval YES/NO

---

## Phase 4: Flow Discovery & Composition

**Goal**: Scan existing flows, suggest them to avoid duplication

**Philosophy**: Simple directory scan. AI similarity check is nice-to-have.

### Phase 4 New Studs

```python
# flow_discovery.py - New sub-brick
def scan_flows(flows_dir: Path) -> list[FlowInfo]:
    """
    Scan ai_flows/*.yaml files.

    Returns:
        [FlowInfo(name, description, inputs, outputs)]
    """

def check_similarity(user_goal: str, existing_flows: list[FlowInfo]) -> FlowInfo | None:
    """
    Use AI to check if user's goal matches existing flow.

    Returns:
        FlowInfo if similar, None otherwise
    """
```

### Phase 4 Tasks

**4.1: Flow Scanning** (TEST-FIRST)
- Tests define: finds YAML files, extracts metadata
- Implementation: Parse YAML, extract key fields

**4.2: Similarity Check** (TEST-FIRST)
- Tests define: detects obvious duplicates
- Implementation: Simple AI call with flow descriptions
- Suggest to user, allow ignore

### Phase 4 Skeptical Review (MANDATORY)

Same process. Document in `PHASE_4_REVIEW.md`.

---

## Phase 5: /flow Command (Executor Brick)

**Goal**: Execute workflows from slash command with minimal friction

**Philosophy**: Thin wrapper around DotRunner. Direct, simple, no reimplementation.

**Prerequisites**: Phases 1-4 approved

### Phase 5 Studs

```python
# flow_executor/discovery.py - Sub-brick contract
def list_flows(flows_dir: Path) -> list[FlowInfo]:
    """
    List all available workflows.

    Scans ai_flows/ directory for .yaml files.
    Extracts name, description, required inputs.

    Returns:
        [FlowInfo(name, description, inputs=[...])]
    """

def find_flow(name: str, flows_dir: Path) -> FlowMatch:
    """
    Find workflow file by name (exact or fuzzy).

    Returns:
        FlowMatch with:
        - exact: Path if exact match found
        - fuzzy: list[Path] if multiple fuzzy matches
        - none: empty if no matches
    """

def format_flow_list(flows: list[FlowInfo]) -> str:
    """
    Format flow list for display.

    Returns:
        Formatted string with flow details
    """

# flow_executor/context.py - Sub-brick contract
def extract_required_inputs(workflow: Workflow) -> list[InputSpec]:
    """
    Analyze workflow to find required context variables.

    Scans all node prompts and inputs for {variable} patterns.
    Excludes variables defined in workflow.context.

    Returns:
        [InputSpec(name, description, type_hint)]
    """

def collect_context_simple(required: list[InputSpec]) -> dict[str, Any]:
    """
    Collect context using structured prompts.

    For each required input:
    - Show name and description
    - Prompt user with input()
    - Parse into appropriate type

    Returns:
        {input_name: value}
    """

# flow_executor/executor.py - Sub-brick contract
def execute_workflow(
    workflow_path: Path,
    context: dict[str, Any],
    stream_output: bool = True
) -> ExecutionResult:
    """
    Execute workflow using DotRunner CLI.

    Calls: dotrunner run <path> --context '<json>'
    Streams stdout/stderr if stream_output=True.

    Returns:
        ExecutionResult(
            status="completed"|"failed",
            session_id=str,
            output=str,
            error=str|None
        )
    """

def stream_dotrunner_output(process: subprocess.Popen) -> None:
    """
    Stream DotRunner output to console in real-time.

    Displays progress as workflow executes.

    Returns:
        None (prints to console)
    """
```

### Phase 5 Tasks

**5.1: Flow Discovery Sub-Brick** (TEST-FIRST)

Tests define the stud:
```python
def test_list_flows_returns_all_yaml():
    flows = list_flows(Path("ai_flows"))
    assert all(f.name.endswith(".yaml") for f in flows)

def test_find_flow_exact_match():
    match = find_flow("evidence-based-development", Path("ai_flows"))
    assert match.exact is not None
    assert match.exact.name == "evidence-based-development.yaml"

def test_find_flow_fuzzy_match():
    match = find_flow("evidence", Path("ai_flows"))
    assert len(match.fuzzy) > 0

def test_find_flow_no_match():
    match = find_flow("nonexistent", Path("ai_flows"))
    assert match.exact is None
    assert len(match.fuzzy) == 0
```

Implementation (AFTER tests):
- Glob ai_flows/*.yaml files
- Simple substring matching for fuzzy
- Parse YAML header for metadata
- NO complex indexing or caching

**Evidence**: Discovery tests pass

**5.2: Context Extraction Sub-Brick** (TEST-FIRST)

Tests define the stud:
```python
def test_extract_required_inputs_from_prompts():
    workflow = Workflow(nodes=[
        Node(prompt="Do {task} for {project}")
    ])
    inputs = extract_required_inputs(workflow)
    assert set(i.name for i in inputs) == {"task", "project"}

def test_exclude_workflow_context_variables():
    workflow = Workflow(
        context={"project": "myapp"},
        nodes=[Node(prompt="Do {task} for {project}")]
    )
    inputs = extract_required_inputs(workflow)
    assert "project" not in [i.name for i in inputs]
```

Implementation (AFTER tests):
- Use DotRunner's context.extract_variables()
- Filter out variables in workflow.context
- Return InputSpec objects
- NO type inference initially (all strings)

**Evidence**: Extraction tests pass

**5.3: Context Collection Sub-Brick** (TEST-FIRST)

Tests define the stud:
```python
def test_collect_context_prompts_for_each(monkeypatch):
    required = [
        InputSpec("task", "What to do"),
        InputSpec("project", "Project name")
    ]
    inputs = ["implement auth", "webapp"]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))

    context = collect_context_simple(required)
    assert context == {"task": "implement auth", "project": "webapp"}
```

Implementation (AFTER tests):
- Loop through required inputs
- Use input() for each
- Store in dict
- NO validation initially (just collect)

**Evidence**: Collection tests pass

**5.4: Executor Sub-Brick** (TEST-FIRST)

Tests define the stud:
```python
def test_execute_workflow_calls_dotrunner():
    # Mock subprocess
    result = execute_workflow(
        Path("ai_flows/test.yaml"),
        {"input": "value"},
        stream_output=False
    )
    # Verify subprocess.run called with correct args
    # Verify result status is set

def test_execute_workflow_handles_failure():
    # Mock failed dotrunner execution
    result = execute_workflow(Path("bad.yaml"), {})
    assert result.status == "failed"
    assert result.error is not None
```

Implementation (AFTER tests):
- Build dotrunner command: `dotrunner run <path> --context '<json>'`
- Use subprocess.run() or subprocess.Popen()
- Parse output for session_id
- Return ExecutionResult
- NO output streaming initially

**Evidence**: Executor tests pass

**5.5: Output Streaming Enhancement** (TEST-FIRST)

Tests define the stud:
```python
def test_stream_output_displays_progress(capsys):
    # Mock Popen with fake output
    # Call stream_dotrunner_output()
    # Verify output captured in capsys
```

Implementation (AFTER tests):
- Use subprocess.Popen() instead of run()
- Read stdout/stderr line-by-line
- Print to console in real-time
- Handle process termination

**Evidence**: Streaming works, output visible

**5.6: Slash Command Definition** (MANUAL TEST)

Create `.claude/commands/flow.md`:
```markdown
# /flow Command

Execute DotRunner workflows from ai_flows/ directory.

## Usage

/flow                          # List available workflows
/flow <name>                   # Execute workflow by name
/flow <name> <natural language context>  # With context

## Examples

/flow evidence-based-development
/flow code-review files=auth.py,users.py project=webapp
```

Wire command to executor:
- Command delegates to flow-executor agent (or calls CLI directly)
- Agent handles discovery, context collection, execution
- Results streamed to chat

Manual test in Claude Code:
- Test `/flow` alone (lists workflows)
- Test `/flow <name>` (executes)
- Test with context
- Test fuzzy matching

**Evidence**: Command works in Claude Code

**5.7: Integration Test** (TEST-FIRST)

Tests define complete flow:
```python
def test_end_to_end_flow_execution():
    # Create workflow with flow-builder
    # Find it with discovery
    # Extract required inputs
    # Collect context (mock input)
    # Execute workflow
    # Verify execution successful
```

**Evidence**: E2E test passes

### Phase 5 Skeptical Review (MANDATORY)

**DO NOT PROCEED TO PHASE 6 UNTIL:**

1. **Run ALL tests** - 100% must pass
2. **Check test coverage** - Must be > 90%
3. **Manual workflow execution**:
   - Run `/flow` in Claude Code
   - List workflows successfully
   - Execute a workflow
   - Verify results displayed
   - Check DotRunner session created
4. **Code review with skeptical eye**:
   - Is executor truly thin wrapper?
   - Any DotRunner reimplementation?
   - Any unnecessary complexity?
   - Can any code be deleted?
5. **Brick regeneration test**:
   - Pick executor.py or discovery.py
   - Delete implementation (keep tests)
   - Rewrite from contract
   - Tests should still pass
6. **Document gaps found**

**Review Deliverable**: `PHASE_5_REVIEW.md` with:
- Test results (all passing)
- Coverage report (>90%)
- Manual test results (command works in Claude Code)
- Code skepticism findings (list simplifications made)
- Brick regeneration test (which brick, did it work)
- Approval to proceed (YES/NO)

**Only proceed if approval is YES**

---

## Phase 6: Natural Language Context Parsing

**Goal**: Let users provide context naturally instead of structured prompts

**Philosophy**: Simple AI parsing with fallback. Don't over-engineer.

**Prerequisites**: Phases 1-5 MUST be approved before starting

### Phase 6 Studs

```python
# flow_executor/nl_parser.py - New sub-brick
def parse_natural_language(user_input: str, required_fields: list[str]) -> dict[str, Any]:
    """
    Parse natural language into structured context.

    Example:
      Input: "implement auth for webapp using jwt"
      Required: ["feature", "project", "technology"]
      Output: {"feature": "auth", "project": "webapp", "technology": "jwt"}

    Uses LLM to extract values. If extraction fails or ambiguous, return None.

    Returns:
        dict with extracted values, or None if unparseable
    """

def confirm_parsed_context(parsed: dict, required: list[str]) -> bool:
    """
    Show parsed context to user for confirmation.

    Displays what was understood.
    Asks: "Is this correct? [Y/n/edit]"

    Returns:
        True if confirmed, False if user wants to redo
    """
```

### Phase 6 Tasks

**6.1: NL Parser Sub-Brick** (TEST-FIRST)
- Tests define: extracts values from natural language
- Tests define: returns None for ambiguous input
- Implementation: Simple LLM call with structured prompt
- NO complex NLP, just AI extraction

**6.2: Confirmation Flow** (TEST-FIRST)
- Tests define: shows parsed values to user
- Tests define: allows re-input on rejection
- Implementation: Rich table display + input()

**6.3: Fallback to Structured** (TEST-FIRST)
- Tests define: falls back if NL parsing fails
- Implementation: detect None return, use structured prompts
- Log that NL failed (for improvement)

**6.4: Integration with Executor** (TEST-FIRST)
- Tests define: executor tries NL first, falls back second
- Implementation: update flow_executor/context.py

### Phase 6 Skeptical Review (MANDATORY)

1. Tests pass (100%)
2. Coverage > 90%
3. Manual test: NL parsing works for common cases
4. Manual test: Fallback works when NL fails
5. Code review: Is parsing simple? Any over-engineering?
6. Brick regeneration test on nl_parser.py
7. Document in `PHASE_6_REVIEW.md`
8. Approval YES/NO

---

## Phase 7: Interactive Test Mode

**Goal**: Let users validate workflows by simulating execution

**Philosophy**: Simple step-through. User provides mock outputs.

**Prerequisites**: Phases 1-6 approved

### Phase 7 Studs

```python
# flow_builder/test_mode.py - New sub-brick
def start_test_session(workflow: Workflow) -> TestSession:
    """
    Begin interactive test session for workflow.

    Returns:
        TestSession object that tracks state
    """

class TestSession:
    """
    Manages interactive testing state.

    Methods:
        - show_current_node() -> None: Display current node info
        - collect_outputs() -> dict: Get mock outputs from user
        - evaluate_routing() -> str: Determine next node based on outputs
        - is_complete() -> bool: Check if workflow finished
    """

def save_test_recording(session: TestSession, output_path: Path) -> None:
    """
    Save test session as reusable test file.

    Format: Simple YAML with node_id -> outputs mapping

    Returns:
        None (writes file)
    """
```

### Phase 7 Tasks

**7.1: TestSession Class** (TEST-FIRST)
- Tests define: tracks workflow state through nodes
- Tests define: evaluates routing based on mock outputs
- Implementation: Simple state machine

**7.2: Interactive Collection** (TEST-FIRST)
- Tests define: prompts user for each output
- Tests define: parses natural language outputs
- Implementation: Use input() + simple parsing

**7.3: Test Recording** (TEST-FIRST)
- Tests define: saves session to YAML
- Tests define: YAML is valid test format
- Implementation: PyYAML dump with structure

**7.4: CLI Integration** (TEST-FIRST)
- Tests define: `amplifier flow-builder --test <workflow>`
- Implementation: Add test mode to CLI

### Phase 7 Skeptical Review (MANDATORY)

Same rigorous process. Document in `PHASE_7_REVIEW.md`.

---

## Phase 8: Error Handling & Edge Cases

**Goal**: Robust error handling with helpful messages

**Philosophy**: Handle common errors gracefully, fail fast on bugs

**Prerequisites**: Phases 1-7 approved

### Phase 8 Studs

```python
# All modules - Error handling contract
"""
Every public function must:
1. Validate inputs
2. Provide helpful error messages
3. Fail fast on programming errors
4. Recover gracefully from user errors
"""

# flow_builder/errors.py - New sub-brick
class FlowBuilderError(Exception):
    """Base exception with user-friendly message"""

class InvalidWorkflowError(FlowBuilderError):
    """Workflow validation failed"""

class AgentNotFoundError(FlowBuilderError):
    """Specified agent doesn't exist"""

def format_error_message(error: Exception) -> str:
    """
    Convert exception to user-friendly message.

    Includes:
    - What went wrong
    - Why it happened
    - How to fix it

    Returns:
        Formatted error message
    """
```

### Phase 8 Tasks

**8.1: Error Classes** (TEST-FIRST)
- Tests define: exception hierarchy
- Tests define: user-friendly messages
- Implementation: Simple exception classes

**8.2: Input Validation** (TEST-FIRST)
- Tests define: validates all user inputs
- Tests define: provides fix suggestions
- Implementation: Add validation to each input point

**8.3: Error Recovery** (TEST-FIRST)
- Tests define: allows retry on user errors
- Tests define: exits fast on programming errors
- Implementation: Add try/except with recovery

**8.4: Edge Case Handling** (TEST-FIRST)
- Tests for:
  - Empty ai_flows/ directory
  - No agents found
  - Malformed YAML
  - Invalid workflow names (special chars)
  - Very long inputs
  - Network failures (for AI calls)

### Phase 8 Skeptical Review (MANDATORY)

Focus on:
- Are error messages actually helpful?
- Can users recover from errors?
- Are edge cases handled?

Document in `PHASE_8_REVIEW.md`.

---

## Phase 9: Example Workflows

**Goal**: Provide working examples users can learn from

**Philosophy**: Real, useful workflows, not toy examples

**Prerequisites**: Phases 1-8 approved

### Phase 9 Deliverables

Create 5 example workflows that actually work:

**9.1: evidence-based-development.yaml**
- Implements feature → verifies evidence → deploys or refactors
- Uses: modular-builder, test-coverage, deployment-specialist
- Demonstrates: conditional routing, evidence-based approach

**9.2: code-review.yaml**
- Checks style → runs tests → reviews architecture
- Uses: code-reviewer, test-coverage, zen-architect
- Demonstrates: linear flow, multiple agents

**9.3: bug-fix-workflow.yaml**
- Reproduces bug → fixes → tests → verifies
- Uses: bug-hunter, modular-builder, test-coverage
- Demonstrates: conditional routing (if tests pass → deploy)

**9.4: documentation-generator.yaml**
- Analyzes code → writes docs → reviews → publishes
- Uses: analysis-engine, zen-architect, deployment-specialist
- Demonstrates: linear flow, documentation pattern

**9.5: refactor-workflow.yaml**
- Analyzes complexity → plans refactor → implements → tests
- Uses: zen-architect, modular-builder, test-coverage
- Demonstrates: multi-step transformation

### Phase 9 Tasks

**For EACH example:**

**9.X.1: Create Workflow** (TEST-FIRST)
- Write test: workflow loads without errors
- Write test: workflow passes validation
- Create YAML file

**9.X.2: Test Execution** (MANUAL)
- Run workflow with real agents
- Verify it completes successfully
- Document any issues found
- Fix workflow or underlying code

**9.X.3: Add Documentation** (TEST-FIRST)
- Write test: README exists and is complete
- Add inline comments to YAML
- Create example outputs
- Document expected behavior

### Phase 9 Skeptical Review (MANDATORY)

For this phase:
1. All examples execute successfully (100%)
2. All examples are documented
3. Examples demonstrate different patterns
4. Examples are actually useful (not toys)
5. Code review: Are examples simple and clear?
6. Document in `PHASE_9_REVIEW.md`

---

## Phase 10: Documentation

**Goal**: Complete, accurate documentation for users and developers

**Philosophy**: Documentation is part of the product, not an afterthought

**Prerequisites**: Phases 1-9 approved

### Phase 10 Deliverables

**10.1: User Documentation**

Create `ai_flows/README.md`:
- What are workflows?
- How to use `/flow` command
- How to view available flows
- How to provide context
- Troubleshooting common issues
- Examples with screenshots

**10.2: Flow Builder Guide**

Create `amplifier/flow_builder/README.md`:
- How to create workflows
- Interrogation process
- Agent selection
- Testing workflows
- Best practices
- Common patterns

**10.3: Developer Documentation**

Create `amplifier/flow_builder/ARCHITECTURE.md`:
- System architecture (with diagrams)
- Brick & stud structure
- How to add new sub-bricks
- How to regenerate bricks
- Testing strategy
- Philosophy alignment

Create `amplifier/flow_builder/TESTING.md`:
- How to run tests
- Coverage requirements
- Writing new tests
- Test-first process

**10.4: Contribution Guide**

Create `amplifier/flow_builder/CONTRIBUTING.md`:
- How to extend system
- Adding new features
- Skeptical review process
- Code standards
- Philosophy principles

### Phase 10 Tasks

**For EACH document:**

**10.X.1: Write Documentation** (TEST-FIRST where applicable)
- Write test: document exists
- Write test: document has required sections
- Create document with complete content

**10.X.2: Accuracy Check** (MANUAL)
- Follow documentation step-by-step
- Verify all instructions work
- Fix any inaccuracies
- Test all code examples

**10.X.3: Clarity Review** (MANUAL)
- Can someone unfamiliar understand it?
- Are examples clear?
- Is it well-organized?
- Improve based on feedback

### Phase 10 Skeptical Review (MANDATORY)

For this phase:
1. All documents exist and are complete
2. All documents are accurate (manually verified)
3. All code examples work
4. Documentation is clear and well-organized
5. Can a new developer use the documentation?
6. Document in `PHASE_10_REVIEW.md`

---

## Phase 11: End-to-End Integration Testing

**Goal**: Verify entire system works together flawlessly

**Philosophy**: Test real scenarios, not artificial ones

**Prerequisites**: Phases 1-10 approved

### Phase 11 Test Scenarios

**11.1: Complete User Journey - Creation**
- User has idea for workflow
- Runs `amplifier flow-builder`
- Answers questions naturally
- Gets working workflow file
- Workflow validates successfully

**11.2: Complete User Journey - Testing**
- User tests workflow interactively
- Provides mock outputs for each step
- Sees routing decisions
- Workflow completes test successfully
- Test file is generated

**11.3: Complete User Journey - Execution**
- User runs `/flow <name>`
- Provides context naturally
- Workflow executes via DotRunner
- Results are displayed
- Session is saved

**11.4: Error Recovery Journey**
- User provides invalid input
- System shows helpful error
- User corrects input
- Workflow completes successfully

**11.5: AI Recommendation Journey**
- User describes vague task
- System recommends appropriate agent
- User overrides with different agent
- Workflow still works correctly

**11.6: Flow Composition Journey**
- User starts creating workflow
- System detects similar existing flow
- User decides to reuse existing flow
- Composition works correctly

### Phase 11 Tasks

**11.1: E2E Test Suite** (AUTOMATED)
- Write comprehensive integration tests
- Test all user journeys
- Test all error paths
- Use real DotRunner, real agents

**11.2: Manual Testing** (HUMAN)
- Follow each journey manually
- Document results
- Find any issues
- Verify user experience is smooth

**11.3: Performance Testing** (AUTOMATED)
- Test with many workflows (20+)
- Test with long workflows (10+ nodes)
- Test AI call latency
- Document performance characteristics

**11.4: Stress Testing** (AUTOMATED)
- Test with malformed inputs
- Test with network failures
- Test with missing agents
- Test with corrupt workflow files

### Phase 11 Skeptical Review (MANDATORY)

For this phase:
1. All E2E tests pass (100%)
2. All manual journeys successful
3. Performance is acceptable
4. Stress tests handled gracefully
5. User experience is smooth
6. System is production-ready
7. Document in `PHASE_11_REVIEW.md`

---

## Phase 12: Final Skeptical Review & Launch Readiness

**Goal**: Comprehensive review of entire system before declaring done

**Philosophy**: Assume there are still issues until proven otherwise

**Prerequisites**: Phases 1-11 approved

### Phase 12 Review Process

**12.1: Complete System Audit**
- Review all phase review documents
- Check all approvals are documented
- Verify all tests still pass
- Verify all coverage still > 90%

**12.2: Fresh Eyes Review**
- Have someone unfamiliar review system
- Can they understand it?
- Can they use it?
- Can they extend it?
- Document feedback

**12.3: Philosophy Audit**
- Is system ruthlessly simple?
- Are all bricks regeneratable?
- Are all studs clear and stable?
- Can we delete anything?
- Is this maintainable long-term?

**12.4: Security Review**
- Check for command injection (subprocess calls)
- Check for path traversal (file operations)
- Check for unsafe AI prompts
- Check for data leakage
- Fix any vulnerabilities

**12.5: Production Readiness**
- Error handling comprehensive?
- Documentation complete?
- Examples all work?
- Performance acceptable?
- Can users actually use it?

### Phase 12 Deliverables

**12.1: FINAL_REVIEW.md**
Document:
- System audit results
- Fresh eyes feedback
- Philosophy audit findings
- Security review results
- Production readiness assessment
- Final approval: GO/NO-GO

**12.2: LAUNCH_CHECKLIST.md**
- All tests passing (link to results)
- All coverage > 90% (link to reports)
- All documentation complete (links)
- All examples working (verification)
- All security issues resolved
- All phase reviews approved
- System ready for users

### Phase 12 Approval Gate

**Only declare DONE if:**
- FINAL_REVIEW.md says GO
- LAUNCH_CHECKLIST.md 100% complete
- No outstanding issues
- System demonstrably simple
- System demonstrably correct

---

## Test-First Discipline

### The Cycle (For Every Sub-Brick)

```
1. Write contract (stud definition)
   ↓
2. Write tests that verify contract
   ↓
3. Run tests → RED (they fail, no implementation)
   ↓
4. Write simplest implementation that passes
   ↓
5. Run tests → GREEN (they pass)
   ↓
6. Refactor to remove duplication
   ↓
7. Run tests → GREEN (still pass)
   ↓
8. Review: Can I delete code?
   ↓
9. If yes, delete and go to step 7
   ↓
10. If no, done
```

### Coverage Requirements

- **Minimum**: 90% for each module
- **Studs (contracts)**: 100% - every contract function must be tested
- **Internal implementation**: Can be lower, we test through contracts

### When Tests Can Be Skipped

- Setup tasks (directory creation)
- Documentation
- That's it. Everything else needs tests.

---

## Skeptical Review Process (After EVERY Phase)

### Review Checklist

**1. Test Results**
- [ ] Run full test suite
- [ ] 100% of tests pass
- [ ] Coverage > 90%
- [ ] Save coverage report

**2. Manual Testing**
- [ ] Follow user workflow end-to-end
- [ ] Try to break it (edge cases, bad input)
- [ ] Verify integration with DotRunner works
- [ ] Document test steps and results

**3. Code Review (Assume There Are Issues)**
- [ ] Read every file
- [ ] Question every abstraction
- [ ] Find unnecessary complexity
- [ ] Delete code that doesn't earn its keep
- [ ] Document what was simplified

**4. Brick Regeneration Test** (Validation Exercise)

> **Note**: This is a "rebuild drill" to prove our architecture works, NOT regular practice.
> We temporarily rewrite ONE brick to validate that contracts are clear and tests verify behavior.
> We keep whichever implementation is simpler and works. This happens once per phase review.

- [ ] Pick one sub-brick at random
- [ ] Delete implementation (keep tests and contract)
- [ ] Rewrite from scratch using only contract + tests
- [ ] Verify tests still pass with new implementation
- [ ] Compare new vs old implementation: which is simpler?
- [ ] **Keep the simpler, working implementation** (new or old)
- [ ] Document which was kept and why

**5. Philosophy Alignment**
- [ ] Is this ruthlessly simple?
- [ ] Are bricks self-contained?
- [ ] Are studs clear and stable?
- [ ] Can I explain every line in one sentence?
- [ ] What can I delete?

**6. Documentation**
- [ ] Create `PHASE_X_REVIEW.md`
- [ ] Include all checklist items above
- [ ] List all issues found (even if fixed)
- [ ] List all simplifications made
- [ ] Approval decision: YES or NO

**7. Approval Gate**
- [ ] If NO: Fix issues, repeat review
- [ ] If YES: Document approval, move to next phase

### Review Document Template

```markdown
# Phase X Review

**Date**: YYYY-MM-DD
**Reviewer**: [Name]

## Test Results
- Tests passing: X/X (100%)
- Coverage: X%
- [Attach coverage report]

## Manual Testing
- Workflow tested: [describe]
- Edge cases tried: [list]
- Integration check: [pass/fail]
- Issues found: [list or "none"]

## Code Review Findings
- Unnecessary complexity found: [list]
- Code deleted: [what and why]
- Simplifications made: [list]
- Remaining concerns: [list or "none"]

## Brick Regeneration Test
- Brick tested: [name]
- Regeneration successful: [yes/no]
- New implementation simpler: [yes/no/same]

## Philosophy Check
- Ruthlessly simple: [yes/no + explanation]
- Bricks/studs clear: [yes/no + explanation]
- Can explain every line: [yes/no + what's unclear]
- Could delete more: [what could be deleted]

## Approval Decision
- [X] APPROVED - Proceed to next phase
- [ ] NOT APPROVED - Fix issues (list below)

Issues to fix before approval:
1. ...
```

---

## Success Criteria

### Phase 1
- Create single-node workflow file
- DotRunner executes it successfully
- 100% tests pass, >90% coverage
- Skeptical review approved

### Phase 3
- Create multi-node workflows with routing
- AI recommends appropriate agents
- Users can override recommendations
- Skeptical review approved

### Phase 5
- `/flow` command lists and executes workflows
- Integration with DotRunner seamless
- Context collection works
- Skeptical review approved

### Overall
- Users create workflows without YAML knowledge
- Users execute workflows with simple commands
- All phases have approved reviews
- System is demonstrably simple (can regenerate any brick)

---

## What Success Looks Like

**For Users:**
- "I described what I wanted and got a working workflow in 2 minutes"
- "I can execute any workflow with `/flow <name>`"
- "It just works, no complexity"

**For Developers:**
- "I can regenerate any module from its contract"
- "I can explain every line easily"
- "Tests are clear and comprehensive"
- "No mysterious complexity"

**For Reviewers:**
- "Every phase passed skeptical review"
- "Code is demonstrably simple"
- "Contracts (studs) are stable and clear"
- "System can be maintained long-term"

---

## Anti-Patterns to Avoid

### ❌ Don't Do This:

1. **Speculative Generality**
   - "We might need to support 20 different workflows someday"
   - → No. Build for 1 workflow. Expand when needed.

2. **Premature Abstraction**
   - "Let's create a base class for all interrogators"
   - → No. Wait until you have 3 concrete cases, then abstract.

3. **Flexibility Theater**
   - "This plugin system lets users extend..."
   - → No. YAGNI. Build what's needed now.

4. **Framework Over-Engineering**
   - "Let's use dependency injection for everything"
   - → No. Use simple functions. Pass parameters.

5. **Testing Theater**
   - 100 tests that check implementation details
   - → No. Test contracts (studs), not implementation.

6. **Moving Without Approval**
   - "The review found minor issues, but let's continue"
   - → No. Fix issues. Get approval. Then continue.

### ✅ Do This Instead:

1. **Solve Today's Problem**
   - Build for current, known requirements
   - Expand when new requirements appear

2. **Emerge Abstractions**
   - Write concrete code first
   - Extract patterns when they repeat (3x rule)

3. **Build What's Needed**
   - Every feature must justify its existence
   - "We might need..." = No
   - "We need..." = Maybe
   - "We're using..." = Yes

4. **Keep It Boring**
   - Functions, not frameworks
   - Dicts, not databases (until needed)
   - `input()`, not fancy TUI (until needed)

5. **Test Contracts**
   - Test what the brick promises (studs)
   - Don't test how it does it (internals)

6. **Earn Your Way Forward**
   - Pass review completely
   - Fix all issues
   - Get explicit approval
   - Then proceed

---

## Timeline

**Don't estimate time. Estimate quality checkpoints.**

- Phase 1 is done when it passes skeptical review
- Phase 2 is done when it passes skeptical review
- Each phase is done when we can't find issues

**Speed is NOT a goal. Quality is the goal.**

If a phase takes 1 day or 5 days, it doesn't matter. It's done when it's provably correct.

---

## Next Steps

1. User reviews this plan
2. User approves or requests changes
3. Begin Phase 1.1 (setup)
4. Phase 1.2 (first sub-brick, test-first)
5. ... continue through Phase 1
6. **STOP. Skeptical review. Get approval.**
7. Only then proceed to Phase 2

**No shortcuts. No rushing. No "good enough."**

We build it right, or we don't build it.
