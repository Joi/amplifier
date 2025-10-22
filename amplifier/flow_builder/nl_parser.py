"""
Natural language context parser - Phase 6.

Simple AI-based extraction of context variables.
"""

from typing import Any

from amplifier.ccsdk_toolkit.core.session import ClaudeSession


async def parse_context(user_input: str, required_fields: list[str]) -> dict[str, Any] | None:
    """
    Parse natural language into structured context.

    Args:
        user_input: Natural language from user
        required_fields: List of field names needed

    Returns:
        Dict with extracted values, or None if unparseable
    """
    if not required_fields:
        return {}

    prompt = f"""Extract these fields from the user's input:

Required fields: {', '.join(required_fields)}

User input: {user_input}

Respond with ONLY a JSON object containing the extracted values.
If you cannot extract a field, use null.

Example response:
{{"task": "implement authentication", "project": "webapp", "technology": "jwt"}}
"""

    async with ClaudeSession() as session:
        response = await session.query(prompt, stream=False)

    try:
        import json

        result = json.loads(response.content.strip())
        return result
    except json.JSONDecodeError:
        return None
