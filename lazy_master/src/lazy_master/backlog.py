"""lazy-master backlog - Task queue management.

Mirrors firstmate AGENTS.md section 10: backlog contract.
data/backlog.md is the durable queue, tracks work items only, never agents.
"""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
import uuid


@dataclass
class BacklogItem:
    """Backlog item."""
    id: str
    description: str
    status: str = "queued"
    type: str = "ship"
    priority: str = "normal"
    mode: str = "no-mistakes"
    yolo: str = "off"
    created: datetime = field(default_factory=datetime.now)
    completed: datetime | None = None
    blocked_by: list[str] = field(default_factory=list)


class Backlog:
    """Task queue management.

    Mirrors firstmate's backlog contract:
    - Tracks work items only, never agents
    - Persistent secondmates never appear as backlog items
    - Update on every dispatch, completion, and decision
    """

    def __init__(self):
        self.items: dict[str, BacklogItem] = {}

    def add(self, description: str, type: str = "ship",
            priority: str = "normal", mode: str = "no-mistakes",
            yolo: str = "off") -> dict[str, Any]:
        """Add item to backlog."""
        item_id = str(uuid.uuid4())[:8]
        item = BacklogItem(
            id=item_id,
            description=description,
            type=type,
            priority=priority,
            mode=mode,
            yolo=yolo,
        )
        self.items[item_id] = item
        return {"id": item_id, "description": description, "status": "queued"}

    def list_items(self, status: str | None = None) -> list[dict[str, Any]]:
        """List backlog items."""
        items = list(self.items.values())
        if status:
            items = [i for i in items if i.status == status]
        return [
            {"id": i.id, "description": i.description, "status": i.status,
             "type": i.type, "priority": i.priority}
            for i in items
        ]

    def ready(self) -> list[dict[str, Any]]:
        """Get ready items (queued, not blocked)."""
        ready = []
        for item in self.items.values():
            if item.status != "queued":
                continue
            if item.blocked_by:
                blocked = any(
                    self.items.get(b) and self.items[b].status != "done"
                    for b in item.blocked_by
                )
                if blocked:
                    continue
            ready.append({
                "id": item.id,
                "description": item.description,
                "priority": item.priority,
            })
        return ready

    def complete(self, item_id: str) -> dict[str, Any]:
        """Mark item as complete."""
        if item_id not in self.items:
            return {"error": True, "code": "NOT_FOUND", "message": f"Item {item_id} not found"}
        self.items[item_id].status = "done"
        self.items[item_id].completed = datetime.now()
        return {"success": True, "id": item_id}
