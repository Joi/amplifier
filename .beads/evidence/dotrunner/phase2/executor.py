"""
Node executor for workflow execution.

Executes individual workflow nodes using AI via Claude session.
"""

import logging
import time
from typing import Any

from ai_working.dotrunner.context import ContextError
from ai_working.dotrunner.context import interpolate
from ai_working.dotrunner.state import NodeResult
from ai_working.dotrunner.workflow import Node
from amplifier.ccsdk_toolkit import ClaudeSession
from amplifier.ccsdk_toolkit import SessionOptions
from amplifier.ccsdk_toolkit.defensive import parse_llm_json
from amplifier.ccsdk_toolkit.defensive import retry_with_feedback
from amplifier.ccsdk_toolkit.sessions import SessionManager

logger = logging.getLogger(__name__)


class NodeExecutor:
    """Executes workflow nodes using AI"""

    def __init__(self, session_manager: SessionManager | None = None):
        """Initialize executor with optional session manager"""
        self.session_mgr = session_manager or SessionManager()
        self.logger = logging.getLogger(__name__)

    async def execute(self, node: Node, context: dict[str, Any]) -> NodeResult:
        """
        Execute a single node.

        Flow:
        1. Interpolate prompt using context
        2. Execute via ClaudeSession
        3. Extract outputs from response
        4. Return NodeResult

        Error handling:
        - Catch ContextError → return failed NodeResult
        - Catch any Exception → return failed NodeResult
        - Always set execution_time
        """
        start_time = time.time()

        try:
            # 1. Interpolate prompt
            prompt = self._interpolate_prompt(node.prompt, context)

            # 2. Execute with AI
            response = await self._execute_generic(prompt)

            # Check for empty response (retry_with_feedback returned None)
            if not response:
                raise RuntimeError("AI execution failed after all retries")

            # 3. Extract outputs
            outputs = self._extract_outputs(response, node.outputs)

            # 4. Return success
            return NodeResult(
                node_id=node.id,
                status="success",
                outputs=outputs,
                raw_response=response,
                execution_time=time.time() - start_time,
            )

        except ContextError as e:
            # Handle missing context variables
            self.logger.error(f"Context error in node {node.id}: {e}")
            return NodeResult(
                node_id=node.id,
                status="failed",
                outputs={},
                raw_response="",
                error=str(e),
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            # Handle all other errors
            self.logger.error(f"Execution error in node {node.id}: {e}")
            return NodeResult(
                node_id=node.id,
                status="failed",
                outputs={},
                raw_response="",
                error=str(e),
                execution_time=time.time() - start_time,
            )

    def _interpolate_prompt(self, template: str, context: dict[str, Any]) -> str:
        """Interpolate context variables into prompt"""
        return interpolate(template, context)

    async def _execute_generic(self, prompt: str) -> str:
        """Execute prompt using ClaudeSession with retry"""
        options = SessionOptions(
            system_prompt="You are executing a workflow step. Provide clear, structured outputs as requested.",
            timeout_seconds=60,
        )

        async with ClaudeSession(options) as session:
            response = await retry_with_feedback(func=session.query, prompt=prompt, max_retries=3)

        # Handle None response from retry_with_feedback (all retries failed)
        if response is None:
            return ""

        # Extract content from response if it's an object
        if hasattr(response, "content"):
            return response.content
        return str(response)

    def _extract_outputs(self, response: str, output_names: list[str]) -> dict[str, Any]:
        """Extract named outputs from AI response"""
        outputs = {}

        # Return empty dict if no outputs requested
        if not output_names:
            return outputs

        # Try JSON parsing first if response looks like JSON
        if any(keyword in response for keyword in ["{", "json"]):
            try:
                parsed = parse_llm_json(response)
                if isinstance(parsed, dict):
                    for name in output_names:
                        if name in parsed:
                            outputs[name] = parsed[name]
                    if outputs:
                        return outputs
            except Exception:
                pass  # Fall back to pattern matching

        # Pattern-based extraction: "name: value"
        # Split response into lines and process each one
        lines = response.strip().split("\n")
        for line in lines:
            line = line.strip()
            if ":" in line and not line.endswith(":"):
                # Split only on first colon to handle values with colons
                parts = line.split(":", 1)
                if len(parts) == 2:
                    key, value = parts[0].strip().lower(), parts[1].strip()
                    # Check if this key matches any requested output
                    for name in output_names:
                        if key == name.lower() and name not in outputs:
                            outputs[name] = value
                            break

        return outputs
