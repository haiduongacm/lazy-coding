"""lazy-pool - Git worktree pool manager."""

from .pool import Pool
from .worktree import Worktree
from .state import State

__version__ = "1.0.0"

__all__ = ["Pool", "Worktree", "State"]
