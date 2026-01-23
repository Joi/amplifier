#!/usr/bin/env python3
"""
Claude Code hook for session start - saves session info and retrieves memories.
Reads JSON from stdin, saves session info, calls amplifier modules, writes JSON to stdout.
"""

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Use venv Python if available
VENV_PYTHON = Path(__file__).parent.parent.parent / ".venv" / "bin" / "python"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    # Re-exec using venv Python
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), __file__] + sys.argv[1:])

# Add amplifier to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Session tracking file location
SESSION_FILE = Path.home() / ".claude" / "current_session.json"


def track_session(input_data: dict) -> None:
    """Save session info for /session command and update tmux."""
    try:
        session_info = {
            "session_id": input_data.get("session_id", ""),
            "session_name": input_data.get("session_name", ""),
            "project_dir": input_data.get("workspace", {}).get("project_dir", ""),
            "current_dir": input_data.get("workspace", {}).get("current_dir", ""),
            "model": input_data.get("model", {}).get("display_name", ""),
        }

        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps(session_info, indent=2))

        # Update tmux window name if in tmux
        if os.environ.get("TMUX"):
            project = os.path.basename(session_info["project_dir"]) or "claude"
            name = session_info["session_name"] or session_info["session_id"][:8] or "session"
            subprocess.run(["tmux", "rename-window", f"{project}:{name}"], check=False)
    except Exception:
        pass  # Don't break the hook chain for tracking failures


# === EARLY SESSION TRACKING ===
# Track session BEFORE importing amplifier modules (which may fail due to missing deps)
# This ensures /session command works even if memory system is unavailable
try:
    raw_input = sys.stdin.read()
    input_data = json.loads(raw_input) if raw_input else {}
    track_session(input_data)
except Exception:
    input_data = {}

# Import logger from the same directory
sys.path.insert(0, str(Path(__file__).parent))
from hook_logger import HookLogger

logger = HookLogger("session_start")


# Try to import amplifier modules for memory retrieval
memory_available = False
try:
    from amplifier.memory import MemoryStore
    from amplifier.search import MemorySearcher
    memory_available = True
except ImportError as e:
    logger.info(f"Amplifier memory modules not available: {e}")


async def main():
    """Search memories and return context. Session already tracked at module load."""
    global input_data  # Use input_data parsed during early session tracking

    try:
        # Session info already saved during early tracking (lines 48-53)
        # Don't read stdin again - it was consumed during early tracking

        # Check if memory system is enabled
        memory_enabled = os.getenv("MEMORY_SYSTEM_ENABLED", "false").lower() in ["true", "1", "yes"]
        if not memory_enabled or not memory_available:
            if not memory_enabled:
                logger.info("Memory system disabled via MEMORY_SYSTEM_ENABLED env var")
            # Return empty response and exit gracefully
            json.dump({}, sys.stdout)
            return

        logger.info("Starting memory retrieval")
        logger.cleanup_old_logs()  # Clean up old logs on each run

        # Use input_data already parsed during early session tracking
        prompt = input_data.get("prompt", "")
        logger.info(f"Prompt length: {len(prompt)}")

        if prompt:
            logger.debug(f"Prompt preview: {prompt[:100]}...")

        if not prompt:
            logger.warning("No prompt provided, exiting")
            json.dump({}, sys.stdout)
            return

        # Initialize modules
        logger.info("Initializing store and searcher")
        store = MemoryStore()
        searcher = MemorySearcher()

        # Check data directory
        logger.debug(f"Data directory: {store.data_dir}")
        logger.debug(f"Data file: {store.data_file}")
        logger.debug(f"Data file exists: {store.data_file.exists()}")

        # Get all memories
        all_memories = store.get_all()
        logger.info(f"Total memories in store: {len(all_memories)}")

        # Search for relevant memories
        logger.info("Searching for relevant memories")
        search_results = searcher.search(prompt, all_memories, limit=5)
        logger.info(f"Found {len(search_results)} relevant memories")

        # Get recent memories too
        recent = store.search_recent(limit=3)
        logger.info(f"Found {len(recent)} recent memories")

        # Format context
        context_parts = []
        if search_results or recent:
            context_parts.append("## Relevant Context from Memory System\n")

            # Add relevant memories
            if search_results:
                context_parts.append("### Relevant Memories")
                for result in search_results[:3]:
                    content = result.memory.content
                    category = result.memory.category
                    score = result.score
                    context_parts.append(f"- **{category}** (relevance: {score:.2f}): {content}")

            # Add recent memories not already shown
            seen_ids = {r.memory.id for r in search_results}
            unique_recent = [m for m in recent if m.id not in seen_ids]
            if unique_recent:
                context_parts.append("\n### Recent Context")
                for mem in unique_recent[:2]:
                    context_parts.append(f"- {mem.category}: {mem.content}")

        # Build response
        context = "\n".join(context_parts) if context_parts else ""

        output = {}
        if context:
            # Calculate memories loaded - unique_recent is always defined after the conditional above
            memories_loaded = len(search_results)
            if search_results:
                # unique_recent is defined when we have search_results
                seen_ids = {r.memory.id for r in search_results}
                unique_recent_count = len([m for m in recent if m.id not in seen_ids])
                memories_loaded += unique_recent_count
            else:
                # No search results, so all recent memories are unique
                memories_loaded += len(recent)

            output = {
                "additionalContext": context,
                "metadata": {
                    "memoriesLoaded": memories_loaded,
                    "source": "amplifier_memory",
                },
            }

        json.dump(output, sys.stdout)
        logger.info(f"Returned {len(context_parts) if context_parts else 0} memory contexts")

    except Exception as e:
        logger.exception("Error during memory retrieval", e)
        json.dump({}, sys.stdout)


if __name__ == "__main__":
    asyncio.run(main())
