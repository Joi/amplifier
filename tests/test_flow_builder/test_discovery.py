"""
Tests for agent discovery module.

Following TEST-FIRST discipline: These tests define the contract (studs)
for the discovery module before implementation.
"""

from pathlib import Path

import pytest

from amplifier.flow_builder.discovery import Agent
from amplifier.flow_builder.discovery import scan_agents


class TestAgentDiscovery:
    """Tests for agent scanning and discovery."""

    def test_scan_agents_returns_list(self, tmp_path):
        """scan_agents() returns a list of Agent objects."""
        # Create test agent file
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()
        agent_file = agent_dir / "test-agent.toml"
        agent_file.write_text("""
description = "Test agent description"
custom_instructions = "Test instructions"
""")

        result = scan_agents(agent_dir)

        assert isinstance(result, list)
        assert all(isinstance(a, Agent) for a in result)

    def test_scan_agents_extracts_name_and_description(self, tmp_path):
        """scan_agents() extracts agent name from filename and description from TOML."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        # Create agent with description
        agent_file = agent_dir / "zen-architect.toml"
        agent_file.write_text("""
description = "Architecture and design expert"
custom_instructions = "Focus on simplicity"
""")

        result = scan_agents(agent_dir)

        assert len(result) == 1
        agent = result[0]
        assert agent.name == "zen-architect"
        assert agent.description == "Architecture and design expert"
        assert agent.toml_path == agent_file

    def test_scan_agents_handles_multiple_agents(self, tmp_path):
        """scan_agents() finds all agent TOML files."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        # Create multiple agents
        (agent_dir / "agent-one.toml").write_text('description = "First"')
        (agent_dir / "agent-two.toml").write_text('description = "Second"')
        (agent_dir / "agent-three.toml").write_text('description = "Third"')

        result = scan_agents(agent_dir)

        assert len(result) == 3
        names = {a.name for a in result}
        assert names == {"agent-one", "agent-two", "agent-three"}

    def test_scan_agents_empty_directory(self, tmp_path):
        """scan_agents() returns empty list for directory with no agents."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        result = scan_agents(agent_dir)

        assert result == []

    def test_scan_agents_handles_malformed_toml(self, tmp_path):
        """scan_agents() skips files with invalid TOML syntax."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        # Valid agent
        (agent_dir / "valid.toml").write_text('description = "Valid agent"')

        # Invalid TOML
        (agent_dir / "invalid.toml").write_text("description = [invalid toml")

        # Another valid one
        (agent_dir / "another.toml").write_text('description = "Another valid"')

        result = scan_agents(agent_dir)

        # Should get 2 valid agents, skip the invalid one
        assert len(result) == 2
        names = {a.name for a in result}
        assert names == {"valid", "another"}

    def test_scan_agents_handles_missing_description(self, tmp_path):
        """scan_agents() handles agents without description field."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        # Agent with no description
        (agent_dir / "no-desc.toml").write_text("custom_instructions = 'Do stuff'")

        result = scan_agents(agent_dir)

        assert len(result) == 1
        assert result[0].name == "no-desc"
        assert result[0].description == ""  # Default to empty string

    def test_scan_agents_ignores_non_toml_files(self, tmp_path):
        """scan_agents() only processes .toml files."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        # Create various file types
        (agent_dir / "agent.toml").write_text('description = "Valid"')
        (agent_dir / "README.md").write_text("# Not an agent")
        (agent_dir / "agent.yaml").write_text("description: yaml")
        (agent_dir / ".hidden.toml").write_text('description = "Hidden"')

        result = scan_agents(agent_dir)

        # Should only get the .toml file (not hidden files)
        assert len(result) == 1
        assert result[0].name == "agent"


class TestAgentDataClass:
    """Tests for Agent data class."""

    def test_agent_has_required_fields(self):
        """Agent has name, description, and toml_path fields."""
        agent = Agent(
            name="test-agent", description="Test description", toml_path=Path("/fake/path.toml")
        )

        assert agent.name == "test-agent"
        assert agent.description == "Test description"
        assert agent.toml_path == Path("/fake/path.toml")
