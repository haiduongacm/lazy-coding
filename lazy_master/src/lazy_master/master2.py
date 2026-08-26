"""lazy-master2 - Secondmate / persistent agent.

Mirrors firstmate AGENTS.md section 6: secondmate is a crewmate with
an isolated firstmate home and a charter, not a second architecture.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional
from datetime import datetime
from pathlib import Path
import json
import uuid


@dataclass
class LazyMaster2:
    """Persistent agent with charter and scope.

    Mirrors firstmate's secondmate: idle by default, acts only on work
    routed by the main firstmate.
    """

    id: str
    name: str = "unnamed"
    harness: str = "claude"
    scope: List[str] = field(default_factory=list)
    projects: List[str] = field(default_factory=list)
    status: str = "idle"
    home: Optional[str] = None
    backend: Any = None
    hand: Any = None

    def __post_init__(self):
        if not self.home:
            self.home = str(Path.cwd() / "state" / "master2" / self.id)

    async def assign(self, task: dict) -> dict:
        """Assign a task to this secondmate.

        Mirrors firstmate: route by scope, not by clone list.
        """
        if self.status == "working":
            return {
                "error": True,
                "code": "BUSY",
                "message": f"Secondmate {self.id} is busy",
            }

        self.status = "working"
        self.hand = task
        return {
            "success": True,
            "secondmate_id": self.id,
            "task": task,
        }

    def get_status(self) -> dict:
        """Get secondmate status."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "scope": self.scope,
            "projects": self.projects,
            "home": self.home,
        }

    def complete(self, result: dict) -> None:
        """Mark task as complete."""
        self.status = "idle"
        self.hand = None

    def fail(self, error: Exception) -> None:
        """Mark task as failed."""
        self.status = "failed"
        self.hand = None
