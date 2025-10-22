"""
Tests for AI-enhanced interrogation (Phase 3.2).

Following TEST-FIRST discipline.
Phase 3.2: Integrate AI recommendations into interrogation flow
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from amplifier.flow_builder.discovery import Agent
from amplifier.flow_builder.interrogation import interrogate_with_ai_recommendations
from amplifier.flow_builder.validation import WorkflowSpec


class TestInterrogationWithAI:
    """Tests for AI-enhanced interrogation flow."""

    @pytest.mark.asyncio
    async def test_interrogate_with_ai_shows_recommendation(self, monkeypatch):
        """interrogate_with_ai_recommendations() shows AI recommendation to user."""
        # Mock available agents
        agents = [
            Agent("zen-architect", "Design architectures", Path("test1.toml")),
            Agent("bug-hunter", "Find bugs", Path("test2.toml")),
        ]

        # Mock user inputs - user accepts recommendation
        inputs = [
            "my-workflow",
            "Design a new authentication module",
            "2",
            "Design Module",
            "Design the module structure",
            "y",  # Accept AI recommendation
            "",  # Outputs (empty)
            "Implement Module",
            "Implement the designed module",
            "y",  # Accept AI recommendation for node 2
            "",  # Outputs (empty)
        ]
        monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

        # Mock recommend_agent to return zen-architect
        with patch("amplifier.flow_builder.interrogation.recommend_agent") as mock_recommend:
            mock_recommend.return_value = agents[0]  # zen-architect

            spec = await interrogate_with_ai_recommendations(agents)

            # Verify recommend_agent was called for each node
            assert mock_recommend.call_count == 2
            # Verify nodes have the recommended agent
            assert spec.nodes[0]["agent"] == "zen-architect"
            assert spec.nodes[1]["agent"] == "zen-architect"

    @pytest.mark.asyncio
    async def test_interrogate_with_ai_allows_override(self, monkeypatch):
        """interrogate_with_ai_recommendations() allows user to override AI recommendation."""
        agents = [
            Agent("zen-architect", "Design architectures", Path("test1.toml")),
            Agent("bug-hunter", "Find bugs", Path("test2.toml")),
        ]

        # Mock user inputs - user overrides recommendation
        inputs = [
            "my-workflow",
            "Fix authentication bugs",
            "1",
            "Fix Bug",
            "Fix the login bug",
            "n",  # Reject AI recommendation
            "bug-hunter",  # Override with bug-hunter
            "",
        ]
        monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

        # Mock recommend_agent to return zen-architect (wrong for bug fixing)
        with patch("amplifier.flow_builder.interrogation.recommend_agent") as mock_recommend:
            mock_recommend.return_value = agents[0]  # zen-architect (wrong choice)

            spec = await interrogate_with_ai_recommendations(agents)

            # Verify user override worked
            assert spec.nodes[0]["agent"] == "bug-hunter"

    @pytest.mark.asyncio
    async def test_interrogate_with_ai_handles_skip(self, monkeypatch):
        """interrogate_with_ai_recommendations() allows skipping agent selection."""
        agents = [Agent("zen-architect", "Design", Path("test1.toml"))]

        # Mock user inputs - user skips agent selection
        inputs = [
            "my-workflow",
            "Do something",
            "1",
            "Step 1",
            "Do the thing",
            "n",  # Reject recommendation
            "",  # Skip agent selection (empty input)
            "",
        ]
        monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

        with patch("amplifier.flow_builder.interrogation.recommend_agent") as mock_recommend:
            mock_recommend.return_value = agents[0]

            spec = await interrogate_with_ai_recommendations(agents)

            # Verify node has no agent (user skipped)
            assert spec.nodes[0].get("agent") is None

    @pytest.mark.asyncio
    async def test_interrogate_with_ai_passes_task_context(self, monkeypatch):
        """interrogate_with_ai_recommendations() passes node task to recommend_agent."""
        agents = [Agent("test-agent", "Test", Path("test.toml"))]

        inputs = [
            "workflow",
            "Overall description",
            "1",
            "Node Name",
            "Specific node task description",
            "y",
            "",
        ]
        monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

        with patch("amplifier.flow_builder.interrogation.recommend_agent") as mock_recommend:
            mock_recommend.return_value = agents[0]

            await interrogate_with_ai_recommendations(agents)

            # Verify recommend_agent received the node's specific task
            call_args = mock_recommend.call_args[0][0]
            assert "Specific node task description" in call_args

    @pytest.mark.asyncio
    async def test_interrogate_with_ai_works_without_agents(self, monkeypatch):
        """interrogate_with_ai_recommendations() works even with empty agent list."""
        # Mock user inputs - no agents available
        inputs = ["workflow", "Description", "1", "Node", "Task", "", ""]
        monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

        spec = await interrogate_with_ai_recommendations([])

        # Verify workflow created without agent
        assert spec.name == "workflow"
        assert len(spec.nodes) == 1
        assert spec.nodes[0].get("agent") is None

    @pytest.mark.asyncio
    async def test_interrogate_with_ai_shows_agent_name(self, monkeypatch, capsys):
        """interrogate_with_ai_recommendations() displays recommended agent name."""
        agents = [Agent("zen-architect", "Design", Path("test.toml"))]

        inputs = ["workflow", "desc", "1", "node", "task", "y", ""]
        monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

        with patch("amplifier.flow_builder.interrogation.recommend_agent") as mock_recommend:
            mock_recommend.return_value = agents[0]

            await interrogate_with_ai_recommendations(agents)

            # Verify agent name was shown to user
            captured = capsys.readouterr()
            assert "zen-architect" in captured.out

    @pytest.mark.asyncio
    async def test_interrogate_with_ai_handles_multi_node(self, monkeypatch):
        """interrogate_with_ai_recommendations() handles multiple nodes with different agents."""
        agents = [
            Agent("zen-architect", "Design", Path("test1.toml")),
            Agent("bug-hunter", "Debug", Path("test2.toml")),
        ]

        inputs = [
            "workflow",
            "Multi-step workflow",
            "2",
            "Design",
            "Design the system",
            "y",  # Accept zen-architect
            "",
            "Debug",
            "Debug the system",
            "n",  # Reject recommendation
            "bug-hunter",  # Override
            "",
        ]
        monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

        with patch("amplifier.flow_builder.interrogation.recommend_agent") as mock_recommend:
            # Return different recommendations for each node
            mock_recommend.side_effect = [agents[0], agents[0]]

            spec = await interrogate_with_ai_recommendations(agents)

            # Verify each node got appropriate agent
            assert spec.nodes[0]["agent"] == "zen-architect"  # Accepted
            assert spec.nodes[1]["agent"] == "bug-hunter"  # Overridden
