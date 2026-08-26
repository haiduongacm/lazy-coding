"""lazy-gate - Git gate and pipeline validation.

Mirrors no-mistakes internal/gate: bare repo creation, hook installation,
remote management, and repository registration.
"""

from .gate import Gate
from .pipeline import Pipeline

__all__ = ["Gate", "Pipeline"]
