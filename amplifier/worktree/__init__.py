"""
Git worktree management module.

This module provides a clean API for managing git worktrees including
creation, removal, stashing, and adoption of remote branches.
"""

from .core import copy_data_directory
from .core import create_worktree
from .core import list_worktrees
from .core import remove_worktree
from .core import setup_worktree_venv
from .manager import WorktreeManager
from .utils import ensure_not_in_worktree
from .utils import extract_feature_name
from .utils import get_repo_name
from .utils import get_worktree_info
from .utils import is_in_worktree
from .utils import resolve_worktree_path
from .utils import run_command

__all__ = [
    # Core operations
    "create_worktree",
    "remove_worktree",
    "setup_worktree_venv",
    "copy_data_directory",
    "list_worktrees",
    # Manager class
    "WorktreeManager",
    # Utilities
    "get_repo_name",
    "resolve_worktree_path",
    "run_command",
    "ensure_not_in_worktree",
    "is_in_worktree",
    "get_worktree_info",
    "extract_feature_name",
]
