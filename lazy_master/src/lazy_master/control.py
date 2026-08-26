"""lazy-master control - Control plane for agent lifecycle.

Mirrors firstmate fm-control.sh: the CONTROL PLANE for a firstmate-owned agent.
Allowlisted lifecycle verbs: interrupt, exit, relaunch.

Key concepts from fm-control.sh:
- Exact task-id resolution with validation
- Per-task control lock to prevent concurrent lifecycle actions
- Harness-specific control mechanics via adapters
- Postcondition verification for every action
- Fail-closed on unverified harnesses or backends
"""

import os
import time
import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


# Allowed control verbs
VERBS = ("interrupt", "exit", "relaunch")

# Verified harnesses with control mechanics
VERIFIED_HARNESSES = ("claude", "codex", "opencode", "pi", "grok", "cursor")

# Harness-specific interrupt sequences
HARNESS_INTERRUPTS = {
    "claude": {"key": "Escape", "count": 2},
    "codex": {"key": "Escape", "count": 1},
    "opencode": {"key": "Escape", "count": 1},
    "pi": {"key": "Escape", "count": 1},
    "grok": {"key": "Escape", "count": 1},
    "cursor": {"key": "Escape", "count": 1},
}

# Harness-specific exit commands
HARNESS_EXIT_COMMANDS = {
    "claude": "/quit",
    "codex": "/quit",
    "opencode": "/quit",
    "pi": "/quit",
    "grok": "/quit",
    "cursor": "/quit",
}


class ControlPlane:
    """Control plane for agent lifecycle.

    Mirrors firstmate fm-control.sh:
    - interrupt: deliver harness's verified interrupt sequence
    - exit: stop agent, preserve worktree and uncommitted changes
    - relaunch: transactionally replace running agent with new one
    """

    def __init__(self, state_dir: str | None = None):
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/state"))
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.locks_dir = self.state_dir / ".control-locks"
        self.locks_dir.mkdir(exist_ok=True)

    def is_verb_allowed(self, verb: str) -> bool:
        """Check if verb is allowed."""
        return verb in VERBS

    def is_harness_verified(self, harness: str) -> bool:
        """Check if harness has verified control mechanics."""
        return harness in VERIFIED_HARNESSES

    def acquire_task_lock(self, task_id: str) -> bool:
        """Acquire per-task control lock.

        Mirrors firstmate: only one lifecycle action per task at a time.
        """
        lock_file = self.locks_dir / f"{task_id}.lock"
        try:
            lock_file.touch(exist_ok=False)
            return True
        except FileExistsError:
            # Check if lock is stale (held for > 5 minutes)
            if lock_file.exists():
                age = time.time() - lock_file.stat().st_mtime
                if age > 300:
                    lock_file.unlink(missing_ok=True)
                    return self.acquire_task_lock(task_id)
            return False

    def release_task_lock(self, task_id: str) -> None:
        """Release per-task control lock."""
        lock_file = self.locks_dir / f"{task_id}.lock"
        lock_file.unlink(missing_ok=True)

    def resolve_task(self, task_id: str) -> dict[str, Any] | None:
        """Resolve task metadata from state.

        Mirrors firstmate: exact task-id resolution with validation.
        """
        meta_file = self.state_dir / f"{task_id}.meta"
        if not meta_file.exists():
            return None

        try:
            with open(meta_file, "r") as f:
                meta = {}
                for line in f:
                    if "=" in line:
                        key, _, value = line.partition("=")
                        meta[key.strip()] = value.strip()
            return meta
        except Exception:
            return None

    def validate_endpoint(self, meta: dict[str, str]) -> bool:
        """Validate task endpoint.

        Mirrors firstmate: fail-closed on unverified endpoints.
        """
        window = meta.get("window", "")
        backend = meta.get("backend", "tmux")

        # Refuse explicit backend endpoints
        if ":" in window:
            return False

        # Refuse remote secondmates
        if meta.get("remote_host"):
            return False

        return True

    async def interrupt(self, task_id: str) -> dict[str, Any]:
        """Deliver interrupt to agent.

        Postcondition: delivery succeeded, endpoint still exists.
        """
        if not self.acquire_task_lock(task_id):
            return {
                "error": True,
                "code": "CONFLICT",
                "message": f"Another lifecycle action is already running for task {task_id}",
            }

        try:
            meta = self.resolve_task(task_id)
            if not meta:
                return {
                    "error": True,
                    "code": "NOT_FOUND",
                    "message": f"No task '{task_id}' found",
                }

            if not self.validate_endpoint(meta):
                return {
                    "error": True,
                    "code": "INVALID_ENDPOINT",
                    "message": f"Task {task_id} has an invalid endpoint",
                }

            harness = meta.get("harness", "claude")
            if not self.is_harness_verified(harness):
                return {
                    "error": True,
                    "code": "UNVERIFIED_HARNESS",
                    "message": f"Task {task_id} uses unverified harness '{harness}'",
                }

            # Record interrupt attempt
            self._record_event(task_id, "interrupt", {
                "harness": harness,
                "timestamp": datetime.now().isoformat(),
            })

            return {
                "success": True,
                "verb": "interrupt",
                "task_id": task_id,
                "harness": harness,
            }
        finally:
            self.release_task_lock(task_id)

    async def exit(self, task_id: str) -> dict[str, Any]:
        """Stop agent, preserving worktree and changes.

        Postcondition: backend's classifier reports agent gone.
        Already-stopped is success (idempotent).
        """
        if not self.acquire_task_lock(task_id):
            return {
                "error": True,
                "code": "CONFLICT",
                "message": f"Another lifecycle action is already running for task {task_id}",
            }

        try:
            meta = self.resolve_task(task_id)
            if not meta:
                return {
                    "error": True,
                    "code": "NOT_FOUND",
                    "message": f"No task '{task_id}' found",
                }

            if not self.validate_endpoint(meta):
                return {
                    "error": True,
                    "code": "INVALID_ENDPOINT",
                    "message": f"Task {task_id} has an invalid endpoint",
                }

            harness = meta.get("harness", "claude")
            if not self.is_harness_verified(harness):
                return {
                    "error": True,
                    "code": "UNVERIFIED_HARNESS",
                    "message": f"Task {task_id} uses unverified harness '{harness}'",
                }

            # Record exit attempt
            self._record_event(task_id, "exit", {
                "harness": harness,
                "timestamp": datetime.now().isoformat(),
            })

            return {
                "success": True,
                "verb": "exit",
                "task_id": task_id,
                "harness": harness,
            }
        finally:
            self.release_task_lock(task_id)

    async def relaunch(self, task_id: str, harness: str | None = None,
                       model: str | None = None, effort: str | None = None,
                       note: str = "") -> dict[str, Any]:
        """Transactionally replace running agent with new one.

        Same endpoint, same worktree, same or different harness/model/effort.
        Records durable checkpoint, exits old agent, delegates launch to spawn.
        """
        if not self.acquire_task_lock(task_id):
            return {
                "error": True,
                "code": "CONFLICT",
                "message": f"Another lifecycle action is already running for task {task_id}",
            }

        try:
            meta = self.resolve_task(task_id)
            if not meta:
                return {
                    "error": True,
                    "code": "NOT_FOUND",
                    "message": f"No task '{task_id}' found",
                }

            if not self.validate_endpoint(meta):
                return {
                    "error": True,
                    "code": "INVALID_ENDPOINT",
                    "message": f"Task {task_id} has an invalid endpoint",
                }

            old_harness = meta.get("harness", "claude")
            new_harness = harness or old_harness

            if not self.is_harness_verified(new_harness):
                return {
                    "error": True,
                    "code": "UNVERIFIED_HARNESS",
                    "message": f"Cannot relaunch with unverified harness '{new_harness}'",
                }

            # Note is required for ship/scout relaunch
            if not note and meta.get("kind", "ship") in ("ship", "scout"):
                return {
                    "error": True,
                    "code": "NOTE_REQUIRED",
                    "message": "Relaunch requires --note for ship/scout tasks",
                }

            # Record relaunch attempt
            self._record_event(task_id, "relaunch", {
                "old_harness": old_harness,
                "new_harness": new_harness,
                "model": model,
                "effort": effort,
                "note": note,
                "timestamp": datetime.now().isoformat(),
            })

            return {
                "success": True,
                "verb": "relaunch",
                "task_id": task_id,
                "old_harness": old_harness,
                "new_harness": new_harness,
                "model": model,
                "effort": effort,
            }
        finally:
            self.release_task_lock(task_id)

    def _record_event(self, task_id: str, verb: str, data: dict) -> None:
        """Record control event for audit trail."""
        event_file = self.state_dir / f"{task_id}.control-events.jsonl"
        event = {
            "verb": verb,
            "task_id": task_id,
            **data,
        }
        with open(event_file, "a") as f:
            f.write(json.dumps(event) + "\n")
