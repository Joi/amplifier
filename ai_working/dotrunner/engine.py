"""
Workflow orchestration engine.

Orchestrates the execution of workflows by coordinating node execution,
managing state, and handling errors.
"""

import logging
import time
from typing import Any

from ai_working.dotrunner.executor import NodeExecutor
from ai_working.dotrunner.state import NodeResult
from ai_working.dotrunner.state import WorkflowResult
from ai_working.dotrunner.state import WorkflowState
from ai_working.dotrunner.workflow import Node
from ai_working.dotrunner.workflow import Workflow
from amplifier.ccsdk_toolkit import SessionManager

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Orchestrates linear workflow execution"""

    def __init__(self, session_manager: SessionManager | None = None, save_checkpoints: bool = True):
        """Initialize engine with optional checkpoint saving"""
        self.session_mgr = session_manager or SessionManager()
        self.executor = NodeExecutor(session_manager)
        self.logger = logging.getLogger(__name__)
        self.save_checkpoints = save_checkpoints
        self.session_id = None

    async def run(self, workflow: Workflow, session_id: str | None = None) -> WorkflowResult:
        """Execute workflow with optional state persistence"""
        from ai_working.dotrunner.persistence import load_state
        from ai_working.dotrunner.persistence import save_state
        from ai_working.dotrunner.persistence import save_workflow

        start_time = time.time()

        # Initialize or restore state
        if session_id and self.save_checkpoints:
            # Try to load existing state for resume
            try:
                state = load_state(session_id)
                self.logger.info(f"Resuming from saved state: {len(state.results)} nodes completed")
            except FileNotFoundError:
                # New session with provided ID
                state = WorkflowState(
                    workflow_id=workflow.name,
                    current_node=None,
                    context=workflow.context.copy(),
                    results=[],
                    status="running",
                )
        else:
            # Fresh state
            state = WorkflowState(
                workflow_id=workflow.name,
                current_node=None,
                context=workflow.context.copy(),
                results=[],
                status="running",
            )

        # Save initial state if checkpoints enabled
        if self.save_checkpoints:
            self.session_id = save_state(state, session_id)
            save_workflow(workflow, self.session_id)  # Save workflow for resumption
            self.logger.info(f"Session: {self.session_id}")

        self.logger.info(f"Starting workflow: {workflow.name}")

        try:
            # Execute nodes sequentially
            while True:
                # Get next node
                next_node = self._get_next_node(workflow, state)
                if not next_node:
                    break

                self.logger.info(f"Executing node: {next_node.id} ({next_node.name})")

                # Execute node
                result = await self._execute_node(next_node, state)

                # Update state
                state.results.append(result)
                state.current_node = next_node.id
                state.context.update(result.outputs)
                state.execution_path.append(next_node.id)  # Track execution path

                # Save checkpoint after each node
                if self.save_checkpoints:
                    save_state(state, self.session_id)

                # Check for failure
                if result.status == "failed":
                    self.logger.error(f"Node {next_node.id} failed: {result.error}")
                    state.status = "failed"
                    break

            # Mark completed if got through all nodes
            if state.status == "running":
                state.status = "completed"

            # Final save
            if self.save_checkpoints:
                save_state(state, self.session_id)

            self.logger.info(f"Workflow {workflow.name} {state.status}")

            return WorkflowResult(
                workflow_id=workflow.name,
                status=state.status,
                total_time=time.time() - start_time,
                node_results=state.results,
                final_context=state.context,
                error=None if state.status == "completed" else "Workflow failed",
                execution_path=state.execution_path,
            )

        except Exception as e:
            state.status = "failed"
            if self.save_checkpoints:
                save_state(state, self.session_id)
            self.logger.exception(f"Workflow execution failed: {e}")
            return WorkflowResult(
                workflow_id=workflow.name,
                status="failed",
                total_time=time.time() - start_time,
                node_results=state.results,
                final_context=state.context,
                error=str(e),
                execution_path=state.execution_path,
            )

    def _get_next_node_id(self, current_node: Node, context: dict[str, Any]) -> str | None:
        """Determine next node ID - supports linear and conditional routing"""
        if current_node.next is None:
            return None

        # Linear routing (string)
        if isinstance(current_node.next, str):
            return current_node.next

        # Conditional routing (dict)
        if isinstance(current_node.next, dict):
            return self._resolve_conditional_next(current_node, context)

        return None

    def _resolve_conditional_next(self, node: Node, context: dict[str, Any]) -> str | None:
        """Resolve conditional routing based on first output value"""
        if not isinstance(node.next, dict):
            return None

        # Get routing value from first output
        routing_value = ""
        if node.outputs:
            output_name = node.outputs[0]
            routing_value = str(context.get(output_name, "")).lower()

        # Try to match conditions (case-insensitive)
        for condition, target in node.next.items():
            if condition == "default":
                continue
            if condition.lower() == routing_value:
                self.logger.info(f"Routing condition matched: {condition} → {target}")
                return target

        # Use default if no match
        if "default" in node.next:
            self.logger.info(f"Using default route: {node.next['default']}")
            return node.next["default"]

        # Error if no match and no default
        raise ValueError(f"No routing condition matched '{routing_value}' and no default specified for node {node.id}")

    def _get_next_node(self, workflow: Workflow, state: WorkflowState) -> Node | None:
        """Get next node to execute"""
        # If no current node, return first
        if not state.current_node:
            return workflow.nodes[0] if workflow.nodes else None

        # Get current node
        current = workflow.get_node(state.current_node)
        if not current:
            return None

        # Check if node is terminal
        if current.type == "terminal":
            return None

        # Get next node ID using routing logic
        next_id = self._get_next_node_id(current, state.context)
        if next_id:
            return workflow.get_node(next_id)

        return None

    async def _execute_node(self, node: Node, state: WorkflowState) -> NodeResult:
        """Execute a single node"""
        return await self.executor.execute(node, state.context)
