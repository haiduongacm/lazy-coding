"""lazy-gate - Git gate + pipeline validation."""

from .gate import Gate
from .pipeline import Pipeline
from .worktree import Worktree

__version__ = "1.0.0"

__all__ = ["Gate", "Pipeline", "Worktree"]
