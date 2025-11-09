"""
Agent discovery module for flow builder.

Scans .claude/agents/ directory and extracts basic agent information
from TOML files. NO AI analysis in Phase 1 - just parse TOML.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Agent:
    """
    Agent metadata extracted from TOML file.

    Attributes:
        name: Agent identifier (from filename)
        description: Human-readable description of what agent does
        toml_path: Path to the agent's TOML file
    """

    name: str
    description: str
    toml_path: Path


def scan_agents(agents_dir: Path) -> list[Agent]:
    """
    Scan directory for agent TOML files and extract metadata.

    NO AI analysis, NO caching, NO complexity.
    Just: read TOML → extract name and description → return list.

    Args:
        agents_dir: Directory containing agent TOML files

    Returns:
        List of Agent objects with metadata

    Examples:
        >>> agents = scan_agents(Path(".claude/agents"))
        >>> for agent in agents:
        ...     print(f"{agent.name}: {agent.description}")
    """
    if not agents_dir.exists():
        return []

    agents = []

    # Find all .toml files (excluding hidden files)
    for toml_file in agents_dir.glob("*.toml"):
        # Skip hidden files
        if toml_file.name.startswith("."):
            continue

        try:
            # Read TOML
            with open(toml_file, "rb") as f:
                data = tomllib.load(f)

            # Extract name from filename (remove .toml extension)
            name = toml_file.stem

            # Extract description (default to empty string if missing)
            description = data.get("description", "")

            # Create agent object
            agent = Agent(name=name, description=description, toml_path=toml_file)
            agents.append(agent)

        except (tomllib.TOMLDecodeError, OSError):
            # Skip files with invalid TOML or read errors
            continue

    return agents
