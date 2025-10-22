"""
Tests for AI analysis module (Phase 3.1).

Following TEST-FIRST discipline.
Phase 3: Add AI agent recommendations - keep simple, no over-engineering
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from amplifier.flow_builder.ai_analysis import (
    AgentAnalysis,
    analyze_agent,
    recommend_agent,
)
from amplifier.flow_builder.discovery import Agent


class TestAgentAnalysis:
    """Tests for analyzing agent capabilities using AI."""

    @pytest.mark.asyncio
    async def test_analyze_agent_returns_structured_analysis(self):
        """analyze_agent() returns AgentAnalysis with capabilities list."""
        agent = Agent(
            name="zen-architect",
            description="Design simple, elegant architectures",
            toml_path=Path("test.toml"),
        )

        analysis = await analyze_agent(agent)

        assert isinstance(analysis, AgentAnalysis)
        assert analysis.agent_name == "zen-architect"
        assert isinstance(analysis.capabilities, list)
        assert len(analysis.capabilities) >= 3
        assert len(analysis.capabilities) <= 5
        assert all(isinstance(cap, str) for cap in analysis.capabilities)

    @pytest.mark.asyncio
    async def test_analyze_agent_capabilities_are_concise(self):
        """analyze_agent() returns concise one-sentence capabilities."""
        agent = Agent(
            name="test-agent",
            description="Does testing things",
            toml_path=Path("test.toml"),
        )

        analysis = await analyze_agent(agent)

        # Each capability should be a concise sentence
        for cap in analysis.capabilities:
            assert len(cap) < 200  # Reasonable sentence length
            assert len(cap.split()) <= 20  # ~20 words max

    @pytest.mark.asyncio
    async def test_analyze_agent_uses_description(self):
        """analyze_agent() bases analysis on agent description."""
        agent = Agent(
            name="bug-hunter",
            description="Systematically finds and fixes bugs using hypothesis-driven debugging",
            toml_path=Path("test.toml"),
        )

        analysis = await analyze_agent(agent)

        # Capabilities should relate to description
        analysis_text = " ".join(analysis.capabilities).lower()
        assert "bug" in analysis_text or "debug" in analysis_text or "fix" in analysis_text


class TestAgentRecommendation:
    """Tests for recommending agents based on task descriptions."""

    @pytest.mark.asyncio
    async def test_recommend_agent_returns_single_agent(self):
        """recommend_agent() returns one Agent from the list."""
        agents = [
            Agent("zen-architect", "Design architectures", Path("test1.toml")),
            Agent("bug-hunter", "Find and fix bugs", Path("test2.toml")),
            Agent("test-coverage", "Analyze test coverage", Path("test3.toml")),
        ]
        task = "I need to design a new module structure"

        recommended = await recommend_agent(task, agents)

        assert isinstance(recommended, Agent)
        assert recommended in agents

    @pytest.mark.asyncio
    async def test_recommend_agent_chooses_appropriate_agent(self):
        """recommend_agent() chooses agent matching task domain."""
        agents = [
            Agent("zen-architect", "Design simple, elegant architectures", Path("test1.toml")),
            Agent("bug-hunter", "Systematically find and fix bugs", Path("test2.toml")),
        ]

        # Architecture task should recommend zen-architect
        task_architecture = "Design a new module for handling user authentication"
        recommended = await recommend_agent(task_architecture, agents)
        assert recommended.name == "zen-architect"

        # Bug fix task should recommend bug-hunter
        task_bugfix = "Fix the login error that occurs on invalid credentials"
        recommended = await recommend_agent(task_bugfix, agents)
        assert recommended.name == "bug-hunter"

    @pytest.mark.asyncio
    async def test_recommend_agent_with_empty_list_raises_error(self):
        """recommend_agent() raises ValueError with empty agent list."""
        with pytest.raises(ValueError, match="No agents provided"):
            await recommend_agent("do something", [])

    @pytest.mark.asyncio
    async def test_recommend_agent_includes_all_agents_in_prompt(self):
        """recommend_agent() considers all available agents."""
        agents = [
            Agent("agent-a", "Does A things", Path("test1.toml")),
            Agent("agent-b", "Does B things", Path("test2.toml")),
            Agent("agent-c", "Does C things", Path("test3.toml")),
        ]
        task = "Do something"

        # Mock ClaudeSession to verify all agents passed
        from amplifier.ccsdk_toolkit.core.models import SessionResponse

        with patch("amplifier.flow_builder.ai_analysis.ClaudeSession") as mock_session_class:
            # Setup mock session
            mock_session = mock_session_class.return_value.__aenter__.return_value
            mock_session.query.return_value = SessionResponse(content="agent-a")

            await recommend_agent(task, agents)

            # Verify query was called with prompt including all agents
            call_args = mock_session.query.call_args[0][0]
            assert "agent-a" in call_args.lower()
            assert "agent-b" in call_args.lower()
            assert "agent-c" in call_args.lower()


class TestAgentAnalysisDataclass:
    """Tests for AgentAnalysis dataclass."""

    def test_agent_analysis_creation(self):
        """AgentAnalysis can be created with required fields."""
        analysis = AgentAnalysis(
            agent_name="test-agent",
            capabilities=["Can do X", "Can do Y", "Can do Z"],
        )

        assert analysis.agent_name == "test-agent"
        assert len(analysis.capabilities) == 3

    def test_agent_analysis_is_serializable(self):
        """AgentAnalysis can be converted to dict for caching."""
        from dataclasses import asdict

        analysis = AgentAnalysis(
            agent_name="test-agent", capabilities=["Capability 1", "Capability 2"]
        )

        data = asdict(analysis)

        assert data["agent_name"] == "test-agent"
        assert data["capabilities"] == ["Capability 1", "Capability 2"]
