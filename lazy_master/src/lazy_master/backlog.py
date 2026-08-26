"""lazy-master backlog - Task queue management.

Mirrors firstmate AGENTS.md section 10: backlog contract.
data/backlog.md is the durable queue, tracks work items only, never agents.

Key concepts from firstmate:
- Durable queue with dependencies and time gates
- File locking for atomic read/write
- Handoff protocol for cross-home delivery
- Decision tracking (captain holds)
- Re-evaluation after teardown and heartbeat
"""

import os
import json
import time
import platform
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
import uuid

# Conditional import for file locking
if platform.system() != "Windows":
    import fcntl
else:
    fcntl = None


class BacklogItem:
    """Backlog item with dependencies and time gates."""

    def __init__(self, id: str, description: str, type: str = "ship",
                 priority: str = "normal", mode: str = "no-mistakes",
                 yolo: str = "off", project: str | None = None):
        self.id = id
        self.description = description
        self.type = type  # ship, scout
        self.priority = priority  # high, normal, low
        self.mode = mode  # no-mistakes, direct-PR, local-only
        self.yolo = yolo  # on, off
        self.project = project
        self.status = "queued"  # queued, in-progress, done, blocked, held
        self.blocked_by: list[str] = []
        self.time_gate: str | None = None  # ISO timestamp
        self.created = datetime.now().isoformat()
        self.completed: str | None = None
        self.note: str = ""
        self.hold_reason: str | None = None
        self.hold_kind: str | None = None  # captain, dependency, time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "id": self.id,
            "description": self.description,
            "type": self.type,
            "priority": self.priority,
            "mode": self.mode,
            "yolo": self.yolo,
            "project": self.project,
            "status": self.status,
            "blocked_by": self.blocked_by,
            "time_gate": self.time_gate,
            "created": self.created,
            "completed": self.completed,
            "note": self.note,
            "hold_reason": self.hold_reason,
            "hold_kind": self.hold_kind,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BacklogItem":
        """Create from dict."""
        item = cls(
            id=data["id"],
            description=data["description"],
            type=data.get("type", "ship"),
            priority=data.get("priority", "normal"),
            mode=data.get("mode", "no-mistakes"),
            yolo=data.get("yolo", "off"),
            project=data.get("project"),
        )
        item.status = data.get("status", "queued")
        item.blocked_by = data.get("blocked_by", [])
        item.time_gate = data.get("time_gate")
        item.created = data.get("created", item.created)
        item.completed = data.get("completed")
        item.note = data.get("note", "")
        item.hold_reason = data.get("hold_reason")
        item.hold_kind = data.get("hold_kind")
        return item


class Backlog:
    """Task queue management.

    Mirrors firstmate's backlog contract:
    - Tracks work items only, never agents
    - Persistent secondmates never appear as backlog items
    - Update on every dispatch, completion, and decision
    """

    def __init__(self, data_dir: str | None = None):
        self.data_dir = Path(data_dir or os.path.expanduser("~/.lazy-coding/data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backlog_file = self.data_dir / "backlog.json"
        self.items: dict[str, BacklogItem] = {}
        self._load()

    def _load(self) -> None:
        """Load backlog from disk."""
        if not self.backlog_file.exists():
            return

        try:
            with open(self.backlog_file, "r") as f:
                data = json.load(f)
                for item_data in data.get("items", []):
                    item = BacklogItem.from_dict(item_data)
                    self.items[item.id] = item
        except Exception:
            pass

    def _save(self) -> None:
        """Save backlog to disk with atomic write."""
        tmp_file = self.backlog_file.with_suffix(".tmp")
        data = {
            "items": [item.to_dict() for item in self.items.values()],
            "updated": datetime.now().isoformat(),
        }
        
        # Use file locking on Unix, simple write on Windows
        if fcntl:
            with open(tmp_file, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        else:
            with open(tmp_file, "w") as f:
                json.dump(data, f, indent=2)
        
        tmp_file.replace(self.backlog_file)

    def add(self, description: str, type: str = "ship", priority: str = "normal",
            mode: str = "no-mistakes", yolo: str = "off", project: str | None = None,
            blocked_by: list[str] | None = None, time_gate: str | None = None,
            note: str = "") -> dict[str, Any]:
        """Add item to backlog."""
        item_id = str(uuid.uuid4())[:8]
        item = BacklogItem(
            id=item_id,
            description=description,
            type=type,
            priority=priority,
            mode=mode,
            yolo=yolo,
            project=project,
        )
        item.blocked_by = blocked_by or []
        item.time_gate = time_gate
        item.note = note

        self.items[item_id] = item
        self._save()

        return {"id": item_id, "description": description, "status": "queued"}

    def list_items(self, status: str | None = None, type: str | None = None,
                   project: str | None = None) -> list[dict[str, Any]]:
        """List backlog items."""
        items = list(self.items.values())
        if status:
            items = [i for i in items if i.status == status]
        if type:
            items = [i for i in items if i.type == type]
        if project:
            items = [i for i in items if i.project == project]
        return [item.to_dict() for item in items]

    def ready(self) -> list[dict[str, Any]]:
        """Get ready items (queued, not blocked, time gate passed)."""
        now = datetime.now().isoformat()
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
            if item.time_gate and item.time_gate > now:
                continue
            ready.append(item.to_dict())
        return ready

    def hold(self, item_id: str, reason: str, kind: str = "captain",
             until: str | None = None) -> dict[str, Any]:
        """Hold item for captain decision.

        Mirrors firstmate: task held for captain, not closed.
        """
        if item_id not in self.items:
            return {"error": True, "code": "NOT_FOUND", "message": f"Item {item_id} not found"}

        item = self.items[item_id]
        item.status = "held"
        item.hold_reason = reason
        item.hold_kind = kind
        if until:
            item.time_gate = until
        self._save()

        return {"success": True, "id": item_id, "status": "held"}

    def unhold(self, item_id: str) -> dict[str, Any]:
        """Unhold item and return to queue."""
        if item_id not in self.items:
            return {"error": True, "code": "NOT_FOUND", "message": f"Item {item_id} not found"}

        item = self.items[item_id]
        item.status = "queued"
        item.hold_reason = None
        item.hold_kind = None
        self._save()

        return {"success": True, "id": item_id, "status": "queued"}

    def complete(self, item_id: str) -> dict[str, Any]:
        """Mark item as complete."""
        if item_id not in self.items:
            return {"error": True, "code": "NOT_FOUND", "message": f"Item {item_id} not found"}

        self.items[item_id].status = "done"
        self.items[item_id].completed = datetime.now().isoformat()
        self._save()

        return {"success": True, "id": item_id}

    def block(self, item_id: str, blocked_by: list[str]) -> dict[str, Any]:
        """Add dependencies to item."""
        if item_id not in self.items:
            return {"error": True, "code": "NOT_FOUND", "message": f"Item {item_id} not found"}

        self.items[item_id].blocked_by.extend(blocked_by)
        self.items[item_id].status = "blocked"
        self._save()

        return {"success": True, "id": item_id, "blocked_by": blocked_by}

    def reevaluate(self) -> list[dict[str, Any]]:
        """Re-evaluate queued work after teardown/heartbeat.

        Mirrors firstmate: dispatch items only when dependencies and time gates cleared.
        """
        dispatched = []
        for item in self.items.values():
            if item.status == "blocked":
                # Check if dependencies are cleared
                all_clear = all(
                    self.items.get(b) and self.items[b].status == "done"
                    for b in item.blocked_by
                )
                if all_clear:
                    item.status = "queued"
                    dispatched.append(item.to_dict())

        if dispatched:
            self._save()

        return dispatched

    def stats(self) -> dict[str, Any]:
        """Get backlog statistics."""
        statuses = {}
        for item in self.items.values():
            statuses[item.status] = statuses.get(item.status, 0) + 1

        return {
            "total": len(self.items),
            "by_status": statuses,
            "ready": len(self.ready()),
        }
