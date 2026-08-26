"""Gate worktree management."""

import subprocess
from pathlib import Path


class Worktree:
    """Disposable worktree for gate validation."""

    def __init__(self, repo_path=None):
        self.repo_path = Path(repo_path or Path.cwd())

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

    def create(self):
        """Create a disposable worktree for validation."""
        import tempfile
        import uuid

        tmp_dir = Path(tempfile.mkdtemp(prefix="lazy-gate-"))
        branch = f"gate-{uuid.uuid4().hex[:8]}"

        result = self._run("worktree", "add", "--detach", str(tmp_dir), "HEAD")
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create worktree: {result.stderr}")

        return tmp_dir

    def remove(self, worktree_path):
        """Remove a disposable worktree."""
        self._run("worktree", "remove", str(worktree_path), "--force")
