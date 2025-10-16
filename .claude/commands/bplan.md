# Interactive Project Planning with /bplan

You are orchestrating Brian's multi-stage project planning and execution workflow using beads for issue tracking. This is a comprehensive, interactive process that guides projects from conception to completion with test-first discipline.

## Workflow Overview

```
User → Stage 1: Intake → Stage 2: Planning → Stage 3: Execution → Stage 4: Review → Stage 5: Final Reconciliation
         ↓                ↓                     ↓                    ↓                ↓
      Questions      project-planner      phase-executor      phase-reviewer     project-planner
         ↓                ↓                     ↓                    ↓                ↓
      Context         Beads Epic          Beads Updates       Approval/Fix      Completion Check
```

## User's Project Request

$ARGUMENTS

## Stage 1: Interactive Project Intake

**Ask the user these questions ONE AT A TIME** (don't overwhelm them):

1. **Project Description**: "What would you like to build?" (if not provided above)

2. **Existing Documentation**: "Do you have any planning documents, specs, or notes? (provide file paths or say 'none')"

3. **Key Requirements**: "What are the must-have features or requirements?"

4. **Constraints**: "Are there any technical constraints, deadlines, or limitations I should know about?"

5. **Definition of Done**: "How will we know this project is successfully complete?"

6. **Context Files**: "Are there specific files, modules, or docs I should review for context? (use @mentions or say 'you decide')"

**After gathering answers**, create a project brief:

```markdown
# Project Brief: [Project Name]

## Goal
[What needs to be built - 2-3 sentences]

## Requirements
- [Requirement 1]
- [Requirement 2]
[...]

## Constraints
- [Constraint 1 if any]

## Success Criteria
- [Criterion 1]
- [Criterion 2]

## Context
[Relevant files/modules/patterns to follow]
```

**Ask**: "Does this brief accurately capture your project? (yes/adjust)"

If "adjust": Get clarifications and update brief.
If "yes": Proceed to Stage 2.

## Stage 2: Discovery & Planning

**Use the `project-planner` agent** to analyze and create the plan:

```
Task for project-planner agent:

Analyze this project and create a detailed, phased implementation plan:

[Insert project brief]

Requirements:
1. Review @ai_context/IMPLEMENTATION_PHILOSOPHY.md and @ai_context/MODULAR_DESIGN_PHILOSOPHY.md
2. Analyze codebase for relevant patterns (use Glob/Grep extensively)
3. Break project into test-first phases
4. Define acceptance criteria for each phase
5. Specify test strategy (antagonistic, no cheating)
6. Create beads epic and phase issues
7. Define dependencies between phases

Output a comprehensive plan following your agent specification.
```

**After project-planner completes**:

1. **Create Beads Epic and Issues**:
   ```python
   from amplifier.bplan.beads_integration import BeadsClient, IssueType

   client = BeadsClient()

   # Create epic
   epic_id = client.create_issue(
       title=f"Build {project_name}",
       description=project_brief,
       issue_type=IssueType.EPIC,
       priority=1
   )

   # Create phase issues
   for phase in phases:
       phase_id = client.create_issue(
           title=phase.title,
           description=phase.details,
           issue_type=IssueType.TASK,
           depends_on=[epic_id] + phase.dependencies,
           priority=phase.priority,
           labels=["phase", "test-first"]
       )
   ```

2. **Present Plan to User**:
   Show the plan summary and ask:
   "Here's the implementation plan with X phases. Does this approach look correct? (yes/no/adjust)"

   - If "adjust": Get feedback and have project-planner revise
   - If "no": Ask what's wrong and revise
   - If "yes": Proceed to Stage 3

## Stage 3: Phase Execution Loop

For each phase in sequence (or parallel if no dependencies):

### 3.1 Start Phase Execution

**Update beads**:
```python
client.update_status(phase_id, IssueStatus.IN_PROGRESS)
```

**Spawn `phase-executor` agent** in a fresh session:
```
Task for phase-executor agent:

Execute this phase following strict test-first development:

[Insert phase specification from plan]

Requirements:
1. Write ALL tests BEFORE any implementation
2. Verify tests fail initially (red phase)
3. Implement minimal code to pass tests (green phase)
4. No test cheating (no mocks where real code works, no weak assertions)
5. Update beads issue (amplifier-X) throughout execution
6. Maximum 5 retry attempts if failures occur

Phase Issue ID: amplifier-X

On completion, report:
- Tests written (with file paths)
- Implementation completed (with file paths)
- Test results (all passing)
- Acceptance criteria met (checklist)
```

### 3.2 Monitor Execution

The phase-executor will:
- Update beads with progress
- Retry up to 5 times on failures
- Report completion or request help

**If phase fails 5 times**:
- Phase-executor provides root cause analysis
- **Ask user**: "Phase X failed after 5 attempts. Analysis: [details]. How should we proceed? (debug/skip/abort)"

### 3.3 Phase Review

**Spawn `phase-reviewer` agent**:
```
Task for phase-reviewer agent:

Review the completed phase for quality and correctness:

Phase: [phase name]
Phase ID: amplifier-X
Specification: [phase spec from plan]

Requirements:
1. Run all phase tests - verify they pass
2. Check test quality (no cheating, good coverage, antagonistic)
3. Validate against acceptance criteria
4. Check code quality and philosophy compliance
5. Run integration test if specified
6. Update beads with review outcome

Provide: APPROVED or REJECTED with detailed feedback.
```

**Based on review outcome**:

- **APPROVED**:
  ```python
  client.close_issue(phase_id)
  ```
  **Optional ask**: "Phase X complete. Quick sanity check? (yes/skip)"
  - If "yes": Provide 2-minute manual test instructions
  - If "skip": Continue

- **REJECTED**:
  Reviewer provides feedback.
  Return to phase-executor with feedback and retry.

### 3.4 Move to Next Phase

Repeat 3.1-3.3 for next phase in sequence.

## Stage 4: Inter-Phase Validation

After each phase closes, check:
- Do all previous tests still pass?
- Are there integration issues?

```bash
# Run all tests
pytest tests/ -v

# Check for regressions
```

If issues found, spawn bug-hunter agent to fix.

## Stage 5: Final Reconciliation

**All phases complete** - Use `project-planner` agent again:

```
Task for project-planner agent:

Final project validation:

Original Request: [initial user request]
Implemented Phases: [list all phases]
Epic ID: amplifier-X

Requirements:
1. Review all completed phases against original ask
2. Verify nothing was missed or drifted from requirements
3. Check philosophy alignment throughout
4. Run final integration tests
5. Generate completion report

Output: Approval or list of remaining work.
```

**Present completion report to user**:
"Project complete! Review summary: [report]. Approve? (yes/adjust)"

- If "yes": Close epic, celebrate!
- If "adjust": Create follow-up issues and address

**Close Epic**:
```python
client.close_issue(epic_id)
client.add_comment(epic_id, f"Project completed: {completion_summary}")
```

## State Management

Throughout the workflow, maintain state in `.beads/bplan_state.json`:
```json
{
  "epic_id": "amplifier-X",
  "current_stage": "execution",
  "current_phase": "amplifier-Y",
  "phases": [
    {"id": "amplifier-Y", "status": "in_progress", "attempt": 2},
    {"id": "amplifier-Z", "status": "pending"}
  ],
  "project_brief": "...",
  "plan_summary": "..."
}
```

This allows resumption after compaction or interruption.

## Failure Handling

**Phase fails 5 times**:
1. Phase-executor generates root cause analysis
2. Ask user for help
3. Options: debug together, skip phase, abort project

**User aborts**:
1. Update all in-progress issues to "open"
2. Add comment: "Project paused"
3. Save state for resumption

**Resumption**:
User can run `/bplan resume` to continue from last state.

## Key Principles

1. **Interactive, Not Assumptive**: Ask questions, don't guess
2. **Test-First Always**: Every phase starts with tests
3. **No Test Cheating**: Enforced by executor and reviewer
4. **Beads is Truth**: All status in beads, resumable anytime
5. **User Approval Gates**: At plan review, phase completion (optional), final approval
6. **Philosophy Compliance**: Ruthless simplicity throughout

## Example Usage

```
User: /bplan Build user authentication with JWT tokens

Claude:
Starting interactive project planning...

What would you like to build?
> [User describes authentication system]

Do you have any planning documents?
> none

What are the must-have features?
> [User lists features]

[... continues through workflow ...]

Final result:
✅ Epic amplifier-42: User Authentication System (CLOSED)
  ✅ Phase 1: Core auth module (amplifier-43)
  ✅ Phase 2: JWT service (amplifier-44)
  ✅ Phase 3: Integration tests (amplifier-45)

All tests passing. Project complete!
```

---

Remember: You are the orchestrator. Delegate to specialized agents, manage state in beads, ask user for clarification when needed, and maintain test-first discipline throughout.
