"""
Node executor for workflow execution.

Executes individual workflow nodes using AI via Claude session.
"""

import asyncio
import logging
import subprocess
import tempfile
import time
from pathlib import Path
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
        Execute a single node with retry support.

        Flow:
        1. Interpolate prompt using context
        2. Execute via agent or AI based on node configuration
        3. Extract outputs from response
        4. Return NodeResult

        Error handling:
        - Catch ContextError → return failed NodeResult
        - Catch any Exception → retry if configured, then return failed NodeResult
        - Always set execution_time
        """
        start_time = time.time()
        max_attempts = max(1, node.retry_on_failure)
        last_error = None

        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    self.logger.info(f"Retrying node {node.id} (attempt {attempt + 1}/{max_attempts})")

                # 1. Interpolate prompt
                prompt = self._interpolate_prompt(node.prompt, context)

                # 2. Execute with agent or AI
                if node.agent:
                    response = await self._execute_with_agent(node, prompt)
                else:
                    response = await self._execute_generic(prompt, node.outputs)

                # Check for empty response
                if not response:
                    raise RuntimeError("Execution failed after all retries")

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
                # Handle missing context variables - don't retry for these
                self.logger.error(f"Context error in node {node.id}: {e}")
                return NodeResult(
                    node_id=node.id,
                    status="failed",
                    outputs={},
                    raw_response="",
                    error=f"Missing required variables: {e.missing_vars}",
                    execution_time=time.time() - start_time,
                )

            except Exception as e:
                # Handle all other errors - retry if configured
                last_error = e
                if attempt < max_attempts - 1:
                    self.logger.warning(f"Execution error in node {node.id}, will retry: {e}")
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    self.logger.error(f"Execution error in node {node.id} after {max_attempts} attempts: {e}")

        # All retries failed
        return NodeResult(
            node_id=node.id,
            status="failed",
            outputs={},
            raw_response="",
            error=str(last_error),
            execution_time=time.time() - start_time,
        )

    def _interpolate_prompt(self, template: str, context: dict[str, Any]) -> str:
        """Interpolate context variables into prompt"""
        return interpolate(template, context)

    async def _execute_generic(self, prompt: str, output_names: list[str] = None) -> str:
        """Execute prompt using ClaudeSession with retry"""
        system_prompt = "You are executing a workflow step. Provide clear, structured outputs as requested."

        # Add output format guidance if outputs are expected
        if output_names:
            system_prompt += "\n\nIMPORTANT: Your response MUST include these outputs in the format 'output_name: value' on separate lines:\n"
            for name in output_names:
                system_prompt += f"- {name}: <your value here>\n"

        options = SessionOptions(
            system_prompt=system_prompt,
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
                    # Extract all matching outputs from JSON
                    for name in output_names:
                        outputs[name] = parsed.get(name, "")
                    # If we got at least one non-empty value, use JSON results
                    if any(outputs.values()):
                        return outputs
            except Exception:
                pass  # Fall back to pattern matching

        # Pattern-based extraction: "name: value"
        # Split response into lines and process each one
        lines = response.strip().split("\n")

        # Create lowercase mapping for case-insensitive matching
        name_map = {name.lower(): name for name in output_names}

        for line in lines:
            line = line.strip()
            if ":" in line and not line.endswith(":"):
                # Split only on first colon to handle values with colons
                parts = line.split(":", 1)
                if len(parts) == 2:
                    key, value = parts[0].strip().lower(), parts[1].strip()
                    # Check if this key matches any requested output (case-insensitive)
                    if key in name_map:
                        original_name = name_map[key]
                        if original_name not in outputs:
                            outputs[original_name] = value

        # Fallback: If no outputs extracted and we have output names,
        # map entire response to first output (handles plain text responses)
        if not outputs and output_names:
            outputs[output_names[0]] = response.strip()
            # Fill remaining outputs with empty strings
            for name in output_names[1:]:
                outputs[name] = ""
        else:
            # Fill missing outputs with empty strings
            for name in output_names:
                if name not in outputs:
                    outputs[name] = ""

        return outputs

    async def _execute_with_agent(self, node: Node, prompt: str) -> str:
        """Execute using specified agent via subprocess"""

        # Write prompt to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            # Build command
            cmd = ["amplifier", "agent", node.agent]
            if node.agent_mode:
                cmd.extend(["--mode", node.agent_mode])
            cmd.extend(["--prompt-file", prompt_file])
            cmd.append("--json")

            # Execute agent with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
            )

            if result.returncode != 0:
                raise RuntimeError(f"Agent {node.agent} failed: {result.stderr}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Agent {node.agent} execution timed out after 300 seconds")
        finally:
            # Cleanup temp file
            Path(prompt_file).unlink(missing_ok=True)
