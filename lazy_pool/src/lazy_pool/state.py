"""Pool state management with atomic writes."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from datetime import datetime


class State:
    """Atomic state management for worktree pool.

    Mirrors no-mistakes state management with corruption recovery
    and atomic writes.
    """

    def __init__(self, state_dir: str | None = None):
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/pools"))
        self.state_file = self.state_dir / "state.json"
        self.lock_file = self.state_dir / ".lock"
        self.ensure_dir()

    def ensure_dir(self) -> None:
        """Ensure state directory exists."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        """Load state from disk with corruption recovery."""
        if not self.state_file.exists():
            return {"worktrees": {}, "leases": {}, "placement": {}}

        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # Corrupted state, start fresh
            return {"worktrees": {}, "leases": {}, "placement": {}}

    def save(self, state: dict[str, Any]) -> None:
        """Save state atomically using temp file + rename."""
        # Write to temp file first
        tmp_file = self.state_file.with_suffix(".tmp")
        with open(tmp_file, "w") as f:
            json.dump(state, f, indent=2)

        # Atomic rename (on POSIX; on Windows it's not truly atomic but best effort)
        tmp_file.replace(self.state_file)

    def acquire_lock(self, timeout: float = 5.0) -> bool:
        """Acquire file lock with timeout."""
        start = datetime.now().timestamp()
        while datetime.now().timestamp() - start < timeout:
            try:
                self.lock_file.touch(exist_ok=False)
                return True
            except FileExistsError:
                import time
                time.sleep(0.1)
        return False

    def release_lock(self) -> None:
        """Release file lock."""
        if self.lock_file.exists():
            self.lock_file.unlink()

    def record_placement(self, worktree_path: str, repo_id: str, run_id: str) -> None:
        """Record worktree placement for later retrieval."""
        state = self.load()
        state.setdefault("placement", {})[worktree_path] = {
            "repo_id": repo_id,
            "run_id": run_id,
            "recorded_at": datetime.now().isoformat(),
        }
        self.save(state)

    def get_placement(self, worktree_path: str) -> dict[str, Any] | None:
        """Get recorded placement for a worktree."""
        state = self.load()
        return state.get("placement", {}).get(worktree_path)
