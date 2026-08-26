"""Worker hand that executes tasks."""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime


@dataclass
class LazyHand:
    """Worker agent that executes tasks."""

    id: str
    agent: str = "claude"
    backend: Any = None
    worktree: Optional[str] = None
    task: Optional[dict] = None
    status: str = "idle"
    result: Optional[dict] = None
    endpoint: Optional[dict] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    async def assign(self, task: dict) -> dict:
        """Assign a task to this hand."""
        self.task = task
        self.status = "assigned"
        self.started_at = datetime.now().isoformat()

        if self.backend and hasattr(self.backend, "spawn"):
            self.endpoint = await self.backend.spawn(self.id, {
                "agent": self.agent,
                "cwd": self.worktree or ".",
            })
            self.status = "working"

        return self.endpoint or {"id": self.id}

    async def send(self, text: str) -> dict:
        """Send text to the agent."""
        if not self.backend or not self.endpoint:
            return {"delivered": False, "reason": "no-backend"}
        return await self.backend.send(self.endpoint["id"], text)

    async def capture(self, lines: int = 50) -> str:
        """Capture terminal output."""
        if not self.backend or not self.endpoint:
            return ""
        return await self.backend.capture(self.endpoint["id"], lines)

    async def is_alive(self) -> dict:
        """Check if agent is alive."""
        if not self.backend or not self.endpoint:
            return {"alive": False, "reason": "no-backend"}
        return await self.backend.is_alive(self.endpoint["id"])

    async def get_busy_state(self) -> dict:
        """Get busy state."""
        if not self.backend or not self.endpoint:
            return {"state": "unknown", "source": "no-backend"}
        return await self.backend.get_busy_state(self.endpoint["id"])

    def complete(self, result: dict):
        """Mark task as complete."""
        self.result = result
        self.status = "done"
        self.completed_at = datetime.now().isoformat()

    def fail(self, error: Exception):
        """Mark task as failed."""
        self.result = {"error": str(error)}
        self.status = "failed"
        self.completed_at = datetime.now().isoformat()

    async def teardown(self):
        """Teardown endpoint."""
        if self.backend and self.endpoint:
            result = await self.backend.teardown(self.endpoint["id"])
            self.endpoint = None
            return result
        return {"teardown": "no-backend"}

    def get_status(self) -> dict:
        """Get hand status."""
        return {
            "id": self.id,
            "task": self.task.get("description") if self.task else None,
            "status": self.status,
            "agent": self.agent,
            "backend": self.backend.name if self.backend else None,
            "window": self.endpoint.get("window") if self.endpoint else None,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
