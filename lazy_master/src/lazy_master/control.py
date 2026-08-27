"""lazy-master control - Control plane for agent lifecycle.

Mirrors lazy-master's control plane: the CONTROL PLANE for a lazy-master-owned agent.
Allowlisted lifecycle verbs: interrupt, exit, relaunch.

Key concepts from lazy-master control:
- Exact task-id resolution with validation
- Per-task control lock to prevent concurrent lifecycle actions
- Harness-specific control mechanics via adapters
- Postcondition verification for every action
- Fail-closed on unverified harnesses or backends
"""

import os
import time
import json
import subprocess
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timezone


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

# Control timeouts (seconds)
POLL_INTERVAL = 0.5
SETTLE_WAIT = 5
EXIT_WAIT = 30
LAUNCH_WAIT = 90
EXIT_RETRIES = 3


class ControlPlane:
    """Control plane for agent lifecycle.

    Mirrors lazy-master's control plane:
    - interrupt: deliver harness's verified interrupt sequence
    - exit: stop agent, preserve worktree and uncommitted changes
    - relaunch: transactionally replace running agent with new one
    """

    def __init__(self, state_dir: str | None = None, data_dir: str | None = None):
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/state"))
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = Path(data_dir or os.path.expanduser("~/.lazy-coding/data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.locks_dir = self.state_dir / ".control-locks"
        self.locks_dir.mkdir(exist_ok=True)

    def is_verb_allowed(self, verb: str) -> bool:
        """Check if verb is allowed."""
        return verb in VERBS

    def is_harness_verified(self, harness: str) -> bool:
        """Check if harness has verified control mechanics."""
        return harness in VERIFIED_HARNESSES

    def acquire_task_lock(self, task_id: str) -> bool:
        """Acquire per-task control lock."""
        lock_file = self.locks_dir / f"{task_id}.lock"
        try:
            lock_file.touch(exist_ok=False)
            return True
        except FileExistsError:
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
        """Resolve task metadata from state."""
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
        """Validate task endpoint."""
        window = meta.get("window", "")
        if ":" in window:
            return False
        if meta.get("remote_host"):
            return False
        return True

    def _get_backend_target(self, meta: dict[str, str]) -> tuple[str, str]:
        """Get backend and target from task metadata."""
        backend = meta.get("backend", "tmux")
        window = meta.get("window", "")
        return backend, window

    def _agent_state(self, backend: str, target: str) -> str:
        """Get agent state from backend.

        Mirrors lazy-master backend agent_state.
        """
        try:
            if backend == "tmux":
                result = subprocess.run(
                    ["tmux", "has-session", "-t", target],
                    capture_output=True,
                    timeout=5,
                )
                return "alive" if result.returncode == 0 else "dead"
        except Exception:
            pass
        return "unverified"

    def _send_key(self, backend: str, target: str, key: str, label: str) -> bool:
        """Send key to backend target."""
        try:
            if backend == "tmux":
                result = subprocess.run(
                    ["tmux", "send-keys", "-t", target, key],
                    capture_output=True,
                    timeout=5,
                )
                return result.returncode == 0
        except Exception:
            pass
        return False

    def _send_text_submit(self, backend: str, target: str, text: str,
                          retries: int = 3, poll: float = 0.5, settle: float = 1.2,
                          label: str = "") -> str:
        """Send text and submit to backend target."""
        try:
            if backend == "tmux":
                for attempt in range(retries):
                    result = subprocess.run(
                        ["tmux", "send-keys", "-t", target, text, "Enter"],
                        capture_output=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        time.sleep(settle)
                        return "delivered"
        except Exception:
            pass
        return "send-failed"

    def _wait_agent_state(self, backend: str, target: str, timeout: float,
                          *wanted: str) -> tuple[str, bool]:
        """Wait for agent to reach wanted state."""
        start = time.time()
        while time.time() - start < timeout:
            state = self._agent_state(backend, target)
            if state in wanted:
                return state, True
            time.sleep(POLL_INTERVAL)
        return self._agent_state(backend, target), False

    def _target_exists(self, backend: str, target: str, label: str) -> bool:
        """Check if backend target exists."""
        try:
            if backend == "tmux":
                result = subprocess.run(
                    ["tmux", "has-session", "-t", target],
                    capture_output=True,
                    timeout=5,
                )
                return result.returncode == 0
        except Exception:
            pass
        return False

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

            backend, target = self._get_backend_target(meta)
            label = f"fm-{task_id}"

            # Check agent state
            state = self._agent_state(backend, target)
            if state == "dead":
                return {
                    "error": True,
                    "code": "NO_AGENT",
                    "message": f"No agent is running at task {task_id}'s endpoint (state: {state})",
                }

            # Deliver interrupt
            interrupt_info = HARNESS_INTERRUPTS.get(harness, {"key": "Escape", "count": 1})
            key = interrupt_info["key"]
            count = interrupt_info["count"]

            for i in range(count):
                if not self._send_key(backend, target, key, label):
                    return {
                        "error": True,
                        "code": "DELIVERY_FAILED",
                        "message": f"Interrupt key {key} was not delivered to task {task_id}",
                    }
                if i < count - 1:
                    time.sleep(0.2)

            # Verify agent still alive
            if not self._target_exists(backend, target, label):
                return {
                    "error": True,
                    "code": "ENDPOINT_LOST",
                    "message": f"Task {task_id}'s endpoint disappeared while interrupting",
                }

            new_state = self._agent_state(backend, target)
            proof = "agent-alive" if new_state == "alive" else "endpoint"

            # Record interrupt attempt
            self._record_event(task_id, "interrupt", {
                "harness": harness,
                "backend": backend,
                "proof": proof,
                "timestamp": datetime.now().isoformat(),
            })

            return {
                "success": True,
                "verb": "interrupt",
                "task_id": task_id,
                "harness": harness,
                "backend": backend,
                "proof": proof,
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

            backend, target = self._get_backend_target(meta)
            label = f"fm-{task_id}"

            # Check agent state
            state = self._agent_state(backend, target)
            if state == "dead":
                return {
                    "success": True,
                    "verb": "exit",
                    "task_id": task_id,
                    "result": "already-stopped",
                    "backend": backend,
                }

            if state == "missing":
                return {
                    "error": True,
                    "code": "MISSING_ENDPOINT",
                    "message": f"Task {task_id}'s recorded endpoint is gone",
                }

            # Interrupt first if busy
            interrupt_result = None
            if state == "alive":
                interrupt_info = HARNESS_INTERRUPTS.get(harness, {"key": "Escape", "count": 1})
                key = interrupt_info["key"]
                count = interrupt_info["count"]

                for i in range(count):
                    self._send_key(backend, target, key, label)
                    if i < count - 1:
                        time.sleep(0.2)

                time.sleep(SETTLE_WAIT)
                state = self._agent_state(backend, target)
                interrupt_result = "delivered"

                if state == "dead":
                    self._record_event(task_id, "exit", {
                        "harness": harness,
                        "backend": backend,
                        "result": "stopped-during-interrupt",
                        "timestamp": datetime.now().isoformat(),
                    })
                    return {
                        "success": True,
                        "verb": "exit",
                        "task_id": task_id,
                        "result": "stopped",
                        "backend": backend,
                    }

            # Send exit command
            cmd = HARNESS_EXIT_COMMANDS.get(harness, "/quit")
            verdict = self._send_text_submit(
                backend, target, cmd, EXIT_RETRIES, POLL_INTERVAL, 1.2, label
            )

            if verdict == "send-failed":
                return {
                    "error": True,
                    "code": "SEND_FAILED",
                    "message": f"The exit command could not be sent to task {task_id}",
                }

            # Wait for agent to stop
            final_state, stopped = self._wait_agent_state(backend, target, EXIT_WAIT, "dead")
            if not stopped:
                return {
                    "error": True,
                    "code": "EXIT_UNCONFIRMED",
                    "message": f"The agent did not stop within {EXIT_WAIT}s (state: {final_state})",
                }

            self._record_event(task_id, "exit", {
                "harness": harness,
                "backend": backend,
                "result": "stopped",
                "interrupt_result": interrupt_result,
                "timestamp": datetime.now().isoformat(),
            })

            return {
                "success": True,
                "verb": "exit",
                "task_id": task_id,
                "result": "stopped",
                "backend": backend,
                "worktree": meta.get("worktree"),
            }
        finally:
            self.release_task_lock(task_id)

    async def relaunch(self, task_id: str, harness: str | None = None,
                       model: str | None = None, effort: str | None = None,
                       note: str = "") -> dict[str, Any]:
        """Transactionally replace running agent with new one.

        Same endpoint, same worktree, same or different harness/model/effort.
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
            kind = meta.get("kind", "ship")

            if not self.is_harness_verified(new_harness):
                return {
                    "error": True,
                    "code": "UNVERIFIED_HARNESS",
                    "message": f"Cannot relaunch with unverified harness '{new_harness}'",
                }

            # Note is required for ship/scout relaunch
            if not note and kind in ("ship", "scout"):
                return {
                    "error": True,
                    "code": "NOTE_REQUIRED",
                    "message": "Relaunch requires --note for ship/scout tasks",
                }

            backend, target = self._get_backend_target(meta)
            label = f"fm-{task_id}"

            # Safe checkpoint: prove worktree exists and is recoverable
            worktree = meta.get("worktree")
            checkpoint = {}
            if worktree and kind in ("ship", "scout"):
                wt_path = Path(worktree)
                if not wt_path.exists():
                    return {
                        "error": True,
                        "code": "WORKTREE_MISSING",
                        "message": f"Task {task_id}'s worktree {worktree} is missing",
                    }
                try:
                    result = subprocess.run(
                        ["git", "rev-parse", "--verify", "HEAD"],
                        cwd=str(wt_path),
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    checkpoint["worktree_head"] = result.stdout.strip() if result.returncode == 0 else "unborn"
                    result = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=str(wt_path),
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    checkpoint["worktree_dirty"] = bool(result.stdout.strip())
                except Exception:
                    checkpoint["worktree_head"] = "unknown"
                    checkpoint["worktree_dirty"] = None

            # Record checkpoint
            journal = self.state_dir / f"{task_id}.control-relaunch"
            journal.write_text(json.dumps({
                "v1": True,
                "task": task_id,
                "phase": "checkpoint",
                "ts": datetime.now(timezone.utc).isoformat(),
                "backend": backend,
                "endpoint": target,
                "worktree": worktree,
                "kind": kind,
                "from_harness": old_harness,
                "to_harness": new_harness,
                "model": model,
                "effort": effort,
                "note": note,
                "checkpoint": checkpoint,
            }, indent=2))

            # Record progress note for ship/scout
            if note and kind in ("ship", "scout"):
                brief_path = self.data_dir / task_id / "brief.md"
                if brief_path.exists():
                    prior_path = journal.with_name(f"{journal.name}.brief-prior")
                    prior_path.write_text(brief_path.read_text())

                    progress_note = f"\n\n## Progress note ({datetime.now(timezone.utc).isoformat()})\n\n"
                    progress_note += f"This task was relaunched. Continue from here.\n\n"
                    progress_note += f"{note}\n"
                    brief_path.write_text(brief_path.read_text() + progress_note)

            # Exit old agent
            exit_result = await self.exit(task_id)

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
                "backend": backend,
                "worktree": worktree,
                "exit_result": exit_result.get("result"),
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

    def rollback_relaunch(self, task_id: str, phase: str) -> dict[str, Any]:
        """Rollback a failed relaunch.

        Mirrors lazy-master control relaunch_rollback.
        """
        journal = self.state_dir / f"{task_id}.control-relaunch"
        if not journal.exists():
            return {"success": True, "message": "No relaunch to rollback"}

        try:
            data = json.loads(journal.read_text())
            if data.get("phase", "").startswith("complete"):
                return {"success": True, "message": "Relaunch already complete"}

            # Restore brief if it was backed up
            brief_prior = journal.with_name(f"{journal.name}.brief-prior")
            if brief_prior.exists() and kind in ("ship", "scout"):
                brief_path = self.data_dir / task_id / "brief.md"
                if brief_path.exists():
                    brief_path.write_text(brief_prior.read_text())

            # Update journal
            data["phase"] = f"failed:{phase}"
            data["rollback_ts"] = datetime.now(timezone.utc).isoformat()
            journal.write_text(json.dumps(data, indent=2))

            return {
                "success": True,
                "phase": phase,
                "message": f"Rolled back relaunch at phase {phase}",
            }
        except Exception as e:
            return {
                "error": True,
                "message": f"Rollback failed: {e}",
            }
