"""lazy-master2 - Secondmate / persistent agent."""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import json


@dataclass
class LazyMaster2:
    """Persistent agent with charter and scope."""

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
        """Assign a task to this secondmate."""
        if self.status == "working":
            return {"error": True, "code": "BUSY"}

        # Check scope
        if self.scope:
            in_scope = any(
                s.lower() in task.get("description", "").lower()
                for s in self.scope
            )
            if not in_scope:
                return {"error": True, "code": "OUT_OF_SCOPE"}

        from .hand import LazyHand
        self.hand = LazyHand(
            id=f"{self.id}-hand",
            agent=self.harness,
            backend=self.backend,
        )
        self.hand.worktree = task.get("worktree", self.home)
        await self.hand.assign(task)

        self.status = "working"
        self.save()
        return {"success": True, "hand_id": self.hand.id}

    def complete(self, result: dict):
        """Mark task as complete."""
        if self.hand:
            self.hand.complete(result)
        self.status = "idle"
        self.hand = None
        self.save()

    def fail(self, error: Exception):
        """Mark task as failed."""
        if self.hand:
            self.hand.fail(error)
        self.status = "idle"
        self.hand = None
        self.save()

    def get_status(self) -> dict:
        """Get status."""
        return {
            "id": self.id,
            "name": self.name,
            "harness": self.harness,
            "scope": self.scope,
            "projects": self.projects,
            "status": self.status,
        }

    def save(self):
        """Save state to disk."""
        Path(self.home).mkdir(parents=True, exist_ok=True)
        state_file = Path(self.home) / "state.json"
        with open(state_file, "w") as f:
            json.dump(self.get_status(), f, indent=2)

    def load(self):
        """Load state from disk."""
        state_file = Path(self.home) / "state.json"
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
                self.name = state.get("name", self.name)
                self.harness = state.get("harness", self.harness)
                self.scope = state.get("scope", self.scope)
                self.status = state.get("status", self.status)
