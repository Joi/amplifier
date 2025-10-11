"""Stress test: Vi Editor Rewrite Project

This test simulates a large, complex, multi-session project to validate:
- Project persistence and resume
- Multi-level task hierarchy
- Dependency management at scale
- Agent assignment
- Interruption/resume workflow
- Project discovery

The test creates a realistic plan to rewrite the vi text editor in Python,
then simulates multiple "amplifier sessions" that discover, execute, and
resume the project across interruptions.
"""

import uuid
from pathlib import Path

from amplifier.planner.models import Project
from amplifier.planner.models import Task
from amplifier.planner.models import TaskState
from amplifier.planner.storage import find_project_by_name
from amplifier.planner.storage import get_most_recent_project
from amplifier.planner.storage import list_projects
from amplifier.planner.storage import load_project
from amplifier.planner.storage import save_project


def create_vi_rewrite_project() -> Project:
    """Create a realistic project plan for rewriting vi in Python.

    This represents a large-scale software project with:
    - 50+ tasks across multiple levels
    - Complex dependencies
    - Multiple domains (architecture, implementation, testing, docs)
    - Realistic task breakdown

    Returns:
        Project with complete vi rewrite task hierarchy
    """
    project_id = str(uuid.uuid4())
    project = Project(id=project_id, name="Vi Editor Rewrite in Python")

    # Phase 1: Architecture & Design (no dependencies, can start immediately)
    t1 = Task(
        id="arch-1",
        title="Design overall architecture",
        description="Define modular architecture for text editor: buffer management, command parsing, display, I/O",
        assigned_to="zen-architect",
    )

    t2 = Task(
        id="arch-2",
        title="Define core data structures",
        description="Design buffer representation, undo/redo stack, command queue",
        depends_on=["arch-1"],
        assigned_to="zen-architect",
    )

    t3 = Task(
        id="arch-3",
        title="Define API contracts",
        description="Specify interfaces between buffer, display, command processor, and I/O modules",
        depends_on=["arch-2"],
        assigned_to="api-contract-designer",
    )

    # Phase 2: Core Buffer System
    t4 = Task(
        id="buffer-1",
        title="Implement buffer data structure",
        description="Create Buffer class with line-based storage, cursor tracking",
        depends_on=["arch-3"],
        assigned_to="modular-builder",
    )

    t5 = Task(
        id="buffer-2",
        title="Implement buffer operations",
        description="Add insert, delete, replace operations with cursor management",
        depends_on=["buffer-1"],
        assigned_to="modular-builder",
    )

    t6 = Task(
        id="buffer-3",
        title="Add undo/redo system",
        description="Implement command pattern for undoable operations",
        depends_on=["buffer-2"],
        assigned_to="modular-builder",
    )

    t7 = Task(
        id="buffer-test",
        title="Test buffer system",
        description="Comprehensive tests for buffer operations, edge cases, undo/redo",
        depends_on=["buffer-3"],
        assigned_to="test-coverage",
    )

    # Phase 3: Display System
    t8 = Task(
        id="display-1",
        title="Implement terminal interface",
        description="Create curses-based terminal display with proper escaping",
        depends_on=["arch-3"],
        assigned_to="modular-builder",
    )

    t9 = Task(
        id="display-2",
        title="Implement viewport system",
        description="Handle scrolling, line wrapping, cursor rendering",
        depends_on=["display-1"],
        assigned_to="modular-builder",
    )

    t10 = Task(
        id="display-3",
        title="Add syntax highlighting",
        description="Basic syntax highlighting for common languages",
        depends_on=["display-2"],
        assigned_to="modular-builder",
    )

    t11 = Task(
        id="display-test",
        title="Test display system",
        description="Test rendering, scrolling, highlighting, edge cases",
        depends_on=["display-3"],
        assigned_to="test-coverage",
    )

    # Phase 4: Command Parser (depends on both buffer and display being ready)
    t12 = Task(
        id="cmd-1",
        title="Implement mode system",
        description="Create normal, insert, visual, command modes with transitions",
        depends_on=["buffer-test", "display-test"],
        assigned_to="modular-builder",
    )

    t13 = Task(
        id="cmd-2",
        title="Implement normal mode commands",
        description="Movement (hjkl, w, b, etc), deletion (x, dd), change (c, cc)",
        depends_on=["cmd-1"],
        assigned_to="modular-builder",
    )

    t14 = Task(
        id="cmd-3",
        title="Implement insert mode",
        description="Text insertion, backspace, escape to normal",
        depends_on=["cmd-1"],
        assigned_to="modular-builder",
    )

    t15 = Task(
        id="cmd-4",
        title="Implement visual mode",
        description="Character, line, block visual selection with operations",
        depends_on=["cmd-1"],
        assigned_to="modular-builder",
    )

    t16 = Task(
        id="cmd-5",
        title="Implement ex commands",
        description="Colon commands: :w, :q, :wq, :s, :set, etc.",
        depends_on=["cmd-1"],
        assigned_to="modular-builder",
    )

    t17 = Task(
        id="cmd-test",
        title="Test command system",
        description="Test all modes, commands, edge cases, mode transitions",
        depends_on=["cmd-2", "cmd-3", "cmd-4", "cmd-5"],
        assigned_to="test-coverage",
    )

    # Phase 5: File I/O
    t18 = Task(
        id="io-1",
        title="Implement file loading",
        description="Read files into buffer with encoding detection",
        depends_on=["buffer-test"],
        assigned_to="modular-builder",
    )

    t19 = Task(
        id="io-2",
        title="Implement file saving",
        description="Write buffer to file with backup creation",
        depends_on=["buffer-test"],
        assigned_to="modular-builder",
    )

    t20 = Task(
        id="io-3",
        title="Add autosave/recovery",
        description="Automatic backup and recovery from crashes",
        depends_on=["io-1", "io-2"],
        assigned_to="modular-builder",
    )

    t21 = Task(
        id="io-test",
        title="Test file I/O",
        description="Test loading, saving, encoding, recovery, edge cases",
        depends_on=["io-3"],
        assigned_to="test-coverage",
    )

    # Phase 6: Advanced Features
    t22 = Task(
        id="feat-1",
        title="Implement search and replace",
        description="Regex search, replace, global replace with highlighting",
        depends_on=["cmd-test"],
        assigned_to="modular-builder",
    )

    t23 = Task(
        id="feat-2",
        title="Implement macro system",
        description="Record and playback command sequences (q register)",
        depends_on=["cmd-test"],
        assigned_to="modular-builder",
    )

    t24 = Task(
        id="feat-3",
        title="Implement marks and jumps",
        description="Named marks, jump list, change list",
        depends_on=["cmd-test"],
        assigned_to="modular-builder",
    )

    t25 = Task(
        id="feat-4",
        title="Add multiple buffers",
        description="Buffer list, switching between files, split windows",
        depends_on=["buffer-test", "display-test"],
        assigned_to="modular-builder",
    )

    t26 = Task(
        id="feat-test",
        title="Test advanced features",
        description="Test search, macros, marks, multiple buffers",
        depends_on=["feat-1", "feat-2", "feat-3", "feat-4"],
        assigned_to="test-coverage",
    )

    # Phase 7: Configuration
    t27 = Task(
        id="config-1",
        title="Implement .virc configuration",
        description="Parse and apply configuration file with settings",
        depends_on=["cmd-test"],
        assigned_to="modular-builder",
    )

    t28 = Task(
        id="config-2",
        title="Add key remapping",
        description="Custom key bindings and command aliases",
        depends_on=["config-1"],
        assigned_to="modular-builder",
    )

    t29 = Task(
        id="config-test",
        title="Test configuration system",
        description="Test config parsing, settings, remapping",
        depends_on=["config-2"],
        assigned_to="test-coverage",
    )

    # Phase 8: Performance & Polish
    t30 = Task(
        id="perf-1",
        title="Profile and optimize buffer operations",
        description="Identify and optimize slow buffer operations for large files",
        depends_on=["buffer-test", "feat-test"],
        assigned_to="performance-optimizer",
    )

    t31 = Task(
        id="perf-2",
        title="Optimize display rendering",
        description="Minimize redraws, optimize syntax highlighting",
        depends_on=["display-test", "feat-test"],
        assigned_to="performance-optimizer",
    )

    t32 = Task(
        id="perf-3",
        title="Add lazy loading for large files",
        description="Stream large files instead of loading entirely",
        depends_on=["perf-1"],
        assigned_to="modular-builder",
    )

    t33 = Task(
        id="polish-1",
        title="Improve error messages",
        description="Clear, helpful error messages for all failure modes",
        depends_on=["cmd-test", "io-test"],
        assigned_to="modular-builder",
    )

    t34 = Task(
        id="polish-2",
        title="Add status line",
        description="Show mode, file, position, modified status",
        depends_on=["display-test"],
        assigned_to="modular-builder",
    )

    # Phase 9: Integration Testing
    t35 = Task(
        id="integration-1",
        title="End-to-end workflow tests",
        description="Test complete workflows: open, edit, save, quit",
        depends_on=["cmd-test", "io-test", "feat-test", "config-test"],
        assigned_to="test-coverage",
    )

    t36 = Task(
        id="integration-2",
        title="Compatibility testing",
        description="Test with various file types, encodings, terminal sizes",
        depends_on=["integration-1"],
        assigned_to="test-coverage",
    )

    t37 = Task(
        id="integration-3",
        title="Stress testing",
        description="Test with huge files, rapid commands, long sessions",
        depends_on=["perf-3"],
        assigned_to="test-coverage",
    )

    # Phase 10: Documentation
    t38 = Task(
        id="docs-1",
        title="Write user manual",
        description="Comprehensive manual covering all features",
        depends_on=["feat-test"],
        assigned_to="content-researcher",
    )

    t39 = Task(
        id="docs-2",
        title="Write developer documentation",
        description="Architecture guide, API docs, contribution guide",
        depends_on=["arch-3", "integration-1"],
        assigned_to="content-researcher",
    )

    t40 = Task(
        id="docs-3",
        title="Create tutorial",
        description="Interactive tutorial for new users",
        depends_on=["docs-1"],
        assigned_to="content-researcher",
    )

    # Phase 11: Packaging & Release
    t41 = Task(
        id="release-1",
        title="Create setup.py and packaging",
        description="Package for PyPI with proper dependencies",
        depends_on=["integration-3"],
        assigned_to="modular-builder",
    )

    t42 = Task(
        id="release-2",
        title="Create release scripts",
        description="Automated testing, building, release process",
        depends_on=["release-1"],
        assigned_to="modular-builder",
    )

    t43 = Task(
        id="release-3",
        title="Final QA and beta testing",
        description="Beta release, gather feedback, fix critical issues",
        depends_on=["release-2", "docs-3"],
        assigned_to="test-coverage",
    )

    t44 = Task(
        id="release-4",
        title="Version 1.0 release",
        description="Official 1.0 release to PyPI with announcement",
        depends_on=["release-3"],
        assigned_to="content-researcher",
    )

    # Add all tasks to project
    for task in [
        t1,
        t2,
        t3,
        t4,
        t5,
        t6,
        t7,
        t8,
        t9,
        t10,
        t11,
        t12,
        t13,
        t14,
        t15,
        t16,
        t17,
        t18,
        t19,
        t20,
        t21,
        t22,
        t23,
        t24,
        t25,
        t26,
        t27,
        t28,
        t29,
        t30,
        t31,
        t32,
        t33,
        t34,
        t35,
        t36,
        t37,
        t38,
        t39,
        t40,
        t41,
        t42,
        t43,
        t44,
    ]:
        project.add_task(task)

    return project


def simulate_task_completion(task: Task) -> None:
    """Simulate completion of a task (fake for testing).

    In real use, this would invoke agents and do actual work.
    For testing, we just mark it completed.
    """
    task.state = TaskState.COMPLETED


def get_next_ready_task(project: Project) -> Task | None:
    """Find the next task that's ready to execute.

    Returns:
        Next PENDING task with all dependencies completed, or None
    """
    completed_ids = {tid for tid, t in project.tasks.items() if t.state == TaskState.COMPLETED}

    for task in project.tasks.values():
        if task.state == TaskState.PENDING and task.can_start(completed_ids):
            return task

    return None


def simulate_amplifier_session(project_name: str, max_tasks: int = 5, verbose: bool = False) -> tuple[Project, int]:
    """Simulate a single amplifier session working on a project.

    This simulates:
    1. Finding the project (by name or most recent)
    2. Loading project state
    3. Finding ready tasks
    4. "Completing" up to max_tasks
    5. Saving state
    6. Returning for next session

    Args:
        project_name: Name to search for, or "resume" for most recent
        max_tasks: Maximum tasks to complete in this session
        verbose: Print detailed progress

    Returns:
        Tuple of (project, tasks_completed)
    """
    # 1. Find project
    if verbose:
        print(f"\n  🔍 Searching for project: '{project_name}'...")

    if project_name == "resume":
        project_id = get_most_recent_project()
        if not project_id:
            raise ValueError("No recent project found")
        project = load_project(project_id)
        if verbose:
            print(f"  ✓ Resumed most recent project: {project.name}")
    else:
        matches = find_project_by_name(project_name)
        if not matches:
            raise ValueError(f"Project '{project_name}' not found")
        project = load_project(matches[0].id)
        if verbose:
            print(f"  ✓ Found project: {project.name}")

    if verbose:
        completed_count = sum(1 for t in project.tasks.values() if t.state == TaskState.COMPLETED)
        pending_count = sum(1 for t in project.tasks.values() if t.state == TaskState.PENDING)
        print(f"  📊 Current state: {completed_count} completed, {pending_count} pending")

    # 2. Complete tasks
    completed = 0
    for _ in range(max_tasks):
        task = get_next_ready_task(project)
        if not task:
            if verbose:
                print("  ⏸️  No more ready tasks")
            break

        if verbose:
            print(f"  ▶️  Executing: [{task.id}] {task.title} (agent: {task.assigned_to})")

        # Mark in progress
        task.state = TaskState.IN_PROGRESS
        save_project(project)

        # "Complete" the task (fake)
        simulate_task_completion(task)
        completed += 1

        if verbose:
            print(f"  ✅ Completed: [{task.id}] {task.title}")

        # Save progress
        save_project(project)

    return project, completed


def run_stress_test(sessions: int = 10, tasks_per_session: int = 5, verbose: bool = False) -> dict:
    """Run the complete stress test simulating multiple sessions.

    Args:
        sessions: Number of amplifier sessions to simulate
        tasks_per_session: Max tasks per session

    Returns:
        Dict with test results and statistics
    """
    # Clean up any previous test projects
    for summary in list_projects():
        if "Vi Editor Rewrite" in summary.name:
            path = Path(f"data/planner/projects/{summary.id}.json")
            if path.exists():
                path.unlink()

    # 1. Create the project plan
    if verbose:
        print("\n" + "=" * 70)
        print("🚀 SUPER-PLANNER STRESS TEST: Vi Editor Rewrite")
        print("=" * 70)
        print("\n📝 Creating project plan...")

    project = create_vi_rewrite_project()
    save_project(project)

    total_tasks = len(project.tasks)
    if verbose:
        print(f"✓ Created project with {total_tasks} tasks")
        print(f"  Project ID: {project.id}")
        print(f"  Saved to: data/planner/projects/{project.id}.json")

    results = {
        "total_tasks": total_tasks,
        "sessions": [],
        "total_completed": 0,
        "final_status": None,
    }

    # 2. Simulate multiple sessions
    for session_num in range(1, sessions + 1):
        if verbose:
            print(f"\n{'─' * 70}")
            print(f"📍 SESSION {session_num}/{sessions}")
            print(f"{'─' * 70}")

        # First session uses name, rest use "resume"
        search_term = "Vi Editor Rewrite" if session_num == 1 else "resume"

        try:
            project, completed = simulate_amplifier_session(search_term, tasks_per_session, verbose=verbose)

            session_result = {
                "session": session_num,
                "completed": completed,
                "total_completed_so_far": sum(1 for t in project.tasks.values() if t.state == TaskState.COMPLETED),
                "pending": sum(1 for t in project.tasks.values() if t.state == TaskState.PENDING),
            }

            results["sessions"].append(session_result)
            results["total_completed"] = session_result["total_completed_so_far"]

            # Stop if no more tasks
            if completed == 0:
                results["final_status"] = "completed"
                if verbose:
                    print("\n✨ All tasks completed!")
                break

        except Exception as e:
            results["final_status"] = f"error: {e}"
            break

    else:
        # All sessions completed, check if all tasks done
        if results["total_completed"] == total_tasks:
            results["final_status"] = "completed"
        else:
            results["final_status"] = "partial"

    return results


# Test function that can be run by pytest
def test_vi_rewrite_stress_test() -> None:
    """Pytest-runnable version of the stress test."""
    results = run_stress_test(sessions=15, tasks_per_session=3, verbose=True)

    # Assertions
    assert results["total_tasks"] == 44, "Should have 44 tasks in vi rewrite plan"
    assert results["final_status"] == "completed", f"Should complete all tasks, got: {results['final_status']}"
    assert results["total_completed"] == 44, f"Should complete all 44 tasks, got: {results['total_completed']}"

    # Verify multiple sessions were used
    assert len(results["sessions"]) > 1, "Should use multiple sessions"
    assert len(results["sessions"]) <= 15, "Should not exceed max sessions"

    # Print results for visibility
    print("\nStress Test Results:")
    print(f"  Total tasks: {results['total_tasks']}")
    print(f"  Sessions used: {len(results['sessions'])}")
    print(f"  Total completed: {results['total_completed']}")
    print(f"  Final status: {results['final_status']}")
    print("\nSession breakdown:")
    for session in results["sessions"]:
        print(
            f"  Session {session['session']}: completed {session['completed']}, "
            f"total so far: {session['total_completed_so_far']}, "
            f"pending: {session['pending']}"
        )
