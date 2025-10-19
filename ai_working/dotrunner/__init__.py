"""
DotRunner: Declarative Agentic Workflow Orchestration

Execute multi-agent workflows defined in YAML dotfiles with automatic
state persistence, resume capability, and evidence-based validation.
"""

__version__ = "0.1.0"

from ai_working.dotrunner.workflow import Node
from ai_working.dotrunner.workflow import Workflow

__all__ = ["Workflow", "Node"]
