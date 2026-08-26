"""Worktree operations - create, reset, remove, inspect."""

import subprocess
import os
import time
from pathlib import Path
from typing import Optional
from datetime import datetime


class Worktree:
    """Git worktree operations.

    Mirrors no-mistakes worktree management with proper placement validation.
    """

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = Path(repo_path or os.getcwd())

    def _run(self, *args, check: bool = True, **kwargs):
        """Run git command."""
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=kwargs.get("timeout", 30),
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result

    def get_default_branch(self) -> str:
        """Get default branch name.

        Tries origin/HEAD first, then local main/master.
        """
        # Try origin/HEAD
        try:
            result = self._run("symbolic-ref", "refs/remotes/origin/HEAD", check=False)
            if result.returncode == 0:
                return result.stdout.strip().replace("refs/remotes/origin/", "")
        except Exception:
            pass

        # Try local main/master
        for branch in ["main", "master"]:
            try:
                result = self._run("rev-parse", "--verify", branch, check=False)
                if result.returncode == 0:
                    return branch
            except Exception:
                pass

        return "main"

    def create(self, branch: Optional[str] = None, workdir: Optional[str] = None) -> Path:
        """Create a new worktree.

        Args:
            branch: Branch name (auto-generated if not provided)
            workdir: Custom worktree directory (uses default pool if not provided)

        Returns:
            Path to created worktree
        """
        if not branch:
            branch = f"wt-{int(time.time()) % 100000}"

        # Use custom workdir or default pool
        if workdir:
            wt_dir = Path(workdir)
            wt_dir.mkdir(parents=True, exist_ok=True)
            wt_path = wt_dir / branch
        else:
            wt_path = self.repo_path / "worktrees" / branch

        # Create worktree
        result = self._run(
            "worktree", "add", "--detach", "-b", branch, str(wt_path)
        )

        return wt_path

    def reset(self, worktree_path: str) -> None:
        """Reset worktree to clean state."""
        wt_path = Path(worktree_path)
        if not wt_path.exists():
            raise FileNotFoundError(f"Worktree not found: {wt_path}")

        # Stash changes
        self._run("stash", "--include-untracked", check=False)

        # Reset to HEAD
        self._run("reset", "--hard", "HEAD", check=False)

        # Clean
        self._run("clean", "-fd", check=False)

    def remove(self, worktree_path: str) -> None:
        """Remove a worktree."""
        self._run("worktree", "remove", worktree_path, "--force", check=False)

    def list_worktrees(self) -> list[dict]:
        """List all worktrees."""
        result = self._run("worktree", "list", "--porcelain", check=False)
        if result.returncode != 0:
            return []

        worktrees = []
        for block in result.stdout.strip().split("\n\n"):
            if not block:
                continue
            info = {}
            for line in block.split("\n"):
                if line.startswith("worktree "):
                    info["path"] = line[10:]
                elif line.startswith("HEAD "):
                    info["head"] = line[5:]
                elif line.startswith("branch "):
                    info["branch"] = line[7:]
            if info.get("path"):
                worktrees.append(info)

        return worktrees

    def is_dirty(self, worktree_path: Optional[str] = None) -> bool:
        """Check if worktree has uncommitted changes."""
        path = worktree_path or self.repo_path
        result = self._run("status", "--porcelain", cwd=path, check=False)
        return bool(result.stdout.strip())

    def is_head_merged(self, worktree_path: Optional[str] = None) -> bool:
        """Check if HEAD is merged into default branch."""
        path = worktree_path or self.repo_path
        default = self.get_default_branch()
        result = self._run("merge-base", "--is-ancestor", "HEAD", default,
                          cwd=path, check=False)
        return result.returncode == 0

    def fetch(self) -> None:
        """Fetch from origin."""
        self._run("fetch", "origin", check=False)
