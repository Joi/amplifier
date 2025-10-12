---
description: Manage large, multi-level projects with AI coordination
category: project-management
allowed-tools: Task, Bash, Read, Write, Glob, Grep, TodoWrite
---

# Claude Command: Super-Planner

Coordinate large, complex projects with hierarchical tasks, multi-agent execution, and human collaboration.

## Usage

```bash
# Show help and usage instructions
/superplanner help
/superplanner usage

# List all projects
/superplanner list

# Create a new super-plan from a high-level goal
/superplanner create "Build an e-commerce platform with payment integration"

# Show current project status (most recent project)
/superplanner status

# Show status of a specific project
/superplanner status <project-id>

# Execute next batch of ready tasks (most recent project)
/superplanner execute

# Execute tasks for specific project
/superplanner execute <project-id>

# Resume work on interrupted project (most recent project)
/superplanner resume

# Resume specific project
/superplanner resume <project-id>
```

## Arguments

**Mode Selection (first argument):**
- `help` or `usage` - Show detailed usage instructions and examples
- `list` - Show all projects with summaries
- `create` - Initialize new project from goal description
- `status` - Display project state and available tasks (defaults to most recent if no ID given)
- `execute` - Run next batch of tasks with agents (defaults to most recent if no ID given)
- `resume` - Continue interrupted execution (defaults to most recent if no ID given)

**Additional Arguments:**
- `$ARGUMENTS` - Project ID or goal description depending on mode (optional for status/execute/resume)

## What This Command Does

### Help/Usage Mode

When the user runs `/superplanner help` or `/superplanner usage`:

1. **Display usage instructions** from this document
2. **Show command examples** for each mode
3. **Explain when to use super-planner** vs simple tasks
4. **List available agents** that work with super-planner
5. **Provide workflow examples** for common scenarios

Output should include:
- Quick reference for all commands
- Example workflows (create → execute → status → resume)
- When to use super-planner guidance
- Link to full documentation in amplifier/planner/README.md

### List Mode

1. **Scan data/planner/projects/** directory
2. **Load project summaries** (fast, without full task data)
3. **Display table** with: name, ID, task counts, last updated
4. **Sort by most recently updated** first
5. **Show completion percentages** for quick status overview

### Create Mode

1. **Analyze the goal** using super-planner-coordinator agent
2. **Decompose into tasks** with dependencies and hierarchy
3. **Assign appropriate agents** to each task based on domain
4. **Save project** to data/planner/projects/
5. **Display project structure** and first actionable tasks

### Status Mode

1. **Load project** from storage (most recent if no ID given)
2. **Show completion progress** (X/Y tasks completed)
3. **Display task hierarchy** with visual tree structure
4. **List ready tasks** that can be started now
5. **Show blocked tasks** and their dependencies
6. **Identify assigned agents** or humans for each task

### Execute Mode

1. **Load project** (most recent if no ID given)
2. **Find ready tasks** (dependencies met, not started)
3. **Spawn agents in parallel** (respects max_parallel limit)
4. **Monitor execution** and update task states
5. **Handle failures** with retry logic
6. **Update project state** after each task completes
7. **Report results** showing success/failure/skipped

### Resume Mode

1. **Load interrupted project** (most recent if no ID given)
2. **Assess current state** (completed, in-progress, blocked)
3. **Handle abandoned tasks** (reset in_progress → pending if needed)
4. **Continue execution** from where it stopped using orchestrate_execution

## Integration with Sub-Agents

Super-planner delegates to specialized agents:

- **super-planner-coordinator**: Main orchestration and decision-making
- **zen-architect**: Design and architecture tasks
- **modular-builder**: Implementation tasks
- **bug-hunter**: Debugging and fixes
- **test-coverage**: Test creation
- **integration-specialist**: External service integration
- **Any domain-specific agents** as appropriate

## Project Structure

Projects are stored in: `data/planner/projects/{project_id}.json`

```json
{
  "id": "uuid",
  "name": "Project Name",
  "tasks": [
    {
      "id": "task-1",
      "title": "Task Title",
      "description": "Detailed description",
      "state": "pending|in_progress|completed|blocked",
      "parent_id": null,
      "depends_on": ["task-2"],
      "assigned_to": "agent-name"
    }
  ]
}
```

## Multi-Agent Coordination

Super-planner coordinates multiple agents working in parallel:

1. **Task Distribution**: Assigns tasks based on agent expertise
2. **Dependency Management**: Ensures prerequisite tasks complete first
3. **Parallel Execution**: Runs independent tasks simultaneously
4. **Progress Tracking**: Updates project state in real-time
5. **Failure Handling**: Retries or escalates failed tasks

## Human Collaboration

Super-planner supports human team members:

- **Assign to humans**: Set `assigned_to: "human:john@example.com"`
- **Check human progress**: Status command shows human-assigned tasks
- **Resume after human work**: Execute continues after human completion
- **Mixed teams**: Humans and agents work on same project

## Example Workflows

### Workflow 1: New Project with Explicit IDs

```bash
# 1. Create project
/superplanner create "Build REST API with auth, products, and orders"

# Output:
# Created project: proj-abc123
# ├── Design API schema (ready)
# ├── Implement auth service (waiting on schema)
# └── Implement products service (waiting on schema)

# 2. Execute first batch
/superplanner execute proj-abc123

# Output:
# Executing 1 ready task...
# ✓ Design API schema (zen-architect) - completed
# Ready to start: Implement auth service, Implement products service

# 3. Execute next batch (runs in parallel)
/superplanner execute proj-abc123

# Output:
# Executing 2 tasks in parallel...
# ✓ Implement auth service (modular-builder) - completed
# ✓ Implement products service (modular-builder) - completed

# 4. Check status
/superplanner status proj-abc123

# Output:
# Project: Build REST API (75% complete)
# ├── ✓ Design API schema
# ├── ✓ Implement auth service
# ├── ✓ Implement products service
# ├── → Implement orders service (ready)
# └── ⏸ Deploy services (waiting on all implementations)
```

### Workflow 2: "Keep Going" with Context Compaction

```bash
# 1. Create and start project
/superplanner create "Implement user authentication system"
/superplanner execute

# [Session ends or context gets compacted...]

# 2. Resume without project ID (uses most recent)
/superplanner resume

# Output:
# Resuming project: user-auth-xyz (3/8 tasks completed)
# Continuing from where you left off...
# ✓ Database schema (completed)
# → Password hashing (executing)

# 3. Check what projects exist
/superplanner list

# Output:
# Projects (sorted by recent):
#
# user-auth-xyz    User Authentication    3/8 (38%)  Updated: 2 mins ago
# api-rest-abc     REST API Project       12/15 (80%) Updated: 1 hour ago
# deploy-test-999  Deployment Test        0/5 (0%)    Updated: yesterday

# 4. Switch to different project
/superplanner execute api-rest-abc

# 5. Or just continue most recent
/superplanner execute
```

## Best Practices

1. **Clear goals**: Provide specific, well-defined project goals
2. **Right granularity**: Let decomposer create appropriate task sizes
3. **Check status regularly**: Monitor progress and intervene if needed
4. **Handle failures**: Review blocked tasks and resolve issues
5. **Iterative execution**: Run execute multiple times as dependencies resolve
6. **Save often**: Projects auto-save after each task completion

## Testing Considerations

For testing super-planner:

1. **Stub projects**: Create multi-level test projects with simulated tasks
2. **Fast completion**: Mock task execution for quick test runs
3. **Simulated interruptions**: Test resume functionality
4. **Agent failures**: Verify retry and error handling
5. **Dependency resolution**: Test complex dependency graphs

## Additional Guidance

$ARGUMENTS
