"""lazy-master hand - Worker agent representation.

Mirrors firstmate's crewmate concept: a spawned worker in an isolated worktree.
"""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class LazyHand:
    """Worker agent in an isolated worktree.

    Mirrors firstmate's crewmate: spawned to work on a specific task,
    never addresses the captain directly, communication flows through master.
    """

    id: str
    agent: str = "claude"
    status: str = "idle"
    task: dict[str, Any] | None = None
    worktree: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def get_status(self) -> dict[str, Any]:
        """Get hand status."""
        return {
            "id": self.id,
            "status": self.status,
            "agent": self.agent,
            "task": self.task,
            "worktree": self.worktree,
        }

    def complete(self, result: dict[str, Any]) -> None:
        """Mark hand as done with result."""
        self.status = "done"
        self.result = result
        self.completed_at = datetime.now()

    def fail(self, error: Exception) -> None:
        """Mark hand as failed."""
        self.status = "failed"
        self.result = {"error": str(error)}
        self.completed_at = datetime.now()
