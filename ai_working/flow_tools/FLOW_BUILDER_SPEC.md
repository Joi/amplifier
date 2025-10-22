# Flow Builder Tool Specification

**Version**: 1.0.0
**Status**: Draft
**Created**: 2025-01-20

## Purpose

Interactive CLI tool for creating DotRunner workflow files through guided interrogation. Discovers available agents and flows, recommends appropriate tools for tasks, and generates validated workflow YAML files.

## Architecture

**Type**: CLI tool wrapping an AI agent
**Location**: `amplifier/flow_builder/`
**Entry Point**: `amplifier flow-builder [description]`
**Agent**: Uses dedicated flow-builder agent for natural language processing

## Core Requirements

### 1. Agent Discovery

**Capability**: Scan and understand available Claude Code agents

**Implementation**:
- Read all TOML files from `.claude/agents/`
- Extract `description` and `custom_instructions` fields
- Use LLM to analyze: "What is this agent good at? What tasks does it handle?"
- Build rich agent catalog with capabilities and use cases
- Cache analysis results for session duration

**Output**: Agent catalog with:
```python
{
    "agent_name": {
        "description": "...",
        "capabilities": ["implementation", "testing", ...],
        "best_for": ["building modules", "fixing bugs", ...],
        "toml_path": Path(...)
    }
}
```

### 2. Flow Discovery

**Capability**: Scan existing flows for composition and avoiding redundancy

**Implementation**:
- Scan `ai_flows/*.yaml` directory
- Parse each workflow to extract:
  - Name, description
  - Required inputs, outputs
  - Node structure (high-level)
- Build flow catalog for recommendations

**Usage**:
- Validate `workflow:` references in nodes
- Suggest existing flows when user describes redundant functionality
- Allow user to ignore suggestions

### 3. Interactive Interrogation

**Modes**:

**Mode 1: Full Interrogation** (no arguments)
```bash
amplifier flow-builder
# → Suggests templates, asks structured questions
```

**Mode 2: Quick Mode** (with description)
```bash
amplifier flow-builder "Create a code review workflow"
# → Uses description as starting point, fills gaps interactively
```

**Information to Extract**:

1. **Task/Goal**: What should this workflow accomplish?
2. **Inputs**: What data does the workflow need to start?
   - Names, types (string, list, dict), descriptions
3. **Outputs**: What should the workflow produce?
   - Names, types, descriptions
4. **Steps**: What are the main steps?
   - For each step:
     - Step purpose/description
     - Recommended agent (with override option)
     - Expected outputs from this step
5. **Routing**: How do steps connect?
   - Linear (A → B → C)
   - Conditional (based on outputs)
   - Success criteria for routing decisions
6. **Workflow Name**: Short kebab-case name for the file

**Interaction Style**:
- Natural language throughout
- Handle informal responses ("just use the builder agent")
- Parse complex inputs naturally ("files are auth.py and users.py")
- Show recommendations with easy override

**Template Suggestions**:

When user needs help, suggest common patterns:
- **Simple Linear**: A → B → C (no branching)
- **Conditional**: A → decision → B or C
- **Evidence-Based**: implement → verify → deploy/refactor
- **Review Loop**: implement → review → fix → review (until approved)

### 4. Agent Recommendation

**For each workflow step**:

```
For step "implement feature":
Recommended: modular-builder (best match for implementation tasks)
Use this agent? [Y/n/suggest agent name]:
```

**Response Handling**:
- `Y` or `yes` or Enter → Use recommended agent
- `n` or `no` → Show all available agents with numbers
- `use XXX` or just `XXX` → Use agent XXX (validate it exists)

**Recommendation Logic**:
- Use LLM with agent catalog to match step description to agent capabilities
- Consider: step purpose, required outputs, agent strengths
- Prefer agents that have handled similar tasks

### 5. Workflow Validation

**Structural Validation**:
- No circular dependencies (detect cycles in routing)
- All `next` references point to valid node IDs
- All `workflow` references point to existing files in `ai_flows/`
- Node IDs are unique
- At least one node exists
- Required fields present (name, description, nodes)

**Complexity Validation**:
- Warn if > 10 nodes (suggest breaking into sub-flows)
- Encourage composition for complex workflows

**Output Validation**:
- All output references in prompts/inputs exist in prior nodes
- Context variable references are valid

### 6. Interactive Test Mode

**Purpose**: Let human simulate agent responses to validate workflow logic

**Flow**:
```
Flow Builder: "Let's test the flow interactively."
Flow Builder: "Starting at node 'design' (agent: zen-architect)"
Flow Builder: "This node would receive: {feature: 'user auth'}"
Flow Builder: "What should this node output? (or type 'skip' to skip testing)"
User: "design_doc: Here's a simple auth design..."
Flow Builder: "Moving to node 'implement' (agent: modular-builder)"
Flow Builder: "This node would receive: {design_doc: 'Here's a simple...'}"
User: "implementation: [auth code], files_changed: ['auth.py'], status: success"
Flow Builder: "Routing check - 'status' output is 'success', going to 'verify'"
Flow Builder: "At node 'verify' (agent: test-coverage)"
User: "skip"
Flow Builder: "Test complete! Would you like to save test responses as a test file?"
```

**Test Response Format**:
- Accepts natural language: `"status is success, files are auth.py"`
- Parses into structured outputs: `{status: "success", files: ["auth.py"]}`
- Shows routing decisions based on outputs
- Allows skip for any node

### 7. Test File Generation

**Purpose**: Create automated test files from interactive test sessions or AI generation

**Format** (machine-focused, not human-readable priority):
```yaml
# ai_flows/tests/evidence_based_dev_test.yaml
workflow: evidence-based-development
test_cases:
  - name: happy_path
    description: "Successful implementation with evidence"
    initial_context:
      user_request: "implement user authentication"
      project: "myapp"

    node_outputs:
      - node_id: implement
        outputs:
          implementation: "Mock implementation code..."
          files_changed: ["auth.py", "users.py"]
          status: "success"

      - node_id: verify-evidence
        outputs:
          evidence_score: 0.85
          evidence_status: "excellent"

      - node_id: deploy
        outputs:
          deployment_status: "success"

    expected_path: ["implement", "verify-evidence", "deploy"]
    expected_status: "completed"

  - name: low_evidence_path
    description: "Implementation needs refactoring"
    # ... similar structure
```

**Generation Modes**:
1. **From Interactive Session**: Capture user's test responses
2. **AI Generated**: Tool generates realistic test scenarios automatically
3. **Hybrid**: User provides one example, AI generates variations

**Usage**: Test files can be run by DotRunner in test mode (Phase 2 feature)

### 8. Output Generation

**File Location**: `ai_flows/<workflow-name>.yaml`

**Workflow Structure**:
```yaml
name: "workflow-name"
description: "Human-readable description"
version: "1.0.0"

context:
  # Global context variables if needed
  project: "myapp"

nodes:
  - id: "step-1"
    name: "Step Name"
    agent: "agent-name"
    agent_mode: "EXECUTE"  # or natural language
    prompt: "Do task with {input_var}"
    inputs:
      input_var: "{user_input}"
    outputs:
      - output_var
      - status
    next: "step-2"  # or conditional dict

  - id: "step-2"
    # ...
```

**Post-Generation Actions**:
1. Save workflow file
2. Display summary of created workflow
3. Offer to run interactive test mode
4. Suggest: `Use '/flow workflow-name' to execute this workflow`

## User Experience Flow

### Full Interrogation Mode

```
$ amplifier flow-builder

Welcome to Flow Builder!

I'll help you create a workflow. First, let me discover available agents...
✓ Found 15 agents in .claude/agents/
✓ Analyzing agent capabilities...
✓ Scanning existing flows in ai_flows/...

What should this workflow accomplish?
> Create a code review workflow that checks style, tests, and architecture

Great! Let me suggest some existing flows:
• I found 'code-quality-check' which validates code style and tests
  → Use this as a step? [Y/n]: n

Alright, let's build it from scratch.

What inputs does this workflow need?
> files to review, and the project name

Got it:
  • files (list): Files to review
  • project (string): Project name

What outputs should it produce?
> review report, approval status

Outputs:
  • review_report (string): Review findings
  • approval_status (string): Pass/fail decision

Let's define the steps. How many main steps? [suggest: 3-5]
> 3 steps

Step 1 - What should this step do?
> check code style

Recommended agent: modular-builder
Use this agent? [Y/n/suggest agent name]: n, use code-reviewer

✓ Using code-reviewer

What outputs from this step?
> style_issues, style_status

Step 2 - What should this step do?
> run tests
...

How should steps connect?
> if style_status is pass, go to step 2, otherwise stop

✓ Conditional routing configured

What should we name this workflow?
> code-review-workflow

Validating workflow...
✓ No circular dependencies
✓ All references valid
✓ 3 nodes (under 10 node limit)

Workflow saved to: ai_flows/code-review-workflow.yaml

Would you like to test it interactively? [Y/n]:
```

### Quick Mode

```
$ amplifier flow-builder "Create a code review workflow"

Analyzing request...
✓ Found existing flows: code-quality-check
✓ Identified goal: Code review workflow

I understand you want to create a code review workflow.

What inputs does it need? [suggest: files, project]
> yes use those

What are the main steps? [suggest: style-check → test-run → review]
> yes that works

Recommended agents:
  • style-check: code-reviewer
  • test-run: test-coverage
  • review: zen-architect

Use these? [Y/n]:
> yes

Generating workflow...
✓ Workflow saved to: ai_flows/code-review-workflow.yaml

Test it interactively? [Y/n]:
```

## Technical Implementation

### Module Structure

```
amplifier/flow_builder/
├── __init__.py
├── cli.py              # Click CLI entry point
├── agent.py            # Flow builder agent wrapper
├── discovery.py        # Agent and flow discovery
├── interrogation.py    # Interactive Q&A logic
├── validation.py       # Workflow validation
├── test_mode.py        # Interactive test mode
├── generator.py        # YAML generation
└── test_file.py        # Test file generation
```

### Key Dependencies

- **Click**: CLI framework
- **Rich**: Beautiful terminal output
- **TOML**: Parse agent files
- **PyYAML**: Read/write workflows
- **Claude Code SDK**: Agent execution
- **DotRunner**: Workflow validation (use Workflow.from_yaml, .validate())

### Integration Points

- **Agent Discovery**: Read `.claude/agents/*.toml`
- **Flow Discovery**: Read `ai_flows/*.yaml`
- **Validation**: Use `dotrunner.workflow.Workflow.validate()`
- **Test Files**: Store in `ai_flows/tests/<workflow-name>_test.yaml`

## Phase 1 Features (MVP)

- ✅ Agent discovery with AI analysis
- ✅ Flow discovery for composition awareness
- ✅ Interactive interrogation (both modes)
- ✅ Agent recommendation with override
- ✅ Workflow validation (structure + complexity)
- ✅ Interactive test mode
- ✅ Test file generation (from interactive session)
- ✅ YAML output to `ai_flows/`

## Phase 2 Features (Future)

- ⏸ Edit existing workflows (`--edit` flag)
- ⏸ Test file execution (DotRunner test runner)
- ⏸ AI-generated test scenarios (without human interaction)
- ⏸ Template library with common patterns
- ⏸ Workflow visualization (ASCII graph)
- ⏸ Version control integration (git hooks for workflow changes)
- ⏸ Workflow diff tool (compare versions)

## Success Criteria

- ✅ Can create valid DotRunner workflows through conversation
- ✅ Recommends appropriate agents for tasks
- ✅ Detects and suggests existing flows to avoid duplication
- ✅ Validates workflows before saving
- ✅ Interactive test mode validates routing logic
- ✅ Generates workflows that execute successfully with `/flow` command
- ✅ User can go from idea to working workflow in < 5 minutes

## Philosophy Alignment

- **Ruthless Simplicity**: No complex configuration, just conversation
- **Code for Structure, AI for Intelligence**: CLI provides structure, agent handles understanding
- **User-Centric**: Natural language throughout, no technical YAML knowledge required
- **Quality over Speed**: Takes time to analyze agents properly
- **Composition over Complexity**: Encourages small, composable flows
- **Test-First Thinking**: Built-in testing from the start
