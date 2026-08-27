"""lazy-master session - Session management.

Mirrors lazy-master's session start: session lock, bootstrap, wake queue,
fleet-state digest, context digest, and supervision instructions.

Key concepts from lazy-master:
- Per-home session lock acquisition before anything mutates state
- Bootstrap checks (tool/version, worktree-tangle, harness override)
- Wake queue presentation and acknowledgement
- Fleet-state digest from *.meta files
- Context digest from data/*.md files
- Supervision instructions for detected harness
- Read-once contract
"""

import os
import json
import time
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
import uuid


class Session:
    """Session with lock and lifecycle."""

    def __init__(self, id: str, status: str = "active"):
        self.id = id
        self.status = status
        self.created = datetime.now().isoformat()
        self.lock_acquired = False
        self.digest_generated = False


# Read-once contract text
READ_ONCE_CONTRACT = """
## Read-Once Contract

The digest below is this turn's startup and recovery input.
Read it once and trust it as this turn's authoritative fleet state.

Do not separately re-read the context, backlog, metadata, or bulk status
inputs it just printed unless:
- A source was reported absent or corrupt
- Older history is specifically needed
- A targeted workflow must inspect before writing

An ABSENT operator, shared-operator, lazy-master2, or learnings file means
the lazy-coding repo's built-in defaults.
"""


class SessionManager:
    """Session management.

    Mirrors lazy-master's session start:
    - Acquires per-home session lock first
    - Bootstrap checks
    - Wake queue presentation
    - Fleet-state digest
    - Context digest
    - Supervision instructions
    - Read-once contract
    """

    def __init__(self, state_dir: str | None = None, data_dir: str | None = None):
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/state"))
        self.data_dir = Path(data_dir or os.path.expanduser("~/.lazy-coding/data"))
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file = self.state_dir / ".session.lock"
        self.current_session: Session | None = None

    def acquire_lock(self, timeout: float = 5.0) -> dict[str, Any]:
        """Acquire per-home session lock."""
        if self.lock_file.exists():
            age = time.time() - self.lock_file.stat().st_mtime
            if age < 3600:
                return {
                    "success": False,
                    "error": "lock_held",
                    "message": "Another session is active. Check state/.session.lock",
                }
            self.lock_file.unlink(missing_ok=True)

        session_id = str(uuid.uuid4())[:8]
        lock_data = {
            "session_id": session_id,
            "pid": os.getpid(),
            "acquired": datetime.now().isoformat(),
        }
        self.lock_file.write_text(json.dumps(lock_data))

        self.current_session = Session(id=session_id)
        self.current_session.lock_acquired = True

        return {
            "success": True,
            "session_id": session_id,
        }

    def release_lock(self) -> None:
        """Release session lock."""
        self.lock_file.unlink(missing_ok=True)
        if self.current_session:
            self.current_session.lock_acquired = False

    def bootstrap(self) -> dict[str, Any]:
        """Run bootstrap checks."""
        checks = []

        # Check git availability
        try:
            import subprocess
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                checks.append({
                    "check": "git",
                    "status": "missing",
                    "action": "Install git",
                })
        except Exception:
            checks.append({
                "check": "git",
                "status": "missing",
                "action": "Install git",
            })

        # Check Python availability
        try:
            import subprocess
            result = subprocess.run(
                ["python", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                checks.append({
                    "check": "python",
                    "status": "missing",
                    "action": "Install Python",
                })
        except Exception:
            checks.append({
                "check": "python",
                "status": "missing",
                "action": "Install Python",
            })

        # Check worktree tangle
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                if branch != "main":
                    checks.append({
                        "check": "worktree_tangle",
                        "status": "warning",
                        "branch": branch,
                        "action": f"You are on branch '{branch}', not 'main'",
                    })
        except Exception:
            pass

        return {
            "success": True,
            "checks": checks,
            "all_passed": len(checks) == 0,
        }

    def drain_wakes(self) -> list[dict[str, Any]]:
        """Drain the wake queue."""
        wake_queue = self.state_dir / ".wake-queue"
        if not wake_queue.exists():
            return []

        wakes = []
        with open(wake_queue, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 5:
                    wakes.append({
                        "epoch": int(parts[0]),
                        "seq": int(parts[1]),
                        "kind": parts[2],
                        "key": parts[3],
                        "payload": parts[4],
                    })

        return wakes

    def acknowledge_wakes(self) -> None:
        """Acknowledge all drained wakes."""
        wake_queue = self.state_dir / ".wake-queue"
        if wake_queue.exists():
            wake_queue.unlink()

    def fleet_digest(self) -> dict[str, Any]:
        """Generate fleet-state digest."""
        tasks = []
        for meta_file in self.state_dir.glob("*.meta"):
            if meta_file.is_file():
                task_id = meta_file.stem
                try:
                    with open(meta_file, "r") as f:
                        meta = {}
                        for line in f:
                            if "=" in line:
                                key, _, value = line.partition("=")
                                meta[key.strip()] = value.strip()
                    tasks.append({
                        "id": task_id,
                        **meta,
                    })
                except Exception:
                    pass

        for task in tasks:
            status_file = self.state_dir / f"{task['id']}.status"
            if status_file.exists():
                try:
                    with open(status_file, "r") as f:
                        lines = f.readlines()
                        task["status_tail"] = [l.strip() for l in lines[-5:]]
                except Exception:
                    task["status_tail"] = []

        return {
            "tasks": tasks,
            "total": len(tasks),
            "afk": (self.state_dir / ".afk").exists(),
        }

    def context_digest(self) -> dict[str, Any]:
        """Generate context digest."""
        digest = {}

        for md_file in ["projects.md", "secondmates.md", "captain.md",
                        "captain-shared.md", "learnings.md"]:
            file_path = self.data_dir / md_file
            if file_path.exists():
                try:
                    with open(file_path, "r") as f:
                        digest[md_file] = f.read()
                except Exception:
                    digest[md_file] = None
            else:
                digest[md_file] = None

        return digest

    def supervision_instructions(self, harness: str = "claude",
                                 afk: bool = False,
                                 x_mode: bool = False,
                                 queue_pending: bool = False,
                                 repair_line: bool = False) -> dict[str, Any]:
        """Generate supervision instructions for detected harness.

        Mirrors lazy-master bin/supervision-instructions.sh.
        """
        instructions = {
            "harness": harness,
            "protocol": self._get_harness_protocol(harness),
            "afk": afk,
            "x_mode": x_mode,
            "queue_pending": queue_pending,
        }

        if repair_line:
            instructions["repair"] = self._get_repair_line(harness, afk, x_mode)

        return instructions

    def _get_harness_protocol(self, harness: str) -> str:
        """Get supervision protocol for harness."""
        protocols = {
            "claude": (
                "For Claude: the watcher runs between turns. "
                "A fresh beacon with no live watcher is healthy mid-turn. "
                "Turn-end hooks invoke the turn-end guard."
            ),
            "codex": (
                "For Codex: the watcher runs persistently. "
                "A live watcher with fresh beacon is required."
            ),
            "opencode": (
                "For OpenCode: the watcher runs persistently. "
                "A live watcher with fresh beacon is required."
            ),
            "pi": (
                "For Pi: the extension tears down and respawns the watcher "
                "on every actionable wake. A fresh beacon with unheld lock is healthy "
                "while the Pi session owns continuity."
            ),
            "grok": (
                "For Grok: the watcher runs persistently. "
                "A live watcher with fresh beacon is required."
            ),
            "cursor": (
                "For Cursor: the watcher runs persistently. "
                "A live watcher with fresh beacon is required."
            ),
        }
        return protocols.get(harness, "Unknown harness protocol")

    def _get_repair_line(self, harness: str, afk: bool, x_mode: bool) -> str:
        """Get repair line for supervision instructions."""
        if afk:
            return "Away mode is active. The daemon owns supervision."
        if x_mode:
            return "X-mode relay polling needs supervision. Start the watcher."
        return "Tasks in flight, no live watcher. Start the watcher: lazy-master watcher start"

    def generate_digest(self) -> dict[str, Any]:
        """Generate complete session digest."""
        if not self.current_session or not self.current_session.lock_acquired:
            return {
                "success": False,
                "error": "no_lock",
                "message": "Session lock not acquired",
            }

        # Bootstrap
        bootstrap = self.bootstrap()

        # Wake queue
        wakes = self.drain_wakes()

        # Fleet digest
        fleet = self.fleet_digest()

        # Context digest
        context = self.context_digest()

        # Detect harness
        harness = "claude"

        # Supervision instructions
        supervision = self.supervision_instructions(
            harness=harness,
            afk=(self.state_dir / ".afk").exists(),
            queue_pending=bool(wakes),
        )

        self.current_session.digest_generated = True

        return {
            "success": True,
            "session_id": self.current_session.id,
            "bootstrap": bootstrap,
            "read_once_contract": READ_ONCE_CONTRACT,
            "supervision": supervision,
            "wake_queue": wakes,
            "fleet": fleet,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }

    def status(self) -> dict[str, Any]:
        """Get session status."""
        return {
            "active": self.current_session is not None and self.current_session.lock_acquired,
            "session_id": self.current_session.id if self.current_session else None,
            "lock_exists": self.lock_file.exists(),
        }
