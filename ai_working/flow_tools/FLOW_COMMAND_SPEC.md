# /flow Slash Command Specification

**Version**: 1.0.0
**Status**: Draft
**Created**: 2025-01-20

## Purpose

Claude Code slash command for discovering and executing DotRunner workflows with interactive context collection and fuzzy matching.

## Architecture

**Type**: Slash command (`.claude/commands/flow.md`)
**Invocation**: `/flow [flow-name] [optional natural language context]`
**Backend**: Can be an agent or amplifier tool (uses LLM for natural language parsing)

## Core Requirements

### 1. Flow Discovery

**Capability**: Find workflows in `ai_flows/` directory

**Invocation Patterns**:

**Pattern A: List all flows**
```bash
/flow
# → Lists all available flows with descriptions
```

**Pattern B: Execute by name**
```bash
/flow evidence-based-development
# → Looks for ai_flows/evidence-based-development.yaml
```

**Pattern C: Execute by path**
```bash
/flow ./custom/my-workflow
# → Looks for ./custom/my-workflow.yaml from cwd
```

**Pattern D: With inline context**
```bash
/flow code-review feature="authentication"
# → Executes with initial context
```

### 2. Fuzzy Matching

**Capability**: Match partial flow names with user confirmation

**Examples**:
```bash
/flow evidence
# → Found 'evidence-based-development.yaml'
# → "Did you mean 'evidence-based-development'? [Y/n]:"

/flow review
# → Found 2 matches:
#   1. code-review
#   2. architecture-review
# → "Which flow? [1/2]:"
```

**Matching Logic**:
- Exact match → Execute immediately (unless confirmation bypassed)
- Single fuzzy match → Confirm with user
- Multiple matches → Show numbered list, let user choose
- No matches → Show available flows, suggest closest match

**Fuzzy Algorithm**: Simple substring matching (e.g., "evidence" matches "evidence-based-development")

### 3. Flow Confirmation

**Before execution**, show summary:

```
Flow: evidence-based-development
Description: Implements features with evidence verification

This flow will:
  1. Implement feature using modular-builder
  2. Verify evidence using test-coverage
  3. Deploy or refactor based on evidence score

Required inputs:
  • user_request (string): Feature to implement
  • project (string): Project name

Continue? [Y/n]:
```

**Bypass Confirmation**:

If user's command includes phrases like:
- "and run it"
- "just run"
- "go ahead"
- "execute"

Skip confirmation and proceed directly to context collection.

**Example**:
```bash
/flow evidence and run it
# → Skips confirmation, goes straight to input collection
```

### 4. Interactive Context Collection

**Capability**: Use natural language to collect required workflow inputs

**Flow**:

```bash
/flow evidence-based-development

[Shows flow summary and confirmation]
Continue? [Y/n]: y

This flow needs the following inputs:
  • user_request (string): Feature to implement
  • project (string): Project name

You can provide them now:
> I want to implement user authentication for the webapp project

✓ Understood:
  • user_request: "implement user authentication"
  • project: "webapp"

Is this correct? [Y/n/edit]: y

Starting workflow...
```

**Natural Language Parsing**:

User input: `"I want to implement user authentication for the webapp project"`

Parsed context:
```json
{
  "user_request": "implement user authentication",
  "project": "webapp"
}
```

**Parsing Strategy**:
- Use LLM to extract structured data from natural language
- Match extracted values to required input fields
- Ask for clarification if ambiguous or missing

**Alternative: Structured Prompts**

If natural language parsing fails, fall back to explicit prompts:
```
Enter user_request (Feature to implement):
> implement user authentication

Enter project (Project name):
> webapp
```

**Validation**:
- Show parsed context to user for confirmation
- Allow edit/retry if incorrect
- Ensure all required inputs provided

### 5. Execution

**Process**:

1. Load workflow from `ai_flows/<name>.yaml` (or specified path)
2. Collect/parse context interactively
3. Validate context matches workflow requirements
4. Execute via DotRunner: `dotrunner run <workflow-file> --context <json>`
5. Create session in `.dotrunner/sessions/` (normal DotRunner behavior)
6. Stream execution progress to chat
7. Display final results in chat

**Progress Display**:

```
Executing workflow: evidence-based-development
Session: evidence_based_dev_20250120_153045_a3f2

[Node 1/3] implement (modular-builder) - Running...
✓ Completed in 15.2s

[Node 2/3] verify-evidence (test-coverage) - Running...
✓ Completed in 8.5s

Routing: evidence_status = "excellent" → deploy

[Node 3/3] deploy (deployment-specialist) - Running...
✓ Completed in 5.1s

Workflow completed successfully! (28.8s total)

Results:
  • implementation: [implementation details]
  • evidence_status: excellent
  • deployment_status: success

Session saved: .dotrunner/sessions/evidence_based_dev_20250120_153045_a3f2
```

**Error Handling**:

If workflow fails:
```
✗ Workflow failed at node 'verify-evidence'
Error: Missing required test coverage

Session saved for debugging: .dotrunner/sessions/evidence_based_dev_20250120_153045_a3f2
Resume with: dotrunner resume evidence_based_dev_20250120_153045_a3f2
```

### 6. Flow Listing

**Command**: `/flow` (no arguments)

**Output**:
```
Available workflows in ai_flows/:

evidence-based-development
  Implements features with evidence verification
  Inputs: user_request, project
  Outputs: implementation, evidence_status, deployment_status

code-review
  Multi-step code review with style, tests, and architecture
  Inputs: files, project
  Outputs: review_report, approval_status

architecture-review
  Review system architecture for complexity and maintainability
  Inputs: component, design_doc
  Outputs: review_findings, recommendations

Use: /flow <name> to execute a workflow
```

**Formatting**:
- One workflow per section
- Show name, description, inputs, outputs
- Keep concise and scannable
- Sort alphabetically or by recent use

## Technical Implementation

### Implementation Options

**Option A: Pure Slash Command** (simpler)
```markdown
# .claude/commands/flow.md
Execute DotRunner workflows from ai_flows/ directory.

Usage:
  /flow                    # List available flows
  /flow <name>             # Execute workflow
  /flow <path>             # Execute from path

[Rest of prompt instructs Claude how to handle the command]
```

**Option B: Agent-Backed Command** (more powerful)
```markdown
# .claude/commands/flow.md
Execute DotRunner workflows.

This command delegates to the flow-executor agent which handles:
- Flow discovery and fuzzy matching
- Interactive context collection
- Natural language parsing
- Workflow execution and monitoring

Usage: /flow [name] [context]
```

**Recommendation**: **Option B** (agent-backed) for natural language parsing capability

### Module Structure (if agent-backed)

```
amplifier/flow_executor/
├── __init__.py
├── agent.py            # Flow executor agent
├── discovery.py        # Find and match workflows
├── context.py          # Interactive context collection
├── parser.py           # Natural language → structured data
└── executor.py         # DotRunner execution wrapper
```

### Key Dependencies

- **DotRunner**: Workflow execution (`dotrunner run`)
- **Claude Code SDK**: For agent if using Option B
- **Rich**: Terminal output formatting
- **PyYAML**: Parse workflow files for metadata

### Integration Points

- **Workflow Files**: Read from `ai_flows/*.yaml`
- **DotRunner CLI**: Execute via `dotrunner run <file> --context <json>`
- **Session Management**: Leverage `.dotrunner/sessions/`
- **Flow Builder**: Works with workflows created by flow-builder tool

## User Experience Flow

### Flow Listing

```
> /flow

Available workflows in ai_flows/:

evidence-based-development
  Implements features with evidence verification
  Inputs: user_request, project
  Outputs: implementation, evidence_status, deployment_status

code-review
  Multi-step code review with style, tests, and architecture
  Inputs: files, project
  Outputs: review_report, approval_status

Use: /flow <name> to execute
```

### Exact Match with Confirmation

```
> /flow evidence-based-development

Flow: evidence-based-development
Description: Implements features with evidence verification

This flow will:
  1. Implement feature using modular-builder
  2. Verify evidence using test-coverage
  3. Deploy or refactor based on evidence score

Required inputs:
  • user_request (string): Feature to implement
  • project (string): Project name

Continue? [Y/n]: y

This flow needs the following inputs. Provide them naturally:
> implement user authentication for webapp

✓ Understood:
  • user_request: "implement user authentication"
  • project: "webapp"

Correct? [Y/n]: y

Executing workflow: evidence-based-development
...
```

### Fuzzy Match

```
> /flow evidence

Found: evidence-based-development
Did you mean 'evidence-based-development'? [Y/n]: y

[Proceeds to confirmation and execution]
```

### Multiple Matches

```
> /flow review

Found 2 workflows matching 'review':
  1. code-review
  2. architecture-review

Which flow? [1/2]: 1

[Proceeds with code-review]
```

### Bypass Confirmation

```
> /flow evidence-based-development and just run it

This flow needs inputs. Provide them naturally:
> implement user auth for webapp

✓ Understood:
  • user_request: "implement user auth"
  • project: "webapp"

Correct? [Y/n]: y

Executing workflow...
```

### With Inline Context (Natural Language)

```
> /flow code-review with files auth.py and users.py for project webapp

Flow: code-review
Description: Multi-step code review

✓ Pre-parsed context:
  • files: ["auth.py", "users.py"]
  • project: "webapp"

Correct? [Y/n]: y

Executing workflow...
```

### Path-Based Execution

```
> /flow ./experiments/custom-workflow

Flow: custom-workflow (from ./experiments/custom-workflow.yaml)
Description: Experimental workflow

Continue? [Y/n]: y
...
```

### Execution Progress

```
Executing workflow: evidence-based-development
Session: evidence_based_dev_20250120_153045_a3f2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1/3] implement (modular-builder)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Prompt: Implement user authentication for webapp

[Agent output streams here...]

✓ Completed in 15.2s
Outputs: implementation, files_changed, status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2/3] verify-evidence (test-coverage)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Prompt: Verify test coverage for: auth.py, users.py

[Agent output streams here...]

✓ Completed in 8.5s
Outputs: evidence_status = "excellent"

Routing: evidence_status = "excellent" → deploy

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[3/3] deploy (deployment-specialist)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Completed in 5.1s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Workflow completed successfully! (28.8s)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Final Results:
  • implementation: [Full implementation code]
  • files_changed: ["auth.py", "users.py"]
  • evidence_status: excellent
  • deployment_status: success

Session: .dotrunner/sessions/evidence_based_dev_20250120_153045_a3f2
```

## Phase 1 Features (MVP)

- ✅ Flow listing (`/flow` with no args)
- ✅ Exact match execution
- ✅ Fuzzy matching with confirmation
- ✅ Flow summary before execution
- ✅ Bypass confirmation with "run it" phrases
- ✅ Interactive context collection with natural language
- ✅ Context validation and confirmation
- ✅ Progress display during execution
- ✅ Final results display
- ✅ Path-based execution (`/flow ./path`)
- ✅ DotRunner session integration

## Phase 2 Features (Future)

- ⏸ Resume failed workflows from `/flow` command
- ⏸ Flow history (recently executed flows)
- ⏸ Saved context profiles (reuse common inputs)
- ⏸ Dry-run mode (`/flow --dry-run name`)
- ⏸ Watch mode (re-execute on file changes)
- ⏸ Flow composition from command line
- ⏸ Integration with flow-builder (edit flows inline)

## Success Criteria

- ✅ Can discover and execute workflows with simple commands
- ✅ Fuzzy matching reduces typing (e.g., `/flow ev` works)
- ✅ Natural language context parsing feels intuitive
- ✅ Confirmation steps prevent accidental execution
- ✅ Progress display shows what's happening
- ✅ Error messages are actionable
- ✅ Integration with DotRunner is seamless
- ✅ User can execute workflows without knowing YAML syntax

## Philosophy Alignment

- **Ruthless Simplicity**: One command, multiple modes, all natural
- **User-Centric**: Fuzzy matching, natural language, confirmations
- **Fail-Safe**: Confirmation steps, validation, clear errors
- **Transparency**: Shows what will happen before it happens
- **Integration**: Leverages DotRunner without reinventing it
- **Forgiveness**: Fuzzy matching, natural language parsing, edit capabilities
