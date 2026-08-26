"""Worktree operations - create, reset, remove, inspect."""

import subprocess
from pathlib import Path


class Worktree:
    """Git worktree operations."""

    def __init__(self, repo_path=None):
        self.repo_path = repo_path or Path.cwd()

    def _run(self, *args, **kwargs):
        """Run git command."""
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result

    def get_default_branch(self):
        """Get default branch name."""
        # Try origin/HEAD
        result = self._run("symbolic-ref", "refs/remotes/origin/HEAD")
        if result.returncode == 0:
            return result.stdout.strip().replace("refs/remotes/origin/", "")

        # Try local main/master
        for branch in ["main", "master"]:
            result = self._run("rev-parse", "--verify", branch)
            if result.returncode == 0:
                return branch

        return "main"

    def create(self, branch=None):
        """Create a new worktree."""
        default = self.get_default_branch()
        branch = branch or f"wt-{id(self) % 10000}"

        result = self._run(
            "worktree", "add", "--detach", "-b", branch, "HEAD"
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create worktree: {result.stderr}")

        # Get worktree path
        result = self._run("worktree", "list", "--porcelain")
        lines = result.stdout.strip().split("\n\n")
        last_worktree = lines[-1] if lines else ""
        for line in last_worktree.split("\n"):
            if line.startswith("path "):
                return Path(line[6:])

        raise RuntimeError("Failed to get worktree path")

    def reset(self, worktree_path):
        """Reset worktree to clean state."""
        wt_path = Path(worktree_path)
        if not wt_path.exists():
            raise FileNotFoundError(f"Worktree not found: {wt_path}")

        # Stash changes
        self._run("stash", "--include-untracked")

        # Reset to HEAD
        self._run("reset", "--hard", "HEAD")

        # Clean
        self._run("clean", "-fd")

    def remove(self, worktree_path):
        """Remove a worktree."""
        self._run("worktree", "remove", str(worktree_path), "--force")

    def list(self):
        """List all worktrees."""
        result = self._run("worktree", "list", "--porcelain")
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

    def is_dirty(self, worktree_path=None):
        """Check if worktree has uncommitted changes."""
        path = worktree_path or self.repo_path
        result = self._run("status", "--porcelain")
        return bool(result.stdout.strip())

    def is_head_merged(self, worktree_path=None):
        """Check if HEAD is merged into default branch."""
        path = worktree_path or self.repo_path
        default = self.get_default_branch()
        result = self._run("merge-base", "--is-ancestor", "HEAD", default)
        return result.returncode == 0

    def fetch(self):
        """Fetch from origin."""
        self._run("fetch", "origin")
