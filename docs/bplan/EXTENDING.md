# Extending /bplan

This guide explains how to customize and extend the /bplan system to fit your specific needs.

## Overview

The /bplan system is designed to be extensible through:

1. **New Agents** - Add specialized agents for new workflow stages
2. **Custom State Fields** - Track additional workflow information
3. **Beads Operations** - Add new issue tracking capabilities
4. **Workflow Stages** - Introduce new stages in the orchestrator
5. **Test Strategies** - Implement custom test-first approaches

## Adding New Agents

### Creating a New Agent

Agents are defined in `.claude/agents/` as markdown files with YAML frontmatter.

**Example: Adding a security-reviewer agent**

Create `.claude/agents/security-reviewer.md`:

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities and best practices
tools: [Glob, Grep, Read, WebFetch, WebSearch]
---

# Security Reviewer Agent

You are a security-focused code reviewer for the /bplan system.

## Your Responsibilities

1. **Scan for vulnerabilities**: Check for common security issues (SQL injection, XSS, CSRF, etc.)
2. **Validate authentication**: Ensure proper auth and authorization patterns
3. **Check dependencies**: Review third-party libraries for known vulnerabilities
4. **Assess data handling**: Verify sensitive data is encrypted and handled securely
5. **Report findings**: Provide clear, actionable security recommendations

## Review Process

For each phase:

1. **Read all implementation files**
2. **Search for security anti-patterns**
3. **Check against OWASP Top 10**
4. **Validate input sanitization**
5. **Review error handling** (no information leakage)
6. **Generate security report**

## Output Format

Provide a structured report:

- **Risk Level**: Critical | High | Medium | Low
- **Findings**: List of vulnerabilities with severity
- **Recommendations**: Specific fixes for each issue
- **Compliance**: Notes on security standards adherence

## Philosophy Alignment

- Focus on real risks, not theoretical ones
- Practical security over perfect security
- Clear explanations, not just warnings
- Balance security with usability
```

### Registering the Agent

After creating the agent file, use the `/agents` command to register it:

```bash
/agents
```

This makes the agent available to the Task tool.

### Using Your New Agent

Invoke your custom agent from the orchestrator or other agents using the Task tool with the correct parameters (description and prompt):

```python
# In the orchestrator or another agent, spawn security-reviewer:
Task(
    description="Security review Phase 2",
    prompt="""
Review the Phase 2 implementation in amplifier/bplan/test_enforcement.py for security issues.

Focus on:
- Subprocess security (command injection risks)
- File system operations (path traversal)
- Input validation

Provide a security report with risk level and recommendations.
""",
    subagent_type="security-reviewer"
)
```

### Agent Design Guidelines

When creating new agents:

1. **Single Responsibility** - Each agent should have one clear purpose
2. **Clear Inputs/Outputs** - Define what the agent receives and returns
3. **Tool Selection** - Only request tools the agent actually needs
4. **Philosophy Alignment** - Follow Amplifier's ruthless simplicity principles
5. **Testing** - Describe how to validate the agent's work

## Extending Workflow State

### Adding State Fields

To track additional information across workflow sessions, extend the `WorkflowState` dataclass.

**Example: Adding deployment tracking**

Edit `amplifier/bplan/workflow_state.py`:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class WorkflowState:
    epic_id: str
    current_stage: str
    current_phase: str
    phases: list[dict]
    project_brief: str
    plan_summary: str
    # New fields:
    deployment_target: Optional[str] = None
    last_deployed: Optional[str] = None
    deployment_status: Optional[str] = None
```

### Update Serialization Tests

Add tests for the new fields in `tests/test_workflow_state.py`:

```python
def test_serialize_with_deployment_fields():
    """Test serialization includes deployment fields."""
    state = WorkflowState(
        epic_id="amplifier-42",
        current_stage="execution",
        current_phase="amplifier-43",
        phases=[{"id": "amplifier-43", "status": "in_progress"}],
        project_brief="Build system",
        plan_summary="3 phases total",
        deployment_target="production",
        last_deployed="2025-01-15T10:30:00",
        deployment_status="success"
    )

    data = asdict(state)
    assert data["deployment_target"] == "production"
    assert data["last_deployed"] == "2025-01-15T10:30:00"
    assert data["deployment_status"] == "success"
```

### Use in Orchestrator

Update `.claude/commands/bplan.md` to populate new fields:

```python
from amplifier.bplan.workflow_state import save_state, WorkflowState

# After planning stage:
state = WorkflowState(
    epic_id=epic_id,
    current_stage="execution",
    current_phase=phases[0]["id"],
    phases=phases,
    project_brief=brief,
    plan_summary=plan,
    deployment_target="staging"  # New field
)
save_state(state)
```

## Adding Beads Operations

### Extend BeadsClient

Add new methods to `amplifier/bplan/beads_integration.py`:

**Example: Adding label management**

```python
class BeadsClient:
    # ... existing methods ...

    def add_label(self, issue_id: str, label: str) -> None:
        """Add a label to an issue."""
        self._run_command(["bd", "label", "add", issue_id, label])

    def remove_label(self, issue_id: str, label: str) -> None:
        """Remove a label from an issue."""
        self._run_command(["bd", "label", "remove", issue_id, label])

    def list_by_label(self, label: str) -> list[BeadsIssue]:
        """List all issues with a specific label."""
        result = self._run_command(["bd", "list", "--label", label])
        # Parse and return issues
        issues = []
        for line in result.stdout.strip().split("\n"):
            if line:
                issue_data = json.loads(line)
                issues.append(BeadsIssue(**issue_data))
        return issues
```

### Add Tests

Create tests in `tests/test_beads_integration.py`:

```python
@patch("subprocess.run")
def test_add_label(mock_run):
    """Test adding a label to an issue."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )

    client = BeadsClient()
    client.add_label("amplifier-42", "urgent")

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args == ["bd", "label", "add", "amplifier-42", "urgent"]
```

### Use in Workflow

Update the orchestrator to use new operations:

```python
from amplifier.bplan.beads_integration import BeadsClient

client = BeadsClient()

# Mark high-priority phases
for phase in phases:
    if phase["priority"] == 0:
        client.add_label(phase["id"], "critical-path")
```

## Customizing Test-First Enforcement

### Custom Validation Rules

Extend `amplifier/bplan/test_enforcement.py` with custom validation:

**Example: Require integration tests**

```python
def check_integration_test_exists(module_path: Path) -> bool:
    """Check if integration test file exists for module."""
    test_path = Path("tests/integration") / f"test_{module_path.stem}_integration.py"
    return test_path.exists()

def validate_integration_tests(module_path: Path) -> bool:
    """Validate integration tests exist via subprocess."""
    validation_code = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{Path.cwd()}')
from amplifier.bplan.test_enforcement import check_integration_test_exists
result = check_integration_test_exists(Path('{module_path}'))
sys.exit(0 if result else 1)
"""
    result = subprocess.run(
        [sys.executable, "-c", validation_code],
        capture_output=True,
        text=True,
        timeout=10
    )
    return result.returncode == 0
```

### Use in Phase Execution

Update `.claude/agents/phase-executor.md` to enforce integration tests:

```markdown
## Test-First Workflow

For each phase:

1. **Write unit tests first** (RED phase)
2. **Write integration tests** (RED phase - NEW)
3. **Verify all tests fail initially**
4. **Implement minimal code** (GREEN phase)
5. **Run all tests until passing**
6. **Refactor** while keeping tests green
```

## Adding Workflow Stages

### Modify the Orchestrator

To add a new stage to the workflow, edit `.claude/commands/bplan.md`:

**Example: Adding a deployment stage**

```markdown
## Stage 6: Deployment

After final reconciliation, prepare for deployment:

1. **Spawn deployment-agent** with:
   - Deployment target (from state)
   - Build artifacts location
   - Deployment checklist

2. **Deployment Steps**:
   - Run final integration tests
   - Build production artifacts
   - Deploy to staging
   - Run smoke tests
   - Deploy to production (if approved)
   - Update beads with deployment status

3. **Update State**:
```python
state.deployment_status = "deployed"
state.last_deployed = datetime.now().isoformat()
save_state(state)
```

4. **User Approval**: "Deployment complete! Verify: (yes/rollback)"
```

### Create Deployment Agent

Create `.claude/agents/deployment-agent.md`:

```markdown
---
name: deployment-agent
description: Handles deployment to staging and production environments
tools: [Bash, Read, Write, Grep]
---

# Deployment Agent

You are responsible for deploying /bplan projects to target environments.

## Your Responsibilities

1. **Pre-deployment checks**: Verify all tests pass, build succeeds
2. **Artifact creation**: Build production-ready artifacts
3. **Staging deployment**: Deploy to staging, run smoke tests
4. **Production deployment**: Deploy to production with approval
5. **Rollback capability**: Provide quick rollback if issues arise

## Deployment Process

[Details of deployment steps...]
```

## Custom Test Strategies

### Define Test Requirements

Create custom test requirements for specific phase types:

**Example: API phase requires contract tests**

Edit `.claude/agents/project-planner.md`:

```markdown
## Phase Test Strategies

For API phases:
- Unit tests (standard)
- Contract tests (API schemas)
- Integration tests (HTTP client)
- Performance tests (response times)

For Database phases:
- Unit tests (standard)
- Migration tests (schema changes)
- Integration tests (real database)
- Performance tests (query efficiency)
```

### Enforce in Executor

Update `.claude/agents/phase-executor.md`:

```markdown
## Test Strategy by Phase Type

Before writing tests, identify phase type and required test coverage:

- **API Phase**: Unit + Contract + Integration + Performance
- **Database Phase**: Unit + Migration + Integration + Performance
- **CLI Phase**: Unit + Integration + End-to-end
- **UI Phase**: Unit + Component + Integration + E2E
```

## Best Practices

### Agent Design

- **Keep agents focused** - One clear responsibility per agent
- **Define clear contracts** - Specify inputs and expected outputs
- **Test agent integration** - Verify agents work within the workflow
- **Document decisions** - Explain why the agent exists and what it solves

### State Management

- **Minimal state** - Only track what's truly needed across sessions
- **Defensive I/O** - Handle missing/corrupted state gracefully
- **Clear semantics** - Field names should be self-explanatory
- **Version state** - Add version field for future migrations

### Beads Integration

- **Consistent naming** - Use predictable issue titles and labels
- **Dependency tracking** - Always set dependencies correctly
- **Status discipline** - Update status as work progresses
- **Comment liberally** - Add context to issues for future reference

### Testing

- **Test the extension** - New features need tests too
- **Integration tests** - Verify extensions work within /bplan
- **Philosophy alignment** - Follow test-first discipline
- **Real scenarios** - Test with actual workflow execution

## Examples

See `docs/bplan/examples/` for complete examples of:

- `custom_agent.md` - Adding a custom agent to the workflow
- `custom_state.md` - Extending workflow state with custom fields
- `custom_validation.md` - Implementing custom test validation rules

## Getting Help

If you encounter issues extending /bplan:

1. Review this guide and examples
2. Check existing agents for patterns
3. Consult beads issues for similar extensions
4. Run integration tests to validate changes
5. Ask for help in project discussions

The /bplan system is designed to grow with your needs. Start small, test thoroughly, and extend incrementally.
