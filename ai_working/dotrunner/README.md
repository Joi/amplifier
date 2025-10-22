# DotRunner: Declarative Agentic Workflows

**Define complex AI agent workflows in simple YAML files.**

## The Problem

You want to orchestrate multiple AI agents to solve complex tasks, but:
- **Orchestration is fragile** - Managing agent sequences, state, and error recovery is complex
- **Progress is lost** - Interruptions mean starting over from scratch
- **Context gets messy** - Passing data between agents is manual and error-prone
- **Workflows aren't reusable** - Each task requires custom code

## The Solution

DotRunner is a workflow orchestration system that:

1. **Defines workflows declaratively** - Express agent sequences in simple YAML "dotfiles"
2. **Manages state automatically** - Resume from any point after interruption
3. **Passes context seamlessly** - Agents receive all previous results automatically
4. **Routes intelligently** - Conditional branching based on AI-evaluated outcomes
5. **Handles errors gracefully** - Retry logic, recovery, and clear error reporting

**The result**: Complex multi-agent workflows that are reliable, resumable, and reusable.

## Quick Start

**Prerequisites**: Complete the [Amplifier setup instructions](../../README.md#-step-by-step-setup) first.

### Basic Usage

```bash
# Run a workflow
python -m ai_working.dotrunner run examples/code_review.yaml

# Resume interrupted workflow
python -m ai_working.dotrunner resume code_review
```

### Your First Workflow

1. **Create a workflow file** (`my_workflow.yaml`):

```yaml
workflow:
  name: "simple-review"
  description: "Analyze and review code"

nodes:
  - id: "analyze"
    name: "Analyze Architecture"
    agent: "zen-architect"
    prompt: |
      Analyze the code in {file_path} and identify:
      - Architecture concerns
      - Potential improvements
    outputs:
      - analysis_report

  - id: "summarize"
    name: "Create Summary"
    prompt: |
      Summarize the analysis:
      {analysis_report}
    outputs:
      - summary
```

2. **Run it**:

```bash
python -m ai_working.dotrunner run my_workflow.yaml --context file_path=src/main.py
```

3. **Results saved automatically** - Find them in `.dotrunner/sessions/simple-review/`

## Usage Examples

### Example 1: Linear Code Review

**File**: `examples/simple_linear.yaml`

```yaml
workflow:
  name: "code-review-flow"
  description: "Automated code review workflow"

nodes:
  - id: "analyze"
    name: "Analyze Code"
    agent: "zen-architect"
    prompt: |
      Analyze the code in {file_path} and identify:
      - Architecture concerns
      - Potential improvements
    outputs:
      - analysis_report

  - id: "find-bugs"
    name: "Hunt for Bugs"
    agent: "bug-hunter"
    prompt: |
      Review the code and analysis:
      {analysis_report}
      Find potential bugs and issues
    outputs:
      - bug_report

  - id: "summarize"
    name: "Create Summary"
    prompt: |
      Summarize findings:
      Analysis: {analysis_report}
      Bugs: {bug_report}
    outputs:
      - final_summary
```

**Run it**:
```bash
python -m ai_working.dotrunner run examples/simple_linear.yaml --context file_path=app.py
```

**What happens**:
- zen-architect analyzes the code
- bug-hunter reviews for issues
- Final summary combines both reports
- All results saved to `.dotrunner/sessions/code-review-flow/`

### Example 2: Conditional Branching

**File**: `examples/pr_review.yaml`

```yaml
workflow:
  name: "pr-review"
  description: "Pull request review with conditional paths"

  context:
    pr_number: "${PR_NUMBER}"
    repo: "owner/repo"

nodes:
  - id: "check-size"
    name: "Check PR Size"
    prompt: "Check if PR has more than 500 lines changed. Return JSON with 'is_large' boolean."
    outputs:
      - is_large
    next:
      - when: "{is_large} == true"
        goto: "deep-review"
      - default: "quick-review"

  - id: "quick-review"
    name: "Quick Review"
    agent: "code-reviewer"
    prompt: "Perform quick review of PR {pr_number}"
    next: "done"

  - id: "deep-review"
    name: "Deep Review"
    agent: "zen-architect"
    prompt: "Perform thorough architecture review of PR {pr_number}"
    next: "security-check"

  - id: "security-check"
    name: "Security Review"
    agent: "security-guardian"
    prompt: "Check for security issues in PR {pr_number}"
    next: "done"

  - id: "done"
    name: "Complete"
    type: "terminal"
```

**Run it**:
```bash
PR_NUMBER=123 python -m ai_working.dotrunner run examples/pr_review.yaml
```

**What happens**:
- Checks PR size
- If large → deep review + security check
- If small → quick review
- Routes automatically based on conditions

### Example 3: Resume After Interruption

If your workflow gets interrupted (API timeout, Ctrl+C, etc.):

```bash
# Resume from where it stopped
python -m ai_working.dotrunner resume pr-review
```

**What happens**:
- Loads saved state
- Skips completed nodes
- Continues from current node
- All previous context preserved

## How It Works

### The Pipeline

```
YAML Workflow Definition
         ↓
   [Parse & Validate]
         ↓
    [Load State] ──────→ Resume from saved position
         ↓
  [Execute Node] ──────→ Delegate to agent
         ↓
   [Save State] ───────→ Incremental checkpoint
         ↓
 [Evaluate Next] ──────→ Condition-based routing
         ↓
  [Loop or Complete]
```

### Key Components

- **Workflow Parser**: Loads and validates YAML workflow definitions
- **Execution Engine**: Orchestrates node execution with state management
- **Node Executor**: Delegates work to specialized agents via subprocess (`amplifier agent`)
- **Condition Evaluator**: Routes based on dict-matching or expressions (Phase 2)
- **State Manager**: Saves progress after every node (incremental checkpoints)

### Why It Works

**Code handles the structure**:
- Workflow parsing and validation
- State persistence and recovery
- Node sequencing and routing
- Error handling and retries

**AI handles the intelligence**:
- Agent task execution
- Condition evaluation for routing
- Context-aware content generation
- Decision making based on outcomes

This separation means workflows are both reliable (code manages flow) and intelligent (AI handles content).

## YAML Schema Reference

### Workflow Structure

```yaml
workflow:
  name: "unique-workflow-id"          # Required: Workflow identifier
  description: "Human-readable desc"  # Required: What this workflow does
  context:                            # Optional: Global context available to all nodes
    key1: "value1"
    key2: "${ENV_VAR}"                # Environment variable expansion

nodes:
  - id: "node-id"                     # Required: Unique node identifier
    name: "Human Name"                # Required: Display name
    agent: "agent-name"               # Optional: Specific agent (default: "auto")
    prompt: |                         # Required: Prompt with context interpolation
      Process {previous_output}
      Do something with {context_var}
    outputs:                          # Optional: Named outputs to capture
      - output_name
    next: "next-node-id"              # Optional: Next node (default: sequential)
    retry_on_failure: 3               # Optional: Retry attempts (default: 1)
    type: "terminal"                  # Optional: Mark as end node
```

### Context Interpolation

Variables in prompts are interpolated from:
1. Global workflow context
2. Previous node outputs
3. Environment variables (via `${VAR}`)

Example:
```yaml
prompt: |
  Review the code at {file_path}
  Considering: {analysis.concerns}
  For PR: {pr_number}
```

### Conditional Routing

```yaml
next:
  - when: "{output_var} == 'value'"
    goto: "node-a"
  - when: "{count} > 10"
    goto: "node-b"
  - default: "node-c"
```

Conditions are evaluated by AI with access to all context.

### Agent Selection

```yaml
agent: "zen-architect"     # Use specific agent
agent_mode: "ANALYZE"      # Optional: Standard mode or natural language
```

**Standard Agent Modes**:
- `ANALYZE` - Examine and break down information
- `EVALUATE` - Assess quality, completeness, or correctness
- `EXECUTE` - Perform actions or implement changes
- `REVIEW` - Check work for issues or improvements
- `GENERATE` - Create new content or artifacts

Natural language modes also supported: `agent_mode: "Check if tests pass and return status"`

**Available agents**:
- `zen-architect` - Architecture analysis and design
- `bug-hunter` - Bug detection and fixing
- `test-coverage` - Test analysis and suggestions
- `security-guardian` - Security review
- `modular-builder` - Code implementation

## Configuration

### Command-Line Options

```bash
# Run workflow
python -m ai_working.dotrunner run WORKFLOW.yaml [OPTIONS]

# Required (choose one)
--context KEY=VALUE     # Pass context variables (multiple allowed)

# Optional
--resume                # Resume from saved state
--reset                 # Start fresh (discard saved state)
--verbose              # Enable detailed logging
--state-dir PATH       # Custom state directory (default: .dotrunner/sessions/)
```

### Resume workflow
```bash
python -m ai_working.dotrunner resume WORKFLOW_NAME [OPTIONS]

# Optional
--verbose              # Enable detailed logging
```

### State Files

All working files saved to `.dotrunner/sessions/<session-id>/`:
- `state.json` - Execution state for resume
- `metadata.json` - Session metadata
- `trace.jsonl` - Execution trace log
- `nodes/<node-id>/` - Per-node input/output files

## Troubleshooting

### "Workflow file not found"

**Problem**: Can't locate the YAML file.

**Solution**: Use full path or relative path from project root.

### "Node X failed after N retries"

**Problem**: Node execution failed repeatedly.

**Solution**:
1. Check `.dotrunner/sessions/<session-id>/state.json` for error details
2. Fix the issue (API key, agent availability, etc.)
3. Resume with `python -m ai_working.dotrunner resume <workflow>`

### "Invalid YAML syntax"

**Problem**: Workflow file has syntax errors.

**Solution**:
- Use a YAML validator
- Check indentation (YAML is whitespace-sensitive)
- Ensure all required fields present

### "Context variable not found"

**Problem**: Prompt references undefined variable `{var_name}`.

**Solution**:
- Check variable name spelling
- Ensure variable defined in context or previous node outputs
- Use `--verbose` to see available context

### "API key not found"

**Problem**: Claude API key isn't configured.

**Solution**: Follow [Amplifier setup instructions](../../README.md#-step-by-step-setup).

## Learn More

- **[DESIGN.md](./DESIGN.md)** - Technical architecture and implementation details
- **[Amplifier Documentation](../../README.md)** - Framework that powers this tool
- **[Blog Writer](../blog_writer/)** - Similar multi-stage AI pipeline

## Implementation Status

**Phase 1 - MVP** (Target: Week 1)
- [ ] YAML workflow parsing and validation
- [ ] Linear workflow execution (no branching)
- [ ] State persistence and resume
- [ ] Basic agent delegation via Task tool
- [ ] Context interpolation in prompts
- [ ] CLI with run/resume commands

**Phase 2 - Conditionals** (Target: Week 2)
- [ ] Conditional branching (if/then)
- [ ] AI-driven condition evaluation
- [ ] Loop support with max iterations
- [ ] Retry logic for node failures

**Phase 3 - Advanced** (Future)
- [ ] Parallel node execution
- [ ] Sub-workflows
- [ ] Dynamic node generation
- [ ] Progress visualization
- [ ] Workflow templates

## What's Next?

DotRunner demonstrates declarative AI orchestration:

1. **Use it** - Define workflows for your complex agent tasks
2. **Extend it** - Add new node types or routing logic
3. **Build with it** - Create reusable workflow patterns
4. **Share back** - Contribute example workflows for others

---

**Built following Amplifier principles** - Ruthless simplicity, code for structure, AI for intelligence.
