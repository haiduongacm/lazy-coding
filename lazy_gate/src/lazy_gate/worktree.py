"""Gate worktree management.

Mirrors no-mistakes worktree creation for validation.
"""

import subprocess
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional


class Worktree:
    """Disposable worktree for gate validation.

    Creates temporary worktrees for running validation without
    affecting the main working directory.
    """

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = Path(repo_path or os.getcwd())

    def _run_git(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        """Run git command."""
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result

    def create(self, branch: Optional[str] = None) -> Path:
        """Create a disposable worktree for validation.

        Args:
            branch: Optional branch name

        Returns:
            Path to created worktree
        """
        if not branch:
            branch = f"gate-{uuid.uuid4().hex[:8]}"

        # Create temporary directory
        tmp_dir = Path(tempfile.mkdtemp(prefix="lazy-gate-"))

        # Create worktree
        result = self._run_git(
            "worktree", "add", "--detach", "-b", branch, str(tmp_dir)
        )

        return tmp_dir

    def remove(self, worktree_path: str) -> None:
        """Remove a disposable worktree."""
        self._run_git("worktree", "remove", str(worktree_path), "--force", check=False)

    def list_worktrees(self) -> list[dict]:
        """List all worktrees."""
        result = self._run_git("worktree", "list", "--porcelain", check=False)
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
