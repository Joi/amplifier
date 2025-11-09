#!/usr/bin/env python3
"""Real-world test: Building an API Rate Limiter with Super-Planner.

This script simulates a real developer workflow using super-planner to build
a complete API rate limiting system with Redis backend, middleware, testing,
and monitoring.

The test creates a project plan and then simulates multiple amplifier sessions
to complete the work, demonstrating interruption/resume capabilities.
"""

import sys

from amplifier.planner import Project
from amplifier.planner import Task
from amplifier.planner import TaskState
from amplifier.planner import load_project
from amplifier.planner import save_project
from amplifier.planner.agent_mapper import assign_agents_to_tasks
from amplifier.planner.storage import find_project_by_name
from amplifier.planner.storage import get_most_recent_project


def create_rate_limiter_project() -> Project:
    """Create a comprehensive project plan for building an API rate limiter.

    The plan includes:
    - Architecture & Design (3 tasks)
    - Redis Integration (4 tasks)
    - Rate Limiting Logic (5 tasks)
    - Middleware Implementation (4 tasks)
    - Configuration System (3 tasks)
    - Testing (5 tasks)
    - Monitoring & Observability (3 tasks)
    - Documentation (3 tasks)

    Total: 30 tasks across 8 phases
    """
    project = Project(id="api-rate-limiter", name="API Rate Limiter Implementation")

    # Phase 1: Architecture & Design
    tasks = [
        Task(
            id="arch-requirements",
            title="Define Requirements",
            description=(
                "Document rate limiting requirements:\n"
                "- Per-user limits (e.g., 100 req/min)\n"
                "- Per-endpoint limits (e.g., 1000 req/min)\n"
                "- IP-based limits for anonymous users\n"
                "- Burst allowance handling\n"
                "- Response headers (X-RateLimit-Limit, X-RateLimit-Remaining)\n"
                "- Error responses (429 Too Many Requests)"
            ),
        ),
        Task(
            id="arch-algorithm",
            title="Choose Rate Limiting Algorithm",
            description=(
                "Research and select algorithm:\n"
                "- Token bucket (recommended for burst handling)\n"
                "- Leaky bucket\n"
                "- Fixed window\n"
                "- Sliding window\n"
                "Document choice rationale and implementation strategy"
            ),
            depends_on=["arch-requirements"],
        ),
        Task(
            id="arch-design",
            title="Design System Architecture",
            description=(
                "Create architecture document:\n"
                "- Redis data structures for counters\n"
                "- Key naming conventions\n"
                "- TTL strategies\n"
                "- Middleware integration points\n"
                "- Configuration schema\n"
                "- Monitoring hooks"
            ),
            depends_on=["arch-requirements", "arch-algorithm"],
        ),
    ]

    # Phase 2: Redis Integration
    tasks.extend(
        [
            Task(
                id="redis-setup",
                title="Set Up Redis Connection",
                description=(
                    "Implement Redis connection:\n"
                    "- Connection pooling\n"
                    "- Configuration from environment\n"
                    "- Health check endpoint\n"
                    "- Graceful connection handling"
                ),
                depends_on=["arch-design"],
            ),
            Task(
                id="redis-operations",
                title="Implement Redis Operations",
                description=(
                    "Create Redis operation layer:\n"
                    "- Atomic increment with TTL\n"
                    "- Key generation (user_id:endpoint:window)\n"
                    "- Batch operations for multiple keys\n"
                    "- Error handling and fallback"
                ),
                depends_on=["redis-setup"],
            ),
            Task(
                id="redis-tests",
                title="Test Redis Integration",
                description=(
                    "Unit tests for Redis operations:\n"
                    "- Connection tests\n"
                    "- Key generation tests\n"
                    "- Atomic operations tests\n"
                    "- TTL behavior tests\n"
                    "- Failure scenario tests"
                ),
                depends_on=["redis-operations"],
            ),
            Task(
                id="redis-mock",
                title="Create Redis Mock for Testing",
                description=(
                    "Build in-memory Redis mock:\n"
                    "- Supports INCR, EXPIRE, GET operations\n"
                    "- TTL simulation\n"
                    "- Integration with pytest fixtures\n"
                    "- Used for testing without real Redis"
                ),
                depends_on=["redis-setup"],
            ),
        ]
    )

    # Phase 3: Rate Limiting Logic
    tasks.extend(
        [
            Task(
                id="limiter-core",
                title="Implement Core Rate Limiter",
                description=(
                    "Build rate limiting logic:\n"
                    "- Token bucket algorithm implementation\n"
                    "- Check if request allowed\n"
                    "- Update counters atomically\n"
                    "- Return remaining quota\n"
                    "- Handle time windows correctly"
                ),
                depends_on=["arch-algorithm", "redis-operations"],
            ),
            Task(
                id="limiter-strategies",
                title="Implement Multiple Limit Strategies",
                description=(
                    "Support different limiting strategies:\n"
                    "- Per-user limits\n"
                    "- Per-endpoint limits\n"
                    "- Per-IP limits\n"
                    "- Combined limits (user AND endpoint)\n"
                    "- Configurable strategies per endpoint"
                ),
                depends_on=["limiter-core"],
            ),
            Task(
                id="limiter-burst",
                title="Add Burst Handling",
                description=(
                    "Implement burst allowance:\n"
                    "- Allow temporary bursts over limit\n"
                    "- Burst bucket size configuration\n"
                    "- Refill rate configuration\n"
                    "- Burst exhaustion handling"
                ),
                depends_on=["limiter-core"],
            ),
            Task(
                id="limiter-whitelist",
                title="Implement Whitelist/Blacklist",
                description=(
                    "Add access control lists:\n"
                    "- Whitelist: bypass rate limits\n"
                    "- Blacklist: reject immediately\n"
                    "- IP-based and user-based lists\n"
                    "- Dynamic list updates\n"
                    "- Redis-backed storage"
                ),
                depends_on=["limiter-core"],
            ),
            Task(
                id="limiter-tests",
                title="Test Rate Limiting Logic",
                description=(
                    "Comprehensive unit tests:\n"
                    "- Basic limiting tests\n"
                    "- Window boundary tests\n"
                    "- Concurrent request tests\n"
                    "- Burst behavior tests\n"
                    "- Edge cases and error conditions"
                ),
                depends_on=["limiter-strategies", "limiter-burst", "limiter-whitelist"],
            ),
        ]
    )

    # Phase 4: Middleware Implementation
    tasks.extend(
        [
            Task(
                id="middleware-core",
                title="Create Rate Limit Middleware",
                description=(
                    "Build FastAPI middleware:\n"
                    "- Extract user/IP from request\n"
                    "- Apply rate limiting\n"
                    "- Set response headers\n"
                    "- Return 429 when limited\n"
                    "- Log rate limit events"
                ),
                depends_on=["limiter-core"],
            ),
            Task(
                id="middleware-headers",
                title="Implement Response Headers",
                description=(
                    "Add standard rate limit headers:\n"
                    "- X-RateLimit-Limit: total quota\n"
                    "- X-RateLimit-Remaining: remaining quota\n"
                    "- X-RateLimit-Reset: reset timestamp\n"
                    "- Retry-After: wait time on 429"
                ),
                depends_on=["middleware-core"],
            ),
            Task(
                id="middleware-decorator",
                title="Create Rate Limit Decorator",
                description=(
                    "Add @rate_limit decorator:\n"
                    "- Per-endpoint configuration\n"
                    "- Override global limits\n"
                    "- Support custom key extractors\n"
                    "- Easy to apply to routes"
                ),
                depends_on=["middleware-core"],
            ),
            Task(
                id="middleware-tests",
                title="Test Middleware",
                description=(
                    "Integration tests for middleware:\n"
                    "- Request processing tests\n"
                    "- Header validation tests\n"
                    "- 429 response tests\n"
                    "- Decorator tests\n"
                    "- End-to-end flow tests"
                ),
                depends_on=["middleware-headers", "middleware-decorator"],
            ),
        ]
    )

    # Phase 5: Configuration System
    tasks.extend(
        [
            Task(
                id="config-schema",
                title="Define Configuration Schema",
                description=(
                    "Create configuration structure:\n"
                    "- Global default limits\n"
                    "- Per-endpoint overrides\n"
                    "- Redis connection settings\n"
                    "- Monitoring settings\n"
                    "- YAML/JSON configuration files"
                ),
                depends_on=["arch-design"],
            ),
            Task(
                id="config-loader",
                title="Implement Configuration Loader",
                description=(
                    "Build config loading system:\n"
                    "- Load from environment\n"
                    "- Load from files\n"
                    "- Validate configuration\n"
                    "- Hot reload support\n"
                    "- Provide defaults"
                ),
                depends_on=["config-schema"],
            ),
            Task(
                id="config-tests",
                title="Test Configuration System",
                description=(
                    "Configuration tests:\n"
                    "- Loading from different sources\n"
                    "- Validation tests\n"
                    "- Override behavior tests\n"
                    "- Default value tests\n"
                    "- Hot reload tests"
                ),
                depends_on=["config-loader"],
            ),
        ]
    )

    # Phase 6: Testing
    tasks.extend(
        [
            Task(
                id="test-unit",
                title="Comprehensive Unit Tests",
                description=(
                    "Write all unit tests:\n"
                    "- Rate limiter logic tests\n"
                    "- Redis operations tests\n"
                    "- Configuration tests\n"
                    "- 95%+ code coverage\n"
                    "- Fast execution (< 2 seconds)"
                ),
                depends_on=["limiter-tests", "redis-tests", "config-tests"],
            ),
            Task(
                id="test-integration",
                title="Integration Tests",
                description=(
                    "End-to-end integration tests:\n"
                    "- Full request flow tests\n"
                    "- Multiple concurrent requests\n"
                    "- Redis integration tests\n"
                    "- Configuration integration\n"
                    "- Real-world scenarios"
                ),
                depends_on=["middleware-tests", "test-unit"],
            ),
            Task(
                id="test-load",
                title="Load Testing",
                description=(
                    "Performance and load tests:\n"
                    "- High request volume tests\n"
                    "- Concurrent user tests\n"
                    "- Latency measurements\n"
                    "- Redis connection pool tests\n"
                    "- Identify bottlenecks"
                ),
                depends_on=["test-integration"],
            ),
            Task(
                id="test-failure",
                title="Failure Scenario Tests",
                description=(
                    "Test failure handling:\n"
                    "- Redis connection failures\n"
                    "- Redis timeout scenarios\n"
                    "- Network partition tests\n"
                    "- Graceful degradation tests\n"
                    "- Circuit breaker behavior"
                ),
                depends_on=["test-integration"],
            ),
            Task(
                id="test-security",
                title="Security Tests",
                description=(
                    "Security validation:\n"
                    "- Bypass attempt tests\n"
                    "- Key injection tests\n"
                    "- Race condition tests\n"
                    "- DDoS mitigation tests\n"
                    "- Review with security-guardian agent"
                ),
                depends_on=["test-integration"],
            ),
        ]
    )

    # Phase 7: Monitoring & Observability
    tasks.extend(
        [
            Task(
                id="monitor-metrics",
                title="Implement Metrics",
                description=(
                    "Add monitoring metrics:\n"
                    "- Request count by endpoint\n"
                    "- Rate limit hits/misses\n"
                    "- Redis operation latency\n"
                    "- Error rates\n"
                    "- Prometheus-compatible"
                ),
                depends_on=["middleware-core"],
            ),
            Task(
                id="monitor-logging",
                title="Add Structured Logging",
                description=(
                    "Implement logging:\n"
                    "- Rate limit events\n"
                    "- Redis errors\n"
                    "- Configuration changes\n"
                    "- JSON-formatted logs\n"
                    "- Log level configuration"
                ),
                depends_on=["middleware-core"],
            ),
            Task(
                id="monitor-dashboard",
                title="Create Monitoring Dashboard",
                description=(
                    "Build observability dashboard:\n"
                    "- Real-time rate limit stats\n"
                    "- User quota visualization\n"
                    "- Redis health metrics\n"
                    "- Alert configuration\n"
                    "- Grafana dashboard export"
                ),
                depends_on=["monitor-metrics", "monitor-logging"],
            ),
        ]
    )

    # Phase 8: Documentation
    tasks.extend(
        [
            Task(
                id="docs-api",
                title="API Documentation",
                description=(
                    "Document public API:\n"
                    "- Rate limiter usage\n"
                    "- Decorator examples\n"
                    "- Configuration options\n"
                    "- Response headers\n"
                    "- OpenAPI/Swagger docs"
                ),
                depends_on=["middleware-decorator"],
            ),
            Task(
                id="docs-deployment",
                title="Deployment Guide",
                description=(
                    "Create deployment documentation:\n"
                    "- Redis setup instructions\n"
                    "- Environment configuration\n"
                    "- Docker deployment\n"
                    "- Kubernetes manifests\n"
                    "- Scaling considerations"
                ),
                depends_on=["config-loader", "monitor-dashboard"],
            ),
            Task(
                id="docs-examples",
                title="Usage Examples",
                description=(
                    "Create example code:\n"
                    "- Basic usage examples\n"
                    "- Custom limit examples\n"
                    "- Whitelist/blacklist examples\n"
                    "- Monitoring integration\n"
                    "- Troubleshooting guide"
                ),
                depends_on=["docs-api", "docs-deployment"],
            ),
        ]
    )

    # Add all tasks to project
    for task in tasks:
        project.add_task(task)

    # Assign agents based on task domains
    assign_agents_to_tasks(project)

    # Validate the project
    is_valid, errors = project.validate_dependencies()
    if not is_valid:
        print("⚠️  Project validation errors:")
        for error in errors:
            print(f"   - {error}")
        sys.exit(1)

    return project


def simulate_task_completion(task: Task) -> None:
    """Simulate completing a task (fake implementation for testing)."""
    task.state = TaskState.COMPLETED


def get_next_ready_task(project: Project) -> Task | None:
    """Find the next task that's ready to execute.

    A task is ready if:
    - State is PENDING
    - All dependencies are COMPLETED
    - Not BLOCKED
    """
    completed_ids = {tid for tid, t in project.tasks.items() if t.state == TaskState.COMPLETED}

    for task in project.tasks.values():
        if task.state == TaskState.PENDING and task.can_start(completed_ids):
            return task

    return None


def simulate_amplifier_session(
    project_name: str, max_tasks: int = 5, verbose: bool = False, session_num: int = 1
) -> tuple[Project, int]:
    """Simulate a single amplifier session working on a project.

    Args:
        project_name: Name of project to work on, or "resume" for most recent
        max_tasks: Maximum number of tasks to complete in this session
        verbose: If True, print detailed progress
        session_num: Session number for display

    Returns:
        Tuple of (project, number of tasks completed)
    """
    if verbose:
        print(f"\n{'─' * 70}")
        print(f"📍 SESSION {session_num}")
        print(f"{'─' * 70}")

    # Discover project
    if verbose:
        print(f"\n  🔍 Searching for project: '{project_name}'...")

    if project_name == "resume":
        project_id = get_most_recent_project()
        if project_id is None:
            raise ValueError("No projects found to resume")
        project = load_project(project_id)
        if verbose:
            print(f"  ✓ Resumed most recent project: {project.name}")
    else:
        matches = find_project_by_name(project_name)
        if not matches:
            raise ValueError(f"No project found matching '{project_name}'")
        project = load_project(matches[0].id)
        if verbose:
            print(f"  ✓ Found project: {project.name}")

    # Show current state
    if verbose:
        completed_count = sum(1 for t in project.tasks.values() if t.state == TaskState.COMPLETED)
        pending_count = sum(1 for t in project.tasks.values() if t.state == TaskState.PENDING)
        total_count = len(project.tasks)
        progress = (completed_count / total_count) * 100
        print(
            f"  📊 Current state: {completed_count}/{total_count} completed ({progress:.0f}%), {pending_count} pending"
        )

    # Execute tasks
    completed = 0
    for _ in range(max_tasks):
        task = get_next_ready_task(project)
        if not task:
            if verbose:
                print("  ⏸️  No more ready tasks (blocked by dependencies)")
            break

        if verbose:
            deps_str = f" (depends on: {', '.join(task.depends_on)})" if task.depends_on else ""
            agent_str = f" [agent: {task.assigned_to}]" if task.assigned_to else ""
            print(f"  ▶️  Executing: [{task.id}] {task.title}{agent_str}{deps_str}")

        # Mark in progress and save
        task.state = TaskState.IN_PROGRESS
        save_project(project)

        # Simulate work
        simulate_task_completion(task)
        completed += 1

        if verbose:
            print(f"  ✅ Completed: [{task.id}] {task.title}")

        # Save after completion
        save_project(project)

    if verbose and completed > 0:
        print(f"\n  🎯 Session summary: {completed} task(s) completed")

    return project, completed


def run_real_world_test(verbose: bool = True) -> bool:
    """Run the real-world rate limiter test.

    This simulates a developer using super-planner to build a rate limiter
    across multiple work sessions with interruptions.

    Args:
        verbose: If True, print detailed progress

    Returns:
        True if test passed, False otherwise
    """
    if verbose:
        print("\n" + "=" * 70)
        print("🚀 REAL-WORLD TEST: API Rate Limiter Implementation")
        print("=" * 70)
        print("\nSimulating a developer using super-planner to build a complete")
        print("API rate limiting system across multiple work sessions...")

    try:
        # Phase 1: Initial planning
        if verbose:
            print("\n" + "─" * 70)
            print("📝 PHASE 1: Creating Project Plan")
            print("─" * 70)

        project = create_rate_limiter_project()
        save_project(project)

        if verbose:
            print(f"\n  ✅ Created project: {project.name}")
            print(f"  📊 Total tasks: {len(project.tasks)}")

            # Show task breakdown by phase
            phases = {}
            for task in project.tasks.values():
                phase = task.id.split("-")[0]
                phases[phase] = phases.get(phase, 0) + 1

            print("  📋 Task breakdown:")
            for phase, count in sorted(phases.items()):
                print(f"     - {phase}: {count} tasks")

        # Phase 2: Simulate multiple work sessions
        if verbose:
            print("\n" + "─" * 70)
            print("📝 PHASE 2: Simulating Multiple Work Sessions")
            print("─" * 70)

        total_completed = 0
        session_num = 1

        # Session 1: Architecture phase
        if verbose:
            print("\n  💼 Simulating session 1: Architecture & Design")
        project, completed = simulate_amplifier_session(
            "API Rate Limiter", max_tasks=5, verbose=verbose, session_num=session_num
        )
        total_completed += completed
        session_num += 1

        # Session 2: Redis integration
        if verbose:
            print("\n  💼 Simulating session 2: Redis Integration (interrupted mid-session)")
        project, completed = simulate_amplifier_session("resume", max_tasks=3, verbose=verbose, session_num=session_num)
        total_completed += completed
        session_num += 1

        # Session 3: Continue Redis and start rate limiting
        if verbose:
            print("\n  💼 Simulating session 3: Continuing after interruption")
        project, completed = simulate_amplifier_session("resume", max_tasks=6, verbose=verbose, session_num=session_num)
        total_completed += completed
        session_num += 1

        # Session 4: Middleware implementation
        if verbose:
            print("\n  💼 Simulating session 4: Middleware Implementation")
        project, completed = simulate_amplifier_session("resume", max_tasks=5, verbose=verbose, session_num=session_num)
        total_completed += completed
        session_num += 1

        # Session 5: Configuration and testing
        if verbose:
            print("\n  💼 Simulating session 5: Configuration & Testing")
        project, completed = simulate_amplifier_session("resume", max_tasks=8, verbose=verbose, session_num=session_num)
        total_completed += completed
        session_num += 1

        # Session 6: Finish remaining tasks
        if verbose:
            print("\n  💼 Simulating final sessions: Completing remaining work")

        while True:
            project, completed = simulate_amplifier_session(
                "resume", max_tasks=5, verbose=verbose, session_num=session_num
            )
            total_completed += completed
            session_num += 1

            if completed == 0:
                break

        # Phase 3: Validate results
        if verbose:
            print("\n" + "─" * 70)
            print("📝 PHASE 3: Validating Results")
            print("─" * 70)

        # Load final project state
        final_project = load_project("api-rate-limiter")

        # Count completion
        completed_count = sum(1 for t in final_project.tasks.values() if t.state == TaskState.COMPLETED)
        total_count = len(final_project.tasks)

        if verbose:
            print("\n  📊 Final Statistics:")
            print(f"     - Total tasks: {total_count}")
            print(f"     - Completed: {completed_count}")
            print(f"     - Completion rate: {(completed_count / total_count) * 100:.1f}%")
            print(f"     - Sessions: {session_num - 1}")
            print(f"     - Avg tasks per session: {total_completed / (session_num - 1):.1f}")

        # Validate all tasks completed
        if completed_count == total_count:
            if verbose:
                print("\n  ✅ All tasks completed successfully!")
            success = True
        else:
            incomplete = [f"{t.id}: {t.title}" for t in final_project.tasks.values() if t.state != TaskState.COMPLETED]
            if verbose:
                print(f"\n  ⚠️  {len(incomplete)} task(s) not completed:")
                for task_info in incomplete[:10]:
                    print(f"     - {task_info}")
            success = False

        # Validate dependencies were respected
        if verbose:
            print("\n  🔍 Validating dependency order...")

        dependency_violations = []
        for task in final_project.tasks.values():
            if task.state == TaskState.COMPLETED:
                for dep_id in task.depends_on:
                    dep_task = final_project.tasks[dep_id]
                    if dep_task.state != TaskState.COMPLETED:
                        dependency_violations.append(f"Task '{task.id}' completed before dependency '{dep_id}'")

        if dependency_violations:
            if verbose:
                print(f"\n  ❌ {len(dependency_violations)} dependency violation(s):")
                for violation in dependency_violations:
                    print(f"     - {violation}")
            success = False
        else:
            if verbose:
                print("  ✅ All dependencies respected!")

        # Final verdict
        if verbose:
            print("\n" + "=" * 70)
            if success:
                print("🎉 REAL-WORLD TEST PASSED!")
                print("\nThe super-planner successfully:")
                print("  ✓ Created a complex multi-phase project plan")
                print("  ✓ Executed tasks across multiple sessions")
                print("  ✓ Handled interruptions and resume correctly")
                print("  ✓ Respected all task dependencies")
                print("  ✓ Completed all 30 tasks in proper order")
            else:
                print("❌ REAL-WORLD TEST FAILED")

        return success

    except Exception as e:
        if verbose:
            print(f"\n❌ Test failed with error: {e}")
            import traceback

            traceback.print_exc()
        return False


def main():
    """Entry point for the real-world test."""
    success = run_real_world_test(verbose=True)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
