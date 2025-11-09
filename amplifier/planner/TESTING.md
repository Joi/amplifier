# Super-Planner Testing Strategy

This document outlines the testing approach for the super-planner system, including unit tests, integration tests, and end-to-end tests with simulated multi-level projects.

## Testing Goals

1. **Validate core functionality**: Task management, dependencies, state transitions
2. **Test multi-agent coordination**: Parallel execution, agent assignment, failure handling
3. **Verify interruption handling**: Resume capability, abandoned task recovery
4. **Test at scale**: Large hierarchies, complex dependencies, many parallel tasks
5. **Fast test execution**: Mock task execution for quick iteration

## Test Hierarchy

### Level 1: Unit Tests (Existing)

Located in `tests/test_planner.py` - covers:
- Task creation and validation
- Dependency checking
- Project operations
- Storage persistence

**Keep these tests** - they validate the core data model.

### Level 2: Integration Tests

Test coordination between components:

```python
# tests/test_integration.py

import pytest
from amplifier.planner import (
    Project, Task, TaskState,
    decompose_goal, ProjectContext,
    orchestrate_execution
)

@pytest.mark.asyncio
async def test_goal_to_execution_flow():
    """Test complete flow from goal to execution"""

    # 1. Create project from goal
    project = Project(id="test-proj", name="Test Project")
    context = ProjectContext(project=project, max_depth=2, min_tasks=3)

    tasks = await decompose_goal("Build a simple blog", context)
    for task in tasks:
        project.add_task(task)

    # 2. Verify task structure
    assert len(project.tasks) >= 3
    assert any(t.depends_on for t in project.tasks.values())  # Has dependencies

    # 3. Execute tasks
    results = await orchestrate_execution(project, max_parallel=2)

    # 4. Verify execution
    assert results.status in ["completed", "partial"]
    assert results.completed_tasks > 0


@pytest.mark.asyncio
async def test_parallel_execution():
    """Test that independent tasks run in parallel"""

    project = Project(id="test-parallel", name="Parallel Test")

    # Create independent tasks (no dependencies)
    task1 = Task(id="t1", title="Task 1", description="Independent task 1")
    task2 = Task(id="t2", title="Task 2", description="Independent task 2")
    task3 = Task(id="t3", title="Task 3", description="Independent task 3")

    project.add_task(task1)
    project.add_task(task2)
    project.add_task(task3)

    # Execute with parallelism
    import time
    start = time.time()
    results = await orchestrate_execution(project, max_parallel=3)
    duration = time.time() - start

    # All should complete
    assert results.completed_tasks == 3

    # Should take ~0.5s (mock execution time), not 1.5s sequential
    assert duration < 1.0  # Allows some overhead


@pytest.mark.asyncio
async def test_dependency_ordering():
    """Test that dependencies are respected"""

    project = Project(id="test-deps", name="Dependency Test")

    # Create task chain: t1 -> t2 -> t3
    task1 = Task(id="t1", title="Task 1", description="First task")
    task2 = Task(id="t2", title="Task 2", description="Second task", depends_on=["t1"])
    task3 = Task(id="t3", title="Task 3", description="Third task", depends_on=["t2"])

    project.add_task(task1)
    project.add_task(task2)
    project.add_task(task3)

    # Track execution order
    execution_order = []

    async def track_execution(task: Task):
        execution_order.append(task.id)
        await asyncio.sleep(0.1)
        return f"Completed {task.id}"

    # Monkeypatch the execution function
    import amplifier.planner.orchestrator as orch
    original_execute = orch._execute_with_agent
    orch._execute_with_agent = track_execution

    try:
        results = await orchestrate_execution(project)

        # Verify order
        assert execution_order == ["t1", "t2", "t3"]
        assert results.completed_tasks == 3

    finally:
        orch._execute_with_agent = original_execute
```

### Level 3: Stub Project Tests

Generate multi-level test projects for comprehensive testing:

```python
# tests/test_stub_projects.py

import pytest
import uuid
from amplifier.planner import Project, Task, TaskState

def create_stub_project(depth: int, breadth: int, add_dependencies: bool = True) -> Project:
    """Generate a stub project for testing.

    Args:
        depth: Number of hierarchy levels
        breadth: Number of tasks per level
        add_dependencies: Whether to add dependencies between tasks

    Returns:
        Project with generated task hierarchy
    """

    project = Project(id=str(uuid.uuid4()), name=f"Stub Project {depth}x{breadth}")

    all_tasks = []

    def create_level(level: int, parent_id: str | None = None) -> list[Task]:
        """Recursively create tasks at each level"""

        if level >= depth:
            return []

        level_tasks = []
        previous_task_id = None

        for i in range(breadth):
            task_id = f"L{level}-T{i}"
            task = Task(
                id=task_id,
                title=f"Level {level} Task {i}",
                description=f"Test task at depth {level}, position {i}",
                state=TaskState.PENDING,
                parent_id=parent_id,
                depends_on=[previous_task_id] if add_dependencies and previous_task_id else []
            )

            level_tasks.append(task)
            all_tasks.append(task)

            # Create children for this task
            children = create_level(level + 1, task_id)
            level_tasks.extend(children)

            if add_dependencies:
                previous_task_id = task_id

        return level_tasks

    # Generate all tasks
    create_level(0)

    # Add to project
    for task in all_tasks:
        project.add_task(task)

    return project


@pytest.mark.asyncio
async def test_small_stub_project():
    """Test execution of small stub project (2 levels, 3 tasks each)"""

    project = create_stub_project(depth=2, breadth=3)

    # Should have 3 root tasks + 9 child tasks = 12 total
    assert len(project.tasks) == 12

    # Execute
    results = await orchestrate_execution(project, max_parallel=3)

    # All should complete
    assert results.completed_tasks == 12
    assert results.failed_tasks == 0


@pytest.mark.asyncio
async def test_large_stub_project():
    """Test execution of large stub project (3 levels, 5 tasks each)"""

    project = create_stub_project(depth=3, breadth=5)

    # Should have 5 + 25 + 125 = 155 total tasks
    assert len(project.tasks) == 155

    # Execute with higher parallelism
    results = await orchestrate_execution(project, max_parallel=10)

    # Verify completion
    assert results.completed_tasks == 155
    assert results.status == "completed"


@pytest.mark.asyncio
async def test_deep_hierarchy_stub():
    """Test execution of deep hierarchy (5 levels, 2 tasks each)"""

    project = create_stub_project(depth=5, breadth=2)

    # Should have 2 + 4 + 8 + 16 + 32 = 62 total tasks
    assert len(project.tasks) == 62

    # Execute
    results = await orchestrate_execution(project)

    # All should complete
    assert results.completed_tasks == 62


@pytest.mark.asyncio
async def test_independent_tasks_stub():
    """Test stub project with no dependencies (max parallelism)"""

    project = create_stub_project(depth=2, breadth=5, add_dependencies=False)

    # Execute with limited parallelism
    results = await orchestrate_execution(project, max_parallel=5)

    # All should complete
    assert len(project.tasks) == 30  # 5 root + 25 children
    assert results.completed_tasks == 30

    # Verify high parallelism was utilized
    # (would need timing or instrumentation to prove)
```

### Level 4: Interruption and Resume Tests

Test handling of interruptions and resume functionality:

```python
# tests/test_interruption.py

import pytest
from amplifier.planner import (
    Project, Task, TaskState,
    save_project, load_project,
    orchestrate_execution
)

@pytest.mark.asyncio
async def test_resume_after_interruption():
    """Test resuming execution after interruption"""

    # 1. Create project and partially execute
    project = create_stub_project(depth=2, breadth=3)

    # Execute only first batch
    results = await orchestrate_execution(project, max_parallel=1)  # Serial execution

    # Save state
    save_project(project)

    # Simulate interruption - some tasks completed, some pending
    completed_count = sum(1 for t in project.tasks.values() if t.state == TaskState.COMPLETED)
    assert 0 < completed_count < len(project.tasks)  # Partial completion

    # 2. Reload and resume
    loaded_project = load_project(project.id)

    # Continue execution
    resume_results = await orchestrate_execution(loaded_project)

    # All should now be complete
    final_completed = sum(1 for t in loaded_project.tasks.values() if t.state == TaskState.COMPLETED)
    assert final_completed == len(loaded_project.tasks)


@pytest.mark.asyncio
async def test_abandoned_task_recovery():
    """Test recovery of abandoned in-progress tasks"""

    project = create_stub_project(depth=1, breadth=3)

    # Manually mark a task as in-progress (simulating abandonment)
    first_task = list(project.tasks.values())[0]
    first_task.state = TaskState.IN_PROGRESS
    save_project(project)

    # Reload project
    loaded_project = load_project(project.id)

    # Task should still be in_progress
    reloaded_task = loaded_project.tasks[first_task.id]
    assert reloaded_task.state == TaskState.IN_PROGRESS

    # Resume should reset abandoned tasks
    # (This logic needs to be implemented in orchestrator or coordinator)

    # Execute - should handle abandoned task
    results = await orchestrate_execution(loaded_project)

    # All tasks should complete
    assert results.completed_tasks == len(loaded_project.tasks)


@pytest.mark.asyncio
async def test_simulated_interruptions():
    """Test with simulated random interruptions"""

    project = create_stub_project(depth=3, breadth=3)
    total_tasks = len(project.tasks)

    # Execute with interruptions
    for i in range(5):  # Up to 5 interruption cycles
        results = await orchestrate_execution(project, max_parallel=3)

        if results.status == "completed":
            break

        # Save and reload (simulating interruption)
        save_project(project)
        project = load_project(project.id)

    # Eventually all should complete
    completed = sum(1 for t in project.tasks.values() if t.state == TaskState.COMPLETED)
    assert completed == total_tasks
```

### Level 5: Agent Coordination Tests

Test multi-agent coordination and assignment:

```python
# tests/test_agent_coordination.py

import pytest
from amplifier.planner import (
    Project, Task,
    assign_agent, suggest_agent_for_domain,
    get_agent_workload
)

def test_agent_assignment():
    """Test agent assignment based on task type"""

    # Design tasks -> zen-architect
    design_task = Task(id="t1", title="Design API architecture", description="Create system design")
    agent = suggest_agent_for_domain(design_task)
    assert agent == "zen-architect"

    # Implementation tasks -> modular-builder
    impl_task = Task(id="t2", title="Implement login endpoint", description="Build the endpoint")
    agent = suggest_agent_for_domain(impl_task)
    assert agent == "modular-builder"

    # Bug tasks -> bug-hunter
    bug_task = Task(id="t3", title="Fix authentication bug", description="Debug the error")
    agent = suggest_agent_for_domain(bug_task)
    assert agent == "bug-hunter"

    # Test tasks -> test-coverage
    test_task = Task(id="t4", title="Add unit tests", description="Write test suite")
    agent = suggest_agent_for_domain(test_task)
    assert agent == "test-coverage"


def test_agent_workload_tracking():
    """Test agent workload calculation"""

    project = Project(id="test", name="Test")

    # Assign tasks to agents
    task1 = Task(id="t1", title="Task 1", description="", assigned_to="zen-architect")
    task2 = Task(id="t2", title="Task 2", description="", assigned_to="zen-architect")
    task3 = Task(id="t3", title="Task 3", description="", assigned_to="modular-builder")

    project.add_task(task1)
    project.add_task(task2)
    project.add_task(task3)

    # Check workload
    workload = get_agent_workload(project)

    assert workload["zen-architect"] == 2
    assert workload["modular-builder"] == 1


@pytest.mark.asyncio
async def test_balanced_agent_distribution():
    """Test that agents are distributed evenly"""

    project = create_stub_project(depth=2, breadth=10)

    # Assign agents
    for task in project.tasks.values():
        agent = suggest_agent_for_domain(task)
        task.assigned_to = agent

    # Check distribution
    workload = get_agent_workload(project)

    # Should have multiple agents used
    assert len(workload) > 1

    # No single agent should dominate (within reason)
    max_workload = max(workload.values())
    min_workload = min(workload.values())
    assert max_workload - min_workload < len(project.tasks) * 0.5  # Not too unbalanced
```

## Mock Task Execution

For fast tests, mock the task execution:

```python
# tests/conftest.py

import pytest
import asyncio
from amplifier.planner import orchestrator

@pytest.fixture
def mock_fast_execution(monkeypatch):
    """Mock task execution for fast tests"""

    async def fast_execute(task):
        """Complete tasks instantly"""
        await asyncio.sleep(0.01)  # Minimal delay
        return f"Mock result: {task.title}"

    monkeypatch.setattr(orchestrator, "_execute_with_agent", fast_execute)


@pytest.fixture
def mock_configurable_execution(monkeypatch):
    """Mock execution with configurable delays and failures"""

    class ExecutionMock:
        def __init__(self):
            self.delay = 0.1
            self.failure_rate = 0.0  # 0.0 to 1.0

        async def execute(self, task):
            await asyncio.sleep(self.delay)

            # Randomly fail based on rate
            import random
            if random.random() < self.failure_rate:
                raise RuntimeError(f"Mock failure for {task.id}")

            return f"Mock result: {task.title}"

    mock = ExecutionMock()
    monkeypatch.setattr(orchestrator, "_execute_with_agent", mock.execute)
    return mock
```

## Test Data Generators

Utility functions for generating test scenarios:

```python
# tests/utils.py

def create_linear_chain(length: int) -> Project:
    """Create project with linear task chain (t1 -> t2 -> t3 -> ...)"""

    project = Project(id="linear", name="Linear Chain")
    previous_id = None

    for i in range(length):
        task = Task(
            id=f"t{i}",
            title=f"Task {i}",
            description="",
            depends_on=[previous_id] if previous_id else []
        )
        project.add_task(task)
        previous_id = task.id

    return project


def create_diamond_dependency() -> Project:
    """Create diamond-shaped dependency graph"""

    project = Project(id="diamond", name="Diamond")

    # t1 -> (t2, t3) -> t4
    t1 = Task(id="t1", title="Start", description="")
    t2 = Task(id="t2", title="Branch A", description="", depends_on=["t1"])
    t3 = Task(id="t3", title="Branch B", description="", depends_on=["t1"])
    t4 = Task(id="t4", title="Merge", description="", depends_on=["t2", "t3"])

    for task in [t1, t2, t3, t4]:
        project.add_task(task)

    return project


def create_complex_graph(num_levels: int, fan_out: int) -> Project:
    """Create complex dependency graph with specified structure"""

    project = Project(id="complex", name="Complex Graph")

    # Implementation left as exercise - creates arbitrary complexity
    ...

    return project
```

## Running Tests

```bash
# Run all tests
uv run pytest amplifier/planner/tests/ -v

# Run specific test category
uv run pytest amplifier/planner/tests/test_stub_projects.py -v

# Run with coverage
uv run pytest amplifier/planner/tests/ --cov=amplifier.planner --cov-report=html

# Run fast tests only (exclude slow integration tests)
uv run pytest amplifier/planner/tests/ -m "not slow" -v

# Run slow/integration tests
uv run pytest amplifier/planner/tests/ -m "slow" -v
```

## Test Markers

Use pytest markers to categorize tests:

```python
# Mark slow tests
@pytest.mark.slow
@pytest.mark.asyncio
async def test_large_project():
    ...

# Mark integration tests
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow():
    ...

# Mark unit tests (default)
def test_task_creation():
    ...
```

## Continuous Integration

Add to CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Test Super-Planner
  run: |
    uv run pytest amplifier/planner/tests/ --cov=amplifier.planner
```

## Future Testing Enhancements

1. **Property-based testing** with Hypothesis
2. **Chaos testing** with random interruptions and failures
3. **Performance benchmarks** for large projects
4. **Load testing** with concurrent coordinator instances
5. **End-to-end tests** using actual Claude Code agents
