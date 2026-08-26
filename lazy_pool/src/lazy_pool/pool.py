"""Worktree pool manager."""

from pathlib import Path
from .worktree import Worktree
from .state import State


class Pool:
    """Manage a pool of reusable worktrees."""

    def __init__(self, repo_path=None, state_dir=None):
        self.repo_path = Path(repo_path or Path.cwd())
        self.worktree = Worktree(self.repo_path)
        self.state = State(state_dir)

    def get(self, lease=False):
        """Acquire a worktree from the pool.

        Args:
            lease: If True, create a durable lease

        Returns:
            Worktree path
        """
        state = self.state.load()

        # Find available worktree
        for name, info in state.get("worktrees", {}).items():
            if info.get("status") == "idle":
                # Mark as in-use
                state["worktrees"][name]["status"] = "in-use"
                if lease:
                    state["leases"][name] = {
                        "holder": "current",
                        "timestamp": __import__("datetime").datetime.now().isoformat(),
                    }
                self.state.save(state)
                return Path(info["path"])

        # Create new worktree
        wt_path = self.worktree.create()
        name = wt_path.name

        state.setdefault("worktrees", {})[name] = {
            "path": str(wt_path),
            "status": "in-use",
            "created": __import__("datetime").datetime.now().isoformat(),
        }
        if lease:
            state.setdefault("leases", {})[name] = {
                "holder": "current",
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }
        self.state.save(state)

        return wt_path

    def return_worktree(self, path=None):
        """Return a worktree to the pool.

        Args:
            path: Worktree path (or current directory)
        """
        wt_path = Path(path or Path.cwd())
        name = wt_path.name

        state = self.state.load()

        # Reset worktree
        try:
            self.worktree.reset(wt_path)
        except Exception:
            pass

        # Mark as idle
        if name in state.get("worktrees", {}):
            state["worktrees"][name]["status"] = "idle"

        # Remove lease
        state.get("leases", {}).pop(name, None)

        self.state.save(state)

    def status(self):
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

    def prune(self, dry_run=True):
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

            if self.worktree.is_head_merged(wt_path) and not self.worktree.is_dirty(wt_path):
                if not dry_run:
                    self.worktree.remove(wt_path)
                pruned.append(name)

        if not dry_run:
            for name in pruned:
                state["worktrees"].pop(name, None)
            self.state.save(state)

        return pruned
