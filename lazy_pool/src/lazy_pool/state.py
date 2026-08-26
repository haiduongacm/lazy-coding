"""Pool state management with atomic writes."""

import json
import os
from pathlib import Path


class State:
    """Atomic state management for worktree pool."""

    def __init__(self, state_dir=None):
        self.state_dir = Path(state_dir or os.path.expanduser("~/.lazy-coding/pools"))
        self.state_file = self.state_dir / "state.json"
        self.lock_file = self.state_dir / ".lock"
        self.ensure_dir()

    def ensure_dir(self):
        """Ensure state directory exists."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def load(self):
        """Load state from disk with corruption recovery."""
        if not self.state_file.exists():
            return {"worktrees": {}, "leases": {}}

        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # Corrupted state, start fresh
            return {"worktrees": {}, "leases": {}}

    def save(self, state):
        """Save state atomically."""
        # Write to temp file first
        tmp_file = self.state_file.with_suffix(".tmp")
        with open(tmp_file, "w") as f:
            json.dump(state, f, indent=2)

        # Atomic rename
        tmp_file.replace(self.state_file)

    def acquire_lock(self, timeout=5):
        """Acquire file lock."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            try:
                self.lock_file.touch(exist_ok=False)
                return True
            except FileExistsError:
                time.sleep(0.1)
        return False

    def release_lock(self):
        """Release file lock."""
        if self.lock_file.exists():
            self.lock_file.unlink()
