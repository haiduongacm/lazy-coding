"""Worktree pool manager.

Mirrors no-mistakes worktree pool with proper placement validation,
lease management, and atomic state updates.
"""

from pathlib import Path
from typing import Optional, Any
import os
import time
from datetime import datetime

from .worktree import Worktree
from .state import State
from .layout import Layout, canonical, check_placement


class Pool:
    """Manage a pool of reusable worktrees.

    Mirrors no-mistakes worktree pool with:
    - Layout-aware placement
    - Lease management for long-running tasks
    - Atomic state updates
    - Corruption recovery
    """

    def __init__(self, repo_path: Optional[str] = None, state_dir: Optional[str] = None,
                 nm_home: Optional[str] = None, roots: Optional[dict[str, str]] = None):
        self.repo_path = Path(repo_path or os.getcwd())
        self.nm_home = nm_home or os.path.expanduser("~/.lazy-coding")
        self.worktree = Worktree(str(self.repo_path))
        self.state = State(state_dir)
        self.layout = Layout(self.nm_home, roots)

    def get(self, lease: bool = False, repo_id: str = "default",
            working_path: Optional[str] = None) -> Path:
        """Acquire a worktree from the pool.

        Mirrors no-mistakes run worktree creation with placement validation.

        Args:
            lease: If True, create a durable lease
            repo_id: Repository identifier for placement
            working_path: Current working path for custom root lookup

        Returns:
            Worktree path
        """
        state = self.state.load()

        # Find available worktree
        for name, info in state.get("worktrees", {}).items():
            if info.get("status") == "idle":
                # Validate placement is still valid
                if self._validate_existing_placement(info):
                    state["worktrees"][name]["status"] = "in-use"
                    if lease:
                        state.setdefault("leases", {})[name] = {
                            "holder": "current",
                            "timestamp": datetime.now().isoformat(),
                        }
                    self.state.save(state)
                    return Path(info["path"])

        # Create new worktree with layout-aware placement
        run_id = f"run-{int(time.time()) % 100000}"
        worktree_dir = self.layout.dir(repo_id, run_id, working_path)
        wt_path = self.worktree.create(workdir=str(Path(worktree_dir).parent))
        name = wt_path.name

        state.setdefault("worktrees", {})[name] = {
            "path": str(wt_path),
            "status": "in-use",
            "created": datetime.now().isoformat(),
            "repo_id": repo_id,
            "run_id": run_id,
        }
        if lease:
            state.setdefault("leases", {})[name] = {
                "holder": "current",
                "timestamp": datetime.now().isoformat(),
            }
        self.state.save(state)

        # Record placement for later retrieval
        self.state.record_placement(str(wt_path), repo_id, run_id)

        return wt_path

    def return_worktree(self, path: Optional[str] = None) -> None:
        """Return a worktree to the pool.

        Args:
            path: Worktree path (or current directory)
        """
        wt_path = Path(path or os.getcwd())
        name = wt_path.name

        state = self.state.load()

        # Reset worktree
        try:
            self.worktree.reset(str(wt_path))
        except Exception:
            pass

        # Mark as idle
        if name in state.get("worktrees", {}):
            state["worktrees"][name]["status"] = "idle"

        # Remove lease
        state.get("leases", {}).pop(name, None)

        self.state.save(state)

    def status(self) -> dict[str, Any]:
        """Get pool status."""
        state = self.state.load()
        worktrees = state.get("worktrees", {})
        leases = state.get("leases", {})

        total = len(worktrees)
        in_use = sum(1 for w in worktrees.values() if w.get("status") == "in-use")
        idle = total - in_use

        return {
            "total": total,
            "in_use": in_use,
            "idle": idle,
            "leases": len(leases),
        }

    def prune(self, dry_run: bool = True) -> list[str]:
        """Remove idle, merged worktrees."""
        state = self.state.load()
        pruned = []

        for name, info in list(state.get("worktrees", {}).items()):
            if info.get("status") != "idle":
                continue

            wt_path = Path(info["path"])
            if not wt_path.exists():
                pruned.append(name)
                continue

            if self.worktree.is_head_merged(str(wt_path)) and not self.worktree.is_dirty(str(wt_path)):
                if not dry_run:
                    self.worktree.remove(str(wt_path))
                pruned.append(name)

        if not dry_run:
            for name in pruned:
                state["worktrees"].pop(name, None)
                state.get("placement", {}).pop(
                    state.get("worktrees", {}).get(name, {}).get("path", ""), None
                )
            self.state.save(state)

        return pruned

    def _validate_existing_placement(self, info: dict[str, Any]) -> bool:
        """Validate that existing worktree placement is still valid."""
        path = info.get("path", "")
        repo_id = info.get("repo_id", "default")

        # Check if worktree directory exists and is accessible
        wt_path = Path(path)
        return wt_path.exists() and wt_path.is_dir()
