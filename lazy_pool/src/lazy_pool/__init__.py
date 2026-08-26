"""lazy-pool - Worktree pool management.

Mirrors no-mistakes internal/worktrees: layout management, placement validation,
and custom root configuration per repository.
"""

from .pool import Pool
from .worktree import Worktree
from .state import State
from .layout import Layout

__all__ = ["Pool", "Worktree", "State", "Layout"]
