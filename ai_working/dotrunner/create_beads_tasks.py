#!/usr/bin/env python3
"""
Create beads issues for DotRunner implementation.

This script creates a comprehensive task list following the evidence-based
coding approach from bplantest branch.
"""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path


def create_timestamp():
    """Create ISO 8601 timestamp"""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def get_next_id(issues_file):
    """Get next available dr- prefixed ID"""
    if not issues_file.exists():
        return "dr-1"

    max_id = 0
    with open(issues_file) as f:
        for line in f:
            issue = json.loads(line)
            if issue["id"].startswith("dr-"):
                num = int(issue["id"].split("-")[1])
                max_id = max(max_id, num)

    return f"dr-{max_id + 1}"


def append_issue(issues_file, issue):
    """Append issue to JSONL file"""
    with open(issues_file, "a") as f:
        f.write(json.dumps(issue) + "\n")
    print(f"Created issue: {issue['id']} - {issue['title']}")


def main():
    """Create all dotrunner beads issues"""
    issues_file = Path(".beads/issues.jsonl")

    # Epic: DotRunner MVP
    epic_id = get_next_id(issues_file)
    epic = {
        "id": epic_id,
        "title": "DotRunner: Declarative Agentic Workflow System",
        "description": "Build workflow orchestration system that executes multi-agent workflows defined in YAML dotfiles. Supports linear and conditional flows, state persistence, resume capability, and evidence-based validation.",
        "status": "open",
        "priority": 0,
        "issue_type": "epic",
        "created_at": create_timestamp(),
        "updated_at": create_timestamp(),
    }
    append_issue(issues_file, epic)

    # Phase 1: Core Data Models and Parsing
    phase1_id = get_next_id(issues_file)
    phase1 = {
        "id": phase1_id,
        "title": "Phase 1: Core Data Models and YAML Parsing",
        "description": "Foundation: workflow and node data models, YAML parsing with validation",
        "design": """Phase 1: Core Data Models and YAML Parsing

TESTS FIRST (RED):
- test_workflow_model.py: Test Workflow and Node dataclasses
- test_yaml_parsing.py: Test YAML loading and validation
- test_schema_validation.py: Test required fields, types, relationships
- test_context_merging.py: Test global and node context merging
- Antagonistic tests: Invalid YAML, missing fields, circular dependencies, malformed node refs

IMPLEMENTATION (GREEN):
- ai_working/dotrunner/workflow.py:
  * Workflow dataclass (name, description, nodes, context)
  * Node dataclass (id, name, prompt, agent, outputs, next, retry, type)
  * Workflow.from_yaml(path) - Load and validate
  * Workflow.get_node(id) - Node lookup
  * Workflow.validate() - Schema and relationship validation

- ai_working/dotrunner/parser.py:
  * parse_workflow(path) - YAML → Workflow
  * validate_schema(data) - Schema validation
  * validate_node_refs(workflow) - Check node ID references
  * detect_cycles(workflow) - Prevent infinite loops

ACCEPTANCE CRITERIA:
✓ Workflow and Node models defined with all required fields
✓ YAML files parse correctly into data models
✓ Schema validation catches missing/invalid fields
✓ Node reference validation catches broken links
✓ Circular dependency detection works
✓ Clear error messages for validation failures
✓ Example workflows parse successfully
✓ All tests pass with real YAML files

DEPENDENCIES: None (foundational phase)""",
        "status": "open",
        "priority": 0,
        "issue_type": "task",
        "created_at": create_timestamp(),
        "updated_at": create_timestamp(),
        "external_ref": f"blocks:{epic_id}",
    }
    append_issue(issues_file, phase1)

    # Phase 2: Linear Execution Engine
    phase2_id = get_next_id(issues_file)
    phase2 = {
        "id": phase2_id,
        "title": "Phase 2: Linear Execution Engine",
        "description": "Execute workflows node by node in sequence (no branching yet)",
        "design": """Phase 2: Linear Execution Engine

TESTS FIRST (RED):
- test_engine_linear.py: Test sequential node execution
- test_node_executor.py: Test single node execution
- test_context_interpolation.py: Test {var} replacement in prompts
- test_output_extraction.py: Test capturing named outputs
- test_execution_flow.py: Test full workflow execution
- Antagonistic tests: Missing context vars, node failures, empty results

IMPLEMENTATION (GREEN):
- ai_working/dotrunner/engine.py:
  * WorkflowEngine class
  * run() - Execute workflow from start
  * _get_next_node(state) - Sequential node selection
  * _execute_node(node, state) - Execute single node
  * Error handling and logging

- ai_working/dotrunner/executor.py:
  * NodeExecutor class
  * execute(node, context) - Run node, return outputs
  * _interpolate_prompt(template, context) - Replace {vars}
  * _execute_generic(prompt) - Use ClaudeSession for "auto" agent
  * _extract_outputs(result, names) - Parse named outputs

- ai_working/dotrunner/models.py:
  * WorkflowState dataclass
  * NodeResult dataclass

GOLDEN FILE WORKFLOW:
- Test creates expected output for each node
- Engine executes workflow
- Compare actual vs golden outputs (byte-for-byte)
- Evidence stored in .beads/evidence/dotrunner/

ACCEPTANCE CRITERIA:
✓ Simple linear workflows execute successfully
✓ Context variables interpolate correctly in prompts
✓ Named outputs extracted and available to next nodes
✓ Nodes execute in correct order
✓ Error messages are clear and actionable
✓ Golden file validation passes
✓ Integration tests with real Claude API pass
✓ Evidence files created for validation

DEPENDENCIES: Phase 1 (data models and parsing)""",
        "status": "open",
        "priority": 0,
        "issue_type": "task",
        "created_at": create_timestamp(),
        "updated_at": create_timestamp(),
        "external_ref": f"blocks:{epic_id}",
    }
    append_issue(issues_file, phase2)

    # Phase 3: State Persistence and Resume
    phase3_id = get_next_id(issues_file)
    phase3 = {
        "id": phase3_id,
        "title": "Phase 3: State Persistence and Resume",
        "description": "Save state after every node, enable workflow resume after interruption",
        "design": """Phase 3: State Persistence and Resume

TESTS FIRST (RED):
- test_state_manager.py: Test state save/load operations
- test_resume_workflow.py: Test resume from saved state
- test_incremental_save.py: Test save after each node
- test_state_recovery.py: Test recovery from various failure points
- Antagonistic tests: Corrupted state files, interrupted writes, missing state

IMPLEMENTATION (GREEN):
- ai_working/dotrunner/state.py:
  * StateManager class
  * save(state) - Atomic write to state.json
  * load(workflow_name) - Restore WorkflowState
  * exists(workflow_name) - Check for saved state
  * State directory structure: .data/dotrunner/runs/<workflow-name>/

- ai_working/dotrunner/engine.py updates:
  * Accept resume=True parameter
  * Load state if resuming
  * Save state after EVERY node completion
  * Skip completed nodes on resume
  * Preserve all context and results

- Use defensive file I/O:
  * from amplifier.utils.file_io import write_json, read_json
  * Retry logic for cloud-synced files
  * Atomic writes (temp file + rename)

GOLDEN FILE WORKFLOW:
- Test workflow with 5 nodes
- Interrupt after node 3
- Resume workflow
- Verify nodes 1-3 skipped, 4-5 executed
- Compare final state vs golden state file

ACCEPTANCE CRITERIA:
✓ State saved after every successful node
✓ Resume loads previous state correctly
✓ Completed nodes are skipped on resume
✓ Context and results preserved across interruption
✓ Works with cloud-synced directories (retry logic)
✓ Atomic writes prevent corruption
✓ Clear error if state file missing when resuming
✓ Golden file validation for resume scenarios

DEPENDENCIES: Phase 2 (execution engine)""",
        "status": "open",
        "priority": 0,
        "issue_type": "task",
        "created_at": create_timestamp(),
        "updated_at": create_timestamp(),
        "external_ref": f"blocks:{epic_id}",
    }
    append_issue(issues_file, phase3)

    # Phase 4: CLI and User Interface
    phase4_id = get_next_id(issues_file)
    phase4 = {
        "id": phase4_id,
        "title": "Phase 4: CLI and User Interface",
        "description": "Click-based CLI for running and resuming workflows",
        "design": """Phase 4: CLI and User Interface

TESTS FIRST (RED):
- test_cli_run.py: Test run command
- test_cli_resume.py: Test resume command
- test_cli_validation.py: Test input validation
- test_cli_context_passing.py: Test --context arguments
- Antagonistic tests: Invalid arguments, missing files, malformed context

IMPLEMENTATION (GREEN):
- ai_working/dotrunner/cli.py:
  * @click.group() dotrunner
  * @click.command() run - Run workflow from start
  * @click.command() resume - Resume saved workflow
  * @click.command() validate - Validate workflow file
  * Context parsing (KEY=VALUE format)
  * Progress reporting
  * Error display

- ai_working/dotrunner/__init__.py:
  * Package exports
  * Version info

- ai_working/dotrunner/__main__.py:
  * Entry point for python -m ai_working.dotrunner

Commands:
```bash
# Run workflow
python -m ai_working.dotrunner run workflow.yaml --context key=value

# Resume workflow
python -m ai_working.dotrunner resume workflow-name

# Validate workflow
python -m ai_working.dotrunner validate workflow.yaml
```

ACCEPTANCE CRITERIA:
✓ CLI commands work as expected
✓ Context variables parsed from --context args
✓ Environment variables expanded (${VAR})
✓ Progress displayed during execution
✓ Errors shown clearly with helpful messages
✓ Examples in README work correctly
✓ Help text is clear and complete
✓ All CLI tests pass

DEPENDENCIES: Phase 3 (state management)""",
        "status": "open",
        "priority": 0,
        "issue_type": "task",
        "created_at": create_timestamp(),
        "updated_at": create_timestamp(),
        "external_ref": f"blocks:{epic_id}",
    }
    append_issue(issues_file, phase4)

    # Phase 5: Agent Integration via Task Tool
    phase5_id = get_next_id(issues_file)
    phase5 = {
        "id": phase5_id,
        "title": "Phase 5: Agent Integration via Task Tool",
        "description": "Delegate to specialized agents (zen-architect, bug-hunter, etc.)",
        "design": """Phase 5: Agent Integration via Task Tool

CRITICAL: Agent delegation must work within Claude Code's constraints.
The Task tool is synchronous and must be called directly by Claude Code.

TESTS FIRST (RED):
- test_agent_delegation.py: Test delegation to specific agents
- test_agent_selection.py: Test agent="auto" vs agent="zen-architect"
- test_agent_context.py: Test context passed to agents
- test_agent_results.py: Test agent result parsing
- Antagonistic tests: Unknown agents, agent failures, malformed responses

IMPLEMENTATION APPROACH:

For MVP, use a hybrid approach:
1. When agent="auto": Use ClaudeSession directly (already working)
2. When agent="specific": Document that user must run via Claude Code

Alternative: Create prompt that guides user to delegate:
```python
if node.agent != "auto":
    # Generate instructions for user to delegate
    print(f"Please delegate this task to {node.agent}:")
    print(f"Prompt: {interpolated_prompt}")
    print("Waiting for result...")
    result = input("Paste agent result: ")
```

OR: Integration with Claude Code SDK that IS possible:
```python
# Use the ClaudeSession but with agent-specific system prompts
from amplifier.ccsdk_toolkit import ClaudeSession, SessionOptions

async def _delegate_to_agent(agent: str, task: str):
    options = SessionOptions()
    options.system_prompt = get_agent_system_prompt(agent)

    async with ClaudeSession(options) as session:
        return await session.generate(task)
```

IMPLEMENTATION (GREEN):
- ai_working/dotrunner/executor.py updates:
  * _delegate_to_agent(agent, task) - Agent-specific execution
  * Agent system prompt templates
  * Defensive response parsing using parse_llm_json
  * Clear error messages for agent failures

- ai_working/dotrunner/agents.py:
  * Agent registry (name → system prompt)
  * get_agent_prompt(agent_name) - Get system prompt
  * validate_agent(agent_name) - Check if agent exists

ACCEPTANCE CRITERIA:
✓ agent="auto" works with generic Claude
✓ Specific agents work via system prompts OR
✓ Clear documentation on manual delegation workflow
✓ Agent responses parsed defensively
✓ Errors handled gracefully
✓ Examples with specific agents work
✓ Integration tests with real agents pass

DEPENDENCIES: Phase 4 (CLI)""",
        "status": "open",
        "priority": 0,
        "issue_type": "task",
        "created_at": create_timestamp(),
        "updated_at": create_timestamp(),
        "external_ref": f"blocks:{epic_id}",
    }
    append_issue(issues_file, phase5)

    # Phase 6: Conditional Routing and Branching
    phase6_id = get_next_id(issues_file)
    phase6 = {
        "id": phase6_id,
        "title": "Phase 6: Conditional Routing and Branching",
        "description": "Add conditional next nodes, AI-driven condition evaluation",
        "design": """Phase 6: Conditional Routing and Branching

TESTS FIRST (RED):
- test_condition_evaluator.py: Test condition evaluation
- test_conditional_routing.py: Test routing based on conditions
- test_next_node_selection.py: Test next node determination
- test_branching_workflows.py: Test workflows with branches
- Antagonistic tests: Invalid conditions, ambiguous routing, infinite loops

IMPLEMENTATION (GREEN):
- ai_working/dotrunner/evaluator.py:
  * ConditionEvaluator class
  * evaluate(conditions, context) - Return next node ID
  * _evaluate_condition(when, context) - Evaluate single condition
  * _interpolate_condition(when, context) - Replace {vars}
  * Use AI to evaluate complex conditions

- ai_working/dotrunner/engine.py updates:
  * _evaluate_next(node, state) - Handle conditional routing
  * Support for node.next as list of conditions
  * Loop detection (max iterations per node)
  * Clear error for unmatched conditions

- Condition syntax:
  ```yaml
  next:
    - when: "{is_large} == true"
      goto: "deep-review"
    - when: "{count} > 10"
      goto: "batch-process"
    - default: "continue"
  ```

GOLDEN FILE WORKFLOW:
- Test workflow with branching
- Provide context that triggers each branch
- Verify correct paths taken
- Compare execution trace vs golden trace

ACCEPTANCE CRITERIA:
✓ Simple conditions (==, !=, >, <) evaluate correctly
✓ AI evaluates complex conditions accurately
✓ Default route works when no condition matches
✓ Error if no condition matches and no default
✓ Loop detection prevents infinite cycles
✓ Conditional examples work correctly
✓ Golden file validation for branching paths

DEPENDENCIES: Phase 5 (agent integration)""",
        "status": "open",
        "priority": 0,
        "issue_type": "task",
        "created_at": create_timestamp(),
        "updated_at": create_timestamp(),
        "external_ref": f"blocks:{epic_id}",
    }
    append_issue(issues_file, phase6)

    # Phase 7: Error Handling and Retry Logic
    phase7_id = get_next_id(issues_file)
    phase7 = {
        "id": phase7_id,
        "title": "Phase 7: Error Handling and Retry Logic",
        "description": "Robust error handling, retry logic, clear error reporting",
        "design": """Phase 7: Error Handling and Retry Logic

TESTS FIRST (RED):
- test_retry_logic.py: Test node retry on failure
- test_error_recovery.py: Test recovery from various errors
- test_error_reporting.py: Test error message clarity
- test_partial_failure.py: Test workflow state after failure
- Antagonistic tests: API failures, parsing errors, invalid responses

IMPLEMENTATION (GREEN):
- ai_working/dotrunner/engine.py updates:
  * Retry logic in _execute_node()
  * Exponential backoff for retries
  * Error state preservation
  * Clear error messages with context

- ai_working/dotrunner/errors.py:
  * WorkflowError - Base exception
  * NodeExecutionError - Node execution failed
  * ValidationError - Workflow validation failed
  * StateError - State management failed
  * Error with context (node, prompt, previous results)

- Use retry_with_feedback from ccsdk_toolkit:
  ```python
  from amplifier.ccsdk_toolkit.defensive import retry_with_feedback

  result = await retry_with_feedback(
      async_func=execute_node,
      prompt=node.prompt,
      max_retries=node.retry_on_failure
  )
  ```

ACCEPTANCE CRITERIA:
✓ Nodes retry up to retry_on_failure times
✓ Exponential backoff between retries
✓ Error state saved for debugging
✓ Clear error messages with context
✓ Workflow can resume after fixing issue
✓ All error tests pass
✓ Examples handle errors gracefully

DEPENDENCIES: Phase 6 (conditional routing)""",
        "status": "open",
        "priority": 0,
        "issue_type": "task",
        "created_at": create_timestamp(),
        "updated_at": create_timestamp(),
        "external_ref": f"blocks:{epic_id}",
    }
    append_issue(issues_file, phase7)

    # Phase 8: Documentation and Examples
    phase8_id = get_next_id(issues_file)
    phase8 = {
        "id": phase8_id,
        "title": "Phase 8: Validation, Documentation, and Evidence",
        "description": "Complete documentation, working examples, comprehensive validation",
        "design": """Phase 8: Validation, Documentation, and Evidence

TESTS FIRST (RED):
- test_all_examples.py: Test all example workflows execute
- test_documentation_completeness.py: Verify all docs exist
- test_golden_files_complete.py: Verify all golden files present
- Meta-validation: Use DotRunner to validate itself

IMPLEMENTATION (GREEN):
- Comprehensive README.md ✓ (already created)
- DESIGN.md technical documentation ✓ (already created)
- Example workflows ✓ (already created)
- Add more examples:
  * examples/retry_example.yaml - Demonstrates retry logic
  * examples/loop_example.yaml - Demonstrates loops
  * examples/multi_agent.yaml - All agent types

- Validation script:
  * validate_all_examples.py - Run all examples
  * Check golden files match
  * Verify state persistence works
  * Test resume capability

META-VALIDATION:
Create a workflow that validates DotRunner implementation:
```yaml
workflow:
  name: "dotrunner-validation"
  description: "Validate DotRunner implementation using itself"

nodes:
  - id: "check-tests"
    prompt: "Run all DotRunner tests and verify they pass"
    outputs: [test_results]

  - id: "check-examples"
    prompt: "Execute all example workflows and verify they work"
    outputs: [example_results]

  - id: "check-golden-files"
    prompt: "Verify all golden files exist and match"
    outputs: [golden_validation]

  - id: "final-report"
    prompt: "Create validation report from all checks"
    outputs: [validation_report]
```

ACCEPTANCE CRITERIA:
✓ All examples execute successfully
✓ Documentation complete and accurate
✓ All tests pass
✓ Golden files validate correctly
✓ Meta-validation workflow passes
✓ Evidence files demonstrate all criteria met
✓ README examples are tested and work

DEPENDENCIES: Phase 7 (error handling)""",
        "status": "open",
        "priority": 0,
        "issue_type": "task",
        "created_at": create_timestamp(),
        "updated_at": create_timestamp(),
        "external_ref": f"blocks:{epic_id}",
    }
    append_issue(issues_file, phase8)

    print(f"\n✅ Created {8} DotRunner issues in beads")
    print(f"Epic: {epic_id} - DotRunner: Declarative Agentic Workflow System")
    print("\nPhases:")
    print(f"  {phase1_id} - Phase 1: Core Data Models and YAML Parsing")
    print(f"  {phase2_id} - Phase 2: Linear Execution Engine")
    print(f"  {phase3_id} - Phase 3: State Persistence and Resume")
    print(f"  {phase4_id} - Phase 4: CLI and User Interface")
    print(f"  {phase5_id} - Phase 5: Agent Integration via Task Tool")
    print(f"  {phase6_id} - Phase 6: Conditional Routing and Branching")
    print(f"  {phase7_id} - Phase 7: Error Handling and Retry Logic")
    print(f"  {phase8_id} - Phase 8: Validation, Documentation, and Evidence")


if __name__ == "__main__":
    main()
