"""
AI analysis module for flow builder.

Phase 3: Simple AI integration for agent analysis and recommendations.
NO over-engineering - just basic LLM calls with caching.
"""

from dataclasses import dataclass

from amplifier.ccsdk_toolkit.core.session import ClaudeSession
from amplifier.flow_builder.discovery import Agent


@dataclass
class AgentAnalysis:
    """
    Analysis of an agent's capabilities.

    Attributes:
        agent_name: Name of the analyzed agent
        capabilities: List of 3-5 one-sentence capabilities
    """

    agent_name: str
    capabilities: list[str]


# Simple in-memory cache for agent analyses
_analysis_cache: dict[str, AgentAnalysis] = {}


async def analyze_agent(agent: Agent) -> AgentAnalysis:
    """
    Use Claude to analyze ONE agent's capabilities.

    Phase 3 implementation: Simple LLM call with caching.

    Args:
        agent: Agent to analyze

    Returns:
        AgentAnalysis with 3-5 concise capability descriptions

    Examples:
        >>> agent = Agent("zen-architect", "Design simple architectures", Path("test.toml"))
        >>> analysis = await analyze_agent(agent)
        >>> len(analysis.capabilities)
        4
    """
    # Check cache first
    if agent.name in _analysis_cache:
        return _analysis_cache[agent.name]

    # Build prompt
    prompt = f"""Based on this agent's description, what is it good at?

Agent: {agent.name}
Description: {agent.description}

List 3-5 capabilities in one sentence each. Be concise and specific.
Format as a simple list with one capability per line starting with "- ".

Example format:
- Designs clean, modular architectures
- Identifies complexity and suggests simplifications
- Reviews code for maintainability"""

    # Call Claude using CCSDK toolkit
    async with ClaudeSession() as session:
        response = await session.query(prompt, stream=False)

    # Handle error or empty response
    if response.error or not response.content:
        # Fallback to generic capabilities
        capabilities = [
            agent.description,
            f"Works with {agent.name} tasks",
            "Provides specialized assistance",
        ]
    else:
        # Parse capabilities from response
        capabilities = []
        for line in response.content.strip().split("\n"):
            line = line.strip()
            if line.startswith("-"):
                capability = line[1:].strip()  # Remove leading "- "
                if capability:
                    capabilities.append(capability)

        # Ensure we have 3-5 capabilities
        if len(capabilities) < 3:
            # If parsing failed, return generic capabilities
            capabilities = [
                agent.description,
                f"Works with {agent.name} tasks",
                "Provides specialized assistance",
            ]

    # Limit to 5 capabilities
    capabilities = capabilities[:5]

    # Create and cache analysis
    analysis = AgentAnalysis(agent_name=agent.name, capabilities=capabilities)
    _analysis_cache[agent.name] = analysis

    return analysis


async def recommend_agent(task_description: str, agents: list[Agent]) -> Agent:
    """
    Use Claude to recommend best agent for a task.

    Phase 3 implementation: Simple LLM call with agent catalog.

    Args:
        task_description: What the user wants to accomplish
        agents: List of available agents

    Returns:
        Single Agent object (the recommendation)

    Raises:
        ValueError: If agents list is empty

    Examples:
        >>> agents = [Agent("zen-architect", "Design", Path("test.toml"))]
        >>> task = "Design a new module"
        >>> agent = await recommend_agent(task, agents)
        >>> agent.name
        'zen-architect'
    """
    if not agents:
        raise ValueError("No agents provided for recommendation")

    # Build agent catalog for prompt
    agent_list = []
    for agent in agents:
        agent_list.append(f"- {agent.name}: {agent.description}")

    agent_catalog = "\n".join(agent_list)

    # Build prompt
    prompt = f"""Given these agents and their capabilities, which is best for this task?

Task: {task_description}

Available agents:
{agent_catalog}

Respond with ONLY the agent name (exactly as shown above, no explanation).

Example: zen-architect"""

    # Call Claude using CCSDK toolkit
    async with ClaudeSession() as session:
        response = await session.query(prompt, stream=False)

    # Handle error or empty response
    if response.error or not response.content:
        # Fallback: return first agent
        return agents[0]

    # Parse agent name from response
    agent_name = response.content.strip().lower()

    # Find matching agent
    for agent in agents:
        if agent.name.lower() == agent_name:
            return agent

    # If no exact match, do fuzzy matching
    for agent in agents:
        if agent_name in agent.name.lower() or agent.name.lower() in agent_name:
            return agent

    # Fallback: return first agent
    return agents[0]
