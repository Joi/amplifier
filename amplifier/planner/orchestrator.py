"""Task execution orchestrator for the Super-Planner system.

This module coordinates parallel agent execution while respecting task dependencies.
It follows the modular "bricks and studs" philosophy with a clear public contract.

Public Contract:
    orchestrate_execution(project: Project) -> ExecutionResults

    Purpose: Coordinate parallel execution of project tasks via agents

    Input: Project with tasks and dependencies
    Output: ExecutionResults with status, progress, and outcomes

    Behavior:
    - Resolves task dependencies to determine execution order
    - Spawns agents in parallel where dependencies allow
    - Tracks progress and handles failures gracefully
    - Returns comprehensive execution results
"""

import asyncio
import json
import logging
import re
import shlex
import subprocess
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path
from typing import Any

from amplifier.planner.models import Project
from amplifier.planner.models import Task
from amplifier.planner.models import TaskState
from amplifier.planner.models import TestResult

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result from executing a single task."""

    task_id: str
    status: str  # "success", "failed", "skipped", "already_completed"
    output: Any = None
    error: str | None = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    attempts: int = 1


@dataclass
class ExecutionResults:
    """Results from orchestrating project execution."""

    project_id: str
    status: str  # "completed", "partial", "failed"
    task_results: dict[str, TaskResult] = field(default_factory=dict)
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def add_result(self, result: TaskResult) -> None:
        """Add a task result and update counters."""
        self.task_results[result.task_id] = result

        if result.status == "success":
            self.completed_tasks += 1
        elif result.status == "failed":
            self.failed_tasks += 1
        elif result.status == "skipped":
            self.skipped_tasks += 1
        # "already_completed" doesn't increment any counter - not new work

    def finalize(self) -> None:
        """Finalize results and set overall status."""
        self.completed_at = datetime.now()

        # Count both newly completed and already completed tasks
        already_completed = sum(1 for r in self.task_results.values() if r.status == "already_completed")
        total_completed = self.completed_tasks + already_completed

        if self.failed_tasks == 0 and total_completed == self.total_tasks:
            self.status = "completed"
        elif total_completed > 0:
            self.status = "partial"
        else:
            self.status = "failed"


async def orchestrate_execution(
    project: Project, project_dir: str = ".", max_parallel: int = 5, max_retries: int = 2, depth: int = 0
) -> ExecutionResults:
    """Orchestrate parallel execution of project tasks with hierarchical support.

    Args:
        project: Project containing tasks to execute
        project_dir: Working directory for test execution (default: current directory)
        max_parallel: Maximum number of agents to run in parallel
        max_retries: Maximum retry attempts for failed tasks
        depth: Current recursion depth for hierarchical projects (default: 0)

    Returns:
        ExecutionResults with comprehensive execution information
    """
    max_depth = 3  # Maximum recursion depth limit

    # Check recursion depth limit
    if depth > max_depth:
        raise RecursionError(f"Project nesting exceeds maximum depth {max_depth}")

    # Add depth to logging for hierarchical visibility
    depth_prefix = "  " * depth  # Indentation for hierarchy visualization
    logger.info(f"{depth_prefix}Orchestrating project {project.id} at depth {depth}")

    results = ExecutionResults(project_id=project.id, status="in_progress", total_tasks=len(project.tasks))

    if not project.tasks:
        logger.warning(f"Project {project.id} has no tasks to execute")
        results.status = "completed"
        results.finalize()
        return results

    # Track task states - initialize from existing project state
    completed_ids: set[str] = {tid for tid, t in project.tasks.items() if t.state == TaskState.COMPLETED}
    in_progress_ids: set[str] = set()
    failed_ids: set[str] = {tid for tid, t in project.tasks.items() if t.state == TaskState.BLOCKED}
    queued_ids: set[str] = set()  # Track what's been queued

    # Create execution queue
    execution_queue = asyncio.Queue()

    # Start with tasks that are ready and not already completed or blocked
    for task in project.tasks.values():
        if task.state == TaskState.PENDING and task.can_start(completed_ids) and task.id not in failed_ids:
            await execution_queue.put(task)
            queued_ids.add(task.id)

    # Semaphore to limit parallel execution
    semaphore = asyncio.Semaphore(max_parallel)

    async def execute_task(task: Task) -> TaskResult:
        """Execute a single task with retries and test verification."""
        result = TaskResult(task_id=task.id, status="failed")

        # Check if this is a parent task with a sub-project
        if task.is_parent and task.sub_project_id:
            try:
                async with semaphore:
                    logger.info(
                        f"{depth_prefix}Executing parent task {task.id}: {task.title} (sub-project: {task.sub_project_id})"
                    )
                    in_progress_ids.add(task.id)

                    # Update task state
                    task.state = TaskState.IN_PROGRESS
                    task.updated_at = datetime.now()

                    # Load and recursively orchestrate the sub-project
                    sub_project = _load_project(task.sub_project_id)

                    # Recursively call orchestrate_execution with increased depth
                    sub_results = await orchestrate_execution(
                        sub_project, project_dir, max_parallel, max_retries, depth + 1
                    )

                    # Aggregate sub-project results
                    # Count only newly completed tasks (not already_completed)
                    sub_completed = sum(1 for r in sub_results.task_results.values() if r.status == "success")
                    sub_failed = sum(1 for r in sub_results.task_results.values() if r.status == "failed")
                    sub_total = len(sub_project.tasks)

                    # Determine parent task state based on sub-project results
                    if sub_failed == 0 and sub_completed == sub_total:
                        # All sub-tasks completed successfully
                        result.status = "success"
                        result.output = f"Sub-project completed: {sub_completed}/{sub_total} tasks successful"
                        result.completed_at = datetime.now()

                        task.state = TaskState.COMPLETED
                        task.updated_at = datetime.now()

                        in_progress_ids.discard(task.id)
                        completed_ids.add(task.id)

                        logger.info(f"{depth_prefix}Parent task {task.id} completed successfully")
                    else:
                        # Some sub-tasks failed - keep parent IN_PROGRESS (not BLOCKED)
                        # This prevents blocking sibling projects
                        result.status = "failed"
                        result.error = (
                            f"Sub-project incomplete: {sub_completed}/{sub_total} tasks successful, {sub_failed} failed"
                        )
                        result.completed_at = datetime.now()

                        # Keep task IN_PROGRESS, not BLOCKED, so dependencies aren't blocked
                        task.state = TaskState.IN_PROGRESS
                        task.updated_at = datetime.now()

                        in_progress_ids.add(task.id)  # Keep in progress

                        logger.warning(
                            f"{depth_prefix}Parent task {task.id} remains in progress due to sub-task failures"
                        )

                return result

            except Exception as e:
                logger.error(f"{depth_prefix}Parent task {task.id} failed to orchestrate sub-project: {e}")
                result.error = str(e)
                result.status = "failed"
                result.completed_at = datetime.now()

                task.state = TaskState.BLOCKED
                task.updated_at = datetime.now()

                in_progress_ids.discard(task.id)
                failed_ids.add(task.id)

                return result

        # Original leaf task execution logic
        for attempt in range(1, max_retries + 1):
            try:
                async with semaphore:
                    logger.info(f"{depth_prefix}Executing task {task.id}: {task.title} (attempt {attempt})")
                    in_progress_ids.add(task.id)

                    # Update task state
                    task.state = TaskState.IN_PROGRESS
                    task.updated_at = datetime.now()

                    # Execute via agent using Claude Code SDK
                    output = await _execute_with_agent(task, project_dir)

                    # Check if task requires testing
                    if task.requires_testing:
                        # Transition to TESTING state
                        logger.info(f"Running tests for task {task.id}")
                        task.state = TaskState.TESTING
                        task.updated_at = datetime.now()

                        # Run tests
                        test_result = await _run_task_tests(task, project_dir)

                        if test_result.passed:
                            # Tests passed - mark as completed
                            logger.info(f"Tests passed for task {task.id}")
                            result.status = "success"
                            result.output = f"{output}\n\nTests passed:\n{test_result.output}"
                            result.attempts = attempt
                            result.completed_at = datetime.now()

                            task.state = TaskState.COMPLETED
                            task.updated_at = datetime.now()

                            in_progress_ids.discard(task.id)
                            completed_ids.add(task.id)

                            logger.info(f"Task {task.id} completed successfully with passing tests")
                            break
                        # Tests failed - enter bug-hunter retry loop
                        logger.warning(f"Tests failed for task {task.id}, entering bug-hunter retry loop")
                        task.state = TaskState.TEST_FAILED
                        task.updated_at = datetime.now()

                        # Handle test failure with bug-hunter
                        bug_hunter_result = await _handle_test_failure(
                            task, test_result, project_dir, retry_count=0, max_retries=3
                        )

                        if bug_hunter_result.status == "success":
                            result = bug_hunter_result

                            task.state = TaskState.COMPLETED
                            task.updated_at = datetime.now()

                            in_progress_ids.discard(task.id)
                            completed_ids.add(task.id)

                            logger.info(f"Task {task.id} completed after bug-hunter fixes")
                            break
                        # Bug-hunter failed to fix
                        result.status = "failed"
                        result.error = bug_hunter_result.error
                        result.completed_at = datetime.now()

                        task.state = TaskState.BLOCKED
                        task.updated_at = datetime.now()

                        in_progress_ids.discard(task.id)
                        failed_ids.add(task.id)

                        logger.error(f"Task {task.id} failed even after bug-hunter attempts")
                        break
                    # No testing required - mark as completed
                    result.status = "success"
                    result.output = output
                    result.attempts = attempt
                    result.completed_at = datetime.now()

                    task.state = TaskState.COMPLETED
                    task.updated_at = datetime.now()

                    in_progress_ids.discard(task.id)
                    completed_ids.add(task.id)

                    logger.info(f"Task {task.id} completed successfully (no testing required)")
                    break

            except Exception as e:
                logger.error(f"Task {task.id} failed (attempt {attempt}): {e}")
                result.error = str(e)
                result.attempts = attempt

                if attempt == max_retries:
                    result.status = "failed"
                    result.completed_at = datetime.now()

                    task.state = TaskState.BLOCKED
                    task.updated_at = datetime.now()

                    in_progress_ids.discard(task.id)
                    failed_ids.add(task.id)
                else:
                    # Exponential backoff
                    await asyncio.sleep(2**attempt)

        return result

    async def process_queue():
        """Process tasks from the queue."""
        active_tasks = []

        while execution_queue.qsize() > 0 or active_tasks:
            # Start new tasks
            while not execution_queue.empty() and len(active_tasks) < max_parallel:
                try:
                    task = execution_queue.get_nowait()
                    active_tasks.append(asyncio.create_task(execute_task(task)))
                except asyncio.QueueEmpty:
                    break

            # Wait for at least one task to complete
            if active_tasks:
                done, pending = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)

                # Process completed tasks
                for task_future in done:
                    result = await task_future
                    results.add_result(result)
                    active_tasks.remove(task_future)

                    # Check for newly unblocked tasks only after successful completion
                    if result.status == "success":
                        # Look for tasks that are now ready to run
                        for task_id, task in project.tasks.items():
                            if (
                                task_id not in queued_ids  # Not already queued
                                and task.state == TaskState.PENDING  # Only pending tasks
                                and task.can_start(completed_ids)  # Dependencies met
                                and task_id not in failed_ids  # Not blocked
                            ):
                                await execution_queue.put(task)
                                queued_ids.add(task_id)

                # Update active tasks list
                active_tasks = list(pending)

            # Brief pause to avoid busy waiting
            if execution_queue.empty() and active_tasks:
                await asyncio.sleep(0.1)

    # Execute all tasks
    await process_queue()

    # Handle any remaining unexecuted tasks
    for task_id, task in project.tasks.items():
        if task_id not in results.task_results:
            # Tasks that were already completed before orchestration started
            if task.state == TaskState.COMPLETED:
                result = TaskResult(
                    task_id=task_id,
                    status="already_completed",
                    output="Already completed",
                    completed_at=task.updated_at or datetime.now(),
                )
                results.add_result(result)
            # Tasks skipped due to failed dependencies
            else:
                result = TaskResult(
                    task_id=task_id,
                    status="skipped",
                    error="Dependencies failed or not met",
                    completed_at=datetime.now(),
                )
                results.add_result(result)
                logger.warning(f"Task {task_id} skipped due to unmet dependencies")

    # Finalize results
    results.finalize()

    logger.info(
        f"Orchestration complete for project {project.id}: "
        f"{results.completed_tasks}/{results.total_tasks} completed, "
        f"{results.failed_tasks} failed, {results.skipped_tasks} skipped"
    )

    return results


def _load_project(project_id: str) -> Project:
    """Load a sub-project from the data directory.

    Args:
        project_id: ID of the project to load

    Returns:
        Project instance loaded from disk

    Raises:
        FileNotFoundError: If project file doesn't exist
    """

    # Standard location for project data
    project_file = Path(f"data/planner/projects/{project_id}.json")

    if not project_file.exists():
        raise FileNotFoundError(f"Sub-project not found: {project_id} at {project_file}")

    logger.debug(f"Loading sub-project from {project_file}")

    with open(project_file) as f:
        data = json.load(f)

    # Reconstruct Project from JSON data
    project = Project(
        id=data["id"],
        name=data["name"],
        created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
        updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
    )

    # Reconstruct tasks
    for task_data in data.get("tasks", {}).values():
        task = Task(
            id=task_data["id"],
            title=task_data["title"],
            description=task_data.get("description", ""),
            state=TaskState[task_data.get("state", "PENDING").upper()],
            parent_id=task_data.get("parent_id"),
            depends_on=task_data.get("depends_on", []),
            assigned_to=task_data.get("assigned_to"),
            created_at=datetime.fromisoformat(task_data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(task_data.get("updated_at", datetime.now().isoformat())),
            test_command=task_data.get("test_command"),
            test_file=task_data.get("test_file"),
            requires_testing=task_data.get("requires_testing", True),
            is_parent=task_data.get("is_parent", False),
            sub_project_id=task_data.get("sub_project_id"),
        )
        project.tasks[task.id] = task

    return project


async def _execute_with_agent(task: Task, project_dir: str) -> Any:
    """Execute task with assigned agent using Claude Code SDK.

    Args:
        task: Task to execute
        project_dir: Working directory for task execution

    Returns:
        Agent execution output
    """
    try:
        from claude_code_sdk import ClaudeCodeOptions
        from claude_code_sdk import ClaudeSDKClient
        from claude_code_sdk import CLINotFoundError
        from claude_code_sdk import ProcessError
    except ImportError as e:
        logger.error("Claude Code SDK not installed. Run: pip install claude-code-sdk")
        raise ImportError("Claude Code SDK not installed") from e

    # Infer best agent for this task if not assigned
    agent_type = task.assigned_to or _infer_agent_type(task)

    # Build comprehensive prompt for the agent
    prompt_parts = [f"Task: {task.title}"]

    if task.description:
        prompt_parts.append(f"Description: {task.description}")

    prompt_parts.append("\nPlease implement this task completely.")

    if task.test_command:
        prompt_parts.append(f"\nTest command: {task.test_command}")
        prompt_parts.append("Ensure the implementation passes all tests.")
    elif task.test_file:
        prompt_parts.append(f"\nTest file: {task.test_file}")
        prompt_parts.append("Ensure the implementation passes the tests in this file.")

    if task.depends_on:
        prompt_parts.append(f"\nThis task depends on: {', '.join(task.depends_on)}")
        prompt_parts.append("The dependencies should already be completed.")

    prompt = "\n".join(prompt_parts)

    # Configure SDK options based on agent type
    system_prompt = None
    if agent_type:
        # Set system prompt based on agent type
        agent_prompts = {
            "modular-builder": "You are a modular implementation specialist. Build self-contained modules with clear contracts.",
            "test-coverage": "You are a test coverage specialist. Write comprehensive tests with high coverage.",
            "bug-hunter": "You are a bug hunting specialist. Find and fix bugs systematically.",
            "zen-architect": "You are a zen architect. Design clean, simple, elegant solutions.",
            "integration-specialist": "You are an integration specialist. Connect services and APIs seamlessly.",
            "database-architect": "You are a database architect. Design efficient schemas and queries.",
        }
        system_prompt = agent_prompts.get(agent_type)

        if system_prompt:
            logger.info(f"Using agent type: {agent_type} for task {task.id}")

    options = ClaudeCodeOptions(
        cwd=project_dir,
        max_turns=5,
        permission_mode="acceptEdits",
        system_prompt=system_prompt,
    )

    try:
        # Execute with agent
        async with ClaudeSDKClient(options=options) as client:
            # Send the task query
            await client.query(prompt)

            # Collect response
            output_parts = []
            total_cost = 0.0
            duration_ms = 0

            async for message in client.receive_response():
                # Handle text content
                if hasattr(message, "content"):
                    content = getattr(message, "content", None)
                    if content:
                        for block in content:
                            # Check for text attribute safely
                            if hasattr(block, "text"):
                                text_value = getattr(block, "text", None)
                                if text_value:
                                    output_parts.append(str(text_value))
                            elif hasattr(block, "type") and getattr(block, "type", None) == "text":
                                # Alternative text access pattern
                                if hasattr(block, "value"):
                                    value = getattr(block, "value", None)
                                    if value:
                                        output_parts.append(str(value))

                # Capture metadata from result message
                msg_type = type(message).__name__
                if msg_type == "ResultMessage":
                    # Safe attribute access with defaults
                    total_cost = getattr(message, "total_cost_usd", 0.0) if hasattr(message, "total_cost_usd") else 0.0
                    duration_ms = getattr(message, "duration_ms", 0) if hasattr(message, "duration_ms") else 0

                    logger.info(
                        f"Task {task.id} completed by {agent_type or 'default agent'} "
                        f"(cost: ${total_cost:.4f}, duration: {duration_ms}ms)"
                    )

            output = "".join(output_parts)
            return output if output else f"Task {task.title} completed successfully"

    except CLINotFoundError:
        error_msg = "Claude Code CLI not found. Please install it with: npm install -g @anthropic-ai/claude-code"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except ProcessError as e:
        logger.error(f"Process error executing task {task.id}: {e}")
        raise RuntimeError(f"Agent execution failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error executing task {task.id}: {e}")
        raise RuntimeError(f"Agent execution failed: {e}")


def _infer_agent_type(task: Task) -> str | None:
    """Infer the best agent type based on task title and description.

    Args:
        task: Task to analyze

    Returns:
        Agent type name or None if unclear
    """
    # Combine title and description for analysis
    text = f"{task.title} {task.description}".lower()

    # Keywords for each agent type
    agent_keywords = {
        "modular-builder": ["implement", "build", "create", "module", "component", "feature"],
        "test-coverage": ["test", "spec", "validate", "coverage", "testing", "unit test"],
        "bug-hunter": ["fix", "bug", "debug", "error", "issue", "failure", "broken"],
        "zen-architect": ["design", "architect", "structure", "refactor", "pattern"],
        "integration-specialist": ["integrate", "api", "service", "connect", "endpoint", "webhook"],
        "database-architect": ["database", "schema", "migration", "query", "sql", "index"],
    }

    # Score each agent type
    scores = {}
    for agent_type, keywords in agent_keywords.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > 0:
            scores[agent_type] = score

    # Return agent with highest score, or None if no matches
    if scores:
        best_agent = max(scores.keys(), key=lambda k: scores[k])
        logger.debug(f"Inferred agent type '{best_agent}' for task: {task.title}")
        return best_agent

    logger.debug(f"Could not infer agent type for task: {task.title}")
    return None


async def _run_task_tests(task: Task, project_dir: str) -> TestResult:
    """Run tests associated with a task.

    For tasks with test dependencies (e.g., buffer-impl depends on buffer-tests),
    look for test files in the project directory and execute them.

    Args:
        task: Task to run tests for
        project_dir: Working directory for test execution

    Returns:
        TestResult with:
        - passed: bool
        - output: str (test runner output)
        - failure_details: str (parsed failures for bug-hunter)
    """
    # Determine test command from task metadata or conventions
    test_command = _determine_test_command(task)

    if not test_command:
        logger.warning(f"No test command found for task {task.id}, skipping tests")
        return TestResult(passed=True, output="No tests configured", failure_details=None)

    logger.info(f"Running test command for task {task.id}: {test_command}")

    # Execute test command
    try:
        # Use shlex.split to safely parse command without shell=True
        command_args = shlex.split(test_command)
        result = subprocess.run(
            command_args,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for tests
        )

        # Parse output to determine pass/fail
        passed = _parse_test_success(result.stdout, result.stderr, result.returncode)

        # Extract failure details if tests failed
        failure_details = None
        if not passed:
            failure_details = _extract_failure_details(result.stdout, result.stderr)

        output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"

        return TestResult(passed=passed, output=output, failure_details=failure_details)

    except subprocess.TimeoutExpired:
        return TestResult(
            passed=False,
            output="Test execution timed out after 5 minutes",
            failure_details="Tests exceeded maximum execution time of 5 minutes",
        )
    except Exception as e:
        return TestResult(
            passed=False,
            output=f"Failed to execute tests: {e}",
            failure_details=f"Test execution error: {e}",
        )


def _determine_test_command(task: Task) -> str | None:
    """Determine the test command for a task.

    Uses explicit test_command if provided, otherwise uses conventions:
    1. Pytest convention: pytest tests/test_{task_id}.py -v
    2. Make convention: make test-{task_id}
    3. File-based convention: Look for {task_id}_test.py or test_{task_id}.py

    Args:
        task: Task to determine test command for

    Returns:
        Test command string or None if no tests found
    """
    # Use explicit test command if provided
    if task.test_command:
        return task.test_command

    # Use test file if provided
    if task.test_file:
        if Path(task.test_file).exists():
            # Determine test runner based on file extension
            if task.test_file.endswith(".py"):
                return f"pytest {task.test_file} -v"
            if task.test_file.endswith(".js"):
                return f"npm test -- {task.test_file}"
        return None

    # Convention-based discovery
    task_id_clean = task.id.replace("-", "_")

    # Check for pytest convention
    test_paths = [
        f"tests/test_{task_id_clean}.py",
        f"test_{task_id_clean}.py",
        f"tests/{task_id_clean}_test.py",
        f"{task_id_clean}_test.py",
    ]

    for test_path in test_paths:
        if Path(test_path).exists():
            return f"pytest {test_path} -v"

    # Check for make target
    # Note: This would need to parse Makefile to check if target exists
    # For now, we'll skip this convention

    # No test command found
    return None


def _parse_test_success(stdout: str, stderr: str, return_code: int) -> bool:
    """Parse test output to determine if tests passed.

    Supports common test frameworks:
    - pytest: return code 0 = success
    - unittest: return code 0 = success
    - jest: return code 0 = success

    Args:
        stdout: Standard output from test command
        stderr: Standard error from test command
        return_code: Process return code

    Returns:
        True if tests passed, False otherwise
    """
    # Primary check: return code
    if return_code == 0:
        return True

    # Secondary checks for specific frameworks
    # pytest patterns
    if (
        "passed" in stdout.lower()
        and "failed" not in stdout.lower()
        and re.search(r"\d+ passed", stdout)
        and not re.search(r"\d+ failed", stdout)
    ):
        # Check for pytest summary line like "5 passed in 0.12s"
        return True

    # unittest patterns
    if "OK" in stdout and "FAILED" not in stdout:
        return True

    # jest patterns
    return bool("PASS" in stdout and "FAIL" not in stdout)


def _extract_failure_details(stdout: str, stderr: str) -> str:
    """Extract failure details from test output for bug-hunter.

    Parses test output to extract:
    - Failed test names
    - Assertion errors
    - Stack traces
    - Error messages

    Args:
        stdout: Standard output from test command
        stderr: Standard error from test command

    Returns:
        Formatted failure details string
    """
    details = []

    # Combine outputs for parsing
    output = f"{stdout}\n{stderr}"

    # Extract pytest failures
    pytest_failures = re.findall(r"FAILED (.*?) - (.*?)(?:\n|$)", output)
    for test_name, error in pytest_failures:
        details.append(f"FAILED: {test_name}\nError: {error}")

    # Extract assertion errors
    assertion_errors = re.findall(r"AssertionError: (.*?)(?:\n|$)", output)
    for error in assertion_errors:
        details.append(f"Assertion failed: {error}")

    # Extract general error messages
    error_patterns = [
        r"Error: (.*?)(?:\n|$)",
        r"ERROR: (.*?)(?:\n|$)",
        r"FAIL: (.*?)(?:\n|$)",
        r"Failed: (.*?)(?:\n|$)",
    ]

    for pattern in error_patterns:
        matches = re.findall(pattern, output)
        for match in matches:
            if match not in details:  # Avoid duplicates
                details.append(match)

    # If no specific failures extracted, include summary
    if not details:
        if "failed" in output.lower():
            # Try to extract summary line
            summary_match = re.search(r"(\d+ failed.*?)(?:\n|$)", output)
            if summary_match:
                details.append(f"Test summary: {summary_match.group(1)}")
        else:
            details.append("Tests failed but no specific error details could be extracted")

    return "\n\n".join(details)


async def _handle_test_failure(
    task: Task, test_result: TestResult, project_dir: str, retry_count: int = 0, max_retries: int = 3
) -> TaskResult:
    """Handle test failures with bug-hunter retry loop.

    1. Spawn bug-hunter with failure details
    2. Bug-hunter analyzes and fixes code
    3. Re-run tests
    4. Repeat up to max_retries times

    Args:
        task: Task that failed tests
        test_result: Test result with failure details
        project_dir: Working directory for test execution
        retry_count: Current retry attempt
        max_retries: Maximum number of retries

    Returns:
        TaskResult with success or final failure
    """
    if retry_count >= max_retries:
        return TaskResult(
            task_id=task.id,
            status="failed",
            error=f"Tests failed after {max_retries} bug-hunter attempts:\n{test_result.failure_details}",
            completed_at=datetime.now(),
        )

    # Spawn bug-hunter with context
    test_command = _determine_test_command(task) or "pytest"
    bug_hunter_prompt = f"""Task: {task.title}
Description: {task.description}

Tests have failed with the following errors:
{test_result.failure_details}

Full test output:
{test_result.output}

Please analyze the failures, fix the bugs, and ensure all tests pass.

Test command: {test_command}
Working directory: {project_dir}

Focus on fixing the specific test failures mentioned above. Make minimal changes to fix the issues."""

    logger.info(f"Spawning bug-hunter for task {task.id} (attempt {retry_count + 1}/{max_retries})")

    # Update task state
    task.state = TaskState.IN_PROGRESS
    task.updated_at = datetime.now()

    # Execute bug-hunter
    fix_output = await _execute_with_bug_hunter(bug_hunter_prompt, task, project_dir)

    # Re-run tests
    logger.info(f"Re-running tests after bug-hunter fixes for task {task.id}")
    task.state = TaskState.TESTING
    task.updated_at = datetime.now()

    retest_result = await _run_task_tests(task, project_dir)

    if retest_result.passed:
        # Tests now pass
        task.state = TaskState.COMPLETED
        task.updated_at = datetime.now()

        return TaskResult(
            task_id=task.id,
            status="success",
            output=f"Fixed after {retry_count + 1} bug-hunter attempts:\n{fix_output}\n\nTests now passing:\n{retest_result.output}",
            completed_at=datetime.now(),
        )
    # Tests still failing, recurse
    task.state = TaskState.TEST_FAILED
    task.updated_at = datetime.now()

    return await _handle_test_failure(task, retest_result, project_dir, retry_count + 1, max_retries)


async def _execute_with_bug_hunter(prompt: str, task: Task, project_dir: str) -> str:
    """Spawn bug-hunter agent using Claude Code SDK.

    Args:
        prompt: Bug-hunter prompt with failure details
        task: Task context
        project_dir: Working directory for execution

    Returns:
        Bug-hunter output
    """
    try:
        from claude_code_sdk import ClaudeCodeOptions
        from claude_code_sdk import ClaudeSDKClient
    except ImportError as e:
        logger.error("Claude Code SDK not installed")
        raise ImportError("Claude Code SDK not installed") from e

    # Configure for bug-hunter with bug-fixing system prompt
    options = ClaudeCodeOptions(
        cwd=project_dir,
        max_turns=5,
        permission_mode="acceptEdits",
        system_prompt="You are a bug-hunting specialist. Find and fix bugs systematically with minimal changes.",
    )

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            # Collect response
            output_parts = []
            async for message in client.receive_response():
                if hasattr(message, "content"):
                    content = getattr(message, "content", None)
                    if content:
                        for block in content:
                            if hasattr(block, "text"):
                                text_value = getattr(block, "text", None)
                                if text_value:
                                    output_parts.append(str(text_value))

            output = "".join(output_parts)

        # Return after context manager closes
        return output if output else "Bug-hunter completed fixes"

    except Exception as e:
        logger.error(f"Error executing bug-hunter: {e}")
        raise RuntimeError(f"Bug-hunter execution failed: {e}")


# Public exports
__all__ = ["orchestrate_execution", "ExecutionResults", "TaskResult"]
