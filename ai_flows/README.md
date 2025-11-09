# AI Flows

Example DotRunner workflows demonstrating various patterns.

## Available Workflows

### loop-until-done.yaml
**Purpose**: Keep working on a goal until completion criteria are met.

**Pattern**: work → check → (if incomplete) continue → check → ... → done

**Usage**:
```bash
export GOAL="Your task description here"
uv run python -m ai_working.dotrunner run ai_flows/loop-until-done.yaml
```

**Example**:
```bash
export GOAL="Complete all 12 phases of the implementation plan"
uv run python -m ai_working.dotrunner run ai_flows/loop-until-done.yaml
```

**How it works**:
1. **work** node: Agent works on the goal
2. **check** node: Evaluates if goal is COMPLETE or INCOMPLETE
3. **continue** node: If incomplete, continues working (loops back to check)
4. **done** node: Terminal node when complete

**Safety**: Max 20 iterations by default (configurable in YAML)

### code-review-simple.yaml
Basic code review with style check and test execution.

### knowledge-synthesis.yaml
Multi-step knowledge extraction and synthesis from articles.

### feature-planning.yaml
Feature design with architecture and test strategy.

### bug-investigation.yaml
Systematic bug investigation and fix proposal.

### documentation-gen.yaml
Generate documentation from codebase.

## Creating New Workflows

1. Copy an example workflow
2. Modify nodes and prompts for your use case
3. Test with: `uv run python -m ai_working.dotrunner run your-workflow.yaml`
4. Set context with environment variables or --context flag

## Learn More

See [DotRunner Documentation](../ai_working/dotrunner/README.md) for full workflow capabilities.
