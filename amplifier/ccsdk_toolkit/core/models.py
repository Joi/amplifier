"""Data models for CCSDK Core module."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import Field

# Default model to use for Claude sessions.
# Update this when a better model becomes available.
DEFAULT_MODEL = "claude-opus-4-5-20251101"


# Type alias for MCP server configuration
MCPServerDict = dict[str, dict[str, Any]]


class SessionOptions(BaseModel):
    """Configuration options for Claude sessions.

    Attributes:
        system_prompt: System prompt for the session
        model: Model to use (default: claude-opus-4-5-20251101)
        max_turns: Maximum conversation turns (default: unlimited)
        retry_attempts: Number of retry attempts on failure (default: 3)
        retry_delay: Initial retry delay in seconds (default: 1.0)
        stream_output: Enable real-time streaming output (default: False)
        progress_callback: Optional callback for progress updates
        mcp_servers: MCP server configurations (dict, path to .mcp.json, or None)
        allowed_tools: List of allowed tools (use mcp__{server}__{tool} for MCP tools)
        disallowed_tools: List of disallowed tools
    """

    system_prompt: str = Field(default="You are a helpful assistant")
    model: str = Field(default=DEFAULT_MODEL, description="Model to use")
    max_turns: int = Field(default=1, gt=0)
    retry_attempts: int = Field(default=3, gt=0, le=10)
    retry_delay: float = Field(default=1.0, gt=0, le=10.0)
    stream_output: bool = Field(default=False, description="Enable real-time streaming output")
    progress_callback: Callable[[str], None] | None = Field(
        default=None,
        description="Optional callback for progress updates",
        exclude=True,  # Exclude from serialization since callables can't be serialized
    )
    mcp_servers: MCPServerDict | str | Path | None = Field(
        default=None,
        description="MCP server configurations: dict of servers, path to .mcp.json, or None",
        exclude=True,  # Exclude from JSON serialization
    )
    allowed_tools: list[str] | None = Field(
        default=None,
        description="List of allowed tools (e.g., ['Bash', 'Read', 'mcp__memory__search'])",
    )
    disallowed_tools: list[str] | None = Field(
        default=None,
        description="List of disallowed tools",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "system_prompt": "You are a code review assistant",
                "model": "claude-opus-4-5-20251101",
                "max_turns": 1,
                "retry_attempts": 3,
                "retry_delay": 1.0,
                "stream_output": False,
                "mcp_servers": {
                    "memory": {
                        "command": "npx",
                        "args": ["-y", "@anthropic-ai/mcp-server-memory"],
                    }
                },
                "allowed_tools": ["Read", "Write", "mcp__memory__search"],
            }
        }


class SessionResponse(BaseModel):
    """Response from a Claude session query.

    Attributes:
        content: The response text content
        metadata: Additional metadata about the response
        error: Error message if the query failed
    """

    content: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = Field(default=None)

    @property
    def success(self) -> bool:
        """Check if the response was successful."""
        return self.error is None and bool(self.content)

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Here's the code review...",
                "metadata": {"tokens": 150, "model": "claude-3"},
                "error": None,
            }
        }
